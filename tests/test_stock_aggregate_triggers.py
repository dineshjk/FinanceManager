# -*- coding: utf-8 -*-
# tests/test_stock_aggregate_triggers.py
import importlib
import sqlite3
import sys
from pathlib import Path

tests_dir = Path(__file__).resolve().parent
project_root = tests_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

db_setup = importlib.import_module("StockMan.stock_database_setup")
globals_mod = importlib.import_module("Shared.globals")


def _create_temp_database(tmp_path: Path) -> sqlite3.Connection:
    db_path = tmp_path / "trigger_test.sqlite"
    globals_mod.STOCK_DB_PATH = str(db_path)
    db_setup.STOCK_DB_PATH = str(db_path)
    ok, msg = db_setup.create_database(None)
    assert ok, msg

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _insert_stock(cur: sqlite3.Cursor, stk_code: str, company_name: str) -> int:
    cur.execute(
        """
        INSERT INTO stocks (stk_code, isin, company_name, short_name)
        VALUES (?, ?, ?, ?)
        """,
        (
            stk_code,
            f"IN{stk_code:0<10}",
            company_name,
            stk_code,
        ),
    )
    return cur.lastrowid


def _insert_contract(cur: sqlite3.Cursor, cont_no: str, trd_dt: str) -> None:
    cur.execute(
        """
        INSERT INTO contracts (cont_no, trd_dt, settle_no, settle_dt, no_of_trades)
        VALUES (?, ?, ?, ?, ?)
        """,
        (cont_no, trd_dt, 1, trd_dt, 1),
    )


def _insert_transaction(
    cur: sqlite3.Cursor,
    *,
    id_stk: int,
    cont_no: str,
    trd_dt: str,
    company_name: str,
    trade_type: str,
    qty: int,
    net_amt: float,
) -> int:
    cur.execute(
        """
        INSERT INTO transactions (
            id_stk, cont_no, trd_dt, company_name, trade_type_trd,
            exchange, qty_trd, wap_unit_trd, brok_unit_trd,
            price_lot_trd, brok_lot_trd, etc_trd, sebi_trd,
            sell_chrg_trd, gst_trd, stamp_trd, stt_trd, igst_trd,
            net_amt_trd
        )
        VALUES (?, ?, ?, ?, ?, 'NSE', ?, 10.0, 0.0, ?, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, ?)
        """,
        (
            id_stk,
            cont_no,
            trd_dt,
            company_name,
            trade_type,
            qty,
            net_amt,
            net_amt,
        ),
    )
    return cur.lastrowid


def test_buy_triggers_move_quantities_and_investment_on_stock_change(tmp_path):
    conn = _create_temp_database(tmp_path)
    try:
        cur = conn.cursor()
        alpha_id = _insert_stock(cur, "ALPHA", "Alpha Ltd")
        beta_id = _insert_stock(cur, "BETA", "Beta Ltd")
        _insert_contract(cur, "CNT-1", "2025-01-01")
        tx_id = _insert_transaction(
            cur,
            id_stk=alpha_id,
            cont_no="CNT-1",
            trd_dt="2025-01-01",
            company_name="Alpha Ltd",
            trade_type="BUY",
            qty=10,
            net_amt=1000.0,
        )
        conn.commit()

        cur.execute(
            "SELECT buy_qty, total_investment_amt FROM stocks WHERE id_stk = ?",
            (alpha_id,),
        )
        assert cur.fetchone() == (10, 1000.0)

        cur.execute(
            """
            UPDATE transactions
            SET id_stk = ?, company_name = ?
            WHERE id_trd = ?
            """,
            (beta_id, "Beta Ltd", tx_id),
        )
        conn.commit()

        cur.execute(
            "SELECT buy_qty, total_investment_amt FROM stocks WHERE id_stk = ?",
            (alpha_id,),
        )
        assert cur.fetchone() == (0, 0.0)

        cur.execute(
            "SELECT buy_qty, total_investment_amt FROM stocks WHERE id_stk = ?",
            (beta_id,),
        )
        assert cur.fetchone() == (10, 1000.0)
    finally:
        conn.close()


def test_sell_triggers_move_quantities_and_amounts_on_stock_change(tmp_path):
    conn = _create_temp_database(tmp_path)
    try:
        cur = conn.cursor()
        alpha_id = _insert_stock(cur, "ALPHA", "Alpha Ltd")
        beta_id = _insert_stock(cur, "BETA", "Beta Ltd")
        _insert_contract(cur, "CNT-2", "2025-01-01")
        tx_id = _insert_transaction(
            cur,
            id_stk=alpha_id,
            cont_no="CNT-2",
            trd_dt="2025-01-01",
            company_name="Alpha Ltd",
            trade_type="SELL",
            qty=4,
            net_amt=400.0,
        )
        conn.commit()

        cur.execute(
            "SELECT sell_qty, sell_amt FROM stocks WHERE id_stk = ?",
            (alpha_id,),
        )
        assert cur.fetchone() == (4, 400.0)

        cur.execute(
            """
            UPDATE transactions
            SET id_stk = ?, company_name = ?
            WHERE id_trd = ?
            """,
            (beta_id, "Beta Ltd", tx_id),
        )
        conn.commit()

        cur.execute(
            "SELECT sell_qty, sell_amt FROM stocks WHERE id_stk = ?",
            (alpha_id,),
        )
        assert cur.fetchone() == (0, 0.0)

        cur.execute(
            "SELECT sell_qty, sell_amt FROM stocks WHERE id_stk = ?",
            (beta_id,),
        )
        assert cur.fetchone() == (4, 400.0)
    finally:
        conn.close()
