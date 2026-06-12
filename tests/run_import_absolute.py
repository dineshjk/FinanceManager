# -*- coding: utf-8 -*-
# tests/run_import_absolute.py
#!/usr/bin/env python3
"""Import legacy DB by absolute path into current DB.

This script is intended to run inside the workspace where the legacy DB
path is known. It calls the import helper with an absolute path so the
resolution step is bypassed.
"""

import os
import shutil
import time

# Add project root to the Python path
import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from StockMan.trade_from_file import (
    _fetch_source_transactions,
    import_transaction,
)
from Shared.globals import STOCK_DB_PATH, get_db_connection


def main():
    legacy = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "mystocks_old.db")
    print("Using legacy DB:", legacy)
    rows = _fetch_source_transactions(legacy)
    print("Found rows:", len(rows))
    if not rows:
        print("No rows found; aborting")
        return

    db_path = os.path.abspath(STOCK_DB_PATH)
    print("Current DB:", db_path)
    if os.path.exists(db_path):
        bak = f"{db_path}.bak.{int(time.time())}"
        shutil.copy2(db_path, bak)
        print("Backed up DB to:", bak)

    imported = 0
    failed = 0
    with get_db_connection() as conn:
        for tx in rows:
            ok = import_transaction(conn, tx)
            if ok:
                imported += 1
            else:
                failed += 1

    print(f"Imported: {imported}, Failed: {failed}")

    # print tail of importer_debug.log
    log_path = os.path.join(os.path.dirname(__file__), "log", "importer_debug.log")
    if os.path.exists(log_path):
        print("\n--- importer_debug.log tail ---")
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f.readlines()[-200:]:
                print(line.rstrip())
    else:
        print("No debug log found at", log_path)


if __name__ == "__main__":
    main()
