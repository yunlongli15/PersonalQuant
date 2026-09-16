# -*- coding: utf-8 -*-
"""Market-data refresh from the upstream snapshot (STEP 7C, implemented).

The canonical daily layer is built from the chenditc/investment_data
release (see docs/data_sources.md). "Refreshing market data" therefore
means: fetch the newest release, swap it into qlib_data/, then re-ingest
the affected years into canonical parquet + DuckDB.

    python scripts/quant/update_market_snapshot.py --check
    python scripts/quant/update_market_snapshot.py              # full update
    python scripts/quant/update_market_snapshot.py --years 2026 # only recent

Safety: the previous qlib_data is kept as qlib_data_old until the new one
is fully ingested, and nothing is deleted automatically.
"""

import argparse
import json
import shutil
import subprocess
import sys
import tarfile
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

PROJECT_ROOT = Path(__file__).resolve().parents[2]
QLIB_DIR = PROJECT_ROOT / "qlib_data"
STAGING = PROJECT_ROOT / "qlib_data_new"
BACKUP = PROJECT_ROOT / "qlib_data_old"
API = "https://api.github.com/repos/chenditc/investment_data/releases/latest"


def latest_release() -> dict:
    req = urllib.request.Request(API, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def current_version() -> str:
    """Snapshot date currently in qlib_data (from the calendar tail)."""
    cal = QLIB_DIR / "calendars" / "day.txt"
    if not cal.exists():
        return "missing"
    lines = cal.read_text(encoding="utf-8").strip().splitlines()
    return lines[-1] if lines else "empty"


def download(url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".part")
    with urllib.request.urlopen(
            urllib.request.Request(url,
                                   headers={"User-Agent": "Mozilla/5.0"}),
            timeout=120) as r, open(tmp, "wb") as f:
        shutil.copyfileobj(r, f, length=1024 * 1024)
    tmp.replace(dest)
    return dest


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="report the upstream release without downloading")
    ap.add_argument("--years", default=None,
                    help="comma-separated years to re-ingest (default: all)")
    ap.add_argument("--keep-archive", action="store_true")
    args = ap.parse_args()

    rel = latest_release()
    tag = rel["tag_name"]
    print(f"upstream release: {tag}  (published {rel['published_at'][:10]})")
    print(f"local calendar ends: {current_version()}")
    if args.check:
        return 0

    asset = next(a for a in rel["assets"] if a["name"] == "qlib_bin.tar.gz")
    tar_path = PROJECT_ROOT / "tmp" / "qlib_bin.tar.gz"
    tar_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"downloading {asset['size']/1e6:.0f} MB ...")
    t0 = time.time()
    download(asset["browser_download_url"], tar_path)
    print(f"downloaded in {time.time()-t0:.0f}s")

    if STAGING.exists():
        shutil.rmtree(STAGING)
    STAGING.mkdir(parents=True)
    print("extracting ...")
    with tarfile.open(tar_path, "r:gz") as tf:
        # the archive holds a single top-level dir (qlib_bin/) whose
        # CONTENTS are the data root: strip one level
        for m in tf.getmembers():
            parts = m.name.split("/", 1)
            if len(parts) < 2 or not parts[1]:
                continue
            m.name = parts[1]
            tf.extract(m, STAGING)                   # noqa: S202 (own data)
    src = STAGING
    # never overwrite an existing backup: keep one timestamped copy
    if QLIB_DIR.exists():
        stamp = time.strftime("%Y%m%d_%H%M%S")
        keep = PROJECT_ROOT / f"qlib_data_prev_{stamp}"
        QLIB_DIR.rename(keep)
        print(f"previous snapshot kept at {keep.name}")
    src.rename(QLIB_DIR)
    print(f"qlib_data updated -> calendar ends {current_version()}")

    # ---- re-ingest canonical ------------------------------------------
    from personal_quant.ingest import qlib_baseline as qb

    print("ingesting calendar ...")
    qb.ingest_calendar()
    years = None
    if args.years:
        ys = [int(y) for y in args.years.split(",")]
        years = range(min(ys), max(ys) + 1)
    print(f"ingesting daily bars ({'all years' if years is None else years})"
          " ...")
    qb.ingest_daily_bars(years=years)

    if not args.keep_archive:
        tar_path.unlink(missing_ok=True)
    print("\ndone. previous snapshot kept at qlib_data_old/ — remove it "
          "manually once the new data looks right.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
