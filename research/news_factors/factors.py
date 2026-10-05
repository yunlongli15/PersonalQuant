# -*- coding: utf-8 -*-
"""候选新闻因子：定义 + 实现。

**设计约束**（来自 spec §六~§九、§二十、§二十五）

- 每个因子对应一个说得出口的经济含义，不是"再算一个计数"。
- 窗口一律按**交易日**（5 / 20 / 60），不是自然日 —— spec §八 明确要求。
  这与 STEP 5 那批因子（自然日窗口）不同，注册表里逐条标了 `window_unit`。
- 严格 PIT：T 日的因子只用到 `availability_time <= T` 的事件。
  事件的"日"按 availability 在 Asia/Shanghai 的日期定，
  盘后公告已经由上游推到次一交易日 09:30（docs/步骤5-新闻时点规则.md）。
- 只用结构化字段（类型/方向/严重度/时间/新颖性），**不用任何 NLP**。
- 给定 (as_of_date, symbol, 事件表) 必须能逐位复算 —— 无随机、无模型。

**流（stream）**：先把事件压成"每个交易日每个流一个计数"的日频面板，
再在这上面做窗口运算。流之间正交，因子只是流 + 窗口 + 聚合。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from .taxonomy import PROCEDURAL, SUBSTANTIVE

# ---------------------------------------------------------------------------
# 流：把 (theme, materiality, direction) 映射成日频计数
# ---------------------------------------------------------------------------

#: 主题 -> 流名。只有实测样本量够的主题才立流（见 reports 的 taxonomy 审计）。
THEME_STREAMS: Dict[str, str] = {
    "regulatory": "t_regulatory",
    "investigation": "t_investigation",
    "penalty": "t_penalty",
    "litigation": "t_litigation",
    "pledge": "t_pledge",
    "pledge_release": "t_pledge_release",
    "shareholder_reduce": "t_sh_reduce",
    "shareholder_increase": "t_sh_increase",
    "buyback": "t_buyback",
    "dividend": "t_dividend",
    "mna": "t_mna",
    "major_contract": "t_contract",
    "financing": "t_financing",
    "earnings": "t_earnings",
    "equity_incentive": "t_equity_incentive",
    "related_party": "t_related_party",
    "guarantee": "t_guarantee",
    "debt_default": "t_debt_default",
    "production_change": "t_production_change",
}

#: 所有流名（供审计与注册表引用）
ALL_STREAMS: List[str] = (
    ["n_all", "n_substantive", "n_procedural", "n_unknown",
     "n_neg", "n_pos", "n_neu", "sev_neg", "sev_pos"]
    + list(THEME_STREAMS.values())
    + ["n_types"]           # 当日出现的事件类型数（用于"新类型"类因子）
)


def streams_from_events(ev: pd.DataFrame) -> pd.DataFrame:
    """事件表 -> 日频流表（long：symbol / date / 各流）。

    要求 ev 已有 taxonomy 列：`theme` / `materiality` / `dir_hint` /
    `severity` / `sdate`（availability 的交易日）。
    """
    e = ev
    g = e.groupby(["symbol", "sdate"], sort=False)
    parts = {
        "n_all": g.size(),
        "n_substantive": e[e["materiality"] == SUBSTANTIVE]
        .groupby(["symbol", "sdate"], sort=False).size(),
        "n_procedural": e[e["materiality"] == PROCEDURAL]
        .groupby(["symbol", "sdate"], sort=False).size(),
        "n_unknown": e[e["materiality"] == "unknown"]
        .groupby(["symbol", "sdate"], sort=False).size(),
        "n_neg": e[(e["dir_hint"] == "negative") &
                   (e["materiality"] == SUBSTANTIVE)]
        .groupby(["symbol", "sdate"], sort=False).size(),
        "n_pos": e[(e["dir_hint"] == "positive") &
                   (e["materiality"] == SUBSTANTIVE)]
        .groupby(["symbol", "sdate"], sort=False).size(),
        "n_neu": e[(e["dir_hint"] == "neutral") &
                   (e["materiality"] == SUBSTANTIVE)]
        .groupby(["symbol", "sdate"], sort=False).size(),
        "sev_neg": e[(e["dir_hint"] == "negative") &
                     (e["materiality"] == SUBSTANTIVE)]
        .groupby(["symbol", "sdate"], sort=False)["severity"].sum(),
        "sev_pos": e[(e["dir_hint"] == "positive") &
                     (e["materiality"] == SUBSTANTIVE)]
        .groupby(["symbol", "sdate"], sort=False)["severity"].sum(),
        "n_types": g["theme"].nunique(),
    }
    for theme, name in THEME_STREAMS.items():
        parts[name] = (e[e["theme"] == theme]
                       .groupby(["symbol", "sdate"], sort=False).size())
    out = pd.DataFrame(parts).fillna(0.0)
    out.index.names = ["symbol", "sdate"]
    return out.reset_index()


# ---------------------------------------------------------------------------
# 因子定义
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FactorSpec:
    name: str
    definition: str
    source_streams: List[str]
    window: int
    direction: str            # 预期符号：positive / negative / unknown
    hypothesis: str
    kind: str = "sum"         # sum | mean | ratio | zscore | first | streak
    status: str = "candidate"
    window_unit: str = "trading_days"
    #: 对照组标记：**预期没有 alpha**，用来证明检验本身能分辨真伪。
    #: 如果不设这种因子，整张 IC 表就没有"阴性对照"。
    control: bool = False


def _specs() -> List[FactorSpec]:
    S: List[FactorSpec] = []

    # ---- A. 负面重大事件（spec §七A）-----------------------------------
    for w in (5, 20, 60):
        S.append(FactorSpec(
            f"negative_event_count_{w}d",
            f"实质性负面事件数，过去 {w} 个交易日", ["n_neg"], w, "negative",
            "负面事件提高信息不确定性并压制短期估值，窗口内越多越负"))
    S.append(FactorSpec(
        "negative_event_severity_20d",
        "实质性负面事件的严重度之和（按 taxonomy 先验加权），20 日",
        ["sev_neg"], 20, "negative",
        "同样是一件事，立案调查与一般诉讼的冲击量级差一个数量级；"
        "按严重度加权的信息量高于简单计数"))
    for theme, nm in (("regulatory", "regulatory_negative_count_20d"),
                      ("litigation", "litigation_negative_count_20d"),
                      ("investigation", "investigation_count_20d"),
                      ("penalty", "penalty_count_20d"),
                      ("pledge", "pledge_risk_count_20d"),
                      ("shareholder_reduce",
                       "shareholder_reduction_count_20d")):
        S.append(FactorSpec(
            nm, f"{theme} 类事件数，20 日", [THEME_STREAMS[theme]], 20,
            "negative", f"{theme} 是具体风险来源，比混合计数更干净"))
    S.append(FactorSpec(
        "material_negative_count_20d",
        "剔除程序性公告后的负面事件数，20 日", ["n_neg"], 20, "negative",
        "**核心对照**：若 negative_event_count 的 IC 主要来自程序性公告，"
        "那么把程序性剔除后 IC 应显著下降；不下降才说明信号是真的",
        ))
    S.append(FactorSpec(
        "debt_default_count_20d", "债务违约/破产重整/冻结类事件数，20 日",
        ["t_debt_default"], 20, "negative",
        "存续性风险事件，预期是最强的单点负面冲击"))

    # ---- B. 正面重大事件（spec §七B）-----------------------------------
    for w in (5, 20, 60):
        S.append(FactorSpec(
            f"positive_event_count_{w}d",
            f"实质性正面事件数，过去 {w} 个交易日", ["n_pos"], w, "positive",
            "正面事件（增持/回购/中标/分红）是管理层与市场之间的正向信号"))
    for theme, nm in (("buyback", "repurchase_count_20d"),
                      ("shareholder_increase",
                       "shareholder_increase_count_20d"),
                      ("major_contract", "major_contract_count_20d"),
                      ("equity_incentive", "equity_incentive_count_20d")):
        S.append(FactorSpec(
            nm, f"{theme} 类事件数，20 日", [THEME_STREAMS[theme]], 20,
            "positive", f"{theme} 的正向含义比混合计数更明确"))

    # ---- C. 新闻异常强度（spec §七C、§十九）----------------------------
    S.append(FactorSpec(
        "news_intensity_20d", "实质性公告数 / 该股过去 120 日自身均值",
        ["n_substantive"], 20, "unknown",
        "相对自身历史的异常放量比绝对条数更能反映信息冲击；"
        "绝对条数在很大程度上只是公司规模与活跃度的代理", kind="ratio"))
    S.append(FactorSpec(
        "abnormal_news_intensity_20d",
        "实质性公告数的自身 z 分数（基线 120 日）",
        ["n_substantive"], 20, "unknown",
        "用自身历史标准化，消除公司间固定差异", kind="zscore"))

    # ---- D. 新闻新颖性（spec §七D、§十八）------------------------------
    S.append(FactorSpec(
        "first_negative_event_20d",
        "过去 180 日首次出现负面事件（0/1），20 日窗口内",
        ["n_neg"], 20, "negative",
        "**重点候选**：首次出现的负面事件信息量最大；"
        "第 10 次重复的边际信息接近于零。计数会把两者混为一谈",
        kind="first"))
    S.append(FactorSpec(
        "new_event_type_count_20d",
        "过去 180 日未出现过的主题数，20 日窗口内",
        ["n_types"], 20, "unknown",
        "新类型的公告意味着出现了此前没有的经营/治理维度"))

    # ---- E. 新闻新鲜度（spec §七E）------------------------------------
    S.append(FactorSpec(
        "weighted_negative_event_20d",
        "负面事件按 0.5^(龄/10交易日) 指数衰减加权",
        ["n_neg"], 20, "negative",
        "同样一条负面公告，昨天发生与 20 天前发生对当前定价的含义不同；"
        "权重公式取最简单可复现的指数衰减，不做参数搜索", kind="decay"))
    S.append(FactorSpec(
        "negative_event_days_20d",
        "窗口内**有**负面事件的天数（不是条数）",
        ["n_neg"], 20, "negative",
        "一天发 5 条和 5 天各发 1 条含义不同：后者说明风险在持续"))

    # ---- F. 正负平衡（spec §七F）--------------------------------------
    for w in (20, 60):
        S.append(FactorSpec(
            f"positive_negative_balance_{w}d",
            f"(正面数 - 负面数) / (正面数 + 负面数 + 1)，{w} 日",
            ["n_pos", "n_neg"], w, "positive",
            "净情绪方向；分母加 1 是拉普拉斯式平滑，"
            "避免无事件股票的 0/0", kind="balance"))
    S.append(FactorSpec(
        "negative_positive_ratio_20d",
        "负面数 / (正面数 + 1)，20 日", ["n_pos", "n_neg"], 20, "negative",
        "与 balance 互补：对负面更敏感的非对称刻画", kind="ratio2"))

    # ---- G. 风险持续性（spec §七G）------------------------------------
    S.append(FactorSpec(
        "negative_event_streak_60d",
        "截至 T 连续出现负面事件的最大天数（60 日窗口内）",
        ["n_neg"], 60, "negative",
        "连续暴露说明问题未解决，与单次冲击应当区分", kind="streak"))

    # ---- 阴性对照 ------------------------------------------------------
    S.append(FactorSpec(
        "procedural_count_20d",
        "程序性公告数（股东大会/章程/法律意见书/内控制度），20 日",
        ["n_procedural"], 20, "unknown",
        "**阴性对照**：行政流程公告按经济逻辑不该有预测力。"
        "它若拿到显著 IC，说明这套检验在捕风捉影，"
        "全表的结论都要打折", control=True))
    S.append(FactorSpec(
        "unknown_count_20d", "taxonomy 未能归类的公告数，20 日",
        ["n_unknown"], 20, "unknown",
        "第二个阴性对照：分类失败的残余不该携带信息", control=True))

    return S


FACTOR_SPECS: Dict[str, FactorSpec] = {s.name: s for s in _specs()}
