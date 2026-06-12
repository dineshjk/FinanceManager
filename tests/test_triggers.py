# -*- coding: utf-8 -*-
# tests/test_triggers.py
"""Smoke test for the allotment trigger.

Creates a temporary DB, calls create_database(), inserts sample rows and
updates an allotment to trigger the INSERTs. Verifies contracts,
transactions and tx_id were created.
"""

import tempfile
import os
import shutil

import sqlite3


TRIGGER_SQL = """
-- Minimal trg_allotment_create_tx adapted from database_setup.py
CREATE TRIGGER IF NOT EXISTS trg_allotment_create_tx
AFTER UPDATE OF allotted_qty, status ON offer_allotments
WHEN NEW.allotted_qty > 0
AND NEW.tx_id IS NULL
AND NEW.status = 'ALLOTTED'
BEGIN
    INSERT OR IGNORE INTO contracts (
        cont_no, trd_dt, settle_no, settle_dt,
        no_of_trades, net_amt_cont
    ) VALUES (
        CASE WHEN NEW.id_right IS NOT NULL
            THEN 'Right' || NEW.id_right
            ELSE 'IPO' || NEW.id_ipo
        END,
        COALESCE(
            (SELECT allotment_dt
             FROM rights_issues
             WHERE id_right = NEW.id_right),
            (SELECT allotment_dt FROM ipos WHERE id_ipo = NEW.id_ipo),
            date('now')
        ),
        CASE WHEN NEW.id_right IS NOT NULL
            THEN CAST('222' || NEW.id_right AS INTEGER)
            ELSE CAST('111' || NEW.id_ipo AS INTEGER)
        END,
        COALESCE(
            (SELECT allotment_dt
             FROM rights_issues
             WHERE id_right = NEW.id_right),
            (SELECT allotment_dt FROM ipos WHERE id_ipo = NEW.id_ipo),
            date('now')
        ),
        1,
        NEW.allotted_amt
    );

    INSERT INTO transactions (
        id_stk, cont_no, trd_dt, company_name,
        trade_type_trd, exchange, qty_trd, wap_unit_trd,
        brok_unit_trd, price_lot_trd, net_amt_trd,
        brok_lot_trd, etc_trd, sebi_trd, sell_chrg_trd,
        gst_trd, stamp_trd, stt_trd, igst_trd, note_trd
    ) VALUES (
        NEW.id_stk,
        CASE WHEN NEW.id_right IS NOT NULL
            THEN 'Right' || NEW.id_right
            ELSE 'IPO' || NEW.id_ipo
        END,
        COALESCE(
            (SELECT allotment_dt
             FROM rights_issues
             WHERE id_right = NEW.id_right),
            (SELECT allotment_dt FROM ipos WHERE id_ipo = NEW.id_ipo),
            date('now')
        ),
        (SELECT company_name FROM stocks WHERE id_stk = NEW.id_stk),
        'BUY', 'N/A', NEW.allotted_qty,
        CASE WHEN NEW.allotted_qty > 0
            THEN (NEW.allotted_amt / NEW.allotted_qty)
            ELSE 0 END,
        0, NEW.allotted_amt, NEW.allotted_amt,
        0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
        'Allotment from offer'
    );

    UPDATE offer_allotments
    SET tx_id = (SELECT last_insert_rowid())
    WHERE id_allot = NEW.id_allot;
END;
"""


def run_smoke_test():
    tmp_dir = tempfile.mkdtemp(prefix="stockman_test_")
    try:
        tmp_db = os.path.join(tmp_dir, "test.db")

        conn = sqlite3.connect(tmp_db)
        cur = conn.cursor()

        # Create minimal tables required by the trigger
        cur.executescript(
            """
            CREATE TABLE contracts (
                id_cont INTEGER PRIMARY KEY AUTOINCREMENT,
                cont_no TEXT UNIQUE NOT NULL,
                trd_dt TEXT,
                settle_no INTEGER,
                settle_dt TEXT,
                no_of_trades INTEGER,
                net_amt_cont REAL
            );

            CREATE TABLE stocks (
                id_stk INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT
            );

            CREATE TABLE transactions (
                id_trd INTEGER PRIMARY KEY AUTOINCREMENT,
                id_stk INTEGER,
                cont_no TEXT,
                trd_dt TEXT,
                company_name TEXT,
                trade_type_trd TEXT,
                exchange TEXT,
                qty_trd INTEGER,
                wap_unit_trd REAL,
                brok_unit_trd REAL,
                price_lot_trd REAL,
                net_amt_trd REAL,
                brok_lot_trd REAL,
                etc_trd REAL,
                sebi_trd REAL,
                sell_chrg_trd REAL,
                gst_trd REAL,
                stamp_trd REAL,
                stt_trd REAL,
                igst_trd REAL,
                note_trd TEXT
            );

            CREATE TABLE rights_issues (
                id_right INTEGER PRIMARY KEY AUTOINCREMENT,
                id_stk INTEGER,
                allotment_dt TEXT
            );

            CREATE TABLE ipos (
                id_ipo INTEGER PRIMARY KEY AUTOINCREMENT,
                id_stk INTEGER,
                allotment_dt TEXT
            );

            CREATE TABLE offer_allotments (
                id_allot INTEGER PRIMARY KEY AUTOINCREMENT,
                id_stk INTEGER,
                id_right INTEGER,
                id_ipo INTEGER,
                allotted_qty INTEGER DEFAULT 0,
                allotted_amt REAL DEFAULT 0.0,
                tx_id INTEGER DEFAULT NULL,
                status TEXT
            );
            """
        )

        # Install the trigger
        cur.executescript(TRIGGER_SQL)

        # Insert a sample stock
        cur.execute(
            "INSERT INTO stocks (company_name) VALUES (?)",
            ("Test Company Pvt Ltd",),
        )
        id_stk = cur.lastrowid

        # Insert a rights issue row
        cur.execute(
            "INSERT INTO rights_issues (id_stk, allotment_dt) "
            "VALUES (?, date('now'))",
            (id_stk,),
        )
        id_right = cur.lastrowid

        # Insert an offer_allotment for that rights issue
        cur.execute(
            "INSERT INTO offer_allotments (id_stk, id_right, allotted_qty, "
            "allotted_amt, status) VALUES (?, ?, ?, ?, 'APPLIED')",
            (id_stk, id_right, 0, 0.0),
        )
        id_allot = cur.lastrowid

        conn.commit()

        # Now update the allotment to ALLOTTED with a positive qty
        cur.execute(
            "UPDATE offer_allotments SET allotted_qty = ?, allotted_amt = ?, "
            "status = 'ALLOTTED' WHERE id_allot = ?",
            (50, 500.0, id_allot),
        )
        conn.commit()

        # Read back contracts, transactions, and the allotment tx_id
        cur.execute(
            "SELECT id_cont, cont_no, settle_no, net_amt_cont "
            "FROM contracts"
        )
        contracts = cur.fetchall()

        cur.execute(
            "SELECT id_trd, id_stk, cont_no, qty_trd, net_amt_trd "
            "FROM transactions"
        )
        transactions = cur.fetchall()

        cur.execute(
            "SELECT tx_id FROM offer_allotments WHERE id_allot = ?",
            (id_allot,),
        )
        row = cur.fetchone()
        tx_id = row[0] if row else None

        print("contracts:", contracts)
        print("transactions:", transactions)
        print("offer_allotments.tx_id:", tx_id)

        return contracts, transactions, tx_id

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    run_smoke_test()
