# -*- coding: utf-8 -*-
"""冻结生产策略 -> experiments/clean/production_clean_v1.json

    python scripts/quant/freeze_production_strategy.py [--strategy production_clean_v1]

PHASE 7 §十三：生产模型必须**版本化**，记录：
模型文件哈希 / 特征清单 / 配置与其哈希 / 训练数据快照 / git commit /
冻结测试段回测指标。

只写这一份记录，不改模型、不改任何 run 产物 —— 它是**指认**，不是生成。
"""

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"],
                                       cwd=PROJECT_ROOT, text=True).strip()
    except Exception:                                          # noqa: BLE001
        return "unknown"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strategy", default=None)
    args = ap.parse_args()

    from pipeline.signals import PROJECT_ROOT as _root  # noqa: F401
    from pipeline.signals import PRODUCTION_STRATEGY, strategy_spec
    from personal_quant.strategy.reproducibility import data_snapshot_id

    name = args.strategy or PRODUCTION_STRATEGY
    spec = strategy_spec(name)
    run_dir = spec["model_path"].parent
    if not spec["model_path"].exists():
        raise SystemExit(f"模型不存在：{spec['model_path']}")

    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    cfg_path = PROJECT_ROOT / manifest["base_config"]

    record = {
        "strategy_version": name,
        "frozen_at": datetime.now().isoformat(timespec="seconds"),
        "git_commit": _git_commit(),
        "model": {
            "path": str(spec["model_path"].relative_to(PROJECT_ROOT)),
            "sha256": _sha256(spec["model_path"]),
            "n_features_total": manifest.get("n_features_total"),
        },
        "features": {
            "custom_features": spec.get("custom_features") or [],
            "feature_version": spec["feature_version"],
            "features_label": spec.get("features_label"),
            "news_factors": "DISABLED" if not spec.get("uses_news", True)
            else "ENABLED",
        },
        "config": {
            "path": manifest["base_config"],
            "sha256": _sha256(cfg_path),
            "model_params": manifest["model_params"],
            "model_seed": manifest["model_seed"],
            "time_split": manifest["time_split"],
            "label": manifest["label"],
            "execution": manifest["execution"],
            "transaction_costs": manifest["transaction_costs"],
            "rebalance": manifest["rebalance"],
            "portfolio": manifest["portfolio"],
        },
        "training_dataset": {
            "snapshot_id": data_snapshot_id(),
            "provider_uri": "qlib_data/",
            "run_manifest": str((run_dir / "manifest.json")
                                .relative_to(PROJECT_ROOT)),
        },
        "backtest_test_period": summary["strategy_metrics"],
        "backtest_ic_test": summary.get("ic", {}).get("test"),
        "notes": [
            "PHASE 7 选定：Alpha158 only，不使用任何新闻因子。",
            "旧策略 S3_v1 / S3_v2 的原产物全部保留，未改动。",
        ],
    }
    out = PROJECT_ROOT / "experiments" / "clean" / f"{name}.json"
    out.write_text(json.dumps(record, indent=2, ensure_ascii=False),
                   encoding="utf-8")
    m = summary["strategy_metrics"]
    print(f"froze {name} -> {out}")
    print(f"  model sha256 {record['model']['sha256'][:16]}…")
    print(f"  dataset {record['training_dataset']['snapshot_id']}")
    print(f"  ann={m['annualized_return']:.4f} sharpe={m['sharpe']:.3f} "
          f"mdd={m['max_drawdown']:.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
