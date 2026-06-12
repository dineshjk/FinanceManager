# -*- coding: utf-8 -*-#
# File: C:\Data\Personal\Finance_and_Investment\finprog\FinanceManager\StockMan\run_importer_test.py


"""Test runner: create a small dummy source DB, simulate choosing it via
the file dialog, open the importer modal, and auto-close after a short
delay so logs are produced for verification."""

import os
import sqlite3
import time
import tkinter as tk
from unittest import mock

from Shared.globals import STOCK_DB_PATH
from StockMan.trade_from_file import trade_entry_from_file


def _create_dummy_source(db_path: str) -> None:
    # Create a minimal DB with a transactions and exchange_orders table
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    try:
        cur.execute("""
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
            )
            """)
        cur.execute("""
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
            )
            """)
        # Insert a single transaction and one exchange_order
        # Use ISO date strings to satisfy CHECK constraints
        trd_dt = "2025-01-01"
        ord_dt = "2025-01-01"
        cur.execute(
            (
                "INSERT INTO transactions (cont_no, trd_dt, company_name, "
                "trade_type_trd, id_stk, qty_trd, wap_unit_trd, "
                "brok_unit_trd, net_amt_trd) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
            ),
            (1, trd_dt, "DUMMY CO", "BUY", 100, 10, 50.0, 5.0, 5000.0),
        )
        id_trd = cur.lastrowid
        cur.execute(
            (
                "INSERT INTO exchange_orders (id_trd, ord_no, ord_dt, trd_no, "
                "qty_eo, rate_eo, brok_unit_eo, net_rate_eo, net_total_eo) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
            ),
            (id_trd, 1, ord_dt, 1, 100, 50.0, 5.0, 50.0, 5000.0),
        )
        conn.commit()
    finally:
        conn.close()


def run():
    root = tk.Tk()
    root.withdraw()

    # Ensure the source DB sits beside the active DB (mimic user's layout)
    try:
        db_dir = os.path.dirname(os.path.abspath(STOCK_DB_PATH))
    except Exception:
        db_dir = os.getcwd()
    src_path = os.path.join(db_dir, "mystocks_old.db")
    _create_dummy_source(src_path)

    # Monkeypatch filedialog.askopenfilename to return our dummy file
    import tkinter.filedialog as _fd

    def _fake_askopenfilename(*a, **kw):
        return src_path

    with mock.patch.object(_fd, "askopenfilename", _fake_askopenfilename):
        # Open importer; schedule an auto-close shortly after so the flow runs
        # and auto-invoke the chooser so we exercise the full path resolution
        trade_entry_from_file(root, auto_close=True, auto_choose=True)
        # Let Tk process events so the modal can appear and log
        try:
            root.update()
        except Exception:
            pass
        # Give it a moment to perform logging
        time.sleep(0.5)


if __name__ == "__main__":
    run()


# File: C:\Data\Personal\Finance_and_Investment\finprog\FinanceManager\StockMan\run_importer_test.py ends here
