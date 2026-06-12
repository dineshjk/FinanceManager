# -*- coding: utf-8 -*-
# File: C:\Data\Personal\Finance_and_Investment\finprog\FinanceManager\StockMan\primary_offer_remove.py

"""
primary_offer_remove.py
-----------------------

Modal window and helpers for removing existing Primary Offers
(IPOs, FPOs, SME IPOs, and Rights Issues) in the StockMan application.
"""

from typing import Union
import tkinter as tk
from tkinter import ttk
import sqlite3

# Local project imports
from Shared.globals import get_db_connection, logger
from Shared.dialog_utils import (
    show_colorful_info,
    show_colorful_error,
    show_colorful_yesno,
)
from .trade_utils import compute_avg_price
from Shared.modal_utils import disable_parent, enable_parent
from Shared.window_manager import push_window, pop_window


def _perform_offer_removal(id_offer: int, parent_win: tk.Toplevel) -> bool:
    """
    Core logic to remove a primary offer and handle all related data.

    - Validates that the allotted shares haven't been sold yet.
    - Deletes the primary_offer (which cascades to offer_allotments, releasing FK locks).
    - Deletes the transaction, contract, and computed_bank records.
    - Triggers a recalculation of the stock's average price.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys = ON;")

            # 1. Fetch related IDs to clean up surrounding tables
            cursor.execute(
                """
                SELECT oa.tx_id, oa.cont_no, po.id_stk
                FROM primary_offers po
                LEFT JOIN offer_allotments oa ON po.id_offer = oa.id_offer
                WHERE po.id_offer = ?
                """,
                (id_offer,),
            )
            row = cursor.fetchone()

            if not row:
                show_colorful_error(
                    parent_win, "Error", f"Offer ID {id_offer} not found."
                )
                return False

            tx_id, cont_no, id_stk = row

            # 2. Check if transaction exists and if shares are already sold
            if tx_id:
                cursor.execute(
                    "SELECT sold_qty FROM transactions WHERE id_trd = ?",
                    (tx_id,),
                )
                tx_row = cursor.fetchone()

                # Safety Check: Prevent deletion of a BUY lot that has already been sold
                if tx_row and tx_row[0] > 0:
                    show_colorful_error(
                        parent_win,
                        "Action Denied",
                        "Cannot remove this offer because some or all of the allotted shares have already been sold.\n\n"
                        "Please remove the corresponding SELL trades first before removing this offer.",
                    )
                    return False

            # 3. CRITICAL FIX: Delete the primary offer first.
            # This cascades and deletes offer_allotments, removing the foreign key lock on the contract.
            cursor.execute(
                "DELETE FROM primary_offers WHERE id_offer = ?", (id_offer,)
            )

            # 4. Now safely clean up the orphaned transactions, contracts, and bank records
            if tx_id:
                cursor.execute(
                    "DELETE FROM transactions WHERE id_trd = ?", (tx_id,)
                )
            if cont_no:
                cursor.execute(
                    "DELETE FROM computed_bank WHERE cont_no = ?", (cont_no,)
                )
                cursor.execute(
                    "DELETE FROM contracts WHERE cont_no = ?", (cont_no,)
                )

            conn.commit()

            # 5. Re-calculate portfolio averages for the affected stock
            if id_stk:
                compute_avg_price(id_stk)

            return True

    except sqlite3.Error as e:
        show_colorful_error(
            parent_win, "Database Error", f"Failed to remove offer: {e}"
        )
        logger.error(
            "Failed to remove offer ID %s: %s", id_offer, e, exc_info=True
        )
        return False


def remove_primary_offer(
    parent: Union[tk.Toplevel, tk.Tk], calling_button: tk.Widget | None = None
) -> None:
    """
    UI flow to list, select, and remove a Primary Offer (IPO/Rights).
    """
    modal_id = disable_parent(parent, calling_button=calling_button)

    rm_win = tk.Toplevel(parent)
    rm_win.title("🗑️ Remove Primary Offer")
    rm_win.geometry("900x500")
    rm_win.resizable(False, False)
    rm_win.configure(bg="#fae0e0")  # A light red/warning background
    rm_win.transient(parent)
    rm_win.grab_set()
    push_window(rm_win, parent)

    # --- Header ---
    header_lbl = tk.Label(
        rm_win,
        text="Select an IPO or Rights Issue to Remove",
        font=("Helvetica", 16, "bold"),
        bg="#b91c1c",
        fg="white",
        pady=10,
    )
    header_lbl.pack(fill="x")

    # --- Treeview Frame ---
    tree_frame = tk.Frame(rm_win, bg="#fae0e0", padx=20, pady=20)
    tree_frame.pack(fill="both", expand=True)

    # Scrollbar
    tree_scroll = tk.Scrollbar(tree_frame)
    tree_scroll.pack(side="right", fill="y")

    # Treeview Columns
    columns = (
        "ID",
        "Type",
        "Company",
        "Offer Name",
        "Status",
        "Applied",
        "Allotted",
    )
    tree = ttk.Treeview(
        tree_frame,
        columns=columns,
        show="headings",
        yscrollcommand=tree_scroll.set,
        height=12,
    )

    tree.heading("ID", text="ID")
    tree.heading("Type", text="Type")
    tree.heading("Company", text="Company")
    tree.heading("Offer Name", text="Offer Name")
    tree.heading("Status", text="Status")
    tree.heading("Applied", text="Applied Qty")
    tree.heading("Allotted", text="Allotted Qty")

    tree.column("ID", width=50, anchor="center")
    tree.column("Type", width=100, anchor="center")
    tree.column("Company", width=200, anchor="w")
    tree.column("Offer Name", width=200, anchor="w")
    tree.column("Status", width=100, anchor="center")
    tree.column("Applied", width=100, anchor="e")
    tree.column("Allotted", width=100, anchor="e")

    tree.pack(fill="both", expand=True)
    tree_scroll.config(command=tree.yview)

    # --- Populate Data ---
    def refresh_list():
        for item in tree.get_children():
            tree.delete(item)

        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT
                        po.id_offer,
                        po.offer_type,
                        s.company_name,
                        po.offer_name,
                        oa.status,
                        oa.applied_qty,
                        oa.allotted_qty
                    FROM primary_offers po
                    JOIN stocks s ON po.id_stk = s.id_stk
                    LEFT JOIN offer_allotments oa ON po.id_offer = oa.id_offer
                    ORDER BY po.id_offer DESC
                """)
                records = cursor.fetchall()
                for row in records:
                    tree.insert("", "end", values=row)
        except sqlite3.Error as e:
            logger.error("Failed to fetch primary offers for removal: %s", e)
            show_colorful_error(
                rm_win, "Database Error", "Failed to load offers."
            )

    refresh_list()

    # --- Button Frame ---
    btn_frame = tk.Frame(rm_win, bg="#fae0e0", pady=10)
    btn_frame.pack(fill="x")

    def _close_window(_event=None):
        try:
            pop_window()
            enable_parent(modal_id)
            rm_win.destroy()
        except tk.TclError:
            pass

    def _on_remove(_event=None):
        selected = tree.selection()
        if not selected:
            show_colorful_error(
                rm_win, "No Selection", "Please select an offer to remove."
            )
            return

        item = tree.item(selected[0])
        offer_id = item["values"][0]
        offer_type = item["values"][1]
        company = item["values"][2]

        confirmation = show_colorful_yesno(
            rm_win,
            "Confirm Removal",
            f"Are you sure you want to permanently remove the {offer_type} for {company} (ID: {offer_id})?\n\n"
            "This action will also remove the generated trades and cannot be undone.",
        )

        if confirmation:
            if _perform_offer_removal(int(offer_id), rm_win):
                show_colorful_info(
                    rm_win,
                    "Success",
                    f"{offer_type} for {company} (ID: {offer_id}) has been removed successfully.",
                )
                refresh_list()

    remove_btn = tk.Button(
        btn_frame,
        text="🗑️ Remove Selected",
        command=_on_remove,
        font=("Helvetica", 12, "bold"),
        bg="#b91c1c",
        fg="white",
        cursor="hand2",
        width=20,
    )
    remove_btn.pack(side="right", padx=20)

    cancel_btn = tk.Button(
        btn_frame,
        text="Cancel",
        command=_close_window,
        font=("Helvetica", 12, "bold"),
        bg="#475569",
        fg="white",
        cursor="hand2",
        width=10,
    )
    cancel_btn.pack(side="right", padx=10)

    # Double click to remove
    tree.bind("<Double-1>", _on_remove)
    rm_win.bind("<Escape>", _close_window)
    rm_win.protocol("WM_DELETE_WINDOW", _close_window)

    parent.wait_window(rm_win)
    try:
        if parent.winfo_exists():
            parent.grab_set()
    except tk.TclError:
        pass


# File: C:\Data\Personal\Finance_and_Investment\finprog\FinanceManager\StockMan\primary_offer_remove.py ends here
