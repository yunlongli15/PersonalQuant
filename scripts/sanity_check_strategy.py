# -*- coding: utf-8 -*-
"""Manual sanity check: inspect 10 historical rebalance dates in detail.

For each date prints: universe size, Top-20 picks, predicted returns, realized
next-20d returns, execution prices (T+1 open), suspension/limit checks — so a
human can verify the logic makes sense. Writes
reports/step3_sanity_check.md.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATES = [
    "2019-06-28", "2020-03-31", "2020-12-31", "2021-06-30", "2021-12-31",
    "2022-09-30", "2023-06-30", "2024-03-29", "2024-09-30", "2025-06-30",
]


def main() -> int:
    import yaml

    from personal_quant import db
    from personal_quant.strategy.execution import t1_open_and_prev_close
    from personal_quant.strategy.qlib_provider import init_qlib_with_canonical
    from personal_quant.strategy.rebalance import trading_days
    from personal_quant.strategy.universe import build_universe

    config = yaml.safe_load(
        (PROJECT_ROOT / "config" / "strategy_v1.yaml").read_text(encoding="utf-8")
    )
    init_qlib_with_canonical()

    # load the trained model + cached features from run_001
    exp_dir = PROJECT_ROOT / "experiments" / "strategy_v1" / "run_001"
    if not (exp_dir / "model.txt").exists():
        print("run_001 model not found; run backtest_strategy.py first")
        return 1
    from personal_quant.strategy.features import compute_features
    from personal_quant.strategy.model import AlphaModel

    model = AlphaModel.load(exp_dir / "model.txt", dict(config["model"]["params"]),
                            seed=config["model"]["seed"])
    conn = db.connect()
    days = list(trading_days("2015-01-01", "2026-12-31"))
    day_idx = {d: i for i, d in enumerate(days)}

    lines = ["# STEP 3 sanity check（人工核对）", ""]
    for ds in DATES:
        d = pd.Timestamp(ds)
        if d not in day_idx:
            lines.append(f"## {ds}: not a trading day — skipped\n")
            continue
        u = build_universe(d, config)
        feats = compute_features(u["symbol"].tolist(), [d], cache=True)
        f = feats.get(d)
        if f is None or f.empty:
            lines.append(f"## {ds}: no features\n")
            continue
        from personal_quant.strategy.features import flatten_columns

        f = flatten_columns(f)
        pred = model.predict_series(f, f.index).sort_values(ascending=False)
        picks = pred.head(20)
        # realized 20d labels
        i = day_idx[d]
        d2 = days[i + 20] if i + 20 < len(days) else None
        lines.append(f"## {ds}（universe {len(u)}，Top 20）\n")
        lines.append("| rank | symbol | name | predicted | next20d (realized) | "
                     "T+1 open | T close | limit/suspension |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
        names = dict(conn.execute(
            "SELECT symbol, name FROM securities WHERE symbol IN "
            "(SELECT unnest(?::VARCHAR[]))", [list(picks.index)]
        ).fetch_df().values)
        for r, sym in enumerate(picks.index, 1):
            lab = None
            if d2 is not None:
                base = conn.execute(
                    "SELECT close * factor a FROM daily_bars WHERE symbol=? AND trade_date=?",
                    [sym, d]).fetchone()
                fwd = conn.execute(
                    "SELECT close * factor a FROM daily_bars WHERE symbol=? AND trade_date=?",
                    [sym, d2]).fetchone()
                if base and fwd:
                    lab = fwd[0] / base[0] - 1.0
            t1, o, pc = t1_open_and_prev_close(sym, d)
            note = ""
            if o is None:
                note = "NO_BAR(停牌)"
            elif pc is not None and o >= pc * 1.095:
                note = "涨停→NO_TRADE"
            elif pc is not None and o <= pc * 0.905:
                note = "跌停→NO_TRADE"
            lines.append(
                f"| {r} | {sym} | {names.get(sym, '')} | {picks[sym]:.4f} | "
                f"{lab if lab is None else round(lab, 4)} | "
                f"{'' if o is None else round(o, 2)} | "
                f"{'' if pc is None else round(pc, 2)} | {note} |"
            )
        lines.append("")
    report = PROJECT_ROOT / "reports" / "step3_sanity_check.md"
    report.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
