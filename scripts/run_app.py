# -*- coding: utf-8 -*-
"""启动个人投资终端（Streamlit，spec §41）。

    python scripts/run_app.py                 # 127.0.0.1:8501
    python scripts/run_app.py --port 8600
    python scripts/run_app.py --headless      # 不开浏览器

只绑定本机。传非本地地址直接拒绝（与 scripts/webapp/serve.py 同一纪律）：
个人资产数据不出本机。
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP = PROJECT_ROOT / "app" / "app.py"
LOCAL = {"127.0.0.1", "localhost", "::1"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8501)
    ap.add_argument("--headless", action="store_true",
                    help="不自动打开浏览器")
    ap.add_argument("--dev", action="store_true",
                    help="开发模式（文件改动自动重载）")
    args = ap.parse_args()

    if args.host not in LOCAL:
        print(f"refusing to bind beyond localhost: --host {args.host}\n"
              f"个人资产数据只在本机；允许的地址：{sorted(LOCAL)}",
              file=sys.stderr)
        return 1

    if not APP.exists():
        print(f"找不到应用入口：{APP}", file=sys.stderr)
        return 1

    cmd = [sys.executable, "-m", "streamlit", "run", str(APP),
           "--server.address", args.host,
           "--server.port", str(args.port),
           "--server.headless", "true" if args.headless else "false",
           "--browser.gatherUsageStats", "false",     # 不外传任何使用数据
           "--server.fileWatcherType",
           "auto" if args.dev else "none"]
    print(f"启动个人投资终端： http://{args.host}:{args.port}")
    print("（仅本机可访问；不连接券商；数据不出本机）")
    return subprocess.call(cmd, cwd=str(PROJECT_ROOT))


if __name__ == "__main__":
    sys.exit(main())
