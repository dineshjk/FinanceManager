# -*- coding: utf-8 -*-
# tests/test_advice_tracker.py

"""
Unit tests for StockMan AI Advice Tracking & Excel Export logic.
"""

import os
import sqlite3
import tempfile
from unittest.mock import patch
import pytest
import openpyxl

from StockMan import advice_tracker, drive_sync, stock_database_setup


@pytest.fixture
def temp_db():
    """Provides a clean temporary SQLite database with advice_log table."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_path = tmp.name
    tmp.close()

    advice_tracker.ensure_advice_log_table(db_path=db_path)
    yield db_path

    try:
        if os.path.exists(db_path):
            os.remove(db_path)
    except Exception:
        pass


def test_schema_creates_advice_log_table(temp_db):
    """Verify advice_log table is created with correct columns."""
    conn = sqlite3.connect(temp_db)
    try:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(advice_log)")
        cols = {row[1]: row[2] for row in cursor.fetchall()}
    finally:
        conn.close()

    assert "id_advice" in cols
    assert "advice_date" in cols
    assert "advice_text" in cols
    assert "status" in cols
    assert "execution_date" in cols
    assert "notes" in cols


def test_add_and_get_advice(temp_db):
    """Verify adding advice and retrieving from SQLite."""
    adv_id = advice_tracker.add_advice(
        advice_date="2026-10-27",
        advice_text="Buy 30 HDFCBANK",
        status="Fully Followed",
        execution_date="2026-10-27",
        notes="Allotted at CMP ₹1,720",
        db_path=temp_db,
    )
    assert adv_id > 0

    record = advice_tracker.get_advice_by_id(adv_id, db_path=temp_db)
    assert record is not None
    assert record["advice_date"] == "2026-10-27"
    assert record["advice_text"] == "Buy 30 HDFCBANK"
    assert record["status"] == "Fully Followed"
    assert record["execution_date"] == "2026-10-27"
    assert record["notes"] == "Allotted at CMP ₹1,720"


def test_update_advice_and_quick_status(temp_db):
    """Verify updating advice fields and quick status change."""
    adv_id = advice_tracker.add_advice(
        advice_date="2026-10-25",
        advice_text="Trim 50% IOC",
        status="Not Followed",
        execution_date=None,
        notes="",
        db_path=temp_db,
    )

    # 1. Quick status mark to Partially Followed
    ok = advice_tracker.update_advice_status(
        adv_id,
        status="Partially Followed",
        execution_date="2026-10-26",
        db_path=temp_db,
    )
    assert ok is True

    record = advice_tracker.get_advice_by_id(adv_id, db_path=temp_db)
    assert record["status"] == "Partially Followed"
    assert record["execution_date"] == "2026-10-26"

    # 2. Full update
    ok2 = advice_tracker.update_advice(
        id_advice=adv_id,
        advice_date="2026-10-25",
        advice_text="Trim 50% IOC (Sold 25 shares)",
        status="Fully Followed",
        execution_date="2026-10-27",
        notes="Order ID: 12345",
        db_path=temp_db,
    )
    assert ok2 is True

    record2 = advice_tracker.get_advice_by_id(adv_id, db_path=temp_db)
    assert record2["status"] == "Fully Followed"
    assert record2["execution_date"] == "2026-10-27"
    assert "Sold 25 shares" in record2["advice_text"]


def test_delete_advice(temp_db):
    """Verify deleting advice record."""
    adv_id = advice_tracker.add_advice(
        advice_date="2026-10-20",
        advice_text="Add 10 INFY",
        status="Not Followed",
        db_path=temp_db,
    )
    assert advice_tracker.get_advice_by_id(adv_id, db_path=temp_db) is not None

    deleted = advice_tracker.delete_advice(adv_id, db_path=temp_db)
    assert deleted is True
    assert advice_tracker.get_advice_by_id(adv_id, db_path=temp_db) is None


def test_validation_constraints(temp_db):
    """Verify validation errors on malformed dates and invalid status."""
    # Invalid advice date
    with pytest.raises(ValueError, match="Date of Advice must be in YYYY-MM-DD"):
        advice_tracker.add_advice(
            advice_date="invalid-date",
            advice_text="Buy 10 TCS",
            db_path=temp_db,
        )

    # Empty advice text
    with pytest.raises(ValueError, match="Advice Given cannot be empty"):
        advice_tracker.add_advice(
            advice_date="2026-10-28",
            advice_text="",
            db_path=temp_db,
        )

    # Invalid status
    with pytest.raises(ValueError, match="Status must be one of"):
        advice_tracker.add_advice(
            advice_date="2026-10-28",
            advice_text="Buy 10 TCS",
            status="Unknown Status",
            db_path=temp_db,
        )

    # Invalid execution date
    with pytest.raises(ValueError, match="Execution Date must be in YYYY-MM-DD"):
        advice_tracker.add_advice(
            advice_date="2026-10-28",
            advice_text="Buy 10 TCS",
            status="Fully Followed",
            execution_date="2026-13-45",
            db_path=temp_db,
        )


def test_filtering_and_search(temp_db):
    """Verify get_all_advices status filter and search query."""
    advice_tracker.add_advice("2026-10-21", "Buy 30 HDFCBANK", "Fully Followed", "2026-10-21", db_path=temp_db)
    advice_tracker.add_advice("2026-10-22", "Add 10 INFY", "Partially Followed", "2026-10-22", db_path=temp_db)
    advice_tracker.add_advice("2026-10-23", "Trim 50% IOC", "Not Followed", None, db_path=temp_db)

    # Status filter
    fully_list = advice_tracker.get_all_advices(db_path=temp_db, status_filter="Fully Followed")
    assert len(fully_list) == 1
    assert fully_list[0]["advice_text"] == "Buy 30 HDFCBANK"

    not_list = advice_tracker.get_all_advices(db_path=temp_db, status_filter="Not Followed")
    assert len(not_list) == 1
    assert not_list[0]["advice_text"] == "Trim 50% IOC"

    # Search query
    search_infy = advice_tracker.get_all_advices(db_path=temp_db, search_query="INFY")
    assert len(search_infy) == 1
    assert search_infy[0]["advice_text"] == "Add 10 INFY"


def test_parse_advice_from_pick_of_the_day():
    """Verify extraction of date, action, and winner from Pick of the Day markdown."""
    report_sample = """# 🏆 Daily Pick of the Day — Universe & Portfolio Intelligence Report

## Market Snapshot & Sector Balance

**Date:** 2026-10-25 **Market Context:** Nifty 50 consolidated.

## Pick of the Day: Winner Deep-Dive

**Winner:** HDFC Bank Limited (HDFC) **Score:** 92/100 **Thesis:** Asset quality resilient.
- Action: BUY 30 shares of HDFC Bank at CMP (~₹52,000 allocation). Hold remaining ₹48,000 for dips.
"""
    parsed = advice_tracker.parse_advice_from_pick_of_the_day(report_sample)
    assert parsed["advice_date"] == "2026-10-25"
    assert "BUY 30 shares of HDFC Bank" in parsed["advice_text"]
    assert "HDFC Bank Limited (HDFC)" in parsed["winner"]


def test_excel_export_creates_advice_log_sheet(temp_db):
    """
    Verify update_portfolio_excel appends the dedicated 'Advice_Log' worksheet
    with the exact columns: Date of Advice, The Advice Given, Execution Status, Execution Date, Notes.
    """
    # 1. Populate advice_log table
    advice_tracker.add_advice(
        advice_date="2026-10-27",
        advice_text="Buy 30 HDFCBANK",
        status="Fully Followed",
        execution_date="2026-10-27",
        notes="Executed via Zerodha",
        db_path=temp_db,
    )
    advice_tracker.add_advice(
        advice_date="2026-10-25",
        advice_text="Trim 50% IOC",
        status="Not Followed",
        execution_date=None,
        notes="Waiting for rally",
        db_path=temp_db,
    )

    # 2. Create stocks table in temp_db to verify portfolio sheet co-existence
    conn = sqlite3.connect(temp_db)
    try:
        conn.execute("""
            CREATE TABLE stocks (
                id_stk INTEGER PRIMARY KEY,
                stk_code TEXT,
                isin TEXT,
                company_name TEXT,
                curr_avg_price REAL,
                buy_qty INTEGER,
                sell_qty INTEGER
            )
        """)
        conn.execute("""
            INSERT INTO stocks VALUES
            (1, 'HDFCBANK', 'INE040A01034', 'HDFC Bank Ltd', 1720.0, 30, 0)
        """)
        conn.commit()
    finally:
        conn.close()

    # 3. Export to Excel
    tmp_xlsx = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    xlsx_path = tmp_xlsx.name
    tmp_xlsx.close()

    try:
        drive_sync.update_portfolio_excel(
            excel_path=xlsx_path,
            current_appetite=2000000.0,
            cash_available=100000.0,
            db_path=temp_db,
        )

        wb = openpyxl.load_workbook(xlsx_path, data_only=True)
        assert "Portfolio" in wb.sheetnames
        assert "Advice_Log" in wb.sheetnames

        # Verify Advice_Log Sheet Headers
        ws_adv = wb["Advice_Log"]
        expected_headers = [
            "Date of Advice",
            "The Advice Given",
            "Execution Status",
            "Execution Date",
            "Notes",
        ]
        actual_headers = [ws_adv.cell(row=1, column=c).value for c in range(1, 6)]
        assert actual_headers == expected_headers

        # Verify Row 2 (2026-10-27, Buy 30 HDFCBANK, Fully Followed, 2026-10-27)
        assert ws_adv.cell(row=2, column=1).value == "2026-10-27"
        assert ws_adv.cell(row=2, column=2).value == "Buy 30 HDFCBANK"
        assert ws_adv.cell(row=2, column=3).value == "Fully Followed"
        assert ws_adv.cell(row=2, column=4).value == "2026-10-27"
        assert ws_adv.cell(row=2, column=5).value == "Executed via Zerodha"

        # Verify Row 3 (2026-10-25, Trim 50% IOC, Not Followed)
        assert ws_adv.cell(row=3, column=1).value == "2026-10-25"
        assert ws_adv.cell(row=3, column=2).value == "Trim 50% IOC"
        assert ws_adv.cell(row=3, column=3).value == "Not Followed"
        assert ws_adv.cell(row=3, column=4).value in (None, "")

        wb.close()
    finally:
        if os.path.exists(xlsx_path):
            os.remove(xlsx_path)


def test_find_matching_advice_for_trade(temp_db):
    """
    Verify auto-matching logic correctly matches stock ticker/synonyms,
    trade direction, and calculates appropriate status based on quantity.
    """
    # Set up stocks table with HDFC Bank
    conn = sqlite3.connect(temp_db)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS stocks (
                id_stk INTEGER PRIMARY KEY,
                stk_code TEXT,
                short_name TEXT,
                company_name TEXT,
                ticker TEXT,
                curr_avg_price REAL,
                buy_qty INTEGER,
                sell_qty INTEGER
            )
        """)
        conn.execute("""
            INSERT INTO stocks (id_stk, stk_code, short_name, company_name, ticker)
            VALUES (101, 'HDFC', 'HDFC Bank', 'HDFC Bank Limited', 'HDFCBANK.NS')
        """)
        conn.commit()
    finally:
        conn.close()

    # Add open advice
    adv_id = advice_tracker.add_advice(
        advice_date="2026-10-27",
        advice_text="Buy 30 HDFCBANK",
        status="Not Followed",
        db_path=temp_db,
    )

    conn = sqlite3.connect(temp_db)
    try:
        # Case 1: Partial match (buying 15 shares of 30 recommended)
        match_partial = advice_tracker.find_matching_advice_for_trade(
            conn,
            {
                "id_stk": 101,
                "company_name": "HDFC Bank Limited",
                "trade_type_trd": "BUY",
                "qty_trd": 15,
                "trd_dt": "2026-10-28",
            },
        )
        assert match_partial is not None
        assert match_partial["id_advice"] == adv_id
        assert match_partial["new_status"] == "Partially Followed"
        assert match_partial["execution_date"] == "2026-10-28"

        # Case 2: Full match (buying 30 or more shares)
        match_full = advice_tracker.find_matching_advice_for_trade(
            conn,
            {
                "id_stk": 101,
                "company_name": "HDFC Bank Limited",
                "trade_type_trd": "BUY",
                "qty_trd": 30,
                "trd_dt": "2026-10-28",
            },
        )
        assert match_full is not None
        assert match_full["new_status"] == "Fully Followed"

        # Case 3: Direction mismatch (selling instead of buying)
        match_sell = advice_tracker.find_matching_advice_for_trade(
            conn,
            {
                "id_stk": 101,
                "company_name": "HDFC Bank Limited",
                "trade_type_trd": "SELL",
                "qty_trd": 30,
                "trd_dt": "2026-10-28",
            },
        )
        assert match_sell is None
    finally:
        conn.close()


def test_auto_sync_trade_with_advice(temp_db):
    """
    Verify auto_sync_trade_with_advice updates the database record in advice_log
    and updates StockMan_Portfolio.xlsx.
    """
    conn = sqlite3.connect(temp_db)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS stocks (
                id_stk INTEGER PRIMARY KEY,
                stk_code TEXT,
                short_name TEXT,
                company_name TEXT,
                ticker TEXT,
                curr_avg_price REAL,
                buy_qty INTEGER,
                sell_qty INTEGER
            )
        """)
        conn.execute("""
            INSERT INTO stocks (id_stk, stk_code, short_name, company_name, ticker)
            VALUES (201, 'TCS', 'TCS', 'Tata Consultancy Services Ltd', 'TCS.NS')
        """)
        conn.commit()
    finally:
        conn.close()

    adv_id = advice_tracker.add_advice(
        advice_date="2026-10-26",
        advice_text="Buy 10 TCS at CMP",
        status="Not Followed",
        db_path=temp_db,
    )

    trade_info = {
        "id_stk": 201,
        "company_name": "Tata Consultancy Services Ltd",
        "trade_type_trd": "BUY",
        "qty_trd": 10,
        "trd_dt": "2026-10-28",
    }

    res = advice_tracker.auto_sync_trade_with_advice(
        trade_info, db_path=temp_db, trigger_drive_upload=False
    )
    assert res is not None
    assert res["matched"] is True
    assert res["new_status"] == "Fully Followed"
    assert res["execution_date"] == "2026-10-28"

    # Check database status
    record = advice_tracker.get_advice_by_id(adv_id, db_path=temp_db)
    assert record["status"] == "Fully Followed"
    assert record["execution_date"] == "2026-10-28"
    assert "Auto-matched with BUY 10" in record["notes"]


def test_auto_sync_trade_with_advice_adjusts_cash(temp_db):
    """
    Verify auto_sync_trade_with_advice adjusts cash available in Excel
    when net_amt_trd is present.
    """
    import tempfile
    import openpyxl
    from StockMan import drive_sync

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp_xlsx:
        xlsx_path = tmp_xlsx.name

    try:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Portfolio"
        ws.cell(1, 1, "Current Appetite")
        ws.cell(1, 2, 1000000.0)
        ws.cell(2, 1, "Cash Available for Investment")
        ws.cell(2, 2, 50000.0)
        wb.save(xlsx_path)
        wb.close()

        trade_info = {
            "id_stk": 201,
            "company_name": "Tata Consultancy Services Ltd",
            "trade_type_trd": "BUY",
            "qty_trd": 10,
            "trd_dt": "2026-10-28",
            "net_amt_trd": 15000.0,
        }
        res = advice_tracker.auto_sync_trade_with_advice(
            trade_info,
            db_path=temp_db,
            trigger_drive_upload=False,
            excel_path=xlsx_path,
        )
        assert res is not None
        assert res.get("new_cash") == 35000.0

        # Verify persisted to Excel
        app, cash = drive_sync.read_investment_parameters(xlsx_path)
        assert cash == 35000.0
        assert app == 1000000.0
    finally:
        if os.path.exists(xlsx_path):
            os.remove(xlsx_path)


def test_auto_sync_trades_batch_with_advice(temp_db):
    """
    Verify auto_sync_trades_batch_with_advice processes multiple trades
    (e.g., from a Zerodha contract note) and updates advice_log.
    """
    conn = sqlite3.connect(temp_db)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS stocks (
                id_stk INTEGER PRIMARY KEY,
                stk_code TEXT,
                short_name TEXT,
                company_name TEXT,
                ticker TEXT,
                curr_avg_price REAL,
                buy_qty INTEGER,
                sell_qty INTEGER
            )
        """)
        conn.execute("""
            INSERT INTO stocks (id_stk, stk_code, short_name, company_name, ticker)
            VALUES (301, 'INFY', 'Infosys', 'Infosys Limited', 'INFY.NS'),
                   (302, 'ITC', 'ITC', 'ITC Limited', 'ITC.NS')
        """)
        conn.commit()
    finally:
        conn.close()

    adv_infy = advice_tracker.add_advice(
        "2026-10-25", "Buy 25 INFY", "Not Followed", db_path=temp_db
    )
    adv_itc = advice_tracker.add_advice(
        "2026-10-25", "Buy 100 ITC", "Not Followed", db_path=temp_db
    )

    batch_trades = [
        {
            "id_stk": 301,
            "company_name": "Infosys Limited",
            "trade_type_trd": "BUY",
            "qty_trd": 25,
            "trd_dt": "2026-10-28",
        },
        {
            "id_stk": 302,
            "company_name": "ITC Limited",
            "trade_type_trd": "BUY",
            "qty_trd": 50,  # Partial
            "trd_dt": "2026-10-28",
        },
    ]

    results = advice_tracker.auto_sync_trades_batch_with_advice(
        batch_trades, db_path=temp_db, trigger_drive_upload=False
    )
    assert len(results) == 2
    assert results[0]["matched"] is True
    assert results[0]["new_status"] == "Fully Followed"
    assert results[1]["matched"] is True
    assert results[1]["new_status"] == "Partially Followed"

    rec_infy = advice_tracker.get_advice_by_id(adv_infy, db_path=temp_db)
    assert rec_infy["status"] == "Fully Followed"
    assert rec_infy["execution_date"] == "2026-10-28"

    rec_itc = advice_tracker.get_advice_by_id(adv_itc, db_path=temp_db)
    assert rec_itc["status"] == "Partially Followed"
    assert rec_itc["execution_date"] == "2026-10-28"


def test_parse_rebalancing_strategy_and_action():
    """Verify extraction of rebalancing strategy and action from 2026-11-03 style report."""
    report_text = """# 🏆 Daily Pick of the Day — Universe & Portfolio Intelligence Report

## Market Snapshot & Sector Balance

**Date:** 2026-11-03

| Sector | Invested Value (INR) | Weight (%) | Status | Rebalancing Advice |
| :---- | :---- | :---- | :---- | :---- |
| IT & Tech | ₹105,195.69 | 9.5% | UNDER-INVESTED | Priority sector for the available ₹50,000 cash. |

*Rebalancing Strategy:* Funnel the ₹50,000 available cash into the IT sector (specifically HCLTECH) to balance the high Beta of the Defense and Metals allocations.

## Pick of the Day: Winner Deep-Dive

**Winner:** HCL Technologies Limited (HCLTECH) **Score:** 92/100 **Thesis:** Diversifies IT basket.
- Action: BUY 34 shares of HCLTECH at CMP (~₹1,430). Approximate allocation: ₹48,620. Keep the remaining ₹1,380 as a cash buffer.
"""
    parsed = advice_tracker.parse_advice_from_pick_of_the_day(report_text)
    assert parsed["advice_date"] == "2026-11-03"
    assert "HCL Technologies Limited (HCLTECH)" in parsed["winner"]
    assert "BUY 34 shares of HCLTECH" in parsed["advice_text"]
    assert "Rebalancing Strategy" in parsed["advice_text"]
    assert "Funnel the ₹50,000 available cash into the IT sector (specifically HCLTECH)" in parsed["advice_text"]
    assert "Funnel the ₹50,000 available cash into the IT sector (specifically HCLTECH)" in parsed["notes"]
    assert parsed["ticker"] == "HCLTECH"


def test_parse_advice_log_export_table():
    """Verify parsing from markdown ADVICE_LOG_EXPORT table."""
    report_text = """# 🏆 Daily Pick of the Day
### ADVICE_LOG_EXPORT

| Date | Ticker | Action | Quantity | Target_Price | Status |
| :---- | :---- | :---- | :---- | :---- | :---- |
| 2026-11-03 | HCLTECH | BUY | 34 | CMP (~1,430.40) | Pending |
"""
    parsed = advice_tracker.parse_advice_from_pick_of_the_day(report_text)
    assert parsed["advice_date"] == "2026-11-03"
    assert parsed["ticker"] == "HCLTECH"
    assert "BUY 34 shares of HCLTECH" in parsed["advice_text"]


def test_auto_update_advice_from_pick_of_the_day(temp_db):
    """Verify auto_update_advice_from_pick_of_the_day inserts advice and updates excel."""
    report_sample = """# 🏆 Daily Pick of the Day
**Date:** 2026-11-03
*Rebalancing Strategy:* Funnel the ₹50,000 available cash into the IT sector (specifically HCLTECH) to balance the high Beta of the Defense and Metals allocations.
**Winner:** HCL Technologies Limited (HCLTECH)
- Action: BUY 34 shares of HCLTECH at CMP (~₹1,430). Approximate allocation: ₹48,620.
"""
    tmp_xlsx = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    xlsx_path = tmp_xlsx.name
    tmp_xlsx.close()

    try:
        # Create minimal stocks table
        conn = sqlite3.connect(temp_db)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS stocks (
                    id_stk INTEGER PRIMARY KEY,
                    stk_code TEXT,
                    isin TEXT,
                    company_name TEXT,
                    curr_avg_price REAL,
                    buy_qty INTEGER,
                    sell_qty INTEGER
                )
            """)
            conn.commit()
        finally:
            conn.close()

        res = advice_tracker.auto_update_advice_from_pick_of_the_day(
            report_text_or_path=report_sample,
            db_path=temp_db,
            excel_path=xlsx_path,
            trigger_drive_upload=False,
            update_excel=True,
        )
        assert res is not None
        assert res["is_new"] is True
        assert res["advice_date"] == "2026-11-03"

        # Check DB
        rows = advice_tracker.get_all_advices(db_path=temp_db)
        assert len(rows) == 1
        assert "BUY 34 shares of HCLTECH" in rows[0]["advice_text"]
        assert "Rebalancing Strategy" in rows[0]["advice_text"]
        assert "Funnel the ₹50,000 available cash" in rows[0]["notes"]

        # Check Excel
        wb = openpyxl.load_workbook(xlsx_path, data_only=True)
        assert "Advice_Log" in wb.sheetnames
        ws_adv = wb["Advice_Log"]
        assert ws_adv.cell(row=2, column=1).value == "2026-11-03"
        assert "BUY 34 shares of HCLTECH" in ws_adv.cell(row=2, column=2).value
        assert "Rebalancing Strategy" in ws_adv.cell(row=2, column=2).value
        assert "Funnel the ₹50,000 available cash" in ws_adv.cell(row=2, column=5).value
        wb.close()

        # Second call with same report should not duplicate
        res2 = advice_tracker.auto_update_advice_from_pick_of_the_day(
            report_text_or_path=report_sample,
            db_path=temp_db,
            excel_path=xlsx_path,
            trigger_drive_upload=False,
            update_excel=False,
        )
        assert res2["is_new"] is False
        assert len(advice_tracker.get_all_advices(db_path=temp_db)) == 1

    finally:
        if os.path.exists(xlsx_path):
            os.remove(xlsx_path)


def test_hcltech_rebalancing_trade_automatch(temp_db):
    """Verify that a BUY trade for HCLTECH auto-matches the rebalancing advice."""
    conn = sqlite3.connect(temp_db)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS stocks (
                id_stk INTEGER PRIMARY KEY,
                stk_code TEXT,
                short_name TEXT,
                company_name TEXT,
                ticker TEXT,
                curr_avg_price REAL,
                buy_qty INTEGER,
                sell_qty INTEGER
            )
        """)
        conn.execute("""
            INSERT INTO stocks (id_stk, stk_code, short_name, company_name, ticker)
            VALUES (20, 'HCLTECH', 'HCL Tech', 'HCL Technologies Limited', 'HCLTECH.NS')
        """)
        conn.commit()
    finally:
        conn.close()

    adv_text = (
        "BUY 34 shares of HCLTECH at CMP (~₹1,430). Approximate allocation: ₹48,620. "
        "— Rebalancing Strategy: Funnel the ₹50,000 available cash into the IT sector "
        "(specifically HCLTECH) to balance the high Beta of the Defense and Metals allocations."
    )
    adv_id = advice_tracker.add_advice(
        advice_date="2026-11-03",
        advice_text=adv_text,
        status="Not Followed",
        notes="Rebalancing Strategy: Funnel the ₹50,000 available cash into the IT sector (specifically HCLTECH)",
        db_path=temp_db,
    )

    trade_info = {
        "id_stk": 20,
        "company_name": "HCL Technologies Limited",
        "trade_type_trd": "BUY",
        "qty_trd": 34,
        "trd_dt": "2026-11-04",
    }

    conn = sqlite3.connect(temp_db)
    try:
        matched = advice_tracker.find_matching_advice_for_trade(conn, trade_info)
        assert matched is not None
        assert matched["id_advice"] == adv_id
        assert matched["target_qty"] == 34.0
        assert matched["new_status"] == "Fully Followed"
    finally:
        conn.close()

