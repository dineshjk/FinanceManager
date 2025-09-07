# -*- coding: utf-8 -*-
# File: c:\Users\aumji\source\repos\Finance\FinanceManager\GUIStock\business\trade_operations.py

"""
Trade operations and business logic for the Stock Portfolio Management System.

This module contains functions for adding, modifying, and deleting trades
with database integrity verification.
"""

import sqlite3

# Import using new package structure
from FinanceManager.GUIStock.config.globals import DB_PATH
from FinanceManager.GUIStock.dialogs import (
    show_colorful_info, show_colorful_error, show_colorful_yesno
)


def remove_trade(parent_window):
    """
    Main function to remove a trade - shows selection interface and handles deletion.

    This function provides the same interface as the original remove_trade function
    in transaction_utils.py, maintaining compatibility with existing code.

    Args:
        parent_window: The parent tkinter window for dialog display
    """
    import tkinter as tk
    from tkinter import ttk

    # Handle imports based on execution context
    try:
        from GUIStock.config.globals import get_db_connection
    except ImportError:
        from config.globals import get_db_connection

    def fetch_all_trades():
        """Fetch all trades with related information"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT
                        t.id_trd,
                        s.stk_code,
                        s.company_name,
                        t.trd_dt,
                        t.qty_trd,
                        t.wap_unit_trd,
                        (t.qty_trd * t.wap_unit_trd) as total_value
                    FROM transactions t
                    JOIN stocks s ON t.id_stk = s.id_stk
                    ORDER BY t.trd_dt DESC, t.id_trd DESC
                """)
                return cursor.fetchall()
        except Exception as e:
            show_colorful_error(parent_window, "Database Error",
                               f"Failed to fetch trades: {str(e)}")
            return []

    def delete_selected_trade(trade_id):
        """Delete the selected trade with confirmation and verification"""
        return remove_trade_by_id(parent_window, trade_id)

    def on_delete_selected():
        """Handle delete button click"""
        selection = trades_tree.selection()
        if not selection:
            show_colorful_error(delete_win, "No Selection",
                               "Please select a trade to delete!")
            return

        # Get selected trade details
        item = trades_tree.item(selection[0])
        values = item['values']
        trade_id = values[0]

        if delete_selected_trade(trade_id):
            # Refresh the trades list
            refresh_trades_list()

    def refresh_trades_list():
        """Refresh the trades list"""
        # Clear existing items
        for item in trades_tree.get_children():
            trades_tree.delete(item)

        # Fetch and populate new data
        trades = fetch_all_trades()
        if not trades:
            show_colorful_info(delete_win, "No Trades",
                              "No trades found in the database!")
            return

        for trade in trades:
            trades_tree.insert('', 'end', values=trade)

    def on_item_select(event):
        """Handle item selection"""
        selection = trades_tree.selection()
        if selection:
            delete_btn.config(state="normal", bg="#dc2626",
                             text="🗑️ Delete Selected Trade")
        else:
            delete_btn.config(state="disabled", bg="#94a3b8",
                             text="Select a Trade First")

    # Create main deletion window
    delete_win = tk.Toplevel(parent_window)
    delete_win.title("🗑️ Remove Trade")
    delete_win.geometry("1000x600")
    delete_win.configure(bg="#f8fafc")
    delete_win.resizable(True, True)
    delete_win.transient(parent_window)
    delete_win.grab_set()

    # Center the window
    delete_win.update_idletasks()
    x = (delete_win.winfo_screenwidth() // 2) - (500)
    y = (delete_win.winfo_screenheight() // 2) - (300)
    delete_win.geometry(f"1000x600+{x}+{y}")

    # Header
    header_frame = tk.Frame(delete_win, bg="#dc2626", height=80)
    header_frame.pack(fill="x")
    header_frame.pack_propagate(False)

    title_label = tk.Label(header_frame, text="🗑️ Remove Trade",
                          font=("Arial", 20, "bold"),
                          bg="#dc2626", fg="white")
    title_label.pack(pady=20)

    # Instructions
    info_frame = tk.Frame(delete_win, bg="#fef3c7", relief="solid", bd=1)
    info_frame.pack(fill="x", padx=20, pady=(20, 10))

    info_text = """📋 Instructions: Select a trade from the list below and click 'Delete Selected Trade' to remove it.
⚠️ Warning: This action cannot be undone. All related records will be permanently deleted."""

    info_label = tk.Label(info_frame, text=info_text, font=("Arial", 10),
                         bg="#fef3c7", fg="#92400e", justify="left")
    info_label.pack(padx=15, pady=10)

    # Trades list frame
    list_frame = tk.LabelFrame(delete_win, text="📊 Available Trades",
                              font=("Arial", 12, "bold"),
                              bg="#f8fafc", fg="#1e293b", relief="groove", bd=2)
    list_frame.pack(fill="both", expand=True, padx=20, pady=10)

    # Create Treeview for trades
    columns = ('ID', 'Stock Code', 'Company', 'Date', 'Quantity', 'WAP',
               'Total')
    trades_tree = ttk.Treeview(list_frame, columns=columns, show='headings',
                              height=15)

    # Configure column headings and widths
    column_widths = {'ID': 60, 'Stock Code': 80, 'Company': 200, 'Date': 100,
                    'Quantity': 100, 'WAP': 100, 'Total': 120}

    for col in columns:
        trades_tree.heading(col, text=col, anchor="center")
        trades_tree.column(col, width=column_widths.get(col, 100),
                          anchor="center")

    # Add scrollbar
    scrollbar = ttk.Scrollbar(list_frame, orient="vertical",
                             command=trades_tree.yview)
    trades_tree.configure(yscrollcommand=scrollbar.set)

    # Pack treeview and scrollbar
    trades_tree.pack(side="left", fill="both", expand=True, padx=(10, 0),
                    pady=10)
    scrollbar.pack(side="right", fill="y", pady=10)

    # Bind selection event
    trades_tree.bind('<<TreeviewSelect>>', on_item_select)

    # Button frame
    btn_frame = tk.Frame(delete_win, bg="#f8fafc")
    btn_frame.pack(fill="x", padx=20, pady=(0, 20))

    # Delete button
    delete_btn = tk.Button(btn_frame, text="Select a Trade First",
                          font=("Arial", 14, "bold"),
                          bg="#94a3b8", fg="white", state="disabled",
                          relief="raised", bd=3, cursor="hand2",
                          command=on_delete_selected, width=25, height=2)
    delete_btn.pack(side="right", padx=(10, 0))

    # Cancel button
    cancel_btn = tk.Button(btn_frame, text="❌ Cancel",
                          font=("Arial", 14, "bold"),
                          bg="#6b7280", fg="white", activebackground="#4b5563",
                          relief="raised", bd=3, cursor="hand2",
                          command=delete_win.destroy, width=15, height=2)
    cancel_btn.pack(side="right")

    # Load initial data
    refresh_trades_list()

    # Set focus and bindings
    delete_win.focus_set()
    delete_win.bind("<Escape>", lambda e: delete_win.destroy())

    # Wait for window to close
    delete_win.wait_window()


def remove_trade_by_id(parent_window, trade_id):
    """
    Remove a trade from the database with confirmation and integrity checks.

    Args:
        parent_window: The parent tkinter window for dialog display
        trade_id (int): The ID of the trade to remove

    Returns:
        bool: True if trade was successfully removed, False otherwise
    """
    if not trade_id:
        show_colorful_error(parent_window, "Error",
                           "No trade ID provided for deletion.")
        return False

    try:
        # Connect to database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # First, check if the trade exists and get details
        cursor.execute("""
            SELECT t.id_trd, s.stk_code, t.qty_trd, t.wap_unit_trd, t.trd_dt,
                   s.company_name
            FROM transactions t
            JOIN stocks s ON t.id_stk = s.id_stk
            WHERE t.id_trd = ?
        """, (trade_id,))

        trade_info = cursor.fetchone()

        if not trade_info:
            show_colorful_error(parent_window, "Trade Not Found",
                               f"No trade found with ID: {trade_id}")
            conn.close()
            return False

        # Extract trade details for confirmation
        tid, stk_code, quantity, price, trade_date, company_name = trade_info

        # Create confirmation message
        confirmation_msg = f"""Are you sure you want to delete this trade?

Trade Details:
- Trade ID: {tid}
- Company: {company_name} ({stk_code})
- Quantity: {quantity:,.0f} shares
- Price: ₹{price:,.2f}
- Date: {trade_date}
- Total Value: ₹{quantity * price:,.2f}

This action cannot be undone. All related records will be permanently removed."""

        # Show confirmation dialog
        if not show_colorful_yesno(parent_window, "Confirm Trade Deletion",
                                  confirmation_msg):
            conn.close()
            return False

        # Check for dependent records that will be affected
        cursor.execute("""
            SELECT COUNT(*) FROM corp_acts
            WHERE id_stk = (SELECT id_stk FROM transactions WHERE id_trd = ?)
            AND act_dt >= ?
        """, (trade_id, trade_date))

        corp_actions_count = cursor.fetchone()[0]

        if corp_actions_count > 0:
            warning_msg = f"""Warning: This trade is associated with {corp_actions_count} corporate action(s).

Deleting this trade may affect the integrity of corporate action calculations.

Do you still want to proceed with the deletion?"""

            if not show_colorful_yesno(parent_window, "Corporate Actions Warning",
                                      warning_msg):
                conn.close()
                return False

        # Perform the deletion (CASCADE will handle related records)
        cursor.execute("DELETE FROM transactions WHERE id_trd = ?", (trade_id,))

        # Verify deletion was successful
        if cursor.rowcount == 0:
            show_colorful_error(parent_window, "Deletion Failed",
                               "Failed to delete the trade. Please try again.")
            conn.rollback()
            conn.close()
            return False

        # Commit the transaction
        conn.commit()

        # Show success message
        success_msg = f"""Trade successfully deleted!

Deleted Trade Details:
- Trade ID: {tid}
- Company: {company_name} ({stk_code})
- Quantity: {quantity:,.0f} shares
- Total Value: ₹{quantity * price:,.2f}

The trade and all related records have been permanently removed from the database."""

        show_colorful_info(parent_window, "Trade Deleted Successfully",
                          success_msg)

        conn.close()
        return True

    except sqlite3.Error as e:
        show_colorful_error(parent_window, "Database Error",
                           f"An error occurred while deleting the trade:\n\n{str(e)}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

    except Exception as e:
        show_colorful_error(parent_window, "Unexpected Error",
                           f"An unexpected error occurred:\n\n{str(e)}")
        if 'conn' in locals():
            conn.close()
        return False


def get_trade_summary(symbol=None, start_date=None, end_date=None):
    """
    Get a summary of trades with optional filtering.

    Args:
        symbol (str, optional): Filter by stock symbol
        start_date (str, optional): Start date for filtering (YYYY-MM-DD)
        end_date (str, optional): End date for filtering (YYYY-MM-DD)

    Returns:
        list: List of trade records matching the criteria
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        query = """
            SELECT t.id_trd, s.stk_code, s.company_name, t.qty_trd,
                   t.wap_unit_trd, t.trd_dt,
                   (t.qty_trd * t.wap_unit_trd) as total_value
            FROM transactions t
            JOIN stocks s ON t.id_stk = s.id_stk
            WHERE 1=1
        """

        params = []

        if symbol:
            query += " AND s.stk_code = ?"
            params.append(symbol)

        if start_date:
            query += " AND t.trd_dt >= ?"
            params.append(start_date)

        if end_date:
            query += " AND t.trd_dt <= ?"
            params.append(end_date)

        query += " ORDER BY t.trd_dt DESC, t.id_trd DESC"

        cursor.execute(query, params)
        trades = cursor.fetchall()

        conn.close()
        return trades

    except sqlite3.Error:
        return []


def validate_trade_data(symbol, quantity, price, trade_date):
    """
    Validate trade data before adding/updating.

    Args:
        symbol (str): Stock symbol
        quantity (float): Number of shares
        price (float): Price per share
        trade_date (str): Trade date (YYYY-MM-DD)

    Returns:
        tuple: (is_valid, error_message)
    """
    errors = []

    if not symbol or not symbol.strip():
        errors.append("Symbol is required")

    if quantity <= 0:
        errors.append("Quantity must be positive")

    if price <= 0:
        errors.append("Price must be positive")

    if not trade_date:
        errors.append("Trade date is required")

    # Additional validation can be added here

    if errors:
        return False, "; ".join(errors)

    return True, ""
