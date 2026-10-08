# -*- coding: utf-8 -*-
"""回填**模拟盘实际成交** —— 只写 executions 层，不动实验。

    python scripts/quant/record_paper_execution.py --list
    python scripts/quant/record_paper_execution.py \\
        --fill 002674.SZ:19.90:200 \\
        --fill 600580.SH:26.50:100 \\
        --skip 600865.SH --skip 002214.SZ \\
        --note "券商模拟盘，只挑了这几只"

**这不会改变实验。** 引擎仍按自己的模型结算那 20 张挂单，
`recommendations/` 与 `decisions/` 两层一个字都不动。
本脚本只往 `executions/<信号日>.json` 写一份"我实际做了什么"。

为什么要单独一层：这样才能回答两个**不同**的问题 ——
    ① 系统建议 → 「完全照系统做会怎样」（永远可回答，不被覆盖）
    ② 实际成交 → 「我实际做了什么、和模型差多少」（本脚本写的东西）

⚠️ 不要把它写进财富库。真实资产走 wealth/（SQLite），
模拟盘走这里，两条线物理隔离，是本项目的架构约束。

三种状态，必须**显式**给出，脚本不替你猜：
    --fill  SYMBOL:PRICE:SHARES   成交了（价、股数按券商回单填）
    --skip  SYMBOL                我选择不买（主动筛掉）
    --no-fill SYMBOL              我下了单但没成交（限价没碰到）
没提到的标的记为「未提及」，一并列出来 —— 不编状态。
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd

from daily_exit_paper import config as C
from daily_exit_paper import decisions as D
from daily_exit_paper import store as ST


def _parse_fill(spec: str) -> dict:
    parts = spec.split(":")
    if len(parts) != 3:
        raise SystemExit(f"--fill 格式应为 SYMBOL:PRICE:SHARES，得到 {spec!r}")
    sym, price, shares = parts
    try:
        price = float(price)
        shares = int(shares)
    except ValueError:
        raise SystemExit(f"--fill 的价/股数不是数字：{spec!r}")
    if price <= 0:
        raise SystemExit(f"{sym}: 成交价必须为正，得到 {price}")
    if shares <= 0:
        raise SystemExit(f"{sym}: 股数必须为正，得到 {shares}")
    if shares % 100:
        raise SystemExit(f"{sym}: A 股按手成交，股数必须是 100 的整数倍"
                         f"（得到 {shares}）")
    return {"symbol": sym, "filled": True, "price": price, "shares": shares}


def main() -> int:
    ap = argparse.ArgumentParser(
        description="回填模拟盘实际成交（只写 executions 层，不动实验）")
    ap.add_argument("--config", default=None,
                    help="实验配置（默认 = 当前生产模型的那个实验）")
    ap.add_argument("--signal-date", default=None,
                    help="信号日（默认：实验里最后一个有建议的信号日）")
    ap.add_argument("--fill", action="append", default=[],
                    metavar="SYM:PRICE:SHARES", help="成交（可重复）")
    ap.add_argument("--skip", action="append", default=[],
                    metavar="SYM", help="我选择不买（可重复）")
    ap.add_argument("--no-fill", action="append", default=[],
                    metavar="SYM", help="下了单但没成交（可重复）")
    ap.add_argument("--note", default="", help="备注（写进记录，留痕）")
    ap.add_argument("--list", action="store_true",
                    help="只列出待成交的挂单，不写任何东西")
    ap.add_argument("--yes", action="store_true", help="跳过确认")
    args = ap.parse_args()

    cfg_path = Path(args.config) if args.config else C.CONFIG_PATH
    if not cfg_path.is_absolute():
        cfg_path = C.PROJECT_ROOT / cfg_path
    s_cfg = C.validate(C.load_config(cfg_path))
    root = C.PROJECT_ROOT / s_cfg["paths"]["root"]
    store = ST.ExperimentStore(root)
    print(f"实验 {s_cfg['strategy_version']}")

    # ---- 信号日 ---------------------------------------------------------
    sig_date = args.signal_date
    if sig_date is None:
        snaps = sorted((root / "recommendations").glob("*.json"))
        if not snaps:
            print(f"[REFUSED] {root.name} 里还没有任何建议记录。")
            return 2
        sig_date = snaps[-1].stem
    print(f"信号日 {sig_date}\n")

    rec = store.read_snapshot("recommendations", sig_date)
    if rec is None:
        print(f"[REFUSED] {sig_date} 没有系统建议 —— 没有可回填的对象。")
        return 2
    entries = {e["symbol"]: e for e in rec["entries"]}

    # ---- --list ---------------------------------------------------------
    if args.list:
        print(f"当日建议 {len(entries)} 张挂单：\n")
        print(f"{'代码':<12}{'名称':<10}{'股数':>6}  {'限价':>8}  预估金额")
        for s, e in entries.items():
            print(f"{s:<12}{e.get('name', ''):<10}{e['quantity']:>6}  "
                  f"{e['limit_price']:>8.2f}  {e['estimated_value']:>10,.0f}")
        ex = store.read_snapshot("executions", sig_date)
        if ex:
            print(f"\n已回填 {len(ex['executions'])} 条（"
                  f"{(ex.get('recorded_at') or '')[:19]}）")
        else:
            print("\n尚未回填。")
        return 0

    # ---- 组装 -----------------------------------------------------------
    execs, problems = [], []
    seen = set()
    for spec in args.fill:
        r = _parse_fill(spec)
        execs.append(r)
        seen.add(r["symbol"])
    for sym in args.skip:
        if sym in seen:
            problems.append(f"{sym} 同时出现在多个状态里")
        execs.append({"symbol": sym, "filled": False, "reason": "user_skip"})
        seen.add(sym)
    for sym in args.no_fill:
        if sym in seen:
            problems.append(f"{sym} 同时出现在多个状态里")
        execs.append({"symbol": sym, "filled": False,
                      "reason": "ordered_but_not_filled"})
        seen.add(sym)

    unknown = [s for s in seen if s not in entries]
    if unknown:
        problems.append(f"以下标的不在 {sig_date} 的建议里（是不是打错了）："
                        f"{unknown}")
    if problems:
        for p in problems:
            print(f"[REFUSED] {p}")
        return 2
    if not execs:
        print("[REFUSED] 什么都没给。用 --fill / --skip / --no-fill "
              "指定，或 --list 看挂单。")
        return 2

    unmentioned = [s for s in entries if s not in seen]
    print(f"将写入 {len(execs)} 条：")
    for e in execs:
        if e.get("filled"):
            print(f"  成交   {e['symbol']}  {e['price']:.2f} x {e['shares']}")
        else:
            tag = "我选择不买" if e.get("reason") == "user_skip" \
                else "下单未成交"
            print(f"  {tag} {e['symbol']}")
    if unmentioned:
        print(f"\n未提及 {len(unmentioned)} 只（不会写入任何状态）：")
        print("  " + "、".join(unmentioned))
    if args.note:
        print(f"\n备注：{args.note}")

    if not args.yes:
        ans = input("\n写入 executions 层？实验本身不会被改动 [y/N] ")
        if ans.strip().lower() not in ("y", "yes"):
            print("已取消，未写入任何东西。")
            return 1

    p = D.record_execution(store, sig_date, execs, note=args.note)
    n_fill = sum(1 for e in execs if e.get("filled"))
    print(f"\n已写入 {p}")
    print(f"  成交 {n_fill} 条，未成交/跳过 {len(execs) - n_fill} 条")
    print(f"  recommendations / decisions 两层未改动；实验账本未改动。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
