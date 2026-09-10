# -*- coding: utf-8 -*-
"""Initialise / inspect the personal wealth database (STEP 7A).

    python scripts/wealth/init_wealth_db.py                 # create + seed
    python scripts/wealth/init_wealth_db.py --status        # what's inside
    python scripts/wealth/init_wealth_db.py --backup        # one-click backup
    python scripts/wealth/init_wealth_db.py --export out/   # CSV + JSON

The wealth DB is local-only personal data (data/wealth/wealth.db,
git-ignored). Nothing here touches the research DuckDB.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--backup", action="store_true")
    ap.add_argument("--export", default=None,
                    help="directory for CSV + JSON exports")
    args = ap.parse_args()

    from wealth import db as wdb
    from wealth import repository as repo
    from wealth import seed

    conn = wdb.connect()
    print(f"wealth db: {wdb.db_path()}")

    if args.backup:
        target = wdb.backup(conn=conn)
        print(f"backup written: {target}")
        return 0

    if args.export:
        out = Path(args.export)
        csv_counts = repo.export_csv(conn, out / "csv")
        repo.export_json(conn, out / "wealth_dump.json")
        print(f"exported CSV to {out / 'csv'} and JSON to "
              f"{out / 'wealth_dump.json'}")
        for t, n in csv_counts.items():
            print(f"  {t}: {n} rows")
        return 0

    created = seed.seed(conn)
    print(f"seed: +{created['platforms']} platforms, "
          f"+{created['accounts']} accounts, "
          f"+{created['categories']} categories")

    if args.status or True:
        platforms = repo.list_platforms(conn)
        products = repo.list_products(conn, include_inactive=True)
        txns = repo.list_transactions(conn)
        snaps = repo.list_snapshots(conn)
        print("\n--- status ---")
        print(f"platforms: {len(platforms)}")
        for p in platforms:
            accts = repo.list_accounts(conn, p["platform_id"])
            prods = [x for a in accts
                     for x in repo.list_products(conn, a["account_id"],
                                                 include_inactive=True)]
            print(f"  {p['name']} ({p['kind']}): {len(accts)} account(s), "
                  f"{len(prods)} product(s)")
        print(f"products: {len(products)}  transactions: {len(txns)}  "
              f"snapshots: {len(snaps)}")
        if not products:
            print("\nnext: add products via the GUI (STEP 7F) or "
                  "wealth.repository.create_product")
    return 0


if __name__ == "__main__":
    sys.exit(main())
