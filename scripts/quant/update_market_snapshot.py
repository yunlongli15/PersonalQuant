# -*- coding: utf-8 -*-
"""Market-data refresh from the upstream snapshot (STEP 7C, implemented).

The canonical daily layer is built from the chenditc/investment_data
release (see docs/数据来源与口径.md). "Refreshing market data" therefore
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


def manifest_info(rel: dict) -> dict:
    """The release's own 511-byte manifest — it carries the REAL data date.

    The release tag is a label (a release named 2026-09-20 can still hold
    data ending 2026-09-18). `target_trade_date` is the truth, so the
    download can be skipped when there is nothing newer.
    """
    url = next((a["browser_download_url"] for a in rel.get("assets", [])
                if a["name"].endswith("manifest.json")), None)
    if not url:
        return {}
    for attempt in (1, 2):
        try:
            req = urllib.request.Request(url,
                                         headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read())
        except Exception:                                      # noqa: BLE001
            if attempt == 2:
                return {}
            time.sleep(2)
    return {}


def download(url: str, dest: Path) -> Path:
    """Chunked download with progress — 500+ MB with no output looks hung."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".part")
    with urllib.request.urlopen(
            urllib.request.Request(url,
                                   headers={"User-Agent": "Mozilla/5.0"}),
            timeout=120) as r, open(tmp, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        done, last = 0, 0.0
        while True:
            chunk = r.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)
            done += len(chunk)
            now = time.time()
            if now - last >= 3.0:
                last = now
                pct = f"{done / total:5.1%}" if total else "  ?  "
                print(f"  下载中 {pct}  {done/1e6:6.1f} / "
                      f"{total/1e6:.0f} MB", flush=True)
    tmp.replace(dest)
    print(f"  下载完成 {done/1e6:.1f} MB", flush=True)
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
    man = manifest_info(rel)
    up_to = man.get("target_trade_date")
    local = current_version()
    print(f"upstream release: {tag}  (published {rel['published_at'][:10]})")
    print(f"upstream data ends: {up_to or '未知'}")
    print(f"local calendar ends: {local}")
    if args.check:
        return 0

    # 上游"数据日"没有超过本地 → 这份快照里没有任何新东西，别下 500 MB。
    # 只看 release 名字会误判：名为 2026-09-20 的 release 数据仍然停在
    # 2026-09-18（实测两者逐字节相同）。
    if up_to and local not in ("missing", "empty") and up_to <= local:
        print(f"\n本地已有 {local} 的数据，上游没有更新的内容 —— "
              f"跳过下载（这份快照约 "
              f"{next(a['size'] for a in rel['assets'] if a['name'].endswith('tar.gz'))/1e6:.0f} MB）。")
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
