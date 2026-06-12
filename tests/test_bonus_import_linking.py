import importlib
import sqlite3
from pathlib import Path

import pytest


@pytest.fixture
def patched_db_paths(tmp_path: Path):
    target_db = tmp_path / "target_stockman.db"
    source_db = tmp_path / "legacy_stockman.db"

    db_setup = importlib.import_module("StockMan.stock_database_setup")
    globals_mod = importlib.import_module("Shared.globals")

    orig_db_path = getattr(globals_mod, "STOCK_DB_PATH", None)
    orig_db_path_ds = getattr(db_setup, "STOCK_DB_PATH", None)

    globals_mod.STOCK_DB_PATH = str(target_db)  # type: ignore[attr-defined]
    db_setup.STOCK_DB_PATH = str(target_db)  # type: ignore[attr-defined]

    yield str(source_db), str(target_db)

    globals_mod.STOCK_DB_PATH = orig_db_path  # type: ignore[attr-defined]
    if orig_db_path_ds is None:
        try:
            delattr(db_setup, "STOCK_DB_PATH")
        except AttributeError:
            pass
    else:
        db_setup.STOCK_DB_PATH = orig_db_path_ds  # type: ignore[attr-defined]


def _create_legacy_bonus_schema(cur: sqlite3.Cursor) -> None:
    cur.executescript("""
        CREATE TABLE stocks (
            id_stk INTEGER PRIMARY KEY,
            stk_code TEXT,
            isin TEXT,
            company_name TEXT,
            short_name TEXT
        );

        CREATE TABLE corp_acts (
            id_act INTEGER PRIMARY KEY,
            id_stk INTEGER NOT NULL,
            act_dt TEXT NOT NULL,
            type_act TEXT NOT NULL,
            details_act TEXT DEFAULT '',
            ratio_old INTEGER DEFAULT 1,
            ratio_new INTEGER DEFAULT 1,
            note_act TEXT DEFAULT ''
        );

        CREATE TABLE bonus_issues (
            id_bonus INTEGER PRIMARY KEY,
            id_act INTEGER,
            id_stk INTEGER NOT NULL,
            id_trd INTEGER,
            ex_dt TEXT NOT NULL,
            record_dt TEXT NOT NULL,
            ratio_old INTEGER NOT NULL,
            ratio_new INTEGER NOT NULL,
            held_qty INTEGER NOT NULL,
            bonus_qty INTEGER NOT NULL,
            note_bonus TEXT DEFAULT ''
        );

        CREATE TABLE contracts (
            id_cont INTEGER PRIMARY KEY,
            cont_no TEXT UNIQUE NOT NULL,
            trd_dt TEXT NOT NULL,
            settle_no INTEGER DEFAULT 0,
            settle_dt TEXT NOT NULL,
            no_of_trades INTEGER DEFAULT 1,
            net_amt_cont REAL DEFAULT 0.0,
            net_amt_cont_applicable REAL DEFAULT 0.0
        );

        CREATE TABLE transactions (
            id_trd INTEGER PRIMARY KEY,
            id_stk INTEGER NOT NULL,
            cont_no TEXT NOT NULL,
            trd_dt TEXT NOT NULL,
            company_name TEXT NOT NULL,
            trade_type_trd TEXT NOT NULL,
            exchange TEXT DEFAULT 'NSE',
            qty_trd INTEGER DEFAULT 0,
            wap_unit_trd REAL DEFAULT 0.0,
            price_lot_trd REAL DEFAULT 0.0,
            net_amt_trd REAL DEFAULT 0.0,
            net_amt_trd_applicable REAL DEFAULT 0.0,
            sold_qty INTEGER DEFAULT 0,
            note_trd TEXT DEFAULT ''
        );

        CREATE TABLE exchange_orders (
            id_eo INTEGER PRIMARY KEY,
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

        CREATE TABLE computed_bank (
            id_comp_bt INTEGER PRIMARY KEY,
            cont_no TEXT,
            comp_bt_dt TEXT,
            comp_bt_type TEXT,
            comp_bt_amt REAL,
            comp_bt_amt_applicable REAL,
            comp_bt_desc TEXT
        );
        """)


def test_bonus_trade_import_backfills_bonus_issue_link(patched_db_paths):
    source_db, target_db = patched_db_paths

    db_setup = importlib.import_module("StockMan.stock_database_setup")
    importer = importlib.import_module("StockMan.trade_from_file")

    ok, _ = db_setup.create_database(None)
    assert ok is True

    source_conn = sqlite3.connect(source_db)
    source_conn.row_factory = sqlite3.Row
    source_cur = source_conn.cursor()
    _create_legacy_bonus_schema(source_cur)

    source_cur.execute(
        "INSERT INTO stocks VALUES (?, ?, ?, ?, ?)",
        (1, "ABC", "IN0000000001", "ABC Ltd", "ABC"),
    )
    source_cur.execute(
        """
        INSERT INTO corp_acts
            (id_act, id_stk, act_dt, type_act, details_act, ratio_old,
             ratio_new, note_act)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (7, 1, "2025-01-01", "BONUS", "1:1 Bonus Issue", 1, 1, ""),
    )
    source_cur.execute(
        """
        INSERT INTO bonus_issues
            (id_bonus, id_act, id_stk, id_trd, ex_dt, record_dt, ratio_old,
             ratio_new, held_qty, bonus_qty, note_bonus)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (3, 7, 1, None, "2025-01-01", "2025-01-01", 1, 1, 10, 10, ""),
    )
    source_cur.execute(
        """
        INSERT INTO contracts
            (id_cont, cont_no, trd_dt, settle_no, settle_dt, no_of_trades,
             net_amt_cont, net_amt_cont_applicable)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (1, "BONUS_7", "2025-01-15", 2227, "2025-01-15", 1, 0.0, 0.0),
    )
    source_cur.execute(
        """
        INSERT INTO transactions
            (id_trd, id_stk, cont_no, trd_dt, company_name, trade_type_trd,
             exchange, qty_trd, wap_unit_trd, price_lot_trd, net_amt_trd,
             net_amt_trd_applicable, sold_qty, note_trd)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            11,
            1,
            "BONUS_7",
            "2025-01-15",
            "ABC Ltd",
            "BUY",
            "NSE",
            10,
            0.0,
            0.0,
            0.0,
            0.0,
            0,
            "Bonus Shares Allocation (1:1 Bonus Issue)",
        ),
    )
    source_conn.commit()

    target_conn = sqlite3.connect(target_db)
    importer.sync_stocks(source_conn, target_conn)

    corp_event = {
        "type": "CORP_ACT",
        "date": "2025-01-01",
        "company": "ABC Ltd",
        "action": "BONUS",
        "qty": 0,
        "rate": 0.0,
        "net": 0.0,
        "status": "1:1 Bonus Issue",
        "old_id": 7,
    }
    trade_event = {
        "type": "TRADE",
        "date": "2025-01-15",
        "company": "ABC Ltd",
        "action": "BUY",
        "qty": 10,
        "rate": 0.0,
        "net": 0.0,
        "status": "Executed",
        "old_id": 11,
        "cont_no": "BONUS_7",
    }

    importer.process_single_event(corp_event, source_conn, target_conn)
    importer.process_single_event(trade_event, source_conn, target_conn)

    target_cur = target_conn.cursor()
    target_cur.execute("SELECT id_trd FROM bonus_issues")
    bonus_link = target_cur.fetchone()
    assert bonus_link is not None
    assert bonus_link[0] is not None

    target_cur.execute("UPDATE bonus_issues SET id_trd = NULL")
    target_conn.commit()
    target_conn.close()
    source_conn.close()

    result = db_setup.run_schema_migrations()

    assert result["repaired"].get("bonus_issues.id_trd") == 1
    assert result["unresolved"].get("bonus_issues.id_trd") == 0

    verify_conn = sqlite3.connect(target_db)
    verify_cur = verify_conn.cursor()
    verify_cur.execute("SELECT id_trd FROM bonus_issues")
    repaired_link = verify_cur.fetchone()
    assert repaired_link is not None
    assert repaired_link[0] is not None
    verify_conn.close()
