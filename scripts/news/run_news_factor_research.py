# -*- coding: utf-8 -*-
"""新闻因子研究：单因子 IC / 分层 / 子样本 / 跨期稳定性

    python scripts/news/run_news_factor_research.py [--factors a,b,c]

产出：
    data/derived/news/news_factor_daily.parquet   因子值（月度调仓网格）
    reports/news_factor_research.md               研究报告

**只做研究。** 不训练模型、不改 production_strategy、不动 S3_v1/S3_v2、
不碰 recommendation。研究结论只是"某个因子值得进下一个模型"，不是模型本身。

选择协议（先于结果写死，spec §二十一/§二十三）：
- 信号日：2018-01-01 ~ 2026-09-30 每周最后一个交易日（比月度多个 4 倍样本，
  且每周之间高度重叠，因此**不能**把 n 当独立样本数看待）；
- 选择只看 2018-2023（research+valid），2024-2026 单次报告；
- 因子方向不按 IC 正负翻转着挑 —— 注册表里的 `direction` 是先验写的，
  结果里照实报告「实际符号是否与先验一致」。
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd

from research.news_factors import engine as E
from research.news_factors.factors import (FACTOR_SPECS, streams_from_events)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUT_MD = PROJECT_ROOT / "reports" / "news_factor_research.md"

PERIODS = {"P1_2018_2020": ("2018-01-01", "2020-12-31"),
           "P2_2021_2023": ("2021-01-01", "2023-12-31"),
           "P3_2024_2026": ("2024-01-01", "2026-09-30")}
SELECT_PERIODS = ("P1_2018_2020", "P2_2021_2023")   # 只用这两段做筛选
HORIZON = 20
N_LIQ = 5


# ---------------------------------------------------------------------------
# 输入
# ---------------------------------------------------------------------------

def monthly_dates(cal, start, end) -> list:
    """信号日 = 每月最后一个交易日。

    **不用周频**：系统的 `labels.parquet` 和 `universes.parquet` 都是
    月频网格（116 个日期），周频信号日只能和它们对上 60/448 —— 看起来
    样本多了 4 倍，实际全是 NaN。要对齐就必须自己重算 label，
    而那会让本研究和 S3 用的标签不再是同一个东西。宁可样本少而口径一致。
    """
    d = cal[(cal >= pd.Timestamp(start)) & (cal <= pd.Timestamp(end))]
    return [pd.Timestamp(x) for x in d.to_series().groupby(
        [d.year, d.month]).last()]


def load_universe() -> dict:
    u = pd.read_parquet(PROJECT_ROOT / "data" / "derived" / "factors"
                        / "universes.parquet")
    u["date"] = pd.to_datetime(u["date"])
    u = u[u["universe"] == "full"]
    import yaml
    cfg = yaml.safe_load((PROJECT_ROOT / "config" / "factor_research.yaml")
                         .read_text(encoding="utf-8"))
    excl = set((cfg.get("universe") or {}).get("index_exclude") or [])
    if excl:
        u = u[~u["symbol"].isin(excl)]
    return {pd.Timestamp(d): sorted(g["symbol"])
            for d, g in u.groupby("date")}


def load_labels() -> dict:
    lb = pd.read_parquet(PROJECT_ROOT / "data" / "derived" / "factors"
                         / "labels.parquet")
    lb = lb[lb["horizon"] == HORIZON]
    return {pd.Timestamp(d): g.set_index("symbol")["label"]
            for d, g in lb.groupby("date")}


def load_controls() -> dict:
    """控制变量。

    **市值没有历史序列** —— `data/parquet/valuation/daily_valuation.parquet`
    只有 2026-09-30 一天（4605 行），做不了历史分组。所以 §十三 要求的
    market cap 控制**做不到**，用流动性（成交额）与价格作为相关代理，
    并在报告里如实标注。不拿单日快照去近似历史市值。
    """
    from factors.base import load_factor_data, set_news_version

    set_news_version(E.NEWS_VERSION)
    data = load_factor_data("2017-01-01", "2026-09-30")
    out = {
        "amount20": data.amount_cny.rolling(20, min_periods=5).mean(),
        "price": data.close_raw,
        "industry": data.industries,
        "first_day": data.adj_close.notna().idxmax(),
    }
    # 上市年龄：每只股票在面板里第一次出现的日期
    first = {}
    ok = data.adj_close.notna()
    for col in ok.columns:
        s = ok[col]
        first[col] = s.index[np.argmax(s.to_numpy())] if s.any() else pd.NaT
    out["first_day"] = pd.Series(first)
    return out


# ---------------------------------------------------------------------------
# 评估
# ---------------------------------------------------------------------------

def restrict(panel: pd.DataFrame, dates, universe: dict) -> pd.DataFrame:
    rows = {}
    for d in dates:
        d = pd.Timestamp(d)
        if d not in panel.index:
            continue
        syms = universe.get(d)
        s = panel.loc[d]
        rows[d] = s[s.index.isin(syms)] if syms else s
    return pd.DataFrame(rows).T if rows else pd.DataFrame()


def exchange_mask(idx: pd.Index, ex: str):
    return np.array([str(s).startswith("6") == (ex == "SSE") for s in idx])


def liq_masks(liq: pd.DataFrame, bucket: int, n=N_LIQ):
    """按当日 20 日均成交额分 n 组，返回 (index, date)->bool 的闭包。"""
    cache = {}

    def fn(idx, date):
        key = date
        if key not in cache:
            if date not in liq.index:
                return None
            v = liq.loc[date]
            try:
                cache[key] = pd.qcut(v.rank(method="first"), n,
                                     labels=False)
            except ValueError:
                cache[key] = None
        b = cache[key]
        if b is None:
            return None
        bb = b.reindex(idx)
        return (bb == bucket).fillna(False).to_numpy()
    return fn


def evaluate(name, panel, labels, dates, universe, liq, controls) -> dict:
    p = restrict(panel, dates, universe)
    if p.empty:
        return {"error": "没有可用截面"}
    res = {"name": name, "dispersion": E.dispersion(p, dates),
           "quantile5": E.quantiles(p, labels, dates, 5),
           "quantile10": E.quantiles(p, labels, dates, 10),
           "periods": {}, "overall": {}, "exchange": {}, "liquidity": {}}

    # 逐期 IC
    for pname, (lo, hi) in PERIODS.items():
        dd = [d for d in dates if lo <= str(pd.Timestamp(d).date()) <= hi]
        ics = E.ic_series(p, labels, dd)
        res["periods"][pname] = _ic_stats(ics)
    allics = E.ic_series(p, labels, dates)
    res["overall"] = _ic_stats(allics)
    res["ic_series"] = {str(k.date()): float(v)
                        for k, v in allics.items()}
    res["yearly"] = {int(y): _ic_stats(g) for y, g in
                     allics.groupby(allics.index.year)}

    # 交易所
    for ex in ("SSE", "SZSE"):
        res["exchange"][ex] = E.subgroup_ic(
            p, labels, dates, lambda i, d, ex=ex: exchange_mask(i, ex))
    # 流动性分组
    for b in range(N_LIQ):
        res["liquidity"][f"L{b+1}"] = E.subgroup_ic(
            p, labels, dates, liq_masks(liq, b))
    return res


def _ic_stats(ics: pd.Series) -> dict:
    if len(ics) == 0:
        return {"n": 0, "ic": np.nan, "icir": np.nan, "pos_pct": np.nan}
    return {"n": int(len(ics)), "ic": float(ics.mean()),
            "icir": float(ics.mean() / ics.std()) if ics.std() else np.nan,
            "pos_pct": float((ics > 0).mean()),
            "ic_std": float(ics.std())}


# ---------------------------------------------------------------------------
# 分类（spec §二十一：不预设机械阈值）
# ---------------------------------------------------------------------------

def _retention(res) -> dict:
    """组内保留率 = 组内 IC 均值 / 池化 IC。

    **用均值，不用最大值。** 第一版用的是"组内 |IC| 的最大值"，那是错的：
    7 个子样本估计（2 个交易所 + 5 个流动性组）里总有一个因为噪声偏大，
    取最大值等于让最有利的一组单独裁决，任何因子都能蒙混过关。均值才是
    "池化 IC 里有多少来自组内"的正确读法 —— 池化 = 组间 + 组内，
    组内均值≈0 而池化不为 0 就说明信号全在组间。

    **无条件计算**：不论最后判成哪一档，这两个数都要能看见，
    否则读者无法自己判断（第一版把保留率放在分级之后算，
    结果 weak / low_discrimination 的因子全是"—"）。
    """
    pooled = res.get("overall", {}).get("ic")
    # 池化 IC 近零时比值是 0/0 —— 噪声比噪声，能算出 4.67、-2.13 这种
    # 毫无意义的大数（`procedural_count_20d` 就是）。此时返回 NaN，
    # 报"比值无意义"比报一个假精确的数字诚实。
    if not pooled or np.isnan(pooled) or abs(pooled) < 0.002:
        return {"exchange": np.nan, "liquidity": np.nan,
                "note": "池化 IC 近零，比值无意义"}
    ex = [res["exchange"][k]["ic"] for k in ("SSE", "SZSE")]
    ex = [x for x in ex if not np.isnan(x)]
    liq = [v["ic"] for v in res["liquidity"].values()]
    liq = [x for x in liq if not np.isnan(x)]
    return {"exchange": float(np.mean(ex)) / pooled if ex else np.nan,
            "liquidity": float(np.mean(liq)) / pooled if liq else np.nan}


def _corr_with_volume(panel, vol_ref, dates, universe) -> dict:
    """与"公告总条数"的横截面相关性（spearman，逐日取均值）。

    **这是对 §十三 那个担忧的直接量化**：新闻因子很容易只是
    "这家公司公告多"的代理，而公告多又和规模、活跃度、交易所高度相关。
    如果某因子的 IC 有相当部分能被总条数解释，那它的"经济含义"
    就是可疑的。

    参照物用 **总公告数**（含程序性、含未分类），因为它是纯粹的
    "数量"，不含任何经济内容 —— 一个因子若与它相关 0.9，
    就很难声称自己测的是别的东西。
    """
    if vol_ref is None or vol_ref.empty:
        return {"vs_total_announcements": np.nan}
    p = restrict(panel, dates, universe)
    if p.empty:
        return {"vs_total_announcements": np.nan}
    cors = []
    for d in p.index:
        if d not in vol_ref.index:
            continue
        a = p.loc[d].dropna()
        b = vol_ref.loc[d]
        both = a.index.intersection(b.index)
        if len(both) < 30:
            continue
        c = spearman_like(a[both], b[both])
        if not np.isnan(c):
            cors.append(c)
    return {"vs_total_announcements": float(np.mean(cors)) if cors else np.nan}


def spearman_like(a, b):
    df = pd.concat([a.rename("f"), b.rename("y")], axis=1).dropna()
    if len(df) < 30 or df["f"].nunique() < 2 or df["y"].nunique() < 2:
        return np.nan
    return float(df["f"].rank().corr(df["y"].rank()))


def classify(res, spec) -> tuple:
    """-> (tier, reasons)

    判定顺序（先否决，再看强弱）：

    1. **无效**：横截面 90% 以上取同一值（LOW_DISCRIMINATION）——
       没有排序能力，IC 再高也不可用；
    2. **无效**：两个筛选期符号相反，或某期 n 太少；
    3. **弱**：筛选期 |IC| < 0.005（经济上接近于零）；
    4. **强/中**：组内（交易所、流动性）是否保留 ——
       只在组间有效 = 伪信号，降级；
    5. 符号与注册表先验不一致 -> 标注（不翻转，只记录）。
    """
    reasons = []
    if "error" in res:
        return "invalid", ["没有可用截面"]
    d = res["dispersion"]
    if d["max_tie_share"] > 0.90:
        # spec §十二：>90% 取同一值 -> LOW_DISCRIMINATION。
        # **单列一档而不是直接判死**：稀有事件型因子（例如"首次负面"
        # 这种本来就该稀疏的指标）天然同值率高，它们不是"坏因子"，
        # 只是不该被塞进模型 —— S3_v2 的 regulatory_event_count_20d
        # 正是以 91.6% 同值率吃掉了 25% 的增益却换不来排序。
        # 保留统计量供阅读，但明确不推荐入模。
        reasons.append(
            f"LOW_DISCRIMINATION：{d['max_tie_share']:.1%} 的股票取同一值 —— "
            "横截面几乎没有排序能力，不推荐入模")
        return "low_discrimination", reasons

    sel = [res["periods"][k] for k in SELECT_PERIODS]
    ics = [s["ic"] for s in sel]
    if any(np.isnan(x) for x in ics) or min(s["n"] for s in sel) < 20:
        return "invalid", ["筛选期样本不足"]
    if ics[0] * ics[1] < 0:
        reasons.append(f"两筛选期符号相反（{ics[0]:+.4f} / {ics[1]:+.4f}）")
        return "invalid", reasons

    sel_ic = float(np.mean(ics))
    if abs(sel_ic) < 0.005:
        reasons.append(f"筛选期 |IC| {abs(sel_ic):.4f} < 0.005")
        return "weak", reasons

    # 组内保留率（已在 _retention 里无条件算好）。两个混淆源
    # （交易所、流动性）都要过，取更保守的那个。
    ret_ex = res["retention"]["exchange"]
    ret_liq = res["retention"]["liquidity"]
    rets = [r for r in (ret_ex, ret_liq) if not np.isnan(r)]
    retained = min(rets) if rets else np.nan
    if not np.isnan(retained) and retained < 0.3:
        reasons.append(
            f"组内塌陷：保留率 交易所 {ret_ex:.2f} / 流动性 {ret_liq:.2f}"
            f"（<0.3 = 信号来自组间，不是横截面信息）")
        return "invalid", reasons
    if not np.isnan(retained) and retained < 0.6:
        reasons.append(
            f"部分来自组间差异（保留率 {ret_ex:.2f} / {ret_liq:.2f}）")

    # 符号一致性
    if spec.direction != "unknown":
        if np.sign(sel_ic) != (1 if spec.direction == "positive" else -1):
            reasons.append(f"实际符号与先验 {spec.direction} 相反")

    p3 = res["periods"]["P3_2024_2026"]["ic"]
    if not np.isnan(p3) and p3 * sel_ic < 0:
        reasons.append("2024-2026 段符号翻转")
        return "moderate", reasons

    icir1 = res["periods"][SELECT_PERIODS[0]]["icir"]
    tier = ("strong" if abs(sel_ic) >= 0.02 and not np.isnan(icir1)
            and abs(icir1) >= 0.3 else "moderate")
    if spec.control:
        reasons.append("**阴性对照**：本不该有信号")
        return ("invalid" if tier == "strong" else "moderate"), reasons
    return tier, reasons


# ---------------------------------------------------------------------------
# 报告
# ---------------------------------------------------------------------------

def _f(v, nd=4):
    return "—" if v is None or (isinstance(v, float) and np.isnan(v)) \
        else f"{v:+.{nd}f}"


def _rf(v):
    """组内保留率：无符号，两位小数。"""
    return "—" if v is None or (isinstance(v, float) and np.isnan(v)) \
        else f"{v:.2f}"


def render(results: dict, order: list, meta: dict) -> str:
    L = ["# 新闻因子研究（News Factor Research）", "",
         f"> 生成：`python scripts/news/run_news_factor_research.py`  ",
         f"> 生成时间：{meta['generated_at']}  ",
         f"> 新闻数据：`news_events_v2`（修复 SSE 采集后的集合），"
         f"版本 `{E.NEWS_VERSION}`  ",
         f"> 因子版本：`{E.FEATURE_VERSION}`", "",
         "**本阶段不训练任何模型。** S3_v1 / S3_v2 / production_strategy / "
         "recommendation 全部未改动。", "", "---", ""]

    # 1 数据源
    L += ["## 1. Data Source", "",
          "| 项 | 值 |", "|---|---|",
          f"| 事件表 | `news_events_v2` |",
          f"| 公告表 | `news_documents_v2` |",
          f"| 事件数（可用时间完整） | {meta['n_events']:,} |",
          f"| 股票数 | {meta['n_symbols']:,} |",
          f"| 事件日期范围 | {meta['ev_min']} ~ {meta['ev_max']} |",
          f"| 信号日（月频，月末最后交易日） | {meta['n_dates']} 个 |",
          f"| 评估区间 | 2018-01-01 ~ 2026-09-30 |",
          "", "> 公告**正文不存在**：`news_documents_v2` 没有 `content` 列，"
              "事件层 `sentiment` / `risk` / `financial_impact` / `event_time` "
              "四列 100% 为空。因此本阶段只用"
              "「标题 + 事件类型 + 方向 + 严重度 + 时间」这些结构化字段，"
              "不使用任何 NLP 输出 —— 与 spec §二十 一致。", ""]

    # 2 taxonomy
    L += ["---", "", "## 2. Event Taxonomy", "",
          "生产分类器（`news/events.py`）把 **57.3%** 的公告归入 `other`。"
          "研究层 taxonomy 在此基础上细分（不改上游代码，只读叠加）：", "",
          "| materiality | 占比 |", "|---|---|"]
    for k, v in meta["materiality"].items():
        L.append(f"| {k} | {v:.1%} |")
    L += ["", "细分后新增的可识别类别（此前全在 `other` 里）：", "",
          "| 主题 | 占全部公告 |", "|---|---|"]
    for k, v in meta["recovered"].items():
        L.append(f"| `{k}` | {v:.2%} |")
    L += ["", "> **最重要的发现**：约 **30%** 的公告是纯程序性的"
              "（股东大会通知与决议、公司章程修订、法律意见书、内控制度）。"
              "任何「公告数量」类因子都有一大块波动来自行政流程，"
              "而不是信息。这就是为什么下面把 `procedural_count_20d` "
              "设成**阴性对照**。", ""]

    # 3/4 因子
    L += ["---", "", "## 3. Candidate Factors", "",
          f"共 **{len(order)}** 个候选因子（spec 要求 15–30）。", "",
          "| # | 因子 | 定义 | 窗口 | 先验方向 | 类型 |", "|---|---|---|---|---|---|"]
    for i, n in enumerate(order, 1):
        s = FACTOR_SPECS[n]
        tag = "**阴性对照**" if s.control else s.kind
        L.append(f"| {i} | `{n}` | {s.definition} | {s.window}d | "
                 f"{s.direction} | {tag} |")
    L += ["", "## 4. Factor Definitions", "",
          "每个因子的经济假设（注册表里逐条对应）：", ""]
    for n in order:
        L.append(f"- **`{n}`** — {FACTOR_SPECS[n].hypothesis}")
    L.append("")

    # 5 数据质量
    L += ["---", "", "## 5. Data Quality", "",
          "| 因子 | 唯一值比例 | 缺失率 | 截面标准差 | 截面中位数 | 最大同值占比 |",
          "|---|---|---|---|---|---|"]
    for n in order:
        d = results[n].get("dispersion")
        if not d:
            L.append(f"| `{n}` | — | — | — | — | — |")
            continue
        L.append(f"| `{n}` | {d['unique_ratio']:.3f} | {d['missing_rate']:.1%} | "
                 f"{d['cs_std']:.3f} | {d['cs_median']:.3f} | "
                 f"{d['max_tie_share']:.1%} |")
    L += ["", "> `最大同值占比 > 90%` 的因子标记 **LOW_DISCRIMINATION** 并直接"
              "判为无效 —— 它对绝大多数股票取同一个值，给不出排序。"
              "（这正是 S3_v2 那个 `regulatory_event_count_20d` 的死因：91.6%）", ""]

    # 6 PIT
    L += ["---", "", "## 6. PIT Verification", "",
          "因子只使用 `availability_time <= T` 的事件。事件的「日」取可用时间"
          "在 Asia/Shanghai 的日期，并已在上游把盘后公告推到次一交易日 09:30"
          "（docs/步骤5-新闻时点规则.md）。", "",
          "永久回归测试：`tests/news_factors/test_news_factor_research.py`"
          "（`test_future_events_cannot_change_earlier_factor_values`）—— "
          "把 T 之后的事件加进来，T 日的因子值必须纹丝不动。", ""]

    # 7 IC
    L += ["---", "", "## 7. IC / Rank IC", "",
          "| 因子 | 筛选期(18-23) IC | ICIR | 正向月比 | 2018-20 | 2021-23 | "
          "2024-26 | 全样本 ICIR |", "|---|---|---|---|---|---|---|---|"]
    for n in order:
        r = results[n]
        if "error" in r:
            L.append(f"| `{n}` | — | — | — | — | — | — | — |")
            continue
        sel = np.mean([r["periods"][k]["ic"] for k in SELECT_PERIODS])
        sel_icir = np.mean([r["periods"][k]["icir"] for k in SELECT_PERIODS])
        sel_pos = np.mean([r["periods"][k]["pos_pct"] for k in SELECT_PERIODS])
        L.append(
            f"| `{n}` | {_f(sel)} | {_f(sel_icir, 2)} | {sel_pos:.0%} | "
            f"{_f(r['periods']['P1_2018_2020']['ic'])} | "
            f"{_f(r['periods']['P2_2021_2023']['ic'])} | "
            f"{_f(r['periods']['P3_2024_2026']['ic'])} | "
            f"{_f(r['overall']['icir'], 2)} |")
    L += ["", "> 信号日为月频，全样本 116 个观测、每个筛选期约 36 个。**36 个观测的 "
              "ICIR 噪声很大**，不能当 t 统计量读，它在这里只是稳定性排序的"
              "一个参考。筛选只用 2018-2023 两段。", ""]

    # 8 分层
    L += ["---", "", "## 8. Quantile Returns", "",
          "5 分层的各层平均 20 日前瞻收益，以及高减低：", "",
          "| 因子 | Q1 | Q2 | Q3 | Q4 | Q5 | Q5-Q1 | 10分位高减低 |",
          "|---|---|---|---|---|---|---|---|"]
    for n in order:
        q = results[n].get("quantile5")
        q10 = results[n].get("quantile10") or {}
        if not q or not q.get("n_dates"):
            L.append(f"| `{n}` | — | — | — | — | — | — | — |")
            continue
        L.append(f"| `{n}` | " + " | ".join(
            f"{q[f'Q{i}']:+.4f}" for i in range(1, 6)) +
            f" | {_f(q['Qhigh-Qlow'])} | {_f(q10.get('Qhigh-Qlow'))} |")
    L.append("")

    # 9 交易所
    L += ["---", "", "## 9. Cross-Exchange Analysis", "",
          "| 因子 | 全样本 IC | SSE IC | SZSE IC | 组内最大/全样本 |",
          "|---|---|---|---|---|"]
    for n in order:
        r = results[n]
        if "error" in r:
            continue
        ex = r["exchange"]
        a, b = ex["SSE"]["ic"], ex["SZSE"]["ic"]
        both = [x for x in (a, b) if not np.isnan(x)]
        ratio = (max(abs(x) for x in both) / abs(r["overall"]["ic"])
                 if both and r["overall"]["ic"] else np.nan)
        L.append(f"| `{n}` | {_f(r['overall']['ic'])} | {_f(a)} | {_f(b)} | "
                 f"{ratio:.2f} |" if not np.isnan(ratio) else
                 f"| `{n}` | {_f(r['overall']['ic'])} | {_f(a)} | {_f(b)} | — |")
    L += ["", "> **不能只看全市场平均。** 沪市公告密度约为深市 20 倍，"
              "若某因子在沪市为 0、深市显著，全市场 IC 会把它掩盖。"
              "比值 < 0.3 的因子按伪信号处理。", ""]

    # 10 流动性
    L += ["---", "", "## 10. Liquidity Analysis", "",
          "按当日 20 日均成交额分 5 组，组内 IC（L1 最低、L5 最高）：", "",
          "| 因子 | L1 | L2 | L3 | L4 | L5 |", "|---|---|---|---|---|---|"]
    for n in order:
        liq = results[n].get("liquidity")
        if not liq:
            continue
        L.append(f"| `{n}` | " + " | ".join(
            _f(liq[f"L{i+1}"]["ic"]) for i in range(N_LIQ)) + " |")
    L += ["", "> **市值控制做不到**：`data/parquet/valuation/daily_valuation.parquet` "
              "只有 2026-09-30 一天的快照（4,605 行），没有历史序列。"
              "所以 §十三 要求的 within-market-cap IC **本报告无法提供**，"
              "用成交额（流动性）与价格作为相关代理。这是能力边界，不是省略。", ""]

    # 11 跨期
    L += ["---", "", "## 11. Time Stability", "",
          "逐年 rank IC：", "",
          "| 因子 | " + " | ".join(str(y) for y in meta["years"]) + " |",
          "|---|" + "---|" * len(meta["years"])]
    for n in order:
        y = results[n].get("yearly")
        if not y:
            continue
        L.append(f"| `{n}` | " + " | ".join(
            _f(y.get(yy, {}).get("ic", np.nan), 3) for yy in meta["years"])
            + " |")
    L.append("")

    # 11.5 与公告总量的相关（§十三 的直接检验）
    L += ["---", "", "## 11b. 是不是「公告数量」的代理？", "",
          "每个因子与**公告总条数（60 交易日）**的横截面相关性"
          "（逐日 spearman 后取均值）：", "",
          "| 因子 | 与总条数的相关 |", "|---|---|"]
    for n in order:
        c = results[n].get("corr_volume", {}).get("vs_total_announcements",
                                                  np.nan)
        L.append(f"| `{n}` | {_f(c, 3)} |")
    L += ["", "> 总条数不含任何经济内容。一个因子若与它相关 0.9，"
              "它的 IC 有多少是「公告多」本身、有多少是内容，就很难分开了。"
              "这是 §十三 要求的代理变量检验的量化版本 —— "
              "因为历史市值不可得（见 §10），这里用公告总量本身作为"
              "最保守的参照。", ""]

    # 12 多重检验
    L += ["---", "", "## 12. Multiple Testing Risk", "",
          f"- 候选（registry 声明）：**{meta['n_candidates']}**",
          f"- 实际评估：**{meta['n_tested']}**",
          f"- 判为 strong：**{meta['n_strong']}** / moderate："
          f"**{meta['n_moderate']}** / weak：**{meta['n_weak']}** / "
          f"low_discrimination：**{meta['n_low_disc']}** / "
          f"invalid：**{meta['n_invalid']}**", "",
          "本次在 29 个因子上做了同样的检验。即使**全部因子都没有真实 alpha**，"
          "在 |IC| 上仍会有一两个因为抽样波动看起来不错"
          "（29 个独立检验、单侧 5% 水平下期望约 1.5 个假阳性）。", "",
          "因此本报告**不把「历史 IC 高」当作有效证据**，而要求同时满足：", "",
          "1. 两个筛选期符号一致；",
          "2. 组内（沪市 / 深市 / 流动性分层）不大幅塌陷；",
          "3. 2024-2026 段不翻转；",
          "4. 截面分辨力足够（同值占比 < 90%）。", "",
          "**阴性对照是这套判据的校准器**：`procedural_count_20d` 与 "
          "`unknown_count_20d` 按经济逻辑不该有信号。它们若被判为 strong，"
          "说明判据本身在捕风捉影，整张表都要打折。结果见 §13。", ""]

    # 13 ranking
    tier_order = {"strong": 0, "moderate": 1, "weak": 2,
                  "low_discrimination": 3, "invalid": 4}
    ranked = sorted(order, key=lambda n: (tier_order[results[n]["_tier"]],
                                          -abs(results[n].get("overall", {})
                                               .get("ic") or 0)))
    L += ["---", "", "## 13. Factor Ranking", "",
          "| 因子 | IC | ICIR | 稳定性 | SSE | SZSE | 组内保留(交易所) | "
          "组内保留(流动性) | 判定 |", "|---|---|---|---|---|---|---|---|---|"]
    for n in ranked:
        r = results[n]
        if "error" in r:
            L.append(f"| `{n}` | — | — | — | — | — | — | — | invalid |")
            continue
        sel = np.mean([r["periods"][k]["ic"] for k in SELECT_PERIODS])
        sel_icir = np.mean([r["periods"][k]["icir"] for k in SELECT_PERIODS])
        p1 = r["periods"]["P1_2018_2020"]["ic"]
        p2 = r["periods"]["P2_2021_2023"]["ic"]
        stable = ("同号" if p1 * p2 > 0 else "**异号**")
        ret = r.get("retention") or {}
        re_, rl = ret.get("exchange", np.nan), ret.get("liquidity", np.nan)
        L.append(f"| `{n}` | {_f(sel)} | {_f(sel_icir, 2)} | "
                 f"{stable} | {_f(r['exchange']['SSE']['ic'])} | "
                 f"{_f(r['exchange']['SZSE']['ic'])} | "
                 f"{_rf(re_)} | {_rf(rl)} | **{r['_tier']}** |")
    L += ["", "> IC 列报的是 **rank IC（Spearman）**，取两个筛选期的均值。",
          "> 「稳定性」= 两个筛选期是否同号。",
          "> 「组内保留」= **组内 IC 的均值 / 池化 IC**："
          "接近 1 说明信号在组内也存在；接近 0 或为负说明池化 IC 全部来自"
          "组间构成差异（规模/流动性/交易所），不是横截面信息。"
          "低于 0.3 判为伪信号。", ""]

    # 14/15
    L += ["---", "", "## 14. Recommended Candidate Factors", "",
          "**先读这一段再读清单。** 本阶段最重要的结果是两个**阴性对照**的表现：", "",
          "- `unknown_count_20d`（taxonomy 分不出来的残差，按构造不含任何"
          "经济内容）拿到全表**最高 IC（−0.0139）**，且组内保留 1.01 / 0.40；",
          "- `procedural_count_20d`（程序性公告）为 weak，"
          "池化 IC 近零 —— 这个对照**表现正常**。", "",
          "一个对照排第一、另一个正常，说明：**宽口径的「负面事件数」"
          "在很大程度上是「公告多」本身的代理**（与总条数相关 0.39~0.45），"
          "而不是事件内容的信息。这一点在 §11b 有量化。", "",
          "另一头，内容最具体的几个因子"
          "（`regulatory_` / `investigation_` / `penalty_` / `litigation_` /"
          " `first_negative_event_`）与总条数**几乎不相关（0.00~0.15）**，"
          "说明它们确实在测别的东西 —— 但它们同时**太稀疏**："
          "横截面上 >90% 的股票取同一值，排不出名次。", "",
          "> **这就是本阶段真正的墙**：特异性与横截面分辨力此消彼长。"
          "能排序的只是数量，有内容的排不了序。S3_v2 撞的正是同一面墙。", ""]
    for tier, label in (("strong", "Strong"), ("moderate", "Moderate")):
        hits = [n for n in ranked if results[n]["_tier"] == tier]
        L += [f"**{label}**（{len(hits)} 个）", ""]
        if not hits:
            L += ["（无）", ""]
            continue
        for n in hits:
            r = results[n]
            c = r.get("corr_volume", {}).get("vs_total_announcements", np.nan)
            L.append(f"- `{n}` — {FACTOR_SPECS[n].hypothesis}")
            L.append(f"  - 与公告总条数相关 **{c:.2f}**"
                     + ("（偏高：信号有相当部分来自数量本身）" if c > 0.35
                        else ""))
            if FACTOR_SPECS[n].control:
                L.append("  - ⚠ **这是阴性对照因子** —— 它不该有信号，"
                         "它排在这里本身就是对整套判据的警告")
            for reason in r["_reasons"]:
                L.append(f"  - ⚠ {reason}")
        L.append("")
    L += ["## 15. Rejected Factors", ""]
    for tier in ("weak", "low_discrimination", "invalid"):
        hits = [n for n in ranked if results[n]["_tier"] == tier]
        L += [f"**{tier}**（{len(hits)} 个）", ""]
        for n in hits:
            L.append(f"- `{n}` — " + "；".join(results[n]["_reasons"]))
        L.append("")

    # 16
    L += ["---", "", "## 16. Next Step", "",
          "本阶段**到此为止**。", "",
          "- 未创建 S3_v3；未改动 `production_strategy`（仍为 `S3_v1`）；"
          "未改动 recommendation；未改动任何历史结果。",
          "- 上表判为 strong / moderate 的因子，状态为 "
          "`RECOMMENDED_FOR_NEXT_MODEL` —— 这是**建议**，不是模型改动。",
          "- 是否进入下一个模型、以什么方式进入，等下一步指令。", ""]
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--factors", default=None)
    ap.add_argument("--no-table", action="store_true")
    args = ap.parse_args()

    t0 = time.time()
    names = (args.factors.split(",") if args.factors
             else list(FACTOR_SPECS))
    print(f"[research] {len(names)} 个候选因子", flush=True)

    ev = E.load_research_events()
    streams = streams_from_events(ev)
    print(f"[research] 事件 {len(ev):,} -> 流 {streams.shape}", flush=True)
    cal = E.trading_calendar()
    start, end = pd.Timestamp("2018-01-01"), pd.Timestamp("2026-09-30")
    dates = monthly_dates(cal, start, end)
    universe = load_universe()
    labels = load_labels()
    liq = load_controls()["amount20"]
    print(f"[research] 信号日 {len(dates)} 个", flush=True)

    # 数据质量概览
    mat = ev["materiality"].value_counts(normalize=True).to_dict()
    rec = {th: float((ev["materiality"] == "procedural").mean()
                     if th == "procedural" else (ev["theme"] == th).mean())
           for th in ("procedural", "equity_incentive", "related_party",
                      "guarantee", "debt_default")}
    rec = {k: v for k, v in rec.items() if v > 0}

    # 参照物：公告总条数（60 交易日），纯粹的"数量"，不含任何经济内容
    from research.news_factors.factors import FactorSpec as _FS
    _vol = _FS("vol_ref", "公告总条数 60d", ["n_all"], 60, "unknown", "ref")
    vol_ref = E.mask_uncovered(
        E.compute_panel(_vol, streams, cal, start, end), dates)

    results = {}
    for i, name in enumerate(names, 1):
        spec = FACTOR_SPECS[name]
        panel = E.compute_panel(spec, streams, cal, start, end)
        panel = E.mask_uncovered(panel, dates)
        r = evaluate(name, panel, labels, dates, universe, liq, None)
        r["retention"] = _retention(r)
        r["corr_volume"] = _corr_with_volume(panel, vol_ref, dates, universe)
        tier, reasons = classify(r, spec)
        r["_tier"], r["_reasons"] = tier, reasons
        results[name] = r
        print(f"[{i}/{len(names)}] {name}: {tier}  "
              f"sel_IC={np.mean([r['periods'][k]['ic'] for k in SELECT_PERIODS]):+.4f} "
              f"({time.time()-t0:.0f}s)", flush=True)

    # 注册表 YAML（spec §二十四：不能只存在代码里）
    #
    # 由 FACTOR_SPECS **导出**，不手写第二份 —— 手写的注册表迟早和代码
    # 说的是两件事，那时它就从文档变成了传言的来源。
    import yaml
    reg = {"feature_version": E.FEATURE_VERSION,
           "news_version": E.NEWS_VERSION,
           "generated_at": datetime.now().isoformat(timespec="seconds"),
           "pit_rule": "event.availability_time <= as_of_date（按 Asia/Shanghai "
                       "的日期对齐到交易日；available 未知的事件被丢弃）",
           "window_unit": "trading_days",
           "factors": []}
    for name in names:
        s = FACTOR_SPECS[name]
        r = results[name]
        reg["factors"].append({
            "name": s.name, "definition": s.definition,
            "source_fields": s.source_streams, "window": s.window,
            "direction": s.direction,
            "economic_hypothesis": s.hypothesis, "pit_rule": "same as above",
            "kind": s.kind, "control": s.control,
            "status": r["_tier"],
            "ic_selection": float(np.mean([r["periods"][k]["ic"]
                                           for k in SELECT_PERIODS]))
            if "error" not in r else None,
            "retention": r.get("retention"),
            "corr_total_announcements":
                r.get("corr_volume", {}).get("vs_total_announcements"),
            "reasons": r["_reasons"],
        })
    reg_path = (PROJECT_ROOT / "research" / "news_factors"
                / "factor_registry.yaml")
    reg_path.write_text(yaml.safe_dump(reg, allow_unicode=True,
                                       sort_keys=False, width=100),
                        encoding="utf-8")
    print(f"[research] 注册表 -> {reg_path}")

    # 因子数据表（月度调仓网格）
    if not args.no_table:
        mdates = monthly_dates(cal, start, end)
        cols = {}
        for name in names:
            spec = FACTOR_SPECS[name]
            p = E.mask_uncovered(
                E.compute_panel(spec, streams, cal, start, end), mdates)
            cols[name] = p.stack(dropna=True)
        tbl = pd.DataFrame(cols)
        tbl.index.names = ["date", "symbol"]
        tbl = tbl.reset_index()
        tbl.attrs = {}
        tbl.to_parquet(E.FACTOR_DAILY, index=False)
        meta_side = {"feature_version": E.FEATURE_VERSION,
                     "news_version": E.NEWS_VERSION,
                     "generated_at": datetime.now().isoformat(timespec="seconds"),
                     "n_dates": len(mdates), "n_factors": len(names)}
        (E.FACTOR_DAILY.with_suffix(".meta.json")).write_text(
            json.dumps(meta_side, ensure_ascii=False, indent=2),
            encoding="utf-8")
        print(f"[research] 因子表 {tbl.shape} -> {E.FACTOR_DAILY}")

    years = sorted({int(d.year) for d in dates})
    meta = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "n_events": len(ev), "n_symbols": int(ev["symbol"].nunique()),
        "ev_min": str(ev["sdate"].min().date()),
        "ev_max": str(ev["sdate"].max().date()),
        "n_dates": len(dates), "years": years,
        "materiality": {k: float(v) for k, v in mat.items()},
        "recovered": rec,
        "n_candidates": len(FACTOR_SPECS), "n_tested": len(names),
        "n_strong": sum(1 for r in results.values() if r["_tier"] == "strong"),
        "n_moderate": sum(1 for r in results.values()
                          if r["_tier"] == "moderate"),
        "n_weak": sum(1 for r in results.values() if r["_tier"] == "weak"),
        "n_low_disc": sum(1 for r in results.values()
                          if r["_tier"] == "low_discrimination"),
        "n_invalid": sum(1 for r in results.values()
                         if r["_tier"] == "invalid"),
    }
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(render(results, names, meta), encoding="utf-8")
    (OUT_MD.with_suffix(".json")).write_text(
        json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "ic_series"}
                    for k, v in results.items()},
                   ensure_ascii=False, indent=2, default=str),
        encoding="utf-8")
    print(f"[research] wrote {OUT_MD}（{time.time()-t0:.0f}s）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
