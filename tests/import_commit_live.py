#!/usr/bin/env python3
"""Import legacy DB rows into the live DB and commit changes.

This script will create a timestamped backup of the live DB before making
any changes. Use with care — this performs real writes.
"""

from pathlib import Path
import os
import sys
import shutil
import time
import traceback

# Ensure project root is on sys.path
LEGACY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "mystocks_old.db")


def backup_db(db_path: str) -> str:
    now = time.strftime("%Y%m%d-%H%M%S")
    src = Path(db_path)
    if not src.exists():
        raise FileNotFoundError(f"DB file not found: {db_path}")
    dst = src.with_name(src.name + f".bak.{now}")
    shutil.copy2(str(src), str(dst))
    return str(dst)


def main():
    # Ensure project root is on sys.path and import project modules lazily
    PROJECT_ROOT = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(PROJECT_ROOT))
    from StockMan.trade_from_file import (
        _fetch_source_transactions,
        import_transaction,
    )
    from Shared.globals import (
        STOCK_DB_PATH,
        get_db_connection,
    )

    if not os.path.exists(LEGACY):
        print("Legacy DB not found at:", LEGACY)
        return

    rows = _fetch_source_transactions(LEGACY)
    print(f"Found {len(rows)} transactions in legacy DB: {LEGACY}")
    if not rows:
        return

    live_db = os.path.abspath(STOCK_DB_PATH)
    print(f"Live DB path: {live_db}")
    print("Creating backup of live DB...")
    try:
        bak = backup_db(live_db)
        print("Backup created:", bak)
    except Exception:
        print("Failed to backup live DB; aborting import")
        traceback.print_exc()
        return

    imported = 0
    failed = 0

    with get_db_connection() as conn:
        for i, tx in enumerate(rows, start=1):
            src = tx.get("src_id_trd")
            cont = tx.get("cont_no")
            print(f"Importing {i}/{len(rows)} src_id={src} cont_no={cont}")
            try:
                ok = import_transaction(conn, tx)
            except Exception:
                ok = False
                print("Unexpected exception during import (see traceback):")
                traceback.print_exc()
            if ok:
                imported += 1
                print("  imported")
            else:
                failed += 1
                print("  FAILED - see logs")

    print(f"Import finished. Imported={imported}, Failed={failed}")
    print("If anything looks wrong you can restore the backup:")
    print(f"  copy {bak} {live_db}")


if __name__ == "__main__":
    main()
