# -*- coding: utf-8 -*-
# tests/test_link_repair.py
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


def _create_temp_database(tmp_path: Path) -> tuple[sqlite3.Connection, str]:
    db_path = tmp_path / "link_repair.sqlite"
    globals_mod.STOCK_DB_PATH = str(db_path)
    db_setup.STOCK_DB_PATH = str(db_path)
    ok, msg = db_setup.create_database(None)
    assert ok, msg

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    return conn, str(db_path)


def _insert_stock(cur: sqlite3.Cursor, code: str, name: str) -> int:
    cur.execute(
        """
        INSERT INTO stocks (stk_code, isin, company_name, short_name)
        VALUES (?, ?, ?, ?)
        """,
        (code, f"IN{code:0<10}", name, code),
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
    note_trd: str = "",
) -> int:
    cur.execute(
        """
        INSERT INTO transactions (
            id_stk, cont_no, trd_dt, company_name, trade_type_trd,
            exchange, qty_trd, wap_unit_trd, brok_unit_trd,
            price_lot_trd, brok_lot_trd, etc_trd, sebi_trd,
            sell_chrg_trd, gst_trd, stamp_trd, stt_trd, igst_trd,
            net_amt_trd, note_trd
        )
        VALUES (?, ?, ?, ?, ?, 'NSE', ?, 10.0, 0.0, ?, 0.0, 0.0, 0.0,
                0.0, 0.0, 0.0, 0.0, 0.0, ?, ?)
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
            note_trd,
        ),
    )
    return cur.lastrowid


def _insert_computed_bank(
    cur: sqlite3.Cursor,
    *,
    cont_no: str,
    comp_bt_dt: str,
    comp_bt_type: str,
    comp_bt_amt: float,
    comp_bt_desc: str,
) -> int:
    cur.execute(
        """
        INSERT INTO computed_bank (
            cont_no, comp_bt_dt, comp_bt_type, comp_bt_amt,
            comp_bt_amt_applicable, comp_bt_desc
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            cont_no,
            comp_bt_dt,
            comp_bt_type,
            comp_bt_amt,
            comp_bt_amt,
            comp_bt_desc,
        ),
    )
    return cur.lastrowid


def test_bonus_issue_link_repair_fills_id_trd(tmp_path):
    conn, db_path = _create_temp_database(tmp_path)
    try:
        cur = conn.cursor()
        id_stk = _insert_stock(cur, "BONUS", "Bonus Ltd")

        cur.execute(
            """
            INSERT INTO corp_acts (id_stk, act_dt, type_act, details_act)
            VALUES (?, ?, 'BONUS', ?)
            """,
            (id_stk, "2025-01-10", "1:1 Bonus"),
        )
        id_act = cur.lastrowid

        cur.execute(
            """
            INSERT INTO bonus_issues (
                id_act, id_stk, ex_dt, record_dt, ratio_old, ratio_new,
                held_qty, bonus_qty
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (id_act, id_stk, "2025-01-10", "2025-01-10", 1, 1, 50, 50),
        )
        id_bonus = cur.lastrowid

        _insert_contract(cur, f"BONUS_{id_bonus}", "2025-01-10")
        tx_id = _insert_transaction(
            cur,
            id_stk=id_stk,
            cont_no=f"BONUS_{id_bonus}",
            trd_dt="2025-01-10",
            company_name="Bonus Ltd",
            trade_type="BUY",
            qty=50,
            net_amt=500.0,
        )
        conn.commit()

        repairs = db_setup.repair_existing_links(db_path)
        unresolved = db_setup.verify_existing_links(db_path)

        assert repairs["bonus_issues.id_trd"] >= 1
        assert unresolved["bonus_issues.id_trd"] == 0

        cur.execute("SELECT id_trd FROM bonus_issues WHERE id_bonus = ?", (id_bonus,))
        assert cur.fetchone()[0] == tx_id
    finally:
        conn.close()


def test_merger_link_repair_fills_trade_and_bank_links(tmp_path):
    conn, db_path = _create_temp_database(tmp_path)
    try:
        cur = conn.cursor()
        old_stk = _insert_stock(cur, "OLDCO", "Old Co")
        new_stk = _insert_stock(cur, "NEWCO", "New Co")
        cont_no = "MRG_CONT_1"

        _insert_contract(cur, cont_no, "2025-02-01")
        sell_id = _insert_transaction(
            cur,
            id_stk=old_stk,
            cont_no=cont_no,
            trd_dt="2025-02-01",
            company_name="Old Co",
            trade_type="SELL",
            qty=10,
            net_amt=1000.0,
        )
        buy_id = _insert_transaction(
            cur,
            id_stk=new_stk,
            cont_no=cont_no,
            trd_dt="2025-02-01",
            company_name="New Co",
            trade_type="BUY",
            qty=5,
            net_amt=1000.0,
        )
        comp_bt_id = _insert_computed_bank(
            cur,
            cont_no=cont_no,
            comp_bt_dt="2025-02-01",
            comp_bt_type="CREDIT",
            comp_bt_amt=25.0,
            comp_bt_desc="Merger fractional refund",
        )

        cur.execute(
            """
            INSERT INTO merger (
                id_stk_existing, id_stk_new, name, ratio_old, ratio_new,
                held_qty, newly_allotted_qty, allotment_dt, invested_amt,
                refund_amt, cont_no
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                old_stk,
                new_stk,
                "Merger 1",
                2,
                1,
                10,
                5,
                "2025-02-01",
                1000.0,
                25.0,
                cont_no,
            ),
        )
        id_merger = cur.lastrowid
        conn.commit()

        repairs = db_setup.repair_existing_links(db_path)
        unresolved = db_setup.verify_existing_links(db_path)

        assert repairs["merger.id_extinguish_trd"] >= 1
        assert repairs["merger.id_allotment_trd"] >= 1
        assert repairs["merger.id_trd"] >= 1
        assert repairs["merger.id_comp_bt"] >= 1
        assert unresolved["merger.id_extinguish_trd"] == 0
        assert unresolved["merger.id_allotment_trd"] == 0
        assert unresolved["merger.id_trd"] == 0
        assert unresolved["merger.id_comp_bt"] == 0

        cur.execute(
            """
            SELECT id_extinguish_trd, id_allotment_trd, id_trd, id_comp_bt
            FROM merger WHERE id_merger = ?
            """,
            (id_merger,),
        )
        assert cur.fetchone() == (sell_id, buy_id, buy_id, comp_bt_id)
    finally:
        conn.close()


def test_demerger_link_repair_fills_parent_child_and_bank_links(tmp_path):
    conn, db_path = _create_temp_database(tmp_path)
    try:
        cur = conn.cursor()
        parent_stk = _insert_stock(cur, "PARCO", "Parent Co")
        child_stk = _insert_stock(cur, "CHILD", "Child Co")

        cur.execute(
            """
            INSERT INTO demerger_events (
                id_stk_parent, ex_dt, record_dt, total_held_qty,
                total_invested_amt
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (parent_stk, "2025-03-01", "2025-03-01", 10, 1000.0),
        )
        id_demerger = cur.lastrowid

        _insert_contract(cur, f"DEM_DED_{id_demerger}", "2025-03-01")
        parent_trd_id = _insert_transaction(
            cur,
            id_stk=parent_stk,
            cont_no=f"DEM_DED_{id_demerger}",
            trd_dt="2025-03-01",
            company_name="Parent Co",
            trade_type="SELL",
            qty=10,
            net_amt=600.0,
        )

        _insert_contract(cur, f"DEM_ALT_{id_demerger}_0", "2025-03-01")
        child_trd_id = _insert_transaction(
            cur,
            id_stk=child_stk,
            cont_no=f"DEM_ALT_{id_demerger}_0",
            trd_dt="2025-03-01",
            company_name="Child Co",
            trade_type="BUY",
            qty=4,
            net_amt=400.0,
        )
        child_comp_bt = _insert_computed_bank(
            cur,
            cont_no=f"DEM_ALT_{id_demerger}_0",
            comp_bt_dt="2025-03-01",
            comp_bt_type="CREDIT",
            comp_bt_amt=15.0,
            comp_bt_desc="Demerger fractional refund",
        )

        cur.execute(
            """
            INSERT INTO demerger_allotments (
                id_demerger, id_stk_child, ratio_parent, ratio_child,
                coa_percent, allotted_qty, transferred_cost, refund_amt
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (id_demerger, child_stk, 5, 2, 40.0, 4, 400.0, 15.0),
        )
        id_allotment = cur.lastrowid
        conn.commit()

        repairs = db_setup.repair_existing_links(db_path)
        unresolved = db_setup.verify_existing_links(db_path)

        assert repairs["demerger_events.parent_adjustment_trd_id"] >= 1
        assert repairs["demerger_allotments.id_trd"] >= 1
        assert repairs["demerger_allotments.id_comp_bt"] >= 1
        assert unresolved["demerger_events.parent_adjustment_trd_id"] == 0
        assert unresolved["demerger_allotments.id_trd"] == 0
        assert unresolved["demerger_allotments.id_comp_bt"] == 0

        cur.execute(
            "SELECT parent_adjustment_trd_id FROM demerger_events WHERE id_demerger = ?",
            (id_demerger,),
        )
        assert cur.fetchone()[0] == parent_trd_id

        cur.execute(
            "SELECT id_trd, id_comp_bt FROM demerger_allotments WHERE id_allotment = ?",
            (id_allotment,),
        )
        assert cur.fetchone() == (child_trd_id, child_comp_bt)
    finally:
        conn.close()
