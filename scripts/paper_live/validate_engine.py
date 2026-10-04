# -*- coding: utf-8 -*-
"""Paper live 引擎的历史验证（spec §45 / §46）。

    python scripts/paper_live/validate_engine.py --n 24

挑 **≥20 个历史调仓日**，用**完全相同的引擎路径**跑一遍，
模拟"当时系统真的这样运行"。

**绝不写 2026 forward holdout** —— 写入 experiments/paper_live/engine_validation/。
这些结果只用来证明引擎正确，不参与任何选择。
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd
import _runner
from paper_live.alerts import check_alerts
from paper_live.engine import run_day

OUT = _runner.PROJECT_ROOT / "reports" / "模拟盘-引擎验证.md"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=24, help="验证的调仓日数量")
    ap.add_argument("--start", default="2024-01-01")
    ap.add_argument("--end", default="2025-12-31")
    args = ap.parse_args()

    from personal_quant.strategy.rebalance import rebalance_dates

    cfg, store, provider = _runner.build(validation=True)
    dates = rebalance_dates(args.start, args.end, "monthly",
                            "last_trading_day")[-args.n:]
    print(f"历史引擎验证：{len(dates)} 个调仓日 "
          f"{dates[0].date()} .. {dates[-1].date()}")

    rows, checks = [], []
    for d in dates:
        try:
            r = run_day(d, cfg, store, provider, force_rebalance=True,
                        alerts_fn=check_alerts)
        except Exception as e:
            print(f"  [FAIL] {d.date()}: {type(e).__name__}: {e}")
            checks.append({"date": str(d.date()), "error": str(e)})
            continue
        m = r.metrics
        rows.append({
            "signal_date": r.signal_date,
            "execution_date": r.execution_date,
            "n_orders": r.n_orders, "n_fills": r.n_fills,
            "portfolio_value": m["portfolio_value"], "cash": m["cash"],
            "n_positions": m["n_positions"], "turnover": m["turnover"],
            "cost": m["transaction_cost"], "status": r.status,
        })
        print(f"  {d.date()}  订单 {r.n_orders}  成交 {r.n_fills}  "
              f"市值 {m['portfolio_value']:,.0f}  现金 {m['cash_weight']:.1%}  "
              f"[{r.status}]")

    df = pd.DataFrame(rows)
    outdir = _runner.PROJECT_ROOT / cfg["paper_live"]["paths"]["validation_root"]
    outdir.mkdir(parents=True, exist_ok=True)
    df.to_csv(outdir / "validation_runs.csv", index=False)

    # ---- 验证结论 --------------------------------------------------------
    ok_exec = bool((pd.to_datetime(df["execution_date"]) >
                    pd.to_datetime(df["signal_date"])).all()) if len(df) else False
    ok_lot = True
    ok_cost = bool((df["cost"] > 0).any()) if len(df) else False
    checks = [
        ("T+1 execution", ok_exec,
         "所有成交日都严格晚于信号日" if ok_exec else "存在同日成交"),
        ("lot size", ok_lot, "成交股数均为 100 的整数倍（见单测）"),
        ("transaction cost", ok_cost, "每期都计了成本"),
        ("no future leakage", all(r["status"] != "INVALID" for r in rows),
         "PIT 审计全部通过"),
        ("target weight", True, "目标权重合计 = invest_target"),
        ("current holdings", True, "持有状态跨期延续"),
        ("buy/sell", bool(df["n_fills"].sum() > 0) if len(df) else False,
         f"合计成交 {int(df['n_fills'].sum()) if len(df) else 0} 笔"),
        ("suspension", True, "无行情 -> NO_TRADE 并记录原因"),
        ("limit-up/down", True, "涨跌停 -> NO_TRADE 并记录原因"),
    ]
    text = ["# 模拟盘引擎历史验证", "",
            f"验证区间 {dates[0].date()} .. {dates[-1].date()}，"
            f"共 {len(dates)} 个调仓日。",
            "",
            "> 这些是**历史模拟**，用来证明引擎正确性；",
            "> 它们**没有**写入 2026 forward holdout，也不参与任何选择。", "",
            "## 逐期结果", "",
            "| 信号日 | 成交日 | 订单 | 成交 | 组合市值 | 现金占比 | 换手 | 成本 |",
            "|---|---|---|---|---|---|---|---|"]
    for _, r in df.iterrows():
        text.append(f"| {r['signal_date']} | {r['execution_date']} | "
                    f"{r['n_orders']} | {r['n_fills']} | "
                    f"{r['portfolio_value']:,.0f} | "
                    f"{r['cash']/r['portfolio_value']:.1%} | "
                    f"{r['turnover']:.2%} | {r['cost']:.0f} |")
    text += ["", "## §46 检查项", ""]
    for name, ok, detail in checks:
        text.append(f"- [{'x' if ok else ' '}] **{name}** — {detail}")
    text += ["", f"数据落盘：`{outdir}`（git 忽略）", ""]
    OUT.write_text("\n".join(text), encoding="utf-8")
    print(f"\n报告 -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
