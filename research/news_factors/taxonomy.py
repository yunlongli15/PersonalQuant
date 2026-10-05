# -*- coding: utf-8 -*-
"""研究层的公告 taxonomy。

**为什么另起一层，而不是改 `news/events.py`。**

`news/events.py` 的分类结果已经写进了冻结的 `news_events` /
`news_events_v2` 快照，S3_v1 的生产信号、paper_live 的冻结哈希、
历史回测全都建立在它们上面。改那套规则 = 改历史结果（CLAUDE.md 铁律 3）。

所以这一层是**只读叠加**：以库里已存的 `event_type` 为主轴，
只在它为 `'other'` 时再细分，外加一个 `materiality` 标记。
不动上游一行代码，不重算任何快照。

── 为什么需要细分 ──────────────────────────────────────────────────
实测 `other` 占全部事件 57.3%，其中约一半是**程序性公告**
（股东大会通知与决议、公司章程修订、法律意见书、内控与管理制度）。
"公告数量"这类因子因此有一半波动来自行政流程，而不是信息。
把程序性和实质性分开，是这一步最重要的产出。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

#: 实质性档位
PROCEDURAL = "procedural"    # 行政流程：股东大会、章程、法律意见书…
SUBSTANTIVE = "substantive"  # 有经济含义的事件
UNKNOWN = "unknown"          # 分不出来 —— 如实记录，不硬塞


@dataclass(frozen=True)
class ThemeRule:
    """一条研究层规则。按**特异性排序**，先匹配先返回。"""
    theme: str
    materiality: str
    direction: str            # 经济含义上的先验方向（candidate，不是结论）
    severity: float           # [0,1] 研究层严重度先验
    includes: Tuple[str, ...]
    excludes: Tuple[str, ...] = ()


#: 研究层主题。顺序 = 匹配优先级（特异性高的在前）。
#: 命名对齐 spec §四 列出的类别，并补上实测数据里真实存在、
#: 但现分类器没有的几类（股权激励 / 关联交易 / 担保 / 程序性）。
THEME_RULES: List[ThemeRule] = [
    # ---- 债务与存续风险（严重度最高，必须排在"重整/清算"这类词前面）----
    ThemeRule("debt_default", SUBSTANTIVE, "negative", 0.95,
              ("债务违约", "债务逾期", "逾期债务", "无法清偿", "未能清偿",
               "逾期未偿还", "未能按期兑付", "实质性违约", "资金占用",
               "违规担保", "被冻结", "账户冻结",
               "破产", "重整", "清算", "预重整", "退市风险警示")),
    # ---- 监管与法律 ----
    ThemeRule("investigation", SUBSTANTIVE, "negative", 0.90,
              ("立案调查", "立案告知书", "被立案", "接受调查",
               "涉嫌信息披露违法违规", "涉嫌违法")),
    ThemeRule("penalty", SUBSTANTIVE, "negative", 0.85,
              ("行政处罚", "罚款", "处罚决定", "公开谴责", "通报批评")),
    ThemeRule("regulatory", SUBSTANTIVE, "negative", 0.65,
              ("问询函", "关注函", "警示函", "监管函", "监管措施",
               "行政监管", "监管关注", "督促函", "改正措施")),
    ThemeRule("litigation", SUBSTANTIVE, "negative", 0.60,
              ("诉讼", "仲裁", "起诉", "被诉", "判决", "裁定")),
    # ---- 股东与股权 ----
    ThemeRule("pledge_release", SUBSTANTIVE, "positive", 0.35,
              ("解除质押", "解押", "质押解除", "解除股份质押")),
    ThemeRule("pledge", SUBSTANTIVE, "negative", 0.55,
              ("质押",)),
    ThemeRule("shareholder_reduce", SUBSTANTIVE, "negative", 0.55,
              ("减持", "拟减持", "减持计划", "减持股份")),
    ThemeRule("shareholder_increase", SUBSTANTIVE, "positive", 0.55,
              ("增持", "拟增持", "增持计划", "增持股份")),
    # ---- 资本运作 ----
    ThemeRule("buyback", SUBSTANTIVE, "positive", 0.50,
              ("回购",), excludes=("回购注销公告",)),
    ThemeRule("mna", SUBSTANTIVE, "positive", 0.70,
              ("收购", "并购", "重大资产重组", "吸收合并", "要约收购",
               "资产重组")),
    ThemeRule("equity_incentive", SUBSTANTIVE, "positive", 0.55,
              ("股权激励", "限制性股票", "股票期权", "员工持股计划",
               "激励计划")),
    ThemeRule("related_party", SUBSTANTIVE, "neutral", 0.45,
              ("关联交易", "关联方")),
    ThemeRule("guarantee", SUBSTANTIVE, "negative", 0.50,
              ("对外担保", "担保事项", "提供担保", "担保额度")),
    ThemeRule("dividend", SUBSTANTIVE, "positive", 0.40,
              ("利润分配", "权益分派", "分红", "派息", "现金红利")),
    ThemeRule("major_contract", SUBSTANTIVE, "positive", 0.60,
              ("中标", "重大合同", "合同签订", "签署合同", "框架协议")),
    ThemeRule("financing", SUBSTANTIVE, "neutral", 0.50,
              ("非公开发行", "定向增发", "增发", "配股", "可转换公司债券",
               "可转债", "发行股票", "募集资金", "再融资", "公司债券",
               "中期票据", "短期融资券")),
    # ---- 经营 ----
    ThemeRule("production_change", SUBSTANTIVE, "negative", 0.60,
              ("停产", "复产", "限产", "产能调整")),
    ThemeRule("product_launch", SUBSTANTIVE, "positive", 0.50,
              ("获批上市", "注册证书", "新产品", "获得批件", "获批临床")),
    ThemeRule("earnings", SUBSTANTIVE, "neutral", 0.55,
              ("业绩预告", "业绩预增", "业绩预减", "业绩预亏", "预增公告",
               "预减公告", "扭亏", "业绩快报", "业绩修正", "业绩更正",
               "年年度报告", "年度报告", "半年度报告", "季度报告",
               "定期报告", "年报")),
    # ---- 程序性（**必须排在最后一批实质性规则之后**，否则会抢走
    #      "关于召开股东大会审议股权激励的公告" 这类标题）----
    ThemeRule("procedural", PROCEDURAL, "neutral", 0.05,
              ("股东大会", "临时股东", "章程", "法律意见", "律师",
               "管理制度", "内部控制", "议事规则", "工作制度",
               "审计机构", "会计师事务所", "续聘", "聘任", "独立董事",
               "监事会决议", "资料", "提示性公告", "签字", "承诺书",
               "会议通知", "通知公告", "决议公告", "会议决议")),
]


def _matches(title: str, rule: ThemeRule) -> bool:
    if any(x in title for x in rule.excludes):
        return False
    return any(x in title for x in rule.includes)


def classify(title: str, base_type: str = "other") -> Tuple[str, str, str, float]:
    """-> (theme, materiality, direction_hint, severity)

    `base_type` 是库里已存的 event_type：

    - 不是 `other` 时**直接采信**（生产分类器对它有把握），只是把
      `materiality` 标成实质性、严重度从 `THEME_SEVERITY` 取；
    - 是 `other` 时用研究层规则细分，分不出来就诚实返回
      `('other', 'unknown', 'neutral', 0.0)`。
    """
    if base_type and base_type != "other":
        return (base_type, SUBSTANTIVE,
                BASE_DIRECTION.get(base_type, "neutral"),
                BASE_SEVERITY.get(base_type, 0.5))
    t = title or ""
    for rule in THEME_RULES:
        if _matches(t, rule):
            return rule.theme, rule.materiality, rule.direction, rule.severity
    return "other", UNKNOWN, "neutral", 0.0


#: 生产分类器判过的类型：方向与严重度沿用 `news/events.py` 的先验，
#: **不在这里另立一套** —— 两套先验打架会让"研究层"和"生产层"
#: 对同一个事件说不同的话。
BASE_DIRECTION = {
    "unpledge": "positive", "penalty": "negative",
    "investigation": "negative", "bankruptcy": "negative",
    "regulatory": "negative", "earnings_forecast": "neutral",
    "earnings_revision": "neutral", "earnings": "neutral",
    "share_buyback": "positive", "shareholder_change": "negative",
    "dividend": "positive", "major_contract": "positive",
    "asset_purchase": "neutral", "asset_sale": "neutral",
    "m_and_a": "positive", "financing": "neutral",
    "refinancing": "neutral", "lawsuit": "negative", "pledge": "negative",
    "management_change": "neutral", "production_change": "negative",
    "product_launch": "positive", "capacity_expansion": "neutral",
    "guidance": "neutral", "government_policy": "neutral",
}

BASE_SEVERITY = {
    "earnings": 0.55, "earnings_forecast": 0.60, "earnings_revision": 0.50,
    "dividend": 0.40, "share_buyback": 0.50, "shareholder_change": 0.50,
    "management_change": 0.50, "major_contract": 0.60, "m_and_a": 0.70,
    "financing": 0.60, "refinancing": 0.50, "asset_sale": 0.50,
    "asset_purchase": 0.50, "lawsuit": 0.55, "regulatory": 0.65,
    "penalty": 0.80, "investigation": 0.80, "pledge": 0.55,
    "unpledge": 0.40, "bankruptcy": 0.90, "production_change": 0.60,
    "product_launch": 0.50, "capacity_expansion": 0.50, "guidance": 0.30,
    "government_policy": 0.70, "other": 0.15,
}

#: spec §四 点名要看的分组 -> 研究层主题
SPEC_GROUPS = {
    "监管类": ("regulatory", "investigation", "penalty"),
    "股东类": ("shareholder_reduce", "shareholder_increase",
               "shareholder_change"),
    "减持类": ("shareholder_reduce", "shareholder_change"),
    "增持类": ("shareholder_increase",),
    "质押类": ("pledge", "pledge_release", "unpledge"),
    "诉讼类": ("litigation", "lawsuit"),
    "处罚类": ("penalty",),
    "调查类": ("investigation",),
    "业绩类": ("earnings", "earnings_forecast", "earnings_revision"),
    "回购类": ("buyback", "share_buyback"),
    "并购重组类": ("mna", "asset_purchase", "asset_sale"),
    "重大合同类": ("major_contract",),
    "治理类": ("management_change", "equity_incentive", "related_party"),
    "债务/违约类": ("debt_default", "bankruptcy"),
    "程序性（非实质性）": ("procedural",),
    "其他": ("other",),
}
