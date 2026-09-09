# -*- coding: utf-8 -*-
"""Rule-based event extraction: every event type + direction candidates."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from news.events import RULES_VERSION, classify_title, extract_events, rule_stats
from news.schema import NewsDocument

CASES = [
    ("earnings", "2024年年度报告"),
    ("earnings", "2024年半年度报告摘要"),
    ("earnings_forecast", "2024年度业绩预告"),
    ("earnings_forecast", "业绩预增公告"),
    ("earnings_revision", "2024年度业绩快报"),
    ("dividend", "2024年年度权益分派实施公告"),
    ("share_buyback", "关于以集中竞价交易方式回购公司股份的公告"),
    ("shareholder_change", "关于持股5%以上股东减持股份计划的预披露公告"),
    ("shareholder_change", "关于控股股东增持公司股份计划的公告"),
    ("management_change", "关于公司总经理辞职的公告"),
    ("major_contract", "关于项目中标的公告"),
    ("m_and_a", "重大资产重组进展公告"),
    ("financing", "2024年度向特定对象发行股票募集说明书"),
    ("refinancing", "关于发行公司债券的公告"),
    ("asset_sale", "关于出售子公司股权的公告"),
    ("asset_purchase", "关于购买资产的公告"),
    ("lawsuit", "关于公司涉及诉讼的公告"),
    ("regulatory", "关于收到上海证券交易所问询函的公告"),
    ("regulatory", "关于公司股票交易被实施退市风险警示的公告"),
    ("penalty", "关于收到行政处罚决定书的公告"),
    ("investigation", "关于收到中国证监会立案告知书的公告"),
    ("pledge", "关于控股股东部分股份质押的公告"),
    ("unpledge", "关于控股股东部分股份解除质押的公告"),
    ("bankruptcy", "关于公司破产重整的公告"),
    ("production_change", "关于生产基地停产的公告"),
    ("product_launch", "关于新产品获批上市的公告"),
    ("capacity_expansion", "关于投资建设新生产基地的公告"),
    ("guidance", "关于召开2024年度业绩说明会的公告"),
]


def test_every_event_type_classifies():
    for expected, title in CASES:
        et, direction, importance, confidence = classify_title(title)
        assert et == expected, f"{title!r} -> {et}, expected {expected}"
        assert 0.0 <= importance <= 1.0
        assert 0.0 <= confidence <= 1.0


def test_direction_candidates():
    _, d1, *_ = classify_title("关于减持公司股份计划的公告")
    assert d1 == "negative"
    _, d2, *_ = classify_title("关于增持公司股份计划的公告")
    assert d2 == "positive"
    _, d3, *_ = classify_title("2024年年度报告")
    assert d3 == "neutral"


def test_routine_announcements_are_other():
    for title in ("关于续聘会计师事务所的公告", "董事会决议公告",
                  "关于召开临时股东大会的通知", "公司章程修订公告"):
        et, _, importance, _ = classify_title(title)
        assert et == "other"
        assert importance <= 0.2


def test_no_forced_classification_unknown_stays_other():
    et, *_ = classify_title("公告")
    assert et == "other"


def test_extract_events_produces_schema_events():
    doc = NewsDocument(document_id="d1", source="sse", source_url="u",
                       title="关于股份回购的公告", symbol="600519.SH",
                       published_at="2025-04-01 19:30")
    events = extract_events([doc])
    assert len(events) == 1
    e = events[0]
    assert e.event_type == "share_buyback"
    assert e.symbol == "600519.SH"
    assert e.extraction_method == "rule"
    assert e.extraction_version == RULES_VERSION
    assert e.availability_time is not None


def test_rule_stats_counts():
    stats = rule_stats(["回购公告", "回购进展", "年报"])
    assert stats["share_buyback"] == 2
    assert stats["earnings"] == 1
