# -*- coding: utf-8 -*-
"""微结构 / 行为类候选因子（新增一批，供研究与挖掘使用）。

与 factors/technical.py 相同的严格后视约定：只用 signal date 之前的
数据，逐股滚动，未来数据投毒不变（tests/factors/test_no_future_data.py）。

这一批的选取理由（都是 A 股有文献/经验支持、而现有因子库里没有的）：

  隔夜 / 日内收益分解   A 股隔夜收益与日内收益的预测方向相反
                        （隔夜往往反转、日内往往延续），把日收益拆开
                        比单一动量/反转多一层信息。
  彩票效应 (MAX)        投资者偏好高偏度/极端正收益的股票，这类股票
                        后续跑输（Bali et al. 的 MAX 效应）。
  偏度                 负偏度溢价在 A 股同样被反复观察到。
  Amihud 非流动性       单位成交额引起的价格冲击，流动性溢价代理。
  52 周高点距离         接近历史高点的股票后续更强（George & Hwang）。
  涨跌停统计            A 股独有：涨停/跌停次数直接反映资金与情绪极端状态。
  换手率波动            换手率的不稳定性（情绪不稳定）而非水平。
  量价相关              放量上涨 vs 放量下跌的区别。
  Parkinson 波动        用高低价区间估计波动，比收盘价序列更有效。
  跳空频率              跳空开盘的频率，反映信息冲击的连续性。
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .base import FactorData
from .registry import register


def _out(panel: pd.DataFrame, dates) -> pd.DataFrame:
    if dates is None:
        return panel
    return panel.reindex(pd.DatetimeIndex(dates))


def _ret(data: FactorData) -> pd.DataFrame:
    """Adjusted daily returns (NOT filled — suspension days stay NaN)."""
    return data.adj_close.pct_change()


# --- 隔夜 / 日内分解 ---------------------------------------------------------

@register(dict(
    factor_name="overnight_return_20", category="microstructure",
    formula="mean(open[t]/adj_close[t-1]-1, 20d)",
    source="market", required_fields=["open", "close", "factor"],
    pit=True, direction="neutral",
    description="20 日平均隔夜收益（开盘/昨收-1）—— A 股隔夜部分常反转",
    version="1.0", status="candidate",
))
def overnight_return_20(data: FactorData, dates=None):
    prev_adj_close = data.adj_close.shift(1)
    on = data.close_raw.copy()
    on[:] = np.nan
    bar_open = data.bars.pivot_table(index="trade_date", columns="symbol",
                                     values="open", aggfunc="last")
    bar_open = bar_open.reindex(data.calendar)
    overnight = bar_open / prev_adj_close - 1.0
    return _out(overnight.rolling(20, min_periods=10).mean(), dates)


@register(dict(
    factor_name="intraday_return_20", category="microstructure",
    formula="mean(adj_close[t]/open[t]-1, 20d)",
    source="market", required_fields=["open", "close", "factor"],
    pit=True, direction="neutral",
    description="20 日平均日内收益（收盘/开盘-1）—— A 股日内部分常延续",
    version="1.0", status="candidate",
))
def intraday_return_20(data: FactorData, dates=None):
    bar_open = data.bars.pivot_table(index="trade_date", columns="symbol",
                                     values="open", aggfunc="last")
    bar_open = bar_open.reindex(data.calendar)
    intraday = data.adj_close / bar_open - 1.0
    return _out(intraday.rolling(20, min_periods=10).mean(), dates)


@register(dict(
    factor_name="overnight_intraday_ratio_20", category="microstructure",
    formula="sum(overnight,20d) / sum(intraday,20d)",
    source="market", required_fields=["open", "close", "factor"],
    pit=True, direction="neutral",
    description="隔夜与日内累计收益之比（口径相对化，跨股可比）",
    version="1.0", status="candidate",
))
def overnight_intraday_ratio_20(data: FactorData, dates=None):
    bar_open = data.bars.pivot_table(index="trade_date", columns="symbol",
                                     values="open", aggfunc="last")
    bar_open = bar_open.reindex(data.calendar)
    overnight = bar_open / data.adj_close.shift(1) - 1.0
    intraday = data.adj_close / bar_open - 1.0
    on_sum = overnight.rolling(20, min_periods=10).sum()
    id_sum = intraday.rolling(20, min_periods=10).sum()
    denom = id_sum.abs().replace(0.0, np.nan)
    return _out(on_sum / denom, dates)


# --- 彩票 / 偏度 -------------------------------------------------------------

@register(dict(
    factor_name="max_return_20", category="microstructure",
    formula="mean(largest 3 daily returns in 20d)",
    source="market", required_fields=["close", "factor"],
    pit=True, direction="negative",
    description="彩票效应：极端正收益（MAX）越强，后续越容易跑输",
    version="1.0", status="candidate",
))
def max_return_20(data: FactorData, dates=None):
    r = _ret(data)
    top3 = r.rolling(20, min_periods=15).apply(
        lambda x: np.nanmean(np.sort(x[~np.isnan(x)])[-3:])
        if np.sum(~np.isnan(x)) >= 10 else np.nan, raw=True)
    return _out(top3, dates)


@register(dict(
    factor_name="skewness_60", category="microstructure",
    formula="skew(returns, 60d)",
    source="market", required_fields=["close", "factor"],
    pit=True, direction="negative",
    description="收益偏度（负偏度溢价：高偏度股票后续较弱）",
    version="1.0", status="candidate",
))
def skewness_60(data: FactorData, dates=None):
    return _out(_ret(data).rolling(60, min_periods=40).skew(), dates)


@register(dict(
    factor_name="kurtosis_60", category="microstructure",
    formula="kurt(returns, 60d)",
    source="market", required_fields=["close", "factor"],
    pit=True, direction="neutral",
    description="收益峰度（尾部厚度 / 极端波动频率）",
    version="1.0", status="candidate",
))
def kurtosis_60(data: FactorData, dates=None):
    return _out(_ret(data).rolling(60, min_periods=40).kurt(), dates)


# --- 流动性 / 冲击 -----------------------------------------------------------

@register(dict(
    factor_name="amihud_20", category="liquidity",
    formula="mean(|ret| / amount_cny, 20d) * 1e9",
    source="market", required_fields=["close", "factor", "amount"],
    pit=True, direction="positive",
    description="Amihud 非流动性（单位成交额的价格冲击，放大 1e9）",
    version="1.0", status="candidate",
))
def amihud_20(data: FactorData, dates=None):
    r = _ret(data).abs()
    amt = data.amount_cny.replace(0.0, np.nan)
    illiq = (r / amt) * 1e9
    return _out(illiq.rolling(20, min_periods=10).mean(), dates)


@register(dict(
    factor_name="turnover_volatility_20", category="liquidity",
    formula="std(turnover, 20d)",
    source="market", required_fields=["turnover"],
    pit=True, direction="neutral",
    description="换手率的波动性（情绪不稳定程度，区别于换手率水平）",
    version="1.0", status="candidate",
))
def turnover_volatility_20(data: FactorData, dates=None):
    if data.turnover is None:
        return _out(pd.DataFrame(index=data.calendar), dates)
    return _out(data.turnover.rolling(20, min_periods=10).std(), dates)


@register(dict(
    factor_name="amount_share_20", category="liquidity",
    formula="amount_cny[t] / mean(amount_cny, 20d)",
    source="market", required_fields=["amount", "volume"],
    pit=True, direction="neutral",
    description="当日成交额相对自身 20 日均值（放量倍数，单股内归一）",
    version="1.0", status="candidate",
))
def amount_share_20(data: FactorData, dates=None):
    amt = data.amount_cny
    return _out(amt / amt.rolling(20, min_periods=10).mean(), dates)


# --- 位置 / 波动 -------------------------------------------------------------

@register(dict(
    factor_name="high_52w_proximity", category="price_position",
    formula="close / max(close, 250d)",
    source="market", required_fields=["close", "factor"],
    pit=True, direction="positive",
    description="距 52 周高点比例（接近高点者后续更强，George-Hwang）",
    version="1.0", status="candidate",
))
def high_52w_proximity(data: FactorData, dates=None):
    adj = data.adj_close
    hi = adj.rolling(250, min_periods=120).max()
    return _out(adj / hi.replace(0.0, np.nan), dates)


@register(dict(
    factor_name="parkinson_vol_20", category="volatility",
    formula="sqrt(mean(ln(high/low)^2,20d)/(4 ln2))",
    source="market", required_fields=["high", "low"],
    pit=True, direction="neutral",
    description="Parkinson 高低价波动率（比收盘价波动率更有效的日内波动估计）",
    version="1.0", status="candidate",
))
def parkinson_vol_20(data: FactorData, dates=None):
    hi = data.bars.pivot_table(index="trade_date", columns="symbol",
                               values="high", aggfunc="last") \
        .reindex(data.calendar)
    lo = data.bars.pivot_table(index="trade_date", columns="symbol",
                               values="low", aggfunc="last") \
        .reindex(data.calendar)
    ratio = (hi / lo.replace(0.0, np.nan))
    log2 = np.log(ratio) ** 2
    var = log2.rolling(20, min_periods=10).mean() / (4.0 * np.log(2.0))
    return _out(np.sqrt(var.clip(lower=0.0)), dates)


@register(dict(
    factor_name="gap_count_20", category="microstructure",
    formula="count(|open/prev_close-1| > 3%, 20d) / 20",
    source="market", required_fields=["open", "close", "factor"],
    pit=True, direction="neutral",
    description="跳空频率（信息冲击的连续性 / 情绪化交易程度）",
    version="1.0", status="candidate",
))
def gap_count_20(data: FactorData, dates=None):
    bar_open = data.bars.pivot_table(index="trade_date", columns="symbol",
                                     values="open", aggfunc="last") \
        .reindex(data.calendar)
    gap = (bar_open / data.adj_close.shift(1) - 1.0).abs()
    return _out((gap > 0.03).astype(float).rolling(20, min_periods=10).mean(),
                dates)


# --- A 股特有：涨跌停 --------------------------------------------------------

@register(dict(
    factor_name="limit_up_count_20", category="microstructure",
    formula="count(ret >= 9.5%, 20d)",
    source="market", required_fields=["close", "factor"],
    pit=True, direction="neutral",
    description="20 日内涨停次数（资金关注度 / 情绪极值，A 股特有）",
    version="1.0", status="candidate",
))
def limit_up_count_20(data: FactorData, dates=None):
    r = _ret(data)
    return _out((r >= 0.095).astype(float).rolling(20, min_periods=10).sum(),
                dates)


@register(dict(
    factor_name="limit_down_count_20", category="microstructure",
    formula="count(ret <= -9.5%, 20d)",
    source="market", required_fields=["close", "factor"],
    pit=True, direction="negative",
    description="20 日内跌停次数（风险事件频率，A 股特有）",
    version="1.0", status="candidate",
))
def limit_down_count_20(data: FactorData, dates=None):
    r = _ret(data)
    return _out((r <= -0.095).astype(float).rolling(20, min_periods=10).sum(),
                dates)


# --- 量价关系 ---------------------------------------------------------------

@register(dict(
    factor_name="volume_price_corr_20", category="volume",
    formula="corr(volume, ret, 20d)",
    source="market", required_fields=["volume", "close", "factor"],
    pit=True, direction="neutral",
    description="量价相关性（放量上涨 vs 放量下跌的方向性）",
    version="1.0", status="candidate",
))
def volume_price_corr_20(data: FactorData, dates=None):
    r = _ret(data)
    vol = data.volume_shares
    corr = vol.rolling(20, min_periods=15).corr(r)
    return _out(corr, dates)


@register(dict(
    factor_name="volume_trend_5_60", category="volume",
    formula="mean(volume,5d) / mean(volume,60d)",
    source="market", required_fields=["volume"],
    pit=True, direction="neutral",
    description="短期/长期成交量之比（量能趋势，两窗口比值抵消源缩放）",
    version="1.0", status="candidate",
))
def volume_trend_5_60(data: FactorData, dates=None):
    v = data.volume_raw
    fast = v.rolling(5, min_periods=3).mean()
    slow = v.rolling(60, min_periods=30).mean()
    return _out(fast / slow.replace(0.0, np.nan), dates)
