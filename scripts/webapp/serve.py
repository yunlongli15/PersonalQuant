# -*- coding: utf-8 -*-
"""Launch the local GUI (STEP 7F).

    python scripts/webapp/serve.py                 # http://127.0.0.1:8765
    python scripts/webapp/serve.py --port 9000

Binds 127.0.0.1 only — the personal wealth data never leaves the machine
(spec §41). No auto-reload in normal use: the app reads data files that
backfills may be writing, so a stable process is safer.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--reload", action="store_true")
    args = ap.parse_args()

    import uvicorn

    if args.host not in ("127.0.0.1", "localhost"):
        print("refusing to bind beyond localhost: personal wealth data is "
              "local-only (spec §41)")
        return 1
    print(f"PersonalQuant GUI -> http://{args.host}:{args.port}")
    print("local only · research use · no automatic trading")
    uvicorn.run("webapp.app:app", host=args.host, port=args.port,
                reload=args.reload, log_level="warning")
    return 0


if __name__ == "__main__":
    sys.exit(main())
