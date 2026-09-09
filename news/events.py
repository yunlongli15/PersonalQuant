# -*- coding: utf-8 -*-
"""Rule-based event extraction (title keyword classification).

First version uses ONLY keyword/title rules (no LLM): cheap, explainable,
fully auditable. Each rule carries a DEFAULT direction — which is a
CANDIDATE, never truth: the empirical direction per (event_type) is
estimated on the research period (2018-2021) and the factors consume that
estimate. Rules are ordered by specificity (解除质押 before 质押 etc.).

Output: NewsEvent with event_type / direction / importance / confidence
(rule confidence = 0.7 for specific single-keyword matches, 0.4 for
ambiguous ones) + extraction_method='rule'.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .schema import NewsDocument, NewsEvent, hash_text

RULES_VERSION = "1.0"


@dataclass(frozen=True)
class Rule:
    event_type: str
    direction: str            # rule default (candidate only)
    importance: float
    includes: Tuple[str, ...]
    excludes: Tuple[str, ...] = ()
    confidence: float = 0.7


# ordered: specific first (解除质押 before 质押; 资产购买 before 收购 …)
RULES: List[Rule] = [
    Rule("unpledge", "positive", 0.40, ("解除质押", "解押", "质押解除")),
    Rule("penalty", "negative", 0.80, ("行政处罚", "罚款", "处罚决定")),
    Rule("investigation", "negative", 0.80, ("立案调查", "立案告知书",
                                              "被立案", "接受调查",
                                              "涉嫌信息披露违法违规")),
    Rule("bankruptcy", "negative", 0.90, ("破产", "重整", "清算",
                                          "预重整")),
    Rule("regulatory", "negative", 0.65, ("问询函", "关注函", "警示函",
                                          "监管函", "监管措施", "行政监管",
                                          "退市风险警示", "风险警示")),
    Rule("earnings_forecast", "neutral", 0.60, ("业绩预告", "业绩预增",
                                                "业绩预减", "业绩预亏",
                                                "预增公告", "预减公告",
                                                "扭亏")),
    Rule("earnings_revision", "neutral", 0.50, ("业绩快报", "业绩修正",
                                                "业绩更正")),
    Rule("earnings", "neutral", 0.55, ("年年度报告", "年度报告", "半年度报告",
                                       "第一季度报告", "第三季度报告",
                                       "季度报告", "定期报告", "年报")),
    Rule("share_buyback", "positive", 0.50, ("回购",),
         excludes=("回购注销公告",)),
    Rule("shareholder_change", "negative", 0.50, ("减持",)),
    Rule("shareholder_change", "positive", 0.50, ("增持",)),
    Rule("shareholder_change", "neutral", 0.45, ("权益变动", "股东变动")),
    Rule("dividend", "positive", 0.40, ("利润分配", "权益分派", "分红",
                                        "派息", "现金红利")),
    Rule("major_contract", "positive", 0.60, ("中标", "重大合同", "合同签订",
                                              "签署合同")),
    Rule("asset_purchase", "neutral", 0.50, ("资产购买", "购买资产")),
    Rule("asset_sale", "neutral", 0.50, ("出售资产", "资产出售", "股权转让",
                                          "出售")),
    Rule("m_and_a", "positive", 0.70, ("收购", "并购", "重大资产重组",
                                       "吸收合并", "要约收购")),
    Rule("financing", "neutral", 0.60, ("非公开发行", "定向增发", "增发",
                                        "配股", "可转换公司债券", "可转债",
                                        "发行股票", "募集资金")),
    Rule("refinancing", "neutral", 0.50, ("再融资", "公司债券", "中期票据",
                                          "短期融资券")),
    Rule("lawsuit", "negative", 0.55, ("诉讼", "仲裁")),
    Rule("pledge", "negative", 0.55, ("质押",)),
    Rule("management_change", "neutral", 0.50, ("董事长", "总经理", "财务总监",
                                                "独立董事"),
         excludes=("会计师事务所", "审计机构", "提名委员会", "战略委员会")),
    Rule("production_change", "negative", 0.60, ("停产", "复产", "限产",
                                                 "产能调整")),
    Rule("product_launch", "positive", 0.50, ("获批上市", "注册证书",
                                              "新产品", "获得批件",
                                              "获批临床")),
    Rule("capacity_expansion", "neutral", 0.50, ("扩产", "产能扩张",
                                                 "项目投资", "投资建设")),
    Rule("guidance", "neutral", 0.30, ("业绩说明会", "经营情况")),
    Rule("government_policy", "neutral", 0.70, ("政策", "规划纲要")),
]

# importance defaults per event type (rule tier, recorded in extraction)
IMPORTANCE = {
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

RULES_BY_TYPE = {r.event_type: r for r in RULES}


def classify_title(title: str) -> Tuple[str, str, float, float]:
    """Return (event_type, rule_direction, importance, confidence)."""
    t = title or ""
    for rule in RULES:
        if any(x in t for x in rule.excludes):
            continue
        if any(x in t for x in rule.includes):
            return (rule.event_type, rule.direction,
                    IMPORTANCE[rule.event_type], rule.confidence)
    return "other", "neutral", IMPORTANCE["other"], 0.3


def extract_events(docs: List[NewsDocument]) -> List[NewsEvent]:
    """Classify documents into NewsEvents (availability computed via the
    PIT rules; event_time is not inferred in the rule tier)."""
    from .pit import document_availability

    out: List[NewsEvent] = []
    for doc in docs:
        etype, direction, importance, confidence = classify_title(doc.title)
        avail, unknown = document_availability(doc)
        out.append(NewsEvent(
            event_id=hash_text(doc.document_id, etype)[:24],
            document_id=doc.document_id,
            symbol=doc.symbol,
            event_type=etype,
            publication_time=doc.published_at,
            availability_time=avail,
            availability_unknown=unknown,
            direction=direction,
            importance=importance,
            confidence=confidence,
            extraction_method="rule",
            extraction_version=RULES_VERSION,
        ))
    return out


def rule_stats(titles: List[str]) -> dict:
    """Event-type distribution of a title sample (audit / coverage)."""
    counts: dict = {}
    for t in titles:
        et, *_ = classify_title(t)
        counts[et] = counts.get(et, 0) + 1
    return counts
