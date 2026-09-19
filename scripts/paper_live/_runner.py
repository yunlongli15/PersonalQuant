# -*- coding: utf-8 -*-
"""paper_live 脚本共用装配（run_daily / run_rebalance 的唯一差别是日期语义）。"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd


def build(cfg_path=None, validation: bool = False):
    """返回 (cfg, store, provider)。validation=True 时写另一个 root。"""
    from paper_live import config as plcfg
    from paper_live.data import LiveDataProvider
    from paper_live.store import ForwardStore

    cfg = plcfg.load_config(cfg_path)
    s = cfg["paper_live"]
    root = PROJECT_ROOT / (s["paths"]["validation_root"] if validation
                           else s["paths"]["root"])
    store = ForwardStore(root, forward_start=s["forward_start_date"])
    provider = LiveDataProvider(cfg)
    return cfg, store, provider


def resolve_signal_date(provider, date=None) -> pd.Timestamp:
    if date:
        return pd.Timestamp(date)
    d = provider.latest_trading_day()
    if d is None:
        raise RuntimeError("交易日历为空，无法确定信号日")
    return d


def emit(result, verbose: bool = True) -> None:
    if not verbose:
        return
    print(f"\n=== {result.signal_date}  "
          f"{'调仓日' if result.is_rebalance else '监控日'}  "
          f"状态 {result.status} ===")
    if result.execution_date:
        print(f"成交日（T+1 开盘）：{result.execution_date}")
    print(f"预测 {result.n_predictions} 只 / 订单 {result.n_orders} / "
          f"成交 {result.n_fills}")
    m = result.metrics
    if m:
        print(f"组合市值 {m['portfolio_value']:,.0f}  现金 {m['cash']:,.0f} "
              f"({m['cash_weight']:.1%})  持仓 {m['n_positions']} 只")
        print(f"累计 {m['cumulative_return']:+.2%}  回撤 {m['drawdown']:+.2%}  "
              f"换手 {m['turnover']:.2%}  成本 {m['transaction_cost']:,.0f}")
    for k, v in (result.drift or {}).items():
        print(f"  drift[{k}] = {v.get('status')}")
    for a in result.alerts:
        print(f"  [{a['level']}] {a['code']}: {a['detail']}")
    if result.dry_run:
        print("  (dry-run：未写入 forward_holdout)")
    else:
        n = len([w for w in result.writes if w.get("written")])
        first = result.writes[0].get("path") if result.writes else ""
        print(f"  写入 {n} 项 -> {first}")
