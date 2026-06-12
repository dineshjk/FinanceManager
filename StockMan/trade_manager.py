# -*- coding: utf-8 -*-
# File: FinanceManager/StockMan/trade_manager.py

"""
UI module for viewing historical trades and triggering safe database rollbacks.
"""

import tkinter as tk
from tkinter import ttk
import sqlite3
from typing import Union

# Local imports
from Shared.globals import get_db_connection, logger, UI_THEME
from Shared.dialog_utils import (
    show_colorful_yesno,
    show_colorful_info,
    show_colorful_error,
)
from .rollback_manager import delete_trade
from .trade_update import update_trade
from .trade_utils import rebuild_sell_allocations
from Shared.modal_utils import disable_parent, add_escape_binding
from Shared.window_manager import push_window, pop_window, safe_close_modal
from Shared.gui_utils import apply_button_animations


def show_trade_manager(
    parent: Union[tk.Toplevel, tk.Tk], calling_button: tk.Widget | None = None
) -> None:
    """
    Opens a modal window displaying all trades with options to delete/rollback.
    """
    # Centralized modal management: Disable parent window to prevent interaction
    modal_id = disable_parent(parent, calling_button=calling_button)

    mgr_win = tk.Toplevel(parent)
    mgr_win.title("Trade Manager — Manage / Edit / Remove")
    mgr_win.geometry("950x600")
    mgr_win.configure(bg=UI_THEME["bg_input"])
    mgr_win.transient(parent)
    mgr_win.grab_set()
    mgr_win.focus_set()
    push_window(mgr_win, parent)

    # --- Header ---
    tk.Label(
        mgr_win,
        text="📊 TRADE MANAGER — MANAGE / EDIT / REMOVE",
        font=UI_THEME.get("font_bold", ("Helvetica", 14, "bold")),
        bg=UI_THEME.get("bg_header", "#1e293b"),
        fg=UI_THEME.get("fg_header", "#ffffff"),
        pady=10,
    ).pack(fill="x")

    # --- Treeview Theming ---
    style = ttk.Style()
    if "clam" not in style.theme_names():
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

    # Apply your high-contrast theme to the Treeview table
    style.configure(
        "Dark.Treeview",
        background=UI_THEME.get("charcoal", "#334155"),
        foreground="white",
        fieldbackground=UI_THEME.get("charcoal", "#334155"),
        bordercolor=UI_THEME.get("slate_light", "#475569"),
        rowheight=30,
        font=UI_THEME.get("font_main", ("Helvetica", 12)),
    )
    style.configure(
        "Dark.Treeview.Heading",
        background=UI_THEME.get("dark_slate", "#1e293b"),
        foreground=UI_THEME.get("gold", "#FFD700"),
        font=UI_THEME.get("font_bold", ("Helvetica", 12, "bold")),
    )

    def sort_by_column(tree, col, descending):
        """Sort tree contents when a column header is clicked."""
        data = [
            (tree.set(child, col), child) for child in tree.get_children("")
        ]

        # Helper to handle mixed data types (Currency, Numbers, Strings)
        def convert_type(val):
            try:
                # Strip ₹ symbol and commas for clean numerical sorting
                clean_val = val.replace("₹", "").replace(",", "").strip()
                return float(clean_val)
            except ValueError:
                return val.lower()

        # Sort the data
        data.sort(key=lambda x: convert_type(x[0]), reverse=descending)

        # Rearrange items in sorted positions
        for index, (val, child) in enumerate(data):
            tree.move(child, "", index)

        # Reverse sort direction for the next click
        tree.heading(
            col, command=lambda c=col: sort_by_column(tree, c, not descending)
        )

    # --- Treeview Setup ---
    tree_frame = tk.Frame(
        mgr_win, bg=UI_THEME["bg_input"], bd=1, relief="ridge"
    )
    tree_frame.pack(fill="both", expand=True, padx=15, pady=15)

    tree_scroll = ttk.Scrollbar(tree_frame)
    tree_scroll.pack(side="right", fill="y")

    cols = ("ID", "Date", "Company", "Type", "Qty", "Price", "Net Amount")
    tree = ttk.Treeview(
        tree_frame,
        columns=cols,
        show="headings",
        yscrollcommand=tree_scroll.set,
        style="Dark.Treeview",
    )
    tree_scroll.config(command=tree.yview)

    # Configure the headings and bind the click-to-sort command
    columns_setup = {
        "ID": "ID",
        "Date": "Trade Date",
        "Company": "Company",
        "Type": "Type",
        "Qty": "Quantity",
        "Price": "Avg Price",
        "Net Amount": "Net Amount",
    }

    for col, text in columns_setup.items():
        tree.heading(
            col,
            text=text,
            command=lambda c=col: sort_by_column(tree, c, False),
        )

    # Configure Color Tags for row insertion
    tree.tag_configure("buy_row", foreground="#4ade80")  # Soft green
    tree.tag_configure("sell_row", foreground="#f87171")  # Soft red

    # Hide the ID column
    tree.column("ID", width=0, stretch=tk.NO)
    tree.column("Date", width=120, anchor="center")
    tree.column("Company", width=250, anchor="w")
    tree.column("Type", width=80, anchor="center")
    tree.column("Qty", width=100, anchor="e")
    tree.column("Price", width=120, anchor="e")
    tree.column("Net Amount", width=150, anchor="e")

    tree.pack(fill="both", expand=True)

    # --- Data Loading Logic ---
    def load_data():
        for item in tree.get_children():
            tree.delete(item)
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT t.id_trd, t.trd_dt, c.company_name, t.trade_type_trd, t.qty_trd, t.wap_unit_trd, t.net_amt_trd
                    FROM transactions t
                    JOIN stocks c ON t.id_stk = c.id_stk
                    WHERE t.trade_type_trd IN ('BUY', 'SELL')
                    ORDER BY t.trd_dt DESC, t.id_trd DESC
                """)
                for row in cursor.fetchall():
                    # Determine the trade type to apply the correct color tag
                    trade_type = row[3]
                    row_tag = "buy_row" if trade_type == "BUY" else "sell_row"

                    tree.insert(
                        "",
                        "end",
                        values=(
                            row[0],
                            row[1],
                            row[2],
                            row[3],
                            row[4],
                            f"₹ {row[5]:.2f}",
                            f"₹ {row[6]:.2f}",
                        ),
                        tags=(row_tag,),  # Apply the tag here
                    )
        except sqlite3.Error as e:
            logger.error(f"Failed to load trades: {e}")

    # Load data immediately upon opening
    load_data()

    def _get_selected_trd_id():
        """Return (trd_id, comp_name, trd_type) for the selected row, or None."""
        selected = tree.selection()
        if not selected:
            show_colorful_error(
                mgr_win,
                "Selection Error",
                "Please select a trade from the list first.",
            )
            return None, None, None
        item = tree.item(selected[0])
        return item["values"][0], item["values"][2], item["values"][3]

    def _on_edit():
        trd_id, comp_name, _ = _get_selected_trd_id()
        if trd_id is None:
            return
        update_trade(mgr_win, id_trd=trd_id)
        load_data()

    # --- Action Logic ---
    def _on_delete():
        trd_id, comp_name, trd_type = _get_selected_trd_id()
        if trd_id is None:
            return

        # Fetch id_stk before deletion for FIFO rebalance
        id_stk = None
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT id_stk FROM transactions WHERE id_trd = ?",
                    (trd_id,),
                )
                row = cur.fetchone()
                if row:
                    id_stk = row[0]
        except Exception:
            pass

        # The Safety Net
        confirm = show_colorful_yesno(
            mgr_win,
            "Confirm Rollback",
            f"Are you sure you want to permanently delete this {trd_type} trade for {comp_name}?\n\nThis will reverse all financial calculations and allocations tied to this specific trade.",
        )

        if confirm:
            # Full rollback
            success, msg = delete_trade(trd_id)
            if success:
                # Rebuild FIFO allocations for the affected stock
                if id_stk is not None:
                    rebuild_sell_allocations([id_stk])
                show_colorful_info(
                    mgr_win,
                    "Delete Successful",
                    f"The {trd_type} trade for {comp_name} has been deleted "
                    f"and sell allocations have been rebalanced.",
                )
                load_data()
            else:
                show_colorful_error(mgr_win, "Delete Failed", msg)

    def close_manager():
        safe_close_modal(mgr_win, parent, calling_button)

    # --- Footer Buttons ---
    btn_frame = tk.Frame(mgr_win, bg=UI_THEME["bg_input"])
    btn_frame.pack(fill="x", padx=15, pady=(0, 15))

    edit_btn = tk.Button(
        btn_frame,
        text="✏️ Edit Selected",
        command=_on_edit,
        bg=UI_THEME.get("bg_header", "#1e293b"),
        fg="#60a5fa",
        font=UI_THEME.get("font_bold", ("Helvetica", 14, "bold")),
        width=20,
        cursor="hand2",
        relief="flat",
    )
    edit_btn.pack(side="left")

    del_btn = tk.Button(
        btn_frame,
        text="🗑️ Delete Selected",
        command=_on_delete,
        bg=UI_THEME.get("bg_header", "#1e293b"),
        fg="#ef4444",
        font=UI_THEME.get("font_bold", ("Helvetica", 14, "bold")),
        width=20,
        cursor="hand2",
        relief="flat",
    )
    del_btn.pack(side="left", padx=(10, 0))

    close_btn = tk.Button(
        btn_frame,
        text="Close",
        command=close_manager,
        bg=UI_THEME.get("bg_header", "#1e293b"),
        fg=UI_THEME.get("fg_header", "#ffffff"),
        font=UI_THEME.get("font_bold", ("Helvetica", 14, "bold")),
        width=15,
        cursor="hand2",
        relief="flat",
    )
    close_btn.pack(side="right")

    apply_button_animations(
        edit_btn, UI_THEME["bg_header"], UI_THEME["bg_focus"]
    )
    apply_button_animations(
        del_btn, UI_THEME["bg_header"], UI_THEME["bg_focus"]
    )
    apply_button_animations(
        close_btn, UI_THEME["bg_header"], UI_THEME["bg_focus"]
    )

    def on_esc(_event=None):
        close_manager()
        return "break"  # This is the magic bullet that stops the event from reaching the parent

    mgr_win.bind("<Escape>", on_esc)
    # mgr_win.bind("<KeyRelease-Escape>", on_esc)
    mgr_win.protocol("WM_DELETE_WINDOW", close_manager)

    parent.wait_window(mgr_win)

    # CRITICAL: Restore grab to the Trade Menu so it doesn't fall out of focus
    try:
        if parent.winfo_exists():
            parent.grab_set()
    except tk.TclError:
        pass
