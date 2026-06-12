# -*- coding: utf-8 -*-
# tests/import_all_from_legacy.py
#!/usr/bin/env python3
"""Import all transactions from resolved legacy DB into the current DB.

This script uses the same resolution and import functions as the GUI importer
so behavior is consistent. It will backup the current DB before modifying it.
"""

import os
import shutil
import time
import sqlite3


def main():
    # Local imports after ensuring project root on sys.path (if needed)
    from pathlib import Path

    PROJECT_ROOT = Path(__file__).resolve().parents[2]
    import sys

    sys.path.insert(0, str(PROJECT_ROOT))
    from StockMan.trade_from_file import (
        _fetch_source_transactions,
        import_transaction,
    )
    from Shared.globals import (
        STOCK_DB_PATH,
        logger,
        get_db_connection,
    )

    print("Resolving legacy DB (mystocks_old.db)...")
    rows = _fetch_source_transactions("mystocks_old.db")
    if not rows:
        print("No transactions found in legacy DB. Aborting.")
        return

    db_path = os.path.abspath(STOCK_DB_PATH)
    print(f"Current DB: {db_path}")

    # Backup current DB if it exists
    if os.path.exists(db_path):
        bak = f"{db_path}.bak.{int(time.time())}"
        try:
            shutil.copy2(db_path, bak)
            print(f"Backed up current DB to: {bak}")
        except Exception as exc:
            print(f"Warning: failed to backup DB: {exc}")

    imported = 0
    failed = 0

    # Import using a single connection for speed
    try:
        with get_db_connection() as conn:
            for tx in rows:
                try:
                    ok = import_transaction(conn, tx)
                except Exception as exc:
                    ok = False
                    logger.exception("Exception importing tx: %s", exc)
                if ok:
                    imported += 1
                else:
                    failed += 1
    except sqlite3.Error as exc:
        print(f"Failed to open current DB: {exc}")
        return

    print("Import complete.")
    print(f"Imported: {imported}, Failed: {failed}")

    # Print tail of importer debug log if present
    log_path = os.path.join(os.path.dirname(__file__), "log", "importer_debug.log")
    if os.path.exists(log_path):
        print("\nLast log lines (importer_debug.log):")
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()[-200:]
                for line in lines:
                    print(line.rstrip())
        except Exception as exc:
            print(f"Failed to read debug log: {exc}")
    else:
        print("No importer debug log found.")


if __name__ == "__main__":
    main()
