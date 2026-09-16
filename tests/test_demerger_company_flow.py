# -*- coding: utf-8 -*-
# tests/test_demerger_company_flow.py

import tkinter as tk
from unittest.mock import patch
import pytest
from pathlib import Path
import sys

# Ensure project root importable
tests_dir = Path(__file__).resolve().parent
project_root = tests_dir.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from StockMan import demerger_entry, company_add
import Shared.globals as shared_globals
from StockMan import stock_database_setup as db_setup


@pytest.fixture(scope="module")
def tk_root():
    root = tk.Tk()
    root.withdraw()
    yield root
    try:
        root.destroy()
    except Exception:
        pass


@pytest.fixture
def clean_root(tk_root):
    # Cleanup any leftover children before/after test
    for child in tk_root.winfo_children():
        try:
            child.destroy()
        except Exception:
            pass
    yield tk_root
    for child in tk_root.winfo_children():
        try:
            child.destroy()
        except Exception:
            pass


@pytest.fixture
def test_db(tmp_path, monkeypatch):
    db_path = tmp_path / "demerger_test.db"
    db_setup.STOCK_DB_PATH = str(db_path)
    monkeypatch.setattr(shared_globals, "STOCK_DB_PATH", str(db_path))
    db_setup.create_database(None)
    return str(db_path)


def test_add_company_initial_name(test_db, clean_root):
    """Verify add_company initializes company_name_var with initial_company_name."""
    with patch.object(clean_root, "wait_window", return_value=None):
        with patch("StockMan.company_add.calculate_dialog_size", return_value=(600, 400)):
            with patch("StockMan.company_add.safe_close_modal"):
                company_add.add_company(clean_root, initial_company_name="Jio Financial")


def test_demerger_init_and_cancel(test_db, clean_root, monkeypatch):
    """Verify demerger window initializes cleanly with child row and close handler."""
    company_add.add_company_db(
        "RELIANCE", "INE002A01018", "Reliance Industries Ltd", "RELIANCE", "RELIANCE.NS", "Energy", 10.0, 0.05, 1, 0
    )

    with patch.object(clean_root, "wait_window", return_value=None), \
         patch("Shared.modal_utils.disable_parent", return_value="modal_1"), \
         patch("Shared.window_manager.push_window"), \
         patch("Shared.window_manager.safe_close_modal"), \
         patch("Shared.gui_utils.setup_footer_tooltip", return_value=tk.StringVar()):

        demerger_entry.add_demerger(clean_root)


def test_demerger_missing_child_company_invokes_add(test_db, clean_root, monkeypatch):
    """Test that missing child company during demerger execution prompts user and invokes add company."""
    company_add.add_company_db(
        "RELIANCE", "INE002A01018", "Reliance Industries Ltd", "RELIANCE", "RELIANCE.NS", "Energy", 10.0, 0.05, 1, 0
    )
    with shared_globals.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id_stk FROM stocks WHERE company_name = 'Reliance Industries Ltd'")
        id_parent = cursor.fetchone()[0]
        cursor.execute(
            """INSERT INTO contracts (cont_no, trd_dt, settle_no, settle_dt, no_of_trades)
               VALUES ('C1', '2026-01-01', 12345, '2026-01-01', 1)"""
        )
        cursor.execute(
            """INSERT INTO transactions (id_stk, cont_no, trd_dt, company_name, trade_type_trd, exchange, qty_trd, wap_unit_trd, price_lot_trd, net_amt_trd, net_amt_trd_applicable)
               VALUES (?, 'C1', '2026-01-01', 'Reliance Industries Ltd', 'BUY', 'NSE', 100, 2500.0, 250000.0, 250000.0, 250000.0)""",
            (id_parent,),
        )
        conn.commit()

    with patch.object(clean_root, "wait_window", return_value=None), \
         patch("Shared.modal_utils.disable_parent", return_value="modal_1"), \
         patch("Shared.window_manager.push_window"), \
         patch("Shared.window_manager.safe_close_modal"), \
         patch("Shared.gui_utils.setup_footer_tooltip", return_value=tk.StringVar()):

        demerger_entry.add_demerger(clean_root)

        dem_win = [c for c in clean_root.winfo_children() if isinstance(c, tk.Toplevel)][0]

        save_btn = None
        for w in dem_win.winfo_children():
            if isinstance(w, tk.Frame):
                for sub_w in w.winfo_children():
                    if isinstance(sub_w, tk.Button) and "Execute Demerger" in sub_w.cget("text"):
                        save_btn = sub_w

        assert save_btn is not None

        combos = []
        def find_combos(widget):
            for child in widget.winfo_children():
                if child.winfo_class() == "TCombobox":
                    combos.append(child)
                find_combos(child)

        find_combos(dem_win)
        parent_combo = combos[0]
        child_combo = combos[1]

        parent_var_name = parent_combo.cget("textvariable")
        dem_win.setvar(parent_var_name, "Reliance Industries Ltd")

        child_var_name = child_combo.cget("textvariable")
        dem_win.setvar(child_var_name, "Jio Financial Services")

        # Mock show_colorful_yesno to simulate user clicking Yes to add company
        def mock_add_and_yes(win, title, msg):
            if "Company Not Found" in title or "not found" in msg.lower():
                company_add.add_company_db(
                    "JIOFIN", "INE758E01017", "Jio Financial Services", "JIOFIN", "JIOFIN.NS", "Finance", 10.0, 0.05, 1, 0
                )
                if not hasattr(win, "company_added_list"):
                    setattr(win, "company_added_list", [])
                win.company_added_list.append("Jio Financial Services")
                return True
            return False

        with patch("Shared.dialog_utils.show_colorful_yesno", side_effect=mock_add_and_yes), \
             patch("StockMan.demerger_entry.show_colorful_yesno", side_effect=mock_add_and_yes), \
             patch("StockMan.demerger_entry.add_company"), \
             patch("StockMan.demerger_entry.export_company"), \
             patch("Shared.dialog_utils.show_colorful_error") as mock_err, \
             patch("StockMan.demerger_entry.show_colorful_error", mock_err):

            save_btn.invoke()

            # Verify no "Ensure all Child companies are valid" error occurred
            for call in mock_err.call_args_list:
                assert "Ensure all Child companies are valid" not in str(call)

            # Verify that Jio Financial Services is now present in stocks table
            with shared_globals.get_db_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT company_name FROM stocks WHERE stk_code = 'JIOFIN'")
                row = c.fetchone()
                assert row is not None
                assert row[0] == "Jio Financial Services"


def test_demerger_missing_child_company_declined(test_db, clean_root, monkeypatch):
    """Test that if user declines adding missing child company, error is shown and submission aborts."""
    company_add.add_company_db(
        "RELIANCE", "INE002A01018", "Reliance Industries Ltd", "RELIANCE", "RELIANCE.NS", "Energy", 10.0, 0.05, 1, 0
    )
    with shared_globals.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id_stk FROM stocks WHERE company_name = 'Reliance Industries Ltd'")
        id_parent = cursor.fetchone()[0]
        cursor.execute(
            """INSERT INTO contracts (cont_no, trd_dt, settle_no, settle_dt, no_of_trades)
               VALUES ('C2', '2026-01-01', 12346, '2026-01-01', 1)"""
        )
        cursor.execute(
            """INSERT INTO transactions (id_stk, cont_no, trd_dt, company_name, trade_type_trd, exchange, qty_trd, wap_unit_trd, price_lot_trd, net_amt_trd, net_amt_trd_applicable)
               VALUES (?, 'C2', '2026-01-01', 'Reliance Industries Ltd', 'BUY', 'NSE', 50, 2500.0, 125000.0, 125000.0, 125000.0)""",
            (id_parent,),
        )
        conn.commit()

    with patch.object(clean_root, "wait_window", return_value=None), \
         patch("Shared.modal_utils.disable_parent", return_value="modal_1"), \
         patch("Shared.window_manager.push_window"), \
         patch("Shared.window_manager.safe_close_modal"), \
         patch("Shared.gui_utils.setup_footer_tooltip", return_value=tk.StringVar()):

        demerger_entry.add_demerger(clean_root)

        dem_win = [c for c in clean_root.winfo_children() if isinstance(c, tk.Toplevel)][0]

        save_btn = None
        for w in dem_win.winfo_children():
            if isinstance(w, tk.Frame):
                for sub_w in w.winfo_children():
                    if isinstance(sub_w, tk.Button) and "Execute Demerger" in sub_w.cget("text"):
                        save_btn = sub_w

        combos = []
        def find_combos(widget):
            for child in widget.winfo_children():
                if child.winfo_class() == "TCombobox":
                    combos.append(child)
                find_combos(child)

        find_combos(dem_win)
        parent_combo = combos[0]
        child_combo = combos[1]

        parent_var_name = parent_combo.cget("textvariable")
        dem_win.setvar(parent_var_name, "Reliance Industries Ltd")

        child_var_name = child_combo.cget("textvariable")
        dem_win.setvar(child_var_name, "Unknown Company Ltd")

        # User answers No (False) to adding the company
        with patch("Shared.dialog_utils.show_colorful_yesno", return_value=False), \
             patch("StockMan.demerger_entry.show_colorful_yesno", return_value=False), \
             patch("Shared.dialog_utils.show_colorful_error") as mock_err, \
             patch("StockMan.demerger_entry.show_colorful_error", mock_err):

            save_btn.invoke()

            # Verify an error was displayed informing the user that child company is not valid or was not added
            err_messages = [str(call) for call in mock_err.call_args_list]
            assert any("not valid or was not added" in msg for msg in err_messages)
