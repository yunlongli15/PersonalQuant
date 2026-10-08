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
from typing import Optional
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

PROJECT_ROOT = Path(__file__).resolve().parents[2]
QLIB_DIR = PROJECT_ROOT / "qlib_data"
STAGING = PROJECT_ROOT / "qlib_data_new"
BACKUP = PROJECT_ROOT / "qlib_data_old"
API = "https://api.github.com/repos/chenditc/investment_data/releases/latest"


def latest_release(attempts: int = 3) -> dict:
    """最新 release。**带重试**。

    这是整条刷新链的**第一个**网络调用，以前却是最少保护的那个：
    单次 30 秒超时就抛出去，而 `market_update` 一失败整条
    `refresh_all.py` 就中断 —— 后面 9 个根本不需要联网的作业
    （factor_rebuild / signal / forecast / portfolio）一个都没跑。

    2026-10-08 用户实际遇到：`WinError 10060` 连接超时，
    同一分钟手工测 GitHub 是 0.5 秒 200 —— 纯抖动，重试即可。

    旁边的 `manifest_info()` 一直是带重试的，最外层反而没有 ——
    这个不对称就是问题本身。抖动不该等价于"今晚没数据"。
    """
    last: Optional[Exception] = None
    for attempt in range(1, attempts + 1):
        try:
            req = urllib.request.Request(
                API, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except Exception as e:                                 # noqa: BLE001
            last = e
            if attempt < attempts:
                time.sleep(2 * attempt)          # 2s, 4s —— 退避，不狂打
    raise RuntimeError(
        f"GitHub API 连续 {attempts} 次不可达（最后一次："
        f"{type(last).__name__}: {last}）。这多半是网络问题，"
        f"稍后重跑 `python scripts/quant/refresh_all.py` 即可；"
        f"确实要离线跑就用 `PQ_MODE=offline`（联网作业会记为 SKIPPED）。")


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


def download(url: str, dest: Path, attempts: int = 3) -> Path:
    """分块下载 + 进度。**带重试，且断点续传。**

    这里以前是**没有重试**的，而它偏偏是整条链里最容易失败的一步：
    567 MB 的包，任何一次抖动都直接抛出去打断整个 `refresh_all.py`。
    2026-10-08 实测连挂两次（`WinError 10060`），同一时刻手工测
    GitHub 却是 0.5 秒 200 —— 纯抖动，重试即可。

    重试时用 HTTP Range 从 `.part` 的断点接着下：567 MB 重头再来一次
    要十几分钟，而服务端忽略 Range（返回 200 而不是 206）时自动退回
    从头下，不会把半截文件当完整的用。
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".part")
    last_err: Optional[Exception] = None
    for attempt in range(1, attempts + 1):
        try:
            have = tmp.stat().st_size if tmp.exists() else 0
            req = urllib.request.Request(
                url, headers={"User-Agent": "Mozilla/5.0"})
            if have:
                req.add_header("Range", f"bytes={have}-")
            with urllib.request.urlopen(req, timeout=120) as r:
                # 206 = 按 Range 续传；200 = 服务端忽略了 Range，从头来
                resuming = have > 0 and getattr(r, "status", 200) == 206
                if have and not resuming:
                    have = 0
                total = (int(r.headers.get("Content-Length") or 0) + have)
                mode = "ab" if resuming else "wb"
                done, last = have, 0.0
                if resuming:
                    print(f"  续传自 {have/1e6:.1f} MB", flush=True)
                with open(tmp, mode) as f:
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
            if total and done != total:
                raise IOError(f"下载不完整：{done} / {total} 字节")
            tmp.replace(dest)
            print(f"  下载完成 {done/1e6:.1f} MB", flush=True)
            return dest
        except Exception as e:                                 # noqa: BLE001
            last_err = e
            if attempt < attempts:
                wait = 5 * attempt
                print(f"  下载中断（{type(e).__name__}: {e}）—— "
                      f"{wait}s 后从断点重试 {attempt}/{attempts - 1}",
                      flush=True)
                time.sleep(wait)
    raise RuntimeError(
        f"快照下载连续 {attempts} 次失败（最后一次："
        f"{type(last_err).__name__}: {last_err}）。断点已保留在 "
        f"{tmp}，重跑会从这里续传；确实要离线跑用 PQ_MODE=offline。")


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
