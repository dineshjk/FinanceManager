#!/usr/bin/env python3
"""Perform a dry-run import into the live DB by running the import inside
a transaction and rolling it back at the end.

This exercises the exact SQL path (triggers, constraints, PRAGMAs) but
leaves the live DB unchanged.
"""

from pathlib import Path
import os
import sys
import traceback
import sqlite3

# ensure project root is on sys.path
LEGACY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "mystocks_old.db")


def main():
    # ensure project root is on sys.path and import locally
    PROJECT_ROOT = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(PROJECT_ROOT))
    from StockMan.trade_from_file import (
        _fetch_source_transactions,
        import_transaction,
    )
    from Shared.globals import get_db_connection

    if not os.path.exists(LEGACY):
        print("Legacy DB not found at:", LEGACY)
        return

    rows = _fetch_source_transactions(LEGACY)
    print(f"Found {len(rows)} transactions in legacy DB: {LEGACY}")
    if not rows:
        return

    imported = 0
    failed = 0

    # Run inside a transaction and always rollback at the end
    with get_db_connection() as conn:
        try:
            # Explicit transaction start
            conn.execute("BEGIN")
            print("BEGIN transaction (dry-run)")

            for i, tx in enumerate(rows, start=1):
                src = tx.get("src_id_trd")
                cont = tx.get("cont_no")
                print(
                    "[dry-run] Importing "
                    + str(i)
                    + "/"
                    + str(len(rows))
                    + " src_id="
                    + str(src)
                    + " cont_no="
                    + str(cont)
                )
                try:
                    ok = import_transaction(conn, tx)
                except sqlite3.Error:
                    ok = False
                    print("Unexpected sqlite error during import:")
                    traceback.print_exc()
                if ok:
                    imported += 1
                    print(
                        "  [dry-run] would import: src_id="
                        + str(src)
                        + " cont_no="
                        + str(cont)
                    )
                else:
                    failed += 1
                    print(
                        "  [dry-run] would FAIL: src_id="
                        + str(src)
                        + " cont_no="
                        + str(cont)
                    )

            print(
                "Dry-run summary: would_import="
                + str(imported)
                + ", would_fail="
                + str(failed)
            )

        finally:
            # Always rollback to leave the DB unchanged
            try:
                conn.rollback()
                print("ROLLBACK transaction (dry-run) - live DB unchanged")
            except Exception:
                print("Failed to rollback dry-run transaction; check DB state")


if __name__ == "__main__":
    main()
