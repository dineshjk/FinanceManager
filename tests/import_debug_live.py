# -*- coding: utf-8 -*-
# tests/import_debug_live.py
#!/usr/bin/env python3
"""Import with per-transaction debug output into the live DB.

This script adjusts sys.path so it can be run directly from the scripts
folder. It prints tracebacks for any failing transaction so we can
see constraint/trigger errors coming from the live DB.
"""

from pathlib import Path
import os
import sys
import traceback
import sqlite3

# Ensure the project root (parent of the StockMan package) is on sys.path
LEGACY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "mystocks_old.db")


def main():
    # Ensure the project root (parent of the StockMan package) is on sys.path
    PROJECT_ROOT = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(PROJECT_ROOT))
    from StockMan.trade_from_file import _fetch_source_transactions
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

    with get_db_connection() as conn:
        for i, tx in enumerate(rows, start=1):
            src = tx.get("src_id_trd")
            cont = tx.get("cont_no")
            print(f"Importing {i}/{len(rows)} src_id={src} cont_no={cont}")
            # Use a verbose importer here so we can see the exact SQL error
            try:
                ok = import_transaction_verbose(conn, tx)
            except Exception:
                ok = False
                print("Unexpected exception during verbose import:")
                traceback.print_exc()
            if ok:
                imported += 1
            else:
                failed += 1
    print(f"Import finished. Imported={imported}, Failed={failed}")


def import_transaction_verbose(conn, tx):
    """Run the same sequence as import_transaction but print SQL on errors.

    This is a local copy to avoid modifying the library code and to add
    diagnostic prints.
    """
    cur = conn.cursor()
    try:
        cur.execute("PRAGMA foreign_keys = ON")

        cur.execute(
            (
                "INSERT OR IGNORE INTO contracts"
                " (cont_no, trd_dt, settle_no, settle_dt, no_of_trades)"
                " VALUES (?, ?, ?, ?, ?)"
            ),
            (
                tx.get("cont_no"),
                tx.get("trd_dt"),
                tx.get("settle_no", 0),
                tx.get("settle_dt", tx.get("trd_dt")),
                tx.get("no_of_trades", 1),
            ),
        )

        cur.execute(
            (
                "SELECT id_trd FROM transactions"
                " WHERE cont_no = ? AND company_name = ? AND id_stk = ?"
            ),
            (tx.get("cont_no"), tx.get("company_name"), tx.get("id_stk")),
        )
        found = cur.fetchone()
        if found:
            id_trd = found[0]
            cur.execute(
                (
                    "UPDATE transactions"
                    " SET trd_dt = ?, trade_type_trd = ?"
                    " WHERE id_trd = ?"
                ),
                (tx.get("trd_dt"), tx.get("trade_type_trd"), id_trd),
            )
        else:
            cur.execute(
                (
                    "INSERT INTO transactions"
                    " (cont_no, trd_dt, company_name, trade_type_trd, id_stk)"
                    " VALUES (?, ?, ?, ?, ?)"
                ),
                (
                    tx.get("cont_no"),
                    tx.get("trd_dt"),
                    tx.get("company_name"),
                    tx.get("trade_type_trd"),
                    tx.get("id_stk"),
                ),
            )
            id_trd = cur.lastrowid

        for eo in tx.get("exchange_orders", []):
            try:
                cur.execute(
                    (
                        "UPDATE exchange_orders"
                        " SET id_trd = ?, trd_no = ?, qty_eo = ?, rate_eo = ?,"
                        " brok_unit_eo = ?, net_rate_eo = ?, net_total_eo = ?"
                        " WHERE ord_no = ? AND ord_dt = ?"
                    ),
                    (
                        id_trd,
                        eo.get("trd_no"),
                        eo.get("qty_eo"),
                        eo.get("rate_eo"),
                        eo.get("brok_unit_eo"),
                        eo.get("net_rate_eo"),
                        eo.get("net_total_eo"),
                        eo.get("ord_no"),
                        eo.get("ord_dt"),
                    ),
                )
                if cur.rowcount == 0:
                    cur.execute(
                        (
                            "INSERT INTO exchange_orders"
                            " (id_trd, ord_no, ord_dt, trd_no,"
                            " qty_eo, rate_eo, brok_unit_eo, net_rate_eo,"
                            " net_total_eo)"
                            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
                        ),
                        (
                            id_trd,
                            eo.get("ord_no"),
                            eo.get("ord_dt"),
                            eo.get("trd_no"),
                            eo.get("qty_eo"),
                            eo.get("rate_eo"),
                            eo.get("brok_unit_eo"),
                            eo.get("net_rate_eo"),
                            eo.get("net_total_eo"),
                        ),
                    )
            except sqlite3.Error as e:
                print("SQL error while processing exchange_order:")
                print("  error:", e)
                # Print context: sqlite3 does not expose SQL/params
                # from the exception; print the eo dict and id_trd instead.
                print("  id_trd:", id_trd)
                print("  exchange_order:", eo)
                conn.rollback()
                return False

        conn.commit()
        return True

    except sqlite3.Error as e:
        print("SQL error during import sequence:")
        print("  error:", e)
        conn.rollback()
        return False


if __name__ == "__main__":
    main()
