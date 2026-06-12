# -*- coding: utf-8 -*-
# BankMan/manage_ppf.py

"""
UI module for viewing and managing PPF master records and transactions.

Mirrors the structure and features of StockMan/trade_manager.py and
BankMan/manage_bank.py:
  * Sortable treeview (click any heading to toggle ascending/descending).
  * Colour-coded rows.
  * Edit Selected -- placeholder (inline editing not yet implemented).
  * Delete Selected -- removes the row and cascades required changes.
  * Close / Escape -- safe modal teardown via safe_close_modal.

Two public functions are exposed:

  show_ppf_manager(parent, calling_button=None)
      Displays all ppf_master rows.  Deleting a PPF account is blocked
      when ppf_transactions reference it (ON DELETE RESTRICT in the schema).

  show_ppf_transactions_manager(parent, calling_button=None)
      Displays all ppf_transactions rows.  Deleting a row also:
        1. Finds and removes the linked bank_transactions row
           (module_type='PPF', module_ref_id=ppf_trans_id).
        2. Nulls out pair_id on any transfer counterpart.
        3. Recalculates balance_after for every subsequent row in the
           same bank account so the running total stays correct.
"""

import tkinter as tk
from tkinter import ttk
import sqlite3
from typing import Union

from Shared.globals import get_db_connection, logger, UI_THEME, BANK_DB_PATH
from Shared.dialog_utils import (
    show_colorful_yesno,
    show_colorful_info,
    show_colorful_error,
)
from Shared.modal_utils import disable_parent
from Shared.window_manager import push_window, safe_close_modal
from Shared.gui_utils import apply_button_animations, universal_tree_sort

# ---------------------------------------------------------------------------



# ===========================================================================
# 1.  show_ppf_manager  --  ppf_master rows
# ===========================================================================


def show_ppf_manager(
    parent: Union[tk.Toplevel, tk.Tk],
    calling_button: tk.Widget | None = None,
) -> None:
    """Open a modal window showing all ppf_master records.

    Features
    --------
    * Sortable columns -- click any heading to toggle ascending/descending.
    * Colour-coded rows: active accounts in green, closed accounts in red.
    * Hidden primary-key column used by Edit/Delete without exposing IDs.
    * Edit Selected   -- informs the user editing is not yet available.
    * Delete Selected -- removes the PPF account from ppf_master.  Blocked
                         by the database RESTRICT constraint when linked
                         ppf_transactions rows exist.
    * Escape key and window-close button invoke the safe-close helper.
    * grab_set is restored on *parent* after the modal closes.
    """
    disable_parent(parent, calling_button=calling_button)

    mgr_win = tk.Toplevel(parent)
    mgr_win.title("PPF Master Manager — Manage / View / Remove")
    mgr_win.geometry("980x520")
    mgr_win.configure(bg=UI_THEME["bg_input"])
    mgr_win.transient(parent)
    mgr_win.grab_set()
    mgr_win.focus_set()
    push_window(mgr_win, parent)

    tk.Label(
        mgr_win,
        text="📒  PPF MASTER MANAGER — MANAGE / VIEW / REMOVE",
        font=UI_THEME.get("font_bold", ("Helvetica", 14, "bold")),
        bg=UI_THEME.get("bg_header", "#1e293b"),
        fg=UI_THEME.get("fg_header", "#ffffff"),
        pady=10,
    ).pack(fill="x")

    style = ttk.Style()
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure(
        "PPFMgr.Treeview",
        background=UI_THEME.get("charcoal", "#334155"),
        foreground="white",
        fieldbackground=UI_THEME.get("charcoal", "#334155"),
        bordercolor=UI_THEME.get("slate_light", "#475569"),
        rowheight=30,
        font=UI_THEME.get("font_main", ("Helvetica", 12)),
    )
    style.configure(
        "PPFMgr.Treeview.Heading",
        background=UI_THEME.get("dark_slate", "#1e293b"),
        foreground=UI_THEME.get("gold", "#FFD700"),
        font=UI_THEME.get("font_bold", ("Helvetica", 12, "bold")),
    )

    tree_frame = tk.Frame(mgr_win, bg=UI_THEME["bg_input"], bd=1, relief="ridge")
    tree_frame.pack(fill="both", expand=True, padx=15, pady=15)

    tree_scroll = ttk.Scrollbar(tree_frame)
    tree_scroll.pack(side="right", fill="y")

    cols = (
        "ID",
        "Account Number",
        "Holder Name",
        "Bank",
        "Open Date",
        "Maturity Date",
        "Active",
    )
    tree = ttk.Treeview(
        tree_frame,
        columns=cols,
        show="headings",
        yscrollcommand=tree_scroll.set,
        style="PPFMgr.Treeview",
    )
    tree_scroll.config(command=tree.yview)

    columns_setup = {
        "ID": "ID",
        "Account Number": "PPF Account No.",
        "Holder Name": "Holder Name",
        "Bank": "Bank",
        "Open Date": "Open Date",
        "Maturity Date": "Maturity Date",
        "Active": "Active",
    }
    for col, heading_text in columns_setup.items():
        tree.heading(
            col,
            text=heading_text,
            command=lambda c=col: universal_tree_sort(tree, c, False),
        )

    tree.tag_configure("active_row", foreground="#4ade80")  # green
    tree.tag_configure("inactive_row", foreground="#f87171")  # red

    tree.column("ID", width=0, stretch=tk.NO)
    tree.column("Account Number", width=180, anchor="w")
    tree.column("Holder Name", width=180, anchor="w")
    tree.column("Bank", width=180, anchor="w")
    tree.column("Open Date", width=110, anchor="center")
    tree.column("Maturity Date", width=110, anchor="center")
    tree.column("Active", width=65, anchor="center")

    tree.pack(fill="both", expand=True)

    def load_data() -> None:
        """Clear the treeview and repopulate from ppf_master."""
        for item in tree.get_children():
            tree.delete(item)
        try:
            with get_db_connection(BANK_DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT  pm.ppf_master_id,
                            pm.ppf_account_number,
                            pm.holder_name,
                            b.name,
                            pm.open_dt,
                            pm.maturity_dt,
                            pm.is_active
                    FROM    ppf_master pm
                    JOIN    accounts a ON a.ac_id = pm.account_id
                    JOIN    banks    b ON b.b_id  = a.b_id
                    ORDER BY b.name, pm.holder_name, pm.ppf_account_number
                """)
                for row in cursor.fetchall():
                    is_active = row[6]
                    row_tag = "active_row" if is_active else "inactive_row"
                    tree.insert(
                        "",
                        "end",
                        values=(
                            row[0],  # ppf_master_id (hidden)
                            row[1],  # ppf_account_number
                            row[2],  # holder_name
                            row[3],  # bank name
                            row[4],  # open_dt
                            row[5],  # maturity_dt
                            "Yes" if is_active else "No",
                        ),
                        tags=(row_tag,),
                    )
        except sqlite3.Error as e:
            logger.error("Failed to load ppf_master rows: %s", e)

    load_data()

    def _get_selected() -> tuple:
        """Return (ppf_master_id, ppf_account_number) or (None, None)."""
        selected = tree.selection()
        if not selected:
            show_colorful_error(
                mgr_win,
                "Selection Error",
                "Please select a PPF account from the list first.",
            )
            return None, None
        values = tree.item(selected[0])["values"]
        return values[0], values[1]

    def _on_edit() -> None:
        ppf_id, _ = _get_selected()
        if ppf_id is None:
            return
        show_colorful_info(
            mgr_win,
            "Edit Not Yet Available",
            "Inline editing of PPF master records is not yet implemented.\n\n"
            "To correct a record, delete it and re-enter with the correct "
            "values.",
        )

    def _on_delete() -> None:
        ppf_id, ppf_acct = _get_selected()
        if ppf_id is None:
            return

        tx_count = 0
        try:
            with get_db_connection(BANK_DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT COUNT(*) FROM ppf_transactions " "WHERE ppf_master_id = ?",
                    (ppf_id,),
                )
                row = cur.fetchone()
                if row:
                    tx_count = row[0]
        except sqlite3.Error as e:
            show_colorful_error(
                mgr_win,
                "Error",
                f"Could not check linked transactions: {e}",
            )
            return

        if tx_count > 0:
            show_colorful_error(
                mgr_win,
                "Cannot Delete",
                f"PPF account '{ppf_acct}' has {tx_count} linked "
                f"transaction(s).\n\n"
                f"Delete all ppf_transactions for this account before "
                f"removing the PPF master record.",
            )
            return

        confirm = show_colorful_yesno(
            mgr_win,
            "Confirm Delete",
            f"Are you sure you want to permanently delete the PPF account:\n\n"
            f"  {ppf_acct}\n\n"
            f"This action cannot be undone.",
        )
        if not confirm:
            return

        try:
            with get_db_connection(BANK_DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("PRAGMA foreign_keys = ON;")
                cur.execute(
                    "DELETE FROM ppf_master WHERE ppf_master_id = ?",
                    (ppf_id,),
                )
                conn.commit()
            show_colorful_info(
                mgr_win,
                "Delete Successful",
                f"PPF account '{ppf_acct}' has been permanently deleted.",
            )
            load_data()
        except sqlite3.IntegrityError as e:
            show_colorful_error(
                mgr_win,
                "Delete Blocked",
                f"Could not delete PPF account '{ppf_acct}' — it is still "
                f"referenced by one or more transactions.\n\nDetail: {e}",
            )
        except sqlite3.Error as e:
            show_colorful_error(mgr_win, "Delete Failed", f"Database error: {e}")

    def close_manager() -> None:
        safe_close_modal(mgr_win, parent, calling_button)

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

    _hdr = UI_THEME["bg_header"]
    _foc = UI_THEME["bg_focus"]
    apply_button_animations(edit_btn, _hdr, _foc)
    apply_button_animations(del_btn, _hdr, _foc)
    apply_button_animations(close_btn, _hdr, _foc)

    def on_esc(_event=None):
        close_manager()
        return "break"

    mgr_win.bind("<Escape>", on_esc)
    mgr_win.protocol("WM_DELETE_WINDOW", close_manager)

    parent.wait_window(mgr_win)

    try:
        if parent.winfo_exists():
            parent.grab_set()
    except tk.TclError:
        pass


# ===========================================================================
# 2.  show_ppf_transactions_manager  --  ppf_transactions rows
# ===========================================================================


def show_ppf_transactions_manager(
    parent: Union[tk.Toplevel, tk.Tk],
    calling_button: tk.Widget | None = None,
) -> None:
    """Open a modal window showing all ppf_transactions rows.

    Features
    --------
    * Sortable columns -- click any heading to toggle ascending/descending.
    * Colour-coded rows: deposit rows in green, withdrawal rows in red.
    * Hidden primary-key column used by Edit/Delete without exposing IDs.
    * Edit Selected   -- informs the user editing is not yet available.
    * Delete Selected -- removes the ppf_transactions row and also:
        1. Finds the linked bank_transactions row
           (module_type='PPF', module_ref_id=ppf_trans_id) and deletes it.
        2. Nulls out pair_id references on the transfer counterpart.
        3. Recalculates balance_after for every subsequent transaction in
           the same bank account so the running total stays correct.
    * Escape key and window-close button invoke the safe-close helper.
    * grab_set is restored on *parent* after the modal closes.
    """
    disable_parent(parent, calling_button=calling_button)

    mgr_win = tk.Toplevel(parent)
    mgr_win.title("PPF Transactions Manager — Manage / View / Remove")
    mgr_win.geometry("1100x600")
    mgr_win.configure(bg=UI_THEME["bg_input"])
    mgr_win.transient(parent)
    mgr_win.grab_set()
    mgr_win.focus_set()
    push_window(mgr_win, parent)

    tk.Label(
        mgr_win,
        text="📒  PPF TRANSACTIONS MANAGER — MANAGE / VIEW / REMOVE",
        font=UI_THEME.get("font_bold", ("Helvetica", 14, "bold")),
        bg=UI_THEME.get("bg_header", "#1e293b"),
        fg=UI_THEME.get("fg_header", "#ffffff"),
        pady=10,
    ).pack(fill="x")

    style = ttk.Style()
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure(
        "PPFTxMgr.Treeview",
        background=UI_THEME.get("charcoal", "#334155"),
        foreground="white",
        fieldbackground=UI_THEME.get("charcoal", "#334155"),
        bordercolor=UI_THEME.get("slate_light", "#475569"),
        rowheight=30,
        font=UI_THEME.get("font_main", ("Helvetica", 12)),
    )
    style.configure(
        "PPFTxMgr.Treeview.Heading",
        background=UI_THEME.get("dark_slate", "#1e293b"),
        foreground=UI_THEME.get("gold", "#FFD700"),
        font=UI_THEME.get("font_bold", ("Helvetica", 12, "bold")),
    )

    tree_frame = tk.Frame(mgr_win, bg=UI_THEME["bg_input"], bd=1, relief="ridge")
    tree_frame.pack(fill="both", expand=True, padx=15, pady=15)

    tree_scroll = ttk.Scrollbar(tree_frame)
    tree_scroll.pack(side="right", fill="y")

    cols = (
        "ID",
        "Date",
        "PPF Account",
        "Description",
        "Deposit",
        "Withdrawal",
        "Balance",
    )
    tree = ttk.Treeview(
        tree_frame,
        columns=cols,
        show="headings",
        yscrollcommand=tree_scroll.set,
        style="PPFTxMgr.Treeview",
    )
    tree_scroll.config(command=tree.yview)

    columns_setup = {
        "ID": "ID",
        "Date": "Trans Date",
        "PPF Account": "PPF Account",
        "Description": "Description",
        "Deposit": "Deposit (CR)",
        "Withdrawal": "Withdrawal (DR)",
        "Balance": "PPF Balance",
    }
    for col, heading_text in columns_setup.items():
        tree.heading(
            col,
            text=heading_text,
            command=lambda c=col: universal_tree_sort(tree, c, False),
        )

    # deposit rows (ppf_saving > 0) in green; withdrawal rows in red
    tree.tag_configure("deposit_row", foreground="#4ade80")  # green
    tree.tag_configure("withdrawal_row", foreground="#f87171")  # red

    tree.column("ID", width=0, stretch=tk.NO)
    tree.column("Date", width=110, anchor="center")
    tree.column("PPF Account", width=185, anchor="w")
    tree.column("Description", width=205, anchor="w")
    tree.column("Deposit", width=135, anchor="e")
    tree.column("Withdrawal", width=135, anchor="e")
    tree.column("Balance", width=135, anchor="e")

    tree.pack(fill="both", expand=True)

    def load_data() -> None:
        """Clear the treeview and repopulate from ppf_transactions."""
        for item in tree.get_children():
            tree.delete(item)
        try:
            with get_db_connection(BANK_DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT  pt.ppf_trans_id,
                            pt.ppf_trans_dt,
                            pm.ppf_account_number,
                            COALESCE(pt.ppf_description, ''),
                            pt.ppf_saving,
                            pt.ppf_withdrawal,
                            pt.ppf_balance
                    FROM    ppf_transactions pt
                    JOIN    ppf_master pm
                            ON pm.ppf_master_id = pt.ppf_master_id
                    ORDER BY pt.ppf_trans_dt DESC, pt.ppf_trans_id DESC
                """)
                for row in cursor.fetchall():
                    saving = row[4] or 0.0
                    withdrawal = row[5] or 0.0
                    balance = row[6] or 0.0
                    row_tag = (
                        "deposit_row"
                        if saving > 0.0 and withdrawal == 0.0
                        else "withdrawal_row"
                    )
                    tree.insert(
                        "",
                        "end",
                        values=(
                            row[0],
                            row[1],
                            row[2],
                            row[3],
                            f"₹ {saving:,.2f}" if saving else "",
                            f"₹ {withdrawal:,.2f}" if withdrawal else "",
                            f"₹ {balance:,.2f}",
                        ),
                        tags=(row_tag,),
                    )
        except sqlite3.Error as e:
            logger.error("Failed to load ppf_transactions rows: %s", e)

    load_data()

    def _get_selected() -> tuple:
        """Return (ppf_trans_id, ppf_account, description) or Nones."""
        selected = tree.selection()
        if not selected:
            show_colorful_error(
                mgr_win,
                "Selection Error",
                "Please select a transaction from the list first.",
            )
            return None, None, None
        values = tree.item(selected[0])["values"]
        return values[0], values[2], values[3]

    def _on_edit() -> None:
        ppf_trans_id, _, _ = _get_selected()
        if ppf_trans_id is None:
            return
        show_colorful_info(
            mgr_win,
            "Edit Not Yet Available",
            "Inline editing of PPF transactions is not yet implemented.\n\n"
            "To correct a transaction, delete it and re-enter with the "
            "correct values.",
        )

    def _on_delete() -> None:
        ppf_trans_id, ppf_acct, description = _get_selected()
        if ppf_trans_id is None:
            return

        # Step 1: fetch the linked bank_transactions row (if any)
        bank_row = None
        try:
            with get_db_connection(BANK_DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT  trans_id,
                            account_id,
                            trans_date,
                            deposit_amount,
                            withdrawal_amount,
                            pair_id
                    FROM    bank_transactions
                    WHERE   module_type   = 'PPF'
                      AND   module_ref_id = ?
                    """,
                    (ppf_trans_id,),
                )
                bank_row = cur.fetchone()
        except sqlite3.Error as e:
            show_colorful_error(
                mgr_win,
                "Error",
                f"Could not fetch linked bank transaction: {e}",
            )
            return

        linked_note = (
            "\n  • Also removes the linked bank transaction entry."
            "\n  • Clears any pair reference on the transfer counterpart."
            "\n  • Recalculates all subsequent balances for the account."
            if bank_row is not None
            else ""
        )
        confirm = show_colorful_yesno(
            mgr_win,
            "Confirm Delete",
            f"Permanently delete this PPF transaction?\n\n"
            f"  Account   : {ppf_acct}\n"
            f"  Narration : {description}"
            f"{linked_note}\n\n"
            f"This action cannot be undone.",
        )
        if not confirm:
            return

        # Step 2: execute all DB changes in one connection
        try:
            with get_db_connection(BANK_DB_PATH) as conn:
                cur = conn.cursor()

                if bank_row is not None:
                    (
                        bt_trans_id,
                        account_id,
                        del_date,
                        deposit_amt,
                        withdrawal_amt,
                        row_pair_id,
                    ) = bank_row

                    delta = (deposit_amt or 0.0) - (withdrawal_amt or 0.0)

                    # 2a. Null out pair_id on counterpart rows
                    cur.execute(
                        "UPDATE bank_transactions "
                        "SET    pair_id = NULL "
                        "WHERE  pair_id = ?",
                        (bt_trans_id,),
                    )
                    if row_pair_id is not None:
                        cur.execute(
                            "UPDATE bank_transactions "
                            "SET    pair_id = NULL "
                            "WHERE  pair_id = ? AND trans_id != ?",
                            (row_pair_id, bt_trans_id),
                        )

                    # 2b. Delete the bank_transactions row
                    cur.execute(
                        "DELETE FROM bank_transactions WHERE trans_id = ?",
                        (bt_trans_id,),
                    )

                    # 2c. Recalculate balance_after for subsequent rows
                    if delta != 0.0:
                        cur.execute(
                            """
                            UPDATE bank_transactions
                            SET    balance_after = balance_after - ?
                            WHERE  account_id = ?
                              AND  (
                                     trans_date > ?
                                     OR (trans_date = ? AND trans_id > ?)
                                   )
                            """,
                            (
                                delta,
                                account_id,
                                del_date,
                                del_date,
                                bt_trans_id,
                            ),
                        )

                # 2d. Delete the ppf_transactions row itself
                cur.execute(
                    "DELETE FROM ppf_transactions WHERE ppf_trans_id = ?",
                    (ppf_trans_id,),
                )

                conn.commit()

            show_colorful_info(
                mgr_win,
                "Delete Successful",
                f"The PPF transaction for '{ppf_acct}' has been deleted"
                + (
                    " and downstream balances have been recalculated."
                    if bank_row
                    else "."
                ),
            )
            load_data()

        except sqlite3.Error as e:
            show_colorful_error(mgr_win, "Delete Failed", f"Database error: {e}")

    def close_manager() -> None:
        safe_close_modal(mgr_win, parent, calling_button)

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

    _hdr = UI_THEME["bg_header"]
    _foc = UI_THEME["bg_focus"]
    apply_button_animations(edit_btn, _hdr, _foc)
    apply_button_animations(del_btn, _hdr, _foc)
    apply_button_animations(close_btn, _hdr, _foc)

    def on_esc(_event=None):
        close_manager()
        return "break"

    mgr_win.bind("<Escape>", on_esc)
    mgr_win.protocol("WM_DELETE_WINDOW", close_manager)

    parent.wait_window(mgr_win)

    try:
        if parent.winfo_exists():
            parent.grab_set()
    except tk.TclError:
        pass
