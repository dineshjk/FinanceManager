# -*- coding: utf-8 -*-
# tests/test_sell_management.py
"""
test_sell_management.py
-----------------------

Tests for the central FIFO sell-allocation reconciler introduced in
trade_utils.rebuild_sell_allocations / _rebuild_sell_allocation_for_stock.

Each test creates a fresh in-memory database via database_setup.create_database
and exercises the rebuild service directly (no Tkinter).
"""

import importlib
import sqlite3
import sys
from pathlib import Path

import pytest

tests_dir = Path(__file__).resolve().parent
project_root = tests_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

db_setup = importlib.import_module("StockMan.stock_database_setup")
globals_mod = importlib.import_module("Shared.globals")
trade_utils = importlib.import_module("StockMan.trade_utils")


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _init_db(tmp_path: Path) -> sqlite3.Connection:
    db_path = tmp_path / "sm_test.sqlite"
    globals_mod.STOCK_DB_PATH = str(db_path)
    db_setup.STOCK_DB_PATH = str(db_path)
    ok, msg = db_setup.create_database(None)
    assert ok, msg
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _stock(cur: sqlite3.Cursor, code: str, name: str) -> int:
    cur.execute(
        "INSERT INTO stocks (stk_code, isin, company_name, short_name) VALUES (?,?,?,?)",
        (code, f"IN{code:0<10}", name, code),
    )
    return cur.lastrowid


def _contract(cur: sqlite3.Cursor, cont_no: str, trd_dt: str) -> None:
    cur.execute(
        "INSERT INTO contracts (cont_no, trd_dt, settle_no, settle_dt, no_of_trades) VALUES (?,?,?,?,?)",
        (cont_no, trd_dt, 1, trd_dt, 1),
    )


def _trade(
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
        VALUES (?,?,?,?,?,'NSE',?,10.0,0.0,?,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,?)
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


def _sold_qty(conn: sqlite3.Connection, id_trd: int) -> int:
    row = conn.execute(
        "SELECT sold_qty FROM transactions WHERE id_trd = ?", (id_trd,)
    ).fetchone()
    return row[0] if row else 0


def _sell_records_for_sell(conn: sqlite3.Connection, sell_id_trd: int) -> list:
    return conn.execute(
        "SELECT buy_id_trd, sell_qty FROM sell_records WHERE sell_id_trd = ? ORDER BY buy_id_trd",
        (sell_id_trd,),
    ).fetchall()


# ---------------------------------------------------------------------------
# Test 1: Normal FIFO – 3 buys, 1 sell covering the first two lots
# ---------------------------------------------------------------------------


def test_normal_fifo_three_buys_one_sell(tmp_path):
    conn = _init_db(tmp_path)
    cur = conn.cursor()

    sid = _stock(cur, "AAAA", "Alpha Ltd")
    for cont, dt in [
        ("C1", "2025-01-01"),
        ("C2", "2025-01-03"),
        ("C3", "2025-01-05"),
        ("C4", "2025-01-07"),
    ]:
        _contract(cur, cont, dt)

    buy1 = _trade(
        cur,
        id_stk=sid,
        cont_no="C1",
        trd_dt="2025-01-01",
        company_name="Alpha Ltd",
        trade_type="BUY",
        qty=10,
        net_amt=1000.0,
    )
    buy2 = _trade(
        cur,
        id_stk=sid,
        cont_no="C2",
        trd_dt="2025-01-03",
        company_name="Alpha Ltd",
        trade_type="BUY",
        qty=10,
        net_amt=1100.0,
    )
    buy3 = _trade(
        cur,
        id_stk=sid,
        cont_no="C3",
        trd_dt="2025-01-05",
        company_name="Alpha Ltd",
        trade_type="BUY",
        qty=10,
        net_amt=1200.0,
    )
    sell1 = _trade(
        cur,
        id_stk=sid,
        cont_no="C4",
        trd_dt="2025-01-07",
        company_name="Alpha Ltd",
        trade_type="SELL",
        qty=15,
        net_amt=1800.0,
    )
    conn.commit()

    result = trade_utils.rebuild_sell_allocations([sid])
    assert len(result["failed"]) == 0
    assert len(result["processed"]) == 1
    assert result["processed"][0]["sells_rebuilt"] == 1

    # Reload connection state (rebuild uses its own connection)
    assert _sold_qty(conn, buy1) == 10  # fully consumed
    assert _sold_qty(conn, buy2) == 5  # 5 taken from this lot
    assert _sold_qty(conn, buy3) == 0  # untouched

    records = _sell_records_for_sell(conn, sell1)
    assert len(records) == 2
    assert records[0] == (buy1, 10)
    assert records[1] == (buy2, 5)


# ---------------------------------------------------------------------------
# Test 2: Your exact scenario – delete 3-1 buy, then rebuild
# ---------------------------------------------------------------------------


def test_buy_deleted_then_rebuild_reallocates_to_next_lot(tmp_path):
    """
    1-1-2025: BUY 10  (buy1)
    3-1-2025: BUY 10  (buy2)  ← will be deleted
    5-1-2025: BUY 10  (buy3)
    7-1-2025: SELL 15 (sell1)

    Initial FIFO allocation: buy1 fully matched (10) + buy2 partially (5).
    After deleting buy2 and running rebuild:
      sell1 should be matched to buy1 (10) + buy3 (5).
    """
    conn = _init_db(tmp_path)
    cur = conn.cursor()

    sid = _stock(cur, "BBBB", "Beta Corp")
    for cont, dt in [
        ("D1", "2025-01-01"),
        ("D2", "2025-01-03"),
        ("D3", "2025-01-05"),
        ("D4", "2025-01-07"),
    ]:
        _contract(cur, cont, dt)

    buy1 = _trade(
        cur,
        id_stk=sid,
        cont_no="D1",
        trd_dt="2025-01-01",
        company_name="Beta Corp",
        trade_type="BUY",
        qty=10,
        net_amt=1000.0,
    )
    buy2 = _trade(
        cur,
        id_stk=sid,
        cont_no="D2",
        trd_dt="2025-01-03",
        company_name="Beta Corp",
        trade_type="BUY",
        qty=10,
        net_amt=1100.0,
    )
    buy3 = _trade(
        cur,
        id_stk=sid,
        cont_no="D3",
        trd_dt="2025-01-05",
        company_name="Beta Corp",
        trade_type="BUY",
        qty=10,
        net_amt=1200.0,
    )
    sell1 = _trade(
        cur,
        id_stk=sid,
        cont_no="D4",
        trd_dt="2025-01-07",
        company_name="Beta Corp",
        trade_type="SELL",
        qty=15,
        net_amt=1800.0,
    )
    conn.commit()

    # First rebuild to set baseline allocations (buy1:10 + buy2:5)
    trade_utils.rebuild_sell_allocations([sid])
    assert _sold_qty(conn, buy2) == 5

    # Simulate deleting the 3-1-2025 BUY trade (buy2)
    # Must delete sell_records referencing buy2 first (FK cascade handles it if FK ON)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("DELETE FROM transactions WHERE id_trd = ?", (buy2,))
    conn.commit()

    # Central sell management re-runs
    result = trade_utils.rebuild_sell_allocations([sid])
    assert len(result["failed"]) == 0

    # buy1 fully consumed, buy3 picks up the remaining 5
    assert _sold_qty(conn, buy1) == 10
    assert _sold_qty(conn, buy3) == 5

    records = _sell_records_for_sell(conn, sell1)
    buy_ids = [r[0] for r in records]
    assert buy1 in buy_ids
    assert buy3 in buy_ids
    assert buy2 not in buy_ids

    qtys = {r[0]: r[1] for r in records}
    assert qtys[buy1] == 10
    assert qtys[buy3] == 5


# ---------------------------------------------------------------------------
# Test 3: Sell exceeds available – rebuild fails gracefully for that stock
# ---------------------------------------------------------------------------


def test_rebuild_fails_gracefully_when_sell_exceeds_buys(tmp_path):
    conn = _init_db(tmp_path)
    cur = conn.cursor()

    sid = _stock(cur, "CCCC", "Gamma PLC")
    _contract(cur, "E1", "2025-02-01")
    _contract(cur, "E2", "2025-02-05")

    _trade(
        cur,
        id_stk=sid,
        cont_no="E1",
        trd_dt="2025-02-01",
        company_name="Gamma PLC",
        trade_type="BUY",
        qty=5,
        net_amt=500.0,
    )
    _trade(
        cur,
        id_stk=sid,
        cont_no="E2",
        trd_dt="2025-02-05",
        company_name="Gamma PLC",
        trade_type="SELL",
        qty=10,
        net_amt=1200.0,
    )
    conn.commit()

    result = trade_utils.rebuild_sell_allocations([sid])
    assert len(result["failed"]) == 1
    assert result["failed"][0]["id_stk"] == sid
    assert (
        "available" in result["failed"][0]["error"]
        or "unmatched" in result["failed"][0]["error"]
    )


# ---------------------------------------------------------------------------
# Test 4: All-stocks mode processes multiple stocks independently
# ---------------------------------------------------------------------------


def test_all_stocks_mode_processes_each_stock(tmp_path):
    conn = _init_db(tmp_path)
    cur = conn.cursor()

    s1 = _stock(cur, "S001", "Stock One")
    s2 = _stock(cur, "S002", "Stock Two")
    for cont, dt in [
        ("F1", "2025-03-01"),
        ("F2", "2025-03-10"),
        ("F3", "2025-03-01"),
        ("F4", "2025-03-10"),
    ]:
        _contract(cur, cont, dt)

    _trade(
        cur,
        id_stk=s1,
        cont_no="F1",
        trd_dt="2025-03-01",
        company_name="Stock One",
        trade_type="BUY",
        qty=10,
        net_amt=1000.0,
    )
    _trade(
        cur,
        id_stk=s1,
        cont_no="F2",
        trd_dt="2025-03-10",
        company_name="Stock One",
        trade_type="SELL",
        qty=10,
        net_amt=1100.0,
    )

    _trade(
        cur,
        id_stk=s2,
        cont_no="F3",
        trd_dt="2025-03-01",
        company_name="Stock Two",
        trade_type="BUY",
        qty=20,
        net_amt=2000.0,
    )
    _trade(
        cur,
        id_stk=s2,
        cont_no="F4",
        trd_dt="2025-03-10",
        company_name="Stock Two",
        trade_type="SELL",
        qty=20,
        net_amt=2200.0,
    )
    conn.commit()

    result = trade_utils.rebuild_sell_allocations()  # None → all stocks
    assert len(result["failed"]) == 0
    assert len(result["processed"]) == 2
    processed_ids = {p["id_stk"] for p in result["processed"]}
    assert s1 in processed_ids
    assert s2 in processed_ids


# ---------------------------------------------------------------------------
# Test 5: Stock with only buys (no sells) is skipped gracefully
# ---------------------------------------------------------------------------


def test_stock_with_no_sells_is_skipped(tmp_path):
    conn = _init_db(tmp_path)
    cur = conn.cursor()

    sid = _stock(cur, "G001", "HoldOnly Corp")
    _contract(cur, "G1", "2025-04-01")
    _trade(
        cur,
        id_stk=sid,
        cont_no="G1",
        trd_dt="2025-04-01",
        company_name="HoldOnly Corp",
        trade_type="BUY",
        qty=10,
        net_amt=1000.0,
    )
    conn.commit()

    result = trade_utils.rebuild_sell_allocations([sid])
    # Should succeed (nothing to do) or produce 0 processed (stock not returned
    # by query because it has no SELL trades) – either is acceptable.
    assert len(result["failed"]) == 0


# ---------------------------------------------------------------------------
# Test 6: sell_records are idempotent – running rebuild twice gives same result
# ---------------------------------------------------------------------------


def test_rebuild_is_idempotent(tmp_path):
    conn = _init_db(tmp_path)
    cur = conn.cursor()

    sid = _stock(cur, "H001", "Idem Corp")
    for cont, dt in [
        ("H1", "2025-05-01"),
        ("H2", "2025-05-05"),
        ("H3", "2025-05-10"),
    ]:
        _contract(cur, cont, dt)

    buy1 = _trade(
        cur,
        id_stk=sid,
        cont_no="H1",
        trd_dt="2025-05-01",
        company_name="Idem Corp",
        trade_type="BUY",
        qty=10,
        net_amt=1000.0,
    )
    buy2 = _trade(
        cur,
        id_stk=sid,
        cont_no="H2",
        trd_dt="2025-05-05",
        company_name="Idem Corp",
        trade_type="BUY",
        qty=10,
        net_amt=1100.0,
    )
    sell1 = _trade(
        cur,
        id_stk=sid,
        cont_no="H3",
        trd_dt="2025-05-10",
        company_name="Idem Corp",
        trade_type="SELL",
        qty=15,
        net_amt=1800.0,
    )
    conn.commit()

    trade_utils.rebuild_sell_allocations([sid])
    records_after_first = _sell_records_for_sell(conn, sell1)

    trade_utils.rebuild_sell_allocations([sid])
    records_after_second = _sell_records_for_sell(conn, sell1)

    assert records_after_first == records_after_second
    assert _sold_qty(conn, buy1) == 10
    assert _sold_qty(conn, buy2) == 5


# ---------------------------------------------------------------------------
# Test 7: _perform_trade_removal rolls back BUY deletion on over-sell risk
#
# Simulates the company-correction workflow:
#   1. Enter BUY + SELL for wrong company (sid_wrong).
#   2. Delete the BUY via _perform_trade_removal.
#   3. Assert delete is rejected and transaction is rolled back so no
#      over-sell state is persisted.
# ---------------------------------------------------------------------------


def test_buy_removal_rolls_back_when_it_would_oversell(tmp_path):
    """
    delete_trade on a BUY should fail atomically if removal would
    leave SELL trades unmatched.
    """
    rollback_manager = importlib.import_module("StockMan.rollback_manager")

    conn = _init_db(tmp_path)
    cur = conn.cursor()

    sid = _stock(cur, "ZZZ1", "Wrong Corp")
    _contract(cur, "Z1", "2025-06-01")
    _contract(cur, "Z2", "2025-06-10")

    buy_id = _trade(
        cur,
        id_stk=sid,
        cont_no="Z1",
        trd_dt="2025-06-01",
        company_name="Wrong Corp",
        trade_type="BUY",
        qty=10,
        net_amt=1000.0,
    )
    sell_id = _trade(
        cur,
        id_stk=sid,
        cont_no="Z2",
        trd_dt="2025-06-10",
        company_name="Wrong Corp",
        trade_type="SELL",
        qty=10,
        net_amt=1200.0,
    )
    conn.commit()

    # Establish initial FIFO allocation
    trade_utils.rebuild_sell_allocations([sid])
    assert len(_sell_records_for_sell(conn, sell_id)) == 1
    assert _sold_qty(conn, buy_id) == 10

    # Now remove the BUY trade (simulates deleting wrong-company trade).
    # This must fail because the remaining SELL can no longer be allocated.
    ok, _ = rollback_manager.delete_trade(buy_id)
    assert not ok, "delete_trade should rollback on over-sell"

    # Existing allocation must remain untouched after rollback.
    remaining = conn.execute(
        "SELECT COUNT(*) FROM sell_records WHERE id_stk = ?", (sid,)
    ).fetchone()[0]
    assert remaining == 1

    # BUY row must still exist because removal was rolled back.
    gone = conn.execute(
        "SELECT COUNT(*) FROM transactions WHERE id_trd = ?", (buy_id,)
    ).fetchone()[0]
    assert gone == 1

    assert _sold_qty(conn, buy_id) == 10


# ---------------------------------------------------------------------------
# Test 8: in-transaction enforcement failure is rollback-safe
# ---------------------------------------------------------------------------


def test_enforcement_failure_rollback_restores_prechange_state(tmp_path):
    conn = _init_db(tmp_path)
    cur = conn.cursor()

    sid = _stock(cur, "ZZZ2", "Rollback Corp")
    _contract(cur, "R1", "2025-07-01")
    _contract(cur, "R2", "2025-07-05")

    buy_id = _trade(
        cur,
        id_stk=sid,
        cont_no="R1",
        trd_dt="2025-07-01",
        company_name="Rollback Corp",
        trade_type="BUY",
        qty=10,
        net_amt=1000.0,
    )
    sell_id = _trade(
        cur,
        id_stk=sid,
        cont_no="R2",
        trd_dt="2025-07-05",
        company_name="Rollback Corp",
        trade_type="SELL",
        qty=10,
        net_amt=1200.0,
    )
    conn.commit()

    trade_utils.rebuild_sell_allocations([sid])
    assert _sold_qty(conn, buy_id) == 10
    assert len(_sell_records_for_sell(conn, sell_id)) == 1

    # Simulate an in-flight update that would create over-sell.
    conn.execute("BEGIN")
    conn.execute("UPDATE transactions SET qty_trd = 5 WHERE id_trd = ?", (buy_id,))
    with pytest.raises(ValueError):
        trade_utils.enforce_no_oversell_for_stock(conn.cursor(), sid)
    conn.rollback()

    qty_after = conn.execute(
        "SELECT qty_trd FROM transactions WHERE id_trd = ?", (buy_id,)
    ).fetchone()[0]
    assert qty_after == 10
    assert _sold_qty(conn, buy_id) == 10
    assert len(_sell_records_for_sell(conn, sell_id)) == 1
