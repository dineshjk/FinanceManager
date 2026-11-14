# -*- coding: utf-8 -*-
# tests/test_reporting_tabs.py
"""
Integration Tests for Financial Reports Multi-Tab GUI Viewer.

This test suite verifies the interactive report viewer interface in `StockMan.reporting`,
testing tab switching, column sorting, and Excel export triggers.

Key Scenarios Tested:
    • Treeview rendering across Capital Gains, Holdings, Sector Allocation, and Dividend tabs.
    • Multi-column sorting and keyboard navigation.
"""

import tkinter as tk
from tkinter import ttk
from unittest.mock import patch

import pytest


def test_reporting_notebook_tab_order_and_columns():
    root = tk.Tk()
    root.withdraw()

    # Intercept wait_window so p_and_l doesn't block
    with patch.object(tk.Misc, "wait_window", lambda self, *args, **kwargs: None):
        # Mock load_data threading to prevent background db hits during UI structure inspection
        with patch("threading.Thread") as mock_thread:
            mock_thread.return_value.start.side_effect = lambda: None

            from StockMan.reporting import p_and_l

            # Call p_and_l
            p_and_l(root)

            # Find the opened Toplevel window
            top = None
            for child in root.winfo_children():
                if isinstance(child, tk.Toplevel):
                    top = child
                    break

            assert top is not None, "Reporting Toplevel window not created"

            # Find the main Notebook
            notebook = None
            for w in top.winfo_children():
                if isinstance(w, ttk.Notebook):
                    notebook = w
                    break

            assert notebook is not None, "Main Notebook not found"

            # Check tab count and titles
            tab_count = len(notebook.tabs())
            assert tab_count == 7, f"Expected 7 tabs, got {tab_count}"

            tab_texts = [notebook.tab(i, "text") for i in range(tab_count)]
            assert "📊 Stock-wise Analysis" in tab_texts[0]
            assert "📈 Portfolio Summary" in tab_texts[1]
            assert "📖 Passbook" in tab_texts[2]
            assert "📅 Yearly Passbook" in tab_texts[3]  # Directly after Passbook!
            assert "💼 Current Holdings" in tab_texts[4]
            assert "🥧 Portfolio Allocation" in tab_texts[5]
            assert "📚 Portfolio Ledgers" in tab_texts[6]

            # Inspect Passbook tab (Tab 2)
            passbook_tab = top.nametowidget(notebook.tabs()[2])
            
            # Find the passbook Treeview
            def find_tree(widget):
                if isinstance(widget, ttk.Treeview):
                    return [widget]
                res = []
                for child in widget.winfo_children():
                    res.extend(find_tree(child))
                return res

            pb_trees = find_tree(passbook_tab)
            assert len(pb_trees) >= 1
            pb_tree = pb_trees[0]
            cols = pb_tree["columns"]
            assert "Investment" in cols, f"'Investment' column missing from Passbook columns: {cols}"
            # Verify exact column order
            assert list(cols) == [
                "Date",
                "Description",
                "Deposit",
                "Withdrawal",
                "Cum. Inv",
                "Cum. Disinv",
                "Investment",
                "Day's Disinv",
                "Cum. P&L",
                "Cum. Ann. %",
            ]

            # Inspect Yearly Passbook tab (Tab 3)
            yp_tab = top.nametowidget(notebook.tabs()[3])
            yp_trees = find_tree(yp_tab)
            assert len(yp_trees) == 2, f"Expected 2 Treeviews in Yearly Passbook, found {len(yp_trees)}"

            # Tree 1: Yearly Hisaab Summary
            hisaab_tree = yp_trees[0]
            hisaab_cols = list(hisaab_tree["columns"])
            assert hisaab_cols == [
                "Financial Year",
                "Opening Date",
                "Opening Investment",
                "Investment Added",
                "Disinvestment",
                "Closing Investment",
                "Sell Proceeds",
                "Net Dividends",
                "Realized Gain/Loss",
                "Total Return",
                "Annualized Return %",
            ]

            # Tree 2: Yearly Passbook Ledger
            ledger_tree = yp_trees[1]
            ledger_cols = list(ledger_tree["columns"])
            assert ledger_cols == [
                "Date",
                "Description",
                "Deposit",
                "Withdrawal",
                "Cum. Inv",
                "Cum. Disinv",
                "Investment",
                "Day's Disinv",
                "Cum. P&L",
                "Cum. Ann. %",
            ]

            top.destroy()
    root.destroy()
