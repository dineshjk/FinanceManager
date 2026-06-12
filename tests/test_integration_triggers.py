"""Integration tests for current schema trigger and repair behavior."""

import importlib
import sqlite3
from pathlib import Path

import pytest


@pytest.fixture
def tmp_db_path_fixture(tmp_path: Path):
    """Create a temporary DB and patch the project's STOCK_DB_PATH to use it."""
    tmp_db = tmp_path / "test_stockman.db"

    db_setup = importlib.import_module("StockMan.stock_database_setup")
    globals_mod = importlib.import_module("Shared.globals")

    orig_db_path = getattr(globals_mod, "STOCK_DB_PATH", None)
    globals_mod.STOCK_DB_PATH = str(tmp_db)  # type: ignore[attr-defined]

    orig_db_path_ds = getattr(db_setup, "STOCK_DB_PATH", None)
    db_setup.STOCK_DB_PATH = str(tmp_db)  # type: ignore[attr-defined]

    yield str(tmp_db)

    globals_mod.STOCK_DB_PATH = orig_db_path  # type: ignore[attr-defined]
    if orig_db_path_ds is None:
        try:
            delattr(db_setup, "STOCK_DB_PATH")
        except AttributeError:
            pass
    else:
        db_setup.STOCK_DB_PATH = orig_db_path_ds  # type: ignore[attr-defined]


def test_offer_allotment_link_repair_primary_offer(tmp_db_path_fixture):
    db_setup = importlib.import_module("StockMan.stock_database_setup")

    ok, _ = db_setup.create_database(None)
    assert ok is True

    conn = sqlite3.connect(tmp_db_path_fixture)
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA foreign_keys = ON;")

        cur.execute(
            """
            INSERT INTO stocks (stk_code, isin, company_name, short_name)
            VALUES (?, ?, ?, ?)
            """,
            ("ABC", "IN0000000001", "ABC Ltd", "ABC"),
        )
        id_stk = cur.lastrowid

        cur.execute(
            """
            INSERT INTO primary_offers (
                id_stk, offer_type, offer_name, ann_dt, record_dt,
                open_dt, close_dt, allotment_dt, listing_dt, issue_price
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                id_stk,
                "IPO",
                "ABC IPO",
                "2025-04-01",
                "2025-04-05",
                "2025-04-10",
                "2025-04-12",
                "2025-04-20",
                "2025-04-25",
                20.0,
            ),
        )
        id_offer = cur.lastrowid

        cur.execute(
            """
            INSERT INTO contracts (
                cont_no, trd_dt, settle_no, settle_dt, no_of_trades
            ) VALUES (?, ?, ?, ?, ?)
            """,
            ("IPO1", "2025-04-20", 1111, "2025-04-20", 1),
        )

        cur.execute(
            """
            INSERT INTO transactions (
                id_stk, cont_no, trd_dt, company_name, trade_type_trd,
                exchange, qty_trd, wap_unit_trd, brok_unit_trd,
                price_lot_trd, brok_lot_trd, etc_trd, sebi_trd,
                sell_chrg_trd, gst_trd, stamp_trd, stt_trd, igst_trd,
                net_amt_trd, note_trd
            ) VALUES (?, ?, ?, ?, 'BUY', 'NSE', ?, ?, 0.0, ?, 0.0, 0.0,
                      0.0, 0.0, 0.0, 0.0, 0.0, 0.0, ?, ?)
            """,
            (
                id_stk,
                "IPO1",
                "2025-04-20",
                "ABC Ltd",
                5,
                20.0,
                100.0,
                100.0,
                "Allotment from offer",
            ),
        )
        id_trd = cur.lastrowid

        cur.execute(
            """
            INSERT INTO computed_bank (
                cont_no, comp_bt_dt, comp_bt_type, comp_bt_amt,
                comp_bt_amt_applicable, comp_bt_desc
            ) VALUES (?, ?, 'DEBIT', ?, ?, ?)
            """,
            (
                "IPO1",
                "2025-04-20",
                100.0,
                100.0,
                "IPO allotment debit",
            ),
        )
        id_comp_bt = cur.lastrowid

        cur.execute(
            """
            INSERT INTO offer_allotments (
                id_stk, id_offer, record_qty, entitlement_qty,
                applied_qty, allotted_qty, allotment_dt, allotted_amt,
                status, cont_no
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                id_stk,
                id_offer,
                0,
                0,
                5,
                5,
                "2025-04-20",
                100.0,
                "ALLOTTED",
                "IPO1",
            ),
        )
        id_allot = cur.lastrowid
        conn.commit()

        repairs = db_setup.repair_existing_links(tmp_db_path_fixture)
        unresolved = db_setup.verify_existing_links(tmp_db_path_fixture)

        assert repairs["offer_allotments.tx_id"] >= 1
        assert repairs["offer_allotments.id_comp_bt"] >= 1
        assert unresolved["offer_allotments.tx_id"] == 0
        assert unresolved["offer_allotments.id_comp_bt"] == 0

        cur.execute(
            "SELECT tx_id, id_comp_bt FROM offer_allotments WHERE id_allot = ?",
            (id_allot,),
        )
        tx_id, linked_comp_bt = cur.fetchone()
        assert tx_id == id_trd
        assert linked_comp_bt == id_comp_bt
    finally:
        conn.close()


def test_dividend_triggers_reject_invalid_ex_record_dates(tmp_db_path_fixture):
    db_setup = importlib.import_module("StockMan.stock_database_setup")

    ok, _ = db_setup.create_database(None)
    assert ok is True

    conn = sqlite3.connect(tmp_db_path_fixture)
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA foreign_keys = ON;")

        cur.execute(
            """
            INSERT INTO stocks (stk_code, isin, company_name, short_name)
            VALUES (?, ?, ?, ?)
            """,
            ("DIV", "IN0000000002", "Dividend Ltd", "DIV"),
        )
        id_stk = cur.lastrowid
        conn.commit()

        with pytest.raises(
            sqlite3.IntegrityError,
            match="ex_dt cannot be after record_dt",
        ):
            cur.execute(
                """
                INSERT INTO dividends (
                    id_stk, ex_dt, record_dt, credit_dt, div_type,
                    div_percent, entitled_qty, per_share_amt, tds_amt
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    id_stk,
                    "2025-05-02",
                    "2025-05-01",
                    "2025-05-10",
                    "FINAL",
                    10.0,
                    100,
                    2.0,
                    0.0,
                ),
            )

        cur.execute(
            """
            INSERT INTO dividends (
                id_stk, ex_dt, record_dt, credit_dt, div_type,
                div_percent, entitled_qty, per_share_amt, tds_amt
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                id_stk,
                "2025-05-01",
                "2025-05-01",
                "2025-05-10",
                "FINAL",
                10.0,
                100,
                2.0,
                0.0,
            ),
        )
        id_div = cur.lastrowid
        conn.commit()

        with pytest.raises(
            sqlite3.IntegrityError,
            match=r"ex_dt cannot be after record_dt \(update\)",
        ):
            cur.execute(
                "UPDATE dividends SET ex_dt = ?, record_dt = ? WHERE id_div = ?",
                ("2025-05-03", "2025-05-01", id_div),
            )
        conn.rollback()

        cur.execute(
            "SELECT ex_dt, record_dt FROM dividends WHERE id_div = ?",
            (id_div,),
        )
        assert cur.fetchone() == ("2025-05-01", "2025-05-01")
    finally:
        conn.close()
