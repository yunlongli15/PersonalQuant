# -*- coding: utf-8 -*-
"""Experiment manifest: every run records everything needed to reproduce it."""

from __future__ import annotations

import json
import platform
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import lightgbm
import pandas as pd

from .. import PROJECT_ROOT


def git_commit() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, capture_output=True,
            text=True, timeout=15,
        )
        return out.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def data_snapshot_id() -> str:
    """A compact fingerprint of the canonical parquet layer (size + mtime of
    the daily bars partition files)."""
    files = sorted((PROJECT_ROOT / "data" / "parquet").rglob("*.parquet"))
    import hashlib

    h = hashlib.sha256()
    for f in files:
        st = f.stat()
        h.update(f"{f.name}:{st.st_size}:{int(st.st_mtime)}".encode())
    return h.hexdigest()[:16]


def build_manifest(config: dict, run_id: str, extra: Optional[dict] = None) -> dict:
    manifest = {
        "run_id": run_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "python_version": platform.python_version(),
        "qlib_version": None,
        "lightgbm_version": lightgbm.__version__,
        "pandas_version": pd.__version__,
        "git_commit": git_commit(),
        "data_snapshot_id": data_snapshot_id(),
        "strategy": config["strategy"],
        "model_params": config["model"]["params"],
        "model_seed": config["model"]["seed"],
        "time_split": config["time_split"],
        "universe": config["universe"],
        "portfolio": config["portfolio"],
        "execution": config["execution"],
        "transaction_costs": config["transaction_costs"],
        "rebalance": config["rebalance"],
        "label": config["label"],
        "extra": extra or {},
    }
    try:
        import qlib

        manifest["qlib_version"] = qlib.__version__
    except Exception:
        pass
    return manifest


def save_manifest(manifest: dict, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / "manifest.json"
    p.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, default=str),
                 encoding="utf-8")
    return p
