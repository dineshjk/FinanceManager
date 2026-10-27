# -*- coding: utf-8 -*-
# tests/test_transfer_data.py

"""
Comprehensive unit and integration tests for StockMan transfer_data feature:
- FIFO calculation excluding Zerodha purchases
- Inclusion of corporate actions (bonuses, splits, demergers, IPO/rights)
- Scrip summary rows (weighted average buy price)
- Output Excel export and openpyxl formatting
- UI menu integration
"""

import os
import sqlite3
import tempfile
import pytest
import pandas as pd
import openpyxl

from StockMan.transfer_data import (
    calculate_transfer_data,
    export_transfer_data_to_excel,
    generate_and_export_transfer_data,
    DEFAULT_EXPORT_PATH,
    FlexibleDataFrame,
)
from StockMan.stocks import show_stock_portfolio_menu


@pytest.fixture
def test_db():
    """Create a temporary SQLite database with a rich set of transactions."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    conn = sqlite3.connect(path)
    c = conn.cursor()

    # Create tables
    c.execute(
        """
        CREATE TABLE stocks (
            id_stk INTEGER PRIMARY KEY AUTOINCREMENT,
            stk_code TEXT NOT NULL,
            isin TEXT NOT NULL,
            company_name TEXT NOT NULL
        );
        """
    )

    c.execute(
        """
        CREATE TABLE transactions (
            id_trd INTEGER PRIMARY KEY AUTOINCREMENT,
            id_stk INTEGER NOT NULL,
            cont_no TEXT NOT NULL,
            trd_dt TEXT NOT NULL,
            company_name TEXT NOT NULL,
            trade_type_trd TEXT NOT NULL,
            qty_trd INTEGER DEFAULT 0,
            net_amt_trd REAL DEFAULT 0.0
        );
        """
    )

    # Stock 1: Stock Alpha (ICICI trades: 2 buys, 1 partial sell)
    c.execute(
        "INSERT INTO stocks (id_stk, stk_code, isin, company_name) "
        "VALUES (1, 'ALPHA', 'INE001A01010', 'Alpha Ltd');"
    )
    # Lot 1: Buy 100 @ 100 net = 10,000
    c.execute(
        "INSERT INTO transactions (id_stk, cont_no, trd_dt, company_name, trade_type_trd, qty_trd, net_amt_trd) "
        "VALUES (1, 'ISEC/001', '2024-01-10', 'Alpha Ltd', 'BUY', 100, 10000.0);"
    )
    # Lot 2: Buy 50 @ 200 net = 10,000
    c.execute(
        "INSERT INTO transactions (id_stk, cont_no, trd_dt, company_name, trade_type_trd, qty_trd, net_amt_trd) "
        "VALUES (1, 'ISEC/002', '2024-02-15', 'Alpha Ltd', 'BUY', 50, 10000.0);"
    )
    # Sell 60 shares (should exhaust 60 from Lot 1, leaving 40 in Lot 1 and 50 in Lot 2)
    c.execute(
        "INSERT INTO transactions (id_stk, cont_no, trd_dt, company_name, trade_type_trd, qty_trd, net_amt_trd) "
        "VALUES (1, 'ISEC/003', '2024-03-20', 'Alpha Ltd', 'SELL', 60, 9000.0);"
    )

    # Stock 2: Stock Beta (Completely sold out - should not appear in output)
    c.execute(
        "INSERT INTO stocks (id_stk, stk_code, isin, company_name) "
        "VALUES (2, 'BETA', 'INE002B01010', 'Beta Ltd');"
    )
    c.execute(
        "INSERT INTO transactions (id_stk, cont_no, trd_dt, company_name, trade_type_trd, qty_trd, net_amt_trd) "
        "VALUES (2, 'ISEC/004', '2024-01-05', 'Beta Ltd', 'BUY', 20, 2000.0);"
    )
    c.execute(
        "INSERT INTO transactions (id_stk, cont_no, trd_dt, company_name, trade_type_trd, qty_trd, net_amt_trd) "
        "VALUES (2, 'ISEC/005', '2024-02-05', 'Beta Ltd', 'SELL', 20, 2500.0);"
    )

    # Stock 3: Stock Gamma (Bought in ICICI + Corporate Actions + Zerodha Buy)
    c.execute(
        "INSERT INTO stocks (id_stk, stk_code, isin, company_name) "
        "VALUES (3, 'GAMMA', 'INE003G01010', 'Gamma Ltd');"
    )
    # ICICI Buy: 10 @ 500 = 5000
    c.execute(
        "INSERT INTO transactions (id_stk, cont_no, trd_dt, company_name, trade_type_trd, qty_trd, net_amt_trd) "
        "VALUES (3, 'ISEC/006', '2024-04-01', 'Gamma Ltd', 'BUY', 10, 5000.0);"
    )
    # Bonus Issue: 10 @ 0.0 = 0.0
    c.execute(
        "INSERT INTO transactions (id_stk, cont_no, trd_dt, company_name, trade_type_trd, qty_trd, net_amt_trd) "
        "VALUES (3, 'BONUS_1', '2024-06-01', 'Gamma Ltd', 'BUY', 10, 0.0);"
    )
    # Demerger Allotment: 5 @ 100 = 500
    c.execute(
        "INSERT INTO transactions (id_stk, cont_no, trd_dt, company_name, trade_type_trd, qty_trd, net_amt_trd) "
        "VALUES (3, 'DEM_ALT_1_0', '2024-08-01', 'Gamma Ltd', 'BUY', 5, 500.0);"
    )
    # Primary Offer Allotment: 10 @ 300 = 3000
    c.execute(
        "INSERT INTO transactions (id_stk, cont_no, trd_dt, company_name, trade_type_trd, qty_trd, net_amt_trd) "
        "VALUES (3, 'PO_1', '2024-09-01', 'Gamma Ltd', 'BUY', 10, 3000.0);"
    )
    # Zerodha Buy: 50 @ 600 = 30000 (MUST BE IGNORED)
    c.execute(
        "INSERT INTO transactions (id_stk, cont_no, trd_dt, company_name, trade_type_trd, qty_trd, net_amt_trd) "
        "VALUES (3, 'CNT-26/27-12345678', '2026-09-15', 'Gamma Ltd', 'BUY', 50, 30000.0);"
    )

    conn.commit()
    conn.close()

    yield path

    if os.path.exists(path):
        os.remove(path)


def test_fifo_calculation_and_filtering(test_db):
    """Test that FIFO deduction accurately computes remaining lots and average buy prices."""
    df = calculate_transfer_data(db_path=test_db)

    # Beta Ltd was completely sold out, should NOT be in df
    scrip_names = set(df["Scrip Name"])
    assert "Beta Ltd" not in scrip_names
    assert "Alpha Ltd" in scrip_names
    assert "Gamma Ltd" in scrip_names

    # Check Alpha Ltd lots:
    # Orig: Buy 100 @ 100, Buy 50 @ 200. Sold 60.
    # Rem: Lot 1 has 40 @ 100. Lot 2 has 50 @ 200.
    # Total Qty = 90. Total cost = 40*100 + 50*200 = 14000.
    # Overall Avg Price = 14000 / 90 = 155.5556
    alpha_df = df[df["Scrip Name"] == "Alpha Ltd"]
    assert len(alpha_df) == 3  # 2 lots + 1 summary row

    lot1 = alpha_df.iloc[0]
    assert lot1["Buy Date"] == "2024-01-10"
    assert lot1["Buy Qty"] == 40
    assert abs(lot1["Buy Price"] - 100.0) < 1e-4

    lot2 = alpha_df.iloc[1]
    assert lot2["Buy Date"] == "2024-02-15"
    assert lot2["Buy Qty"] == 50
    assert abs(lot2["Buy Price"] - 200.0) < 1e-4

    summary_alpha = alpha_df.iloc[2]
    assert summary_alpha["Buy Date"] == "Average"
    assert summary_alpha["Buy Qty"] == 90
    assert abs(summary_alpha["Buy Price"] - (14000.0 / 90.0)) < 1e-4


def test_zerodha_exclusion_and_corporate_actions(test_db):
    """Verify that Zerodha purchases are strictly excluded while corporate actions are included."""
    df = calculate_transfer_data(db_path=test_db)
    gamma_df = df[df["Scrip Name"] == "Gamma Ltd"]

    # Gamma had:
    # - Buy 10 @ 500 = 5000
    # - Bonus 10 @ 0 = 0
    # - Demerger 5 @ 100 = 500
    # - PO 10 @ 300 = 3000
    # - Zerodha Buy 50 (MUST BE EXCLUDED)
    # Expected remaining ICICI lots = 4 lots + 1 summary row = 5 rows
    assert len(gamma_df) == 5

    # Check that Zerodha's 50 quantity is NOT in Gamma's total
    summary_gamma = gamma_df[gamma_df["Buy Date"] == "Average"].iloc[0]
    expected_total_qty = 10 + 10 + 5 + 10  # 35 shares
    assert summary_gamma["Buy Qty"] == expected_total_qty

    expected_total_cost = 5000.0 + 0.0 + 500.0 + 3000.0  # 8500.0
    expected_avg_price = round(expected_total_cost / expected_total_qty, 4)
    assert abs(summary_gamma["Buy Price"] - expected_avg_price) < 1e-4


def test_flexible_dataframe_aliases(test_db):
    """Verify FlexibleDataFrame allows case-insensitive and alias column indexing."""
    df = calculate_transfer_data(db_path=test_db)
    assert isinstance(df, FlexibleDataFrame)

    # Test aliases
    assert (df["company_name"] == df["Scrip Name"]).all()
    assert (df["buy_date"] == df["Buy Date"]).all()
    assert (df["buy_qty"] == df["Buy Qty"]).all()
    assert (df["buy_price"] == df["Buy Price"]).all()
    assert (df["symbol"] == df["Symbol"]).all()


def test_excel_export_and_formatting(test_db):
    """Verify export to Excel, sheet name, cell formats, and openpyxl styling."""
    df = calculate_transfer_data(db_path=test_db)

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        saved_path = export_transfer_data_to_excel(df, output_path=tmp_path)
        assert os.path.exists(saved_path)

        wb = openpyxl.load_workbook(saved_path)
        assert "Transfer Stocks" in wb.sheetnames
        ws = wb["Transfer Stocks"]

        # Header checks
        headers = [ws.cell(1, c).value for c in range(1, 6)]
        assert headers == ["Scrip Name", "Symbol", "Buy Date", "Buy Qty", "Buy Price"]
        assert ws.cell(1, 1).font.bold is True
        assert ws.cell(1, 1).fill.fill_type == "solid"

        # Check freeze panes
        assert ws.freeze_panes == "A2"

        # Check summary row styling:
        # Alpha summary is row 4 (row 1 is header, 2 & 3 are lots, 4 is summary)
        alpha_summary_cell = ws.cell(4, 3)
        assert alpha_summary_cell.value == "Average"
        assert ws.cell(4, 1).font.bold is True
        assert ws.cell(4, 1).fill.fill_type == "solid"

        # Read back with pandas to verify structure
        read_df = pd.read_excel(saved_path)
        assert len(read_df) == len(df)
        assert list(read_df.columns) == ["Scrip Name", "Symbol", "Buy Date", "Buy Qty", "Buy Price"]
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_permission_error_handling(test_db, monkeypatch):
    """Test graceful handling when Excel file is locked."""
    df = calculate_transfer_data(db_path=test_db)

    def mock_excel_writer(*args, **kwargs):
        raise PermissionError("Access is denied")

    monkeypatch.setattr(pd, "ExcelWriter", mock_excel_writer)

    with pytest.raises(PermissionError) as exc_info:
        export_transfer_data_to_excel(df, output_path="dummy.xlsx")

    assert "open in another program" in str(exc_info.value)


def test_live_database_transfer_export():
    """Integration test against the live mystocks.db to verify default export path."""
    df, target_path, stats = generate_and_export_transfer_data()

    assert os.path.exists(target_path)
    assert os.path.abspath(target_path) == os.path.abspath(DEFAULT_EXPORT_PATH)
    assert stats["num_scrips"] > 0
    assert stats["num_lots"] > 0
    assert stats["total_qty"] > 0

    # Read back and assert no Zerodha contracts leaked in
    read_df = pd.read_excel(target_path)
    assert len(read_df) == len(df)
    assert set(read_df.columns) == {"Scrip Name", "Symbol", "Buy Date", "Buy Qty", "Buy Price"}


def test_ui_menu_integration(monkeypatch):
    """Test that 'Transfer Data' button is properly registered in Stock Portfolio Menu."""
    from StockMan import stocks
    import tkinter as tk

    from unittest.mock import MagicMock
    captured_config = {}

    def mock_create_menu_window(config):
        captured_config.update(config)
        # Create a dummy window and dummy buttons
        dummy_win = MagicMock()
        dummy_buttons = [MagicMock() for _ in config.get("buttons", [])]
        return dummy_win, dummy_buttons

    monkeypatch.setattr(stocks, "create_menu_window", mock_create_menu_window)
    monkeypatch.setattr(stocks, "disable_parent", lambda p: 1)
    monkeypatch.setattr(stocks, "enable_parent", lambda mid: None)
    monkeypatch.setattr(stocks, "push_window", lambda w, p: None)

    dummy_parent = MagicMock()
    dummy_parent.wait_window = lambda w: None

    stocks.show_stock_portfolio_menu(dummy_parent)
    buttons = captured_config.get("buttons", [])
    button_texts = [b["text"] for b in buttons]
    assert "Transfer Data" in button_texts

    transfer_btn = next(b for b in buttons if b["text"] == "Transfer Data")
    assert transfer_btn["hotkey"] == "F"
    assert callable(transfer_btn["command"])

