# -*- coding: utf-8 -*-
"""daily_exit_paper_v1 每日运行入口（独立实验，PHASE 5）。

    python scripts/quant/run_daily_exit_paper.py --capital 66000          # 首次
    python scripts/quant/run_daily_exit_paper.py                          # 之后每天
    python scripts/quant/run_daily_exit_paper.py --date 2026-10-08
    python scripts/quant/run_daily_exit_paper.py --dry-run                # 只读
    python scripts/quant/run_daily_exit_paper.py --show-state             # 只看状态
    python scripts/quant/run_daily_exit_paper.py --reconcile              # 只对账

**独立运行**：不接入 run_daily.py，不碰 nightly workflow，不写 forward_holdout，
不碰财富库。研究用途，永不自动下单。
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from daily_exit_paper import config as C           # noqa: E402
from daily_exit_paper import engine, ledger, preflight as PF  # noqa: E402
from daily_exit_paper import state as S, store as ST  # noqa: E402
from daily_exit_paper import report as R            # noqa: E402


def _prev_equity(store: ST.ExperimentStore, run_date: str):
    """上一次运行记录的组合市值（用于当日盈亏）。"""
    dates = [d for d in store.snapshot_dates("daily") if d < run_date]
    if not dates:
        return None
    snap = store.read_snapshot("daily", dates[-1]) or {}
    return (snap.get("totals") or {}).get("portfolio_value")


def _safe_stdout() -> None:
    """控制台编码（本机是 GBK）编不出的字符只降级成 '?'，不让整份报告崩掉。

    中文在 GBK 下本来就正常，所以**不改编码**、只放宽错误策略 ——
    改成 utf-8 会让真正的 GBK 终端显示成乱码。
    """
    try:
        sys.stdout.reconfigure(errors="replace")
    except Exception:                                        # noqa: BLE001
        pass


def main() -> int:
    _safe_stdout()
    ap = argparse.ArgumentParser(description="daily_exit_paper_v1 每日运行")
    ap.add_argument("--date", default=None,
                    help="推进到哪一天（默认：数据里最后一个已观测交易日）")
    ap.add_argument("--capital", type=float, default=None,
                    help="实验本金（仅首次需要；之后锁定，改本金必须新建版本）")
    ap.add_argument("--dry-run", action="store_true",
                    help="只读：不写账本、不建订单、不改状态")
    ap.add_argument("--show-state", action="store_true",
                    help="只显示当前状态，不推进")
    ap.add_argument("--reconcile", action="store_true",
                    help="只做对账，不推进")
    ap.add_argument("--preflight", action="store_true",
                    help="只做上线前只读检查（数据新鲜度 / 日历 / 特征日期 / 信号）")
    ap.add_argument("--quiet-preflight", action="store_true",
                    help="不打印 preflight 块（默认每次都打印）")
    ap.add_argument("--max-sessions", type=int, default=None,
                    help="本次最多推进几个交易日（默认不限，用于追赶）")
    ap.add_argument("--json", action="store_true", help="输出机器可读结果")
    ap.add_argument("--config", default=None,
                    help="实验配置路径（默认 config/daily_exit_paper_v1.yaml）。"
                         "每个实验有自己的配置、目录和账本，"
                         "用这个参数选择跑哪一个。")
    args = ap.parse_args()

    cfg = C.load_config(Path(args.config) if args.config else None)
    s_cfg = C.validate(cfg)
    root = C.PROJECT_ROOT / s_cfg["paths"]["root"]
    store = ST.ExperimentStore(root)
    market = engine.LiveMarket(
        signal_strategy=s_cfg.get("signal_strategy") or engine.PINNED_STRATEGY)

    # 上线前只读检查：**永远先跑**。三个时间（系统运行日 / 行情最新日 /
    # 信号日）必须分开说清楚，否则最容易把"历史"当成"今天"。
    pf = PF.run_preflight(market, cfg, capital=args.capital)
    if not args.quiet_preflight or args.preflight:
        print(PF.render_preflight(pf, capital=args.capital))
        print()
    if args.preflight:
        return 0 if pf["ok"] else 1

    if args.show_state or args.reconcile:
        st = store.read_state()
        if st is None:
            print(f"实验尚未开始（{root} 里没有 state.json）。"
                  f"先跑一次：python scripts/quant/run_daily_exit_paper.py "
                  f"--capital <本金>")
            return 0
        prices = market.closes(list(st.get("positions") or {}),
                               st.get("as_of")) if st.get("positions") else {}
        if args.reconcile:
            totals = ledger.reconcile(st, store.read_ledger(), prices)
            print(json.dumps(totals, ensure_ascii=False, indent=2,
                             default=str))
            print("\n对账通过 [OK]（账本重算现金 == state 现金）")
            return 0
        totals = ledger.check_invariants(st, prices)
        print(R.render_state(st, s_cfg, prices, totals))
        return 0

    # 检查不过就不许**写**。dry-run 仍然可以跑（它什么都不写，
    # 正好用来观察"哪里不对"）。
    if not pf["ok"] and not args.dry_run:
        print("[REFUSED] 上线前检查未通过，拒绝写入。"
              "先修数据（见上面的 PREFLIGHT 块），或加 --dry-run 只观察。")
        return 2

    first_official_run = (not args.dry_run
                          and store.read_experiment() is None)
    try:
        res = engine.run(run_date=args.date, capital=args.capital,
                         dry_run=args.dry_run, cfg=cfg, store=store,
                         market=market, max_sessions=args.max_sessions)
    except (engine.EngineError, C.ConfigError, C.ConfigDrift,
            ledger.ReconciliationError, ST.AlreadyWritten) as e:
        print(f"[REFUSED] {type(e).__name__}: {e}")
        return 2
    except ledger.ReconciliationError as e:                  # pragma: no cover
        print(f"[RECONCILE FAILED] {e}")
        return 3

    if args.json:
        print(json.dumps(res.as_dict(), ensure_ascii=False, indent=2,
                         default=str))
        return 0

    exp = store.read_experiment() or {}
    held = list((res.state.get("positions") or {}))
    prices = market.closes(held, res.run_date) if held else {}
    overrides = [o for rep in res.reports for o in rep.overrides]

    if first_official_run:
        # 正式实验的第一次运行：把"从哪一刻、哪个信号日、多少本金开始"
        # 钉在日志里（spec §15）。
        print(R.render_start_banner(exp, s_cfg, pf,
                                    next_exec=pf.get("next_trading_date")))
        print()
    print(R.render_daily(res, s_cfg, exp, prices,
                         previous_value=_prev_equity(store, res.run_date),
                         overrides=overrides, preflight=pf))
    if args.dry_run:
        print("\n(dry-run：未写账本、未建订单、未改状态)")
    else:
        md = R.render_daily_markdown(res, s_cfg, exp, prices,
                                     previous_value=_prev_equity(
                                         store, res.run_date),
                                     preflight=pf, overrides=overrides)
        # 日报目录跟着**实验身份**走，不能写死。写死的话第二个实验
        # 会把第一个实验的历史日报覆盖掉（2026-10-06 实测发生）。
        # 缺省用 strategy_version —— 对 v1 而言正好等于原来的
        # "daily_exit_paper_v1"，因此**不需要改 v1 的配置**
        # （改配置会变哈希 -> ConfigDrift）。
        _rep = ((s_cfg.get("paths") or {}).get("reports")
                or s_cfg["strategy_version"])
        out_dir = C.PROJECT_ROOT / "reports" / _rep
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / f"daily_{res.run_date}.md").write_text(md,
                                                          encoding="utf-8")
        print(f"\n实验目录：{root}")
        print(f"日报：{out_dir / f'daily_{res.run_date}.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
