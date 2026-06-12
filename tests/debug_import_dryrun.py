#!/usr/bin/env python3
"""Attempt importing transactions into a temporary DB and print exceptions.

This will help surface why import_transaction returns False for each transaction.
"""
import os
import sqlite3
import tempfile
import traceback

from StockMan.trade_from_file import (
    _fetch_source_transactions,
    import_transaction,
)

LEGACY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "mystocks_old.db")

SCHEMA_TX = """
CREATE TABLE IF NOT EXISTS contracts (
    cont_no INTEGER,
    trd_dt TEXT,
    settle_no INTEGER,
    settle_dt TEXT,
    no_of_trades INTEGER
);
"""
SCHEMA_TR = """
CREATE TABLE IF NOT EXISTS transactions (
    id_trd INTEGER PRIMARY KEY AUTOINCREMENT,
    cont_no INTEGER,
    trd_dt TEXT,
    company_name TEXT,
    trade_type_trd TEXT,
    id_stk INTEGER,
    qty_trd INTEGER,
    wap_unit_trd REAL,
    brok_unit_trd REAL,
    net_amt_trd REAL
);
"""
SCHEMA_EO = """
CREATE TABLE IF NOT EXISTS exchange_orders (
    id_eo INTEGER PRIMARY KEY AUTOINCREMENT,
    id_trd INTEGER,
    ord_no INTEGER,
    ord_dt TEXT,
    trd_no INTEGER,
    qty_eo INTEGER,
    rate_eo REAL,
    brok_unit_eo REAL,
    net_rate_eo REAL,
    net_total_eo REAL
);
"""


def main():
    rows = _fetch_source_transactions(LEGACY)
    print(f"Found {len(rows)} transactions in legacy DB: {LEGACY}")
    if not rows:
        return

    fd, tmp = tempfile.mkstemp(prefix="stockman_import_test_", suffix=".db")
    os.close(fd)
    print("Using temporary DB:", tmp)
    conn = sqlite3.connect(tmp)
    try:
        cur = conn.cursor()
        cur.executescript(SCHEMA_TX)
        cur.executescript(SCHEMA_TR)
        cur.executescript(SCHEMA_EO)
        conn.commit()

        i = 0
        for tx in rows:
            i += 1
            print(
                f"Importing tx {i}/{len(rows)} cont_no={tx.get('cont_no')} src_id={tx.get('src_id_trd')}"
            )
            try:
                ok = import_transaction(conn, tx)
                print(" -> OK" if ok else " -> FAILED (no exception)")
            except Exception:
                print(" -> EXCEPTION:")
                traceback.print_exc()
    finally:
        conn.close()
        print("Temp DB left at:", tmp)


if __name__ == "__main__":
    main()
