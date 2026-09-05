# -*- coding: utf-8 -*-
"""Core financial metric definitions, unit normalization and sanity checks.

Phase 1 metric set (per project plan):
extracted from the report:
  revenue, cost_of_revenue, net_profit, total_assets, total_liabilities,
  net_assets, operating_cash_flow, roe (reported)
derived (computed, sanity-checked):
  roa, gross_margin, net_margin, debt_to_asset,
  revenue_growth, net_profit_growth (from the previous-year column)

If a metric cannot be extracted reliably we never guess: the pipeline
returns EXTRACTION_FAILED with a recorded reason.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

_NUM_RE = re.compile(r"-?[\d,]+(?:\.\d+)?")

# Unit multipliers to CNY for the accounting-data table header (单位：X)
UNIT_MULTIPLIERS = {
    "元": 1.0,
    "千元": 1e3,
    "万元": 1e4,
    "百万元": 1e6,
    "亿元": 1e8,
}


def parse_unit(text: str) -> tuple[Optional[float], Optional[str]]:
    """Find a unit spec in text; return (multiplier, unit_label).

    Handles '单位：万元', '单位: 百万元', '单位：人民币百万元',
    '（人民币百万元，特别注明除外）' etc.
    """
    patterns = [
        r"单位[:：为]\s*(?:人民币)?\s*(千元|万元|百万元|亿元|元)",
        r"以人民币\s*(千元|万元|百万元|亿元|元)\s*(?:列示|计|计量|计算)",
        r"[（(]\s*人民币\s*(千元|万元|百万元|亿元|元)\s*[，,）)]",
        r"[（(]\s*(千元|万元|百万元|亿元|元)\s*[，,）)]",
        r"[（(]\s*除特别注明外[，,]?\s*金额单位为人民币\s*(千元|万元|百万元|亿元|元)",
    ]
    for pat in patterns:
        m = re.search(pat, text or "")
        if m:
            label = m.group(1)
            return UNIT_MULTIPLIERS[label], label
    return None, None


def parse_number(value) -> Optional[float]:
    """Parse '1,234,567.89' / '1,234,567' / '-12.5' / '21.35%' to float."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip().replace("，", ",")
    if s in ("", "-", "—", "不适用", "N/A", "n/a", "None", "nan"):
        return None
    m = re.search(r"-?[\d,]+(?:\.\d+)?", s)
    if not m:
        return None
    return float(m.group(0).replace(",", ""))


@dataclass(frozen=True)
class MetricDef:
    name: str
    labels: tuple[str, ...]      # row-label keywords, tried in order
    kind: str                    # "amount" | "percent"
    exclude: tuple[str, ...] = ()  # label substrings that disqualify a match
    unit_mult: Optional[float] = None  # fixed multiplier when unit is known
    source: str = "report"

    def match_label(self, label: str) -> bool:
        """Exact or prefix match with a non-CJK boundary.

        '负债合计' matches '负债合计' and '负债合计(万元)' but NOT
        '流动负债合计' or '非流动负债合计'; '营业收入' does not match
        '营业收入增长率'.
        """
        label = label.strip()
        for ex in self.exclude:
            if ex in label:
                return False
        for lab in self.labels:
            if label == lab:
                return True
            if label.startswith(lab):
                rest = label[len(lab):]
                if not re.search(r"[一-鿿]", rest):
                    return True
        return False


METRICS: dict[str, MetricDef] = {
    "revenue": MetricDef("revenue", ("营业收入",), "amount"),
    "cost_of_revenue": MetricDef(
        "cost_of_revenue", ("营业成本", "其中：营业成本", "其中:营业成本"), "amount",
        exclude=("营业成本率",),
    ),
    "net_profit": MetricDef(
        "net_profit",
        ("归属于上市公司股东的净利润", "归属于母公司股东的净利润", "归母净利润",
         "归属于本行股东的净利润", "归属于本行普通股股东的净利润"),
        "amount",
        exclude=("扣除非经常性损益", "其他", "少数股东"),
    ),
    "total_assets": MetricDef(
        "total_assets", ("资产总计", "总资产", "资产合计", "负债及股东权益合计"),
        "amount",
        exclude=("总资产报酬率", "总资产周转率"),
    ),
    "total_liabilities": MetricDef(
        "total_liabilities", ("负债合计", "负债总计", "总负债", "负债总额"), "amount"
    ),
    "net_assets": MetricDef(
        "net_assets",
        ("归属于上市公司股东的净资产", "归属于母公司股东的净资产",
         "归属于母公司股东权益", "归属于母公司所有者权益",
         "归属于本行股东的净资产", "归属于本行普通股股东的净资产",
         "归属于本行股东权益"),
        "amount",
        exclude=("增减",),
    ),
    "operating_cash_flow": MetricDef(
        "operating_cash_flow", ("经营活动产生的现金流量净额", "经营活动现金流量净额"), "amount"
    ),
    "roe": MetricDef("roe", ("加权平均净资产收益率",), "percent",
                     exclude=("扣除非经常性损益",)),
}


# Derived metrics -----------------------------------------------------------

def derive_metrics(values: dict) -> dict:
    """Compute derived metrics from extracted base values.

    Returns {name: (value|None, validation_status, note)}; None value means
    EXTRACTION_FAILED-style absence (never guessed).
    """
    out = {}
    rev = values.get("revenue")
    np_ = values.get("net_profit")
    ta = values.get("total_assets")
    tl = values.get("total_liabilities")
    na = values.get("net_assets")
    cost = values.get("cost_of_revenue")

    def frac(a, b):
        if a is not None and b not in (None, 0):
            return a / b
        return None

    out["net_margin"] = frac(np_, rev)
    out["roa"] = frac(np_, ta)
    out["debt_to_asset"] = frac(tl, ta)
    if rev is not None and cost is not None and rev != 0:
        gm = (rev - cost) / rev
        out["gross_margin"] = gm
    else:
        out["gross_margin"] = None
    return out


def sanity_checks(metric: str, value: Optional[float], context: dict) -> tuple[str, Optional[str]]:
    """Return (validation_status, note).

    status: VALID | VALIDATION_WARNING | EXTRACTION_FAILED
    """
    if value is None:
        return "EXTRACTION_FAILED", context.get("reason")
    if metric == "roe":
        # reported ROE vs net_profit / net_assets (average equity would be
        # better; year-end equity is a first-order check)
        np_, na = context.get("net_profit"), context.get("net_assets")
        if np_ is not None and na not in (None, 0):
            calc = np_ / na
            if abs(value - calc) > 0.02:
                return "VALIDATION_WARNING", (
                    f"reported roe {value:.4f} vs net_profit/net_assets "
                    f"{calc:.4f} differ by >2pp"
                )
    if metric == "net_margin":
        if not (-0.5 <= value <= 0.8):
            return "VALIDATION_WARNING", f"net_margin out of plausible range: {value:.4f}"
        rev = context.get("revenue")
        np_ = context.get("net_profit")
        if rev is not None and np_ is not None and abs(value - np_ / rev) > 0.02:
            return "VALIDATION_WARNING", "net_margin inconsistent with revenue/net_profit"
    if metric == "debt_to_asset":
        if not (0.0 <= value <= 1.5):
            return "VALIDATION_WARNING", f"debt_to_asset out of plausible range: {value:.4f}"
    if metric in ("gross_margin", "roa"):
        if not (-1.0 <= value <= 1.0):
            return "VALIDATION_WARNING", f"{metric} out of plausible range: {value:.4f}"
    return "VALID", None
