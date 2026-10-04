# -*- coding: utf-8 -*-
"""季度研究评审（STEP 12, spec §32）。

    python scripts/quarterly_review.py --quarter 2026-Q3

**只出评审报告，绝不改模型、不选因子、不调参数、不重训。**
输出：reports/quarterly/YYYY-Qn.md
"""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

OUT = PROJECT_ROOT / "reports" / "quarterly"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quarter", required=True, help="例如 2026-Q3")
    args = ap.parse_args()

    from pipeline import freeze as fz
    from pipeline.daily_report import load_latest_summary

    year, q = args.quarter.split("-")
    rec = fz.load_freeze().get("production_freeze") or {}
    ds = load_latest_summary() or {}
    alerts = ds.get("alerts") or []

    L = [
        f"# 季度评审 · {args.quarter}", "",
        "> 本报告**只做评审**。没有训练、没有因子选择、没有参数调整。",
        "",
        "## 1. 生产冻结状态", "",
        f"- 策略 `{rec.get('strategy_version')}` ｜ "
        f"模型 `{rec.get('model_version')}` ｜ "
        f"特征 `{rec.get('feature_version')}`",
        f"- 分配 `{rec.get('allocation_method')}` ｜ "
        f"执行 `{rec.get('execution_model')}` ｜ Top-K {rec.get('top_k')}",
        f"- 冻结日 {rec.get('freeze_date')} ｜ commit "
        f"`{str(rec.get('git_commit'))[:12]}`",
        f"- 冻结校验：**{fz.verify().detail}**",
        "",
        "## 2. Forward 观测", "",
        f"- 起点 {rec.get('forward_holdout_start')}",
    ]
    try:
        from services import strategy_service
        pl = strategy_service.paper_live()
        L += [
            f"- 观测天数：**{pl.get('n_observation_days')}**",
            f"- 累计收益：{pl.get('cumulative_return')}",
            f"- 最大回撤：{pl.get('max_drawdown')}",
            f"- 预测质量：{pl.get('prediction_quality')}",
        ]
        if not pl.get("enough_data"):
            L.append("- **NOT ENOUGH DATA** —— 样本不足，本轮不做任何结论。")
    except Exception as e:                                     # noqa: BLE001
        L.append(f"- 不可用：{type(e).__name__}: {e}")

    L += ["", "## 3. IC / RankIC 趋势", "",
          "- 见 `reports/forward_holdout/*.md` 的逐月 IC/RankIC。",
          "- 单月 IC 波动属正常范围，**不构成任何修改理由**。", "",
          "## 4. 组合与风险", ""]
    try:
        from services import performance_service, risk_service
        perf = performance_service.summary()
        rk = risk_service.metrics()
        L += [f"- 组合收益：{perf.get('cumulative_return')} ｜ "
              f"TWR {perf.get('twr')} ｜ 回撤 {perf.get('max_drawdown')}",
              f"- 风险：{(rk.get('nav_based') or {}).get('volatility')} 波动 ｜ "
              f"HHI {(rk.get('holdings_based') or {}).get('hhi')}"]
    except Exception as e:                                     # noqa: BLE001
        L.append(f"- 不可用：{type(e).__name__}")

    L += ["", "## 5. 数据质量与告警", "",
          f"- 最近一次运行：{ds.get('date')}（{ds.get('status')}）",
          f"- 告警：{len(alerts)} 条"]
    for a in alerts[:10]:
        L.append(f"  - [{a['level']}] {a['code']}: {a['detail'][:70]}")

    L += ["", "## 6. 本轮结论", "",
          "按 V1 协议，季度评审**不产生任何系统变更**。",
          "若确有新想法，必须新建 experiment config / 分支，",
          "不得直接修改生产配置（见 `docs/V1.0冻结规则.md`）。",
          "",
          "> 由 `scripts/quarterly_review.py` 自动生成；未做任何模型训练、",
          "> 因子选择或参数优化。", ""]

    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / f"{args.quarter}.md"
    p.write_text("\n".join(L), encoding="utf-8")
    print(f"季度评审 -> {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
