# -*- coding: utf-8 -*-
# File: FinanceManager/BankMan/manage_loan.py

"""
UI module for viewing and managing Loan master records and transactions.

Mirrors the structure and features of StockMan/trade_manager.py and
BankMan/manage_bank.py:
  * Sortable treeview (click any heading to toggle ascending/descending).
  * Colour-coded rows.
  * Edit Selected -- placeholder (inline editing not yet implemented).
  * Delete Selected -- removes the row and cascades required changes.
  * Close / Escape -- safe modal teardown via safe_close_modal.

Two public functions are exposed:

  show_loan_manager(parent, calling_button=None)
      Displays all loan_master rows.  Deleting a loan is blocked when
      loan_transactions reference it (ON DELETE RESTRICT in the schema).

  show_loan_transactions_manager(parent, calling_button=None)
      Displays all loan_transactions rows.  Deleting a row also:
        1. Finds and removes the linked bank_transactions row
           (module_type='LOAN', module_ref_id=loan_trans_id).
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
# 1.  show_loan_manager  --  loan_master rows
# ===========================================================================


def show_loan_manager(
    parent: Union[tk.Toplevel, tk.Tk],
    calling_button: tk.Widget | None = None,
) -> None:
    """Open a modal window showing all loan_master records.

    Features
    --------
    * Sortable columns -- click any heading to toggle ascending/descending.
    * Colour-coded rows: active loans in green, closed loans in red.
    * Hidden primary-key column used by Edit/Delete without exposing IDs.
    * Edit Selected   -- informs the user editing is not yet available.
    * Delete Selected -- removes the loan from loan_master.  Blocked by
                         the database RESTRICT constraint when linked
                         loan_transactions rows exist.
    * Escape key and window-close button invoke the safe-close helper.
    * grab_set is restored on *parent* after the modal closes.
    """
    disable_parent(parent, calling_button=calling_button)

    mgr_win = tk.Toplevel(parent)
    mgr_win.title("Loan Master Manager — Manage / View / Remove")
    mgr_win.geometry("1150x560")
    mgr_win.configure(bg=UI_THEME["bg_input"])
    mgr_win.transient(parent)
    mgr_win.grab_set()
    mgr_win.focus_set()
    push_window(mgr_win, parent)

    tk.Label(
        mgr_win,
        text="🏦  LOAN MASTER MANAGER — MANAGE / VIEW / REMOVE",
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
        "LoanMgr.Treeview",
        background=UI_THEME.get("charcoal", "#334155"),
        foreground="white",
        fieldbackground=UI_THEME.get("charcoal", "#334155"),
        bordercolor=UI_THEME.get("slate_light", "#475569"),
        rowheight=30,
        font=UI_THEME.get("font_main", ("Helvetica", 12)),
    )
    style.configure(
        "LoanMgr.Treeview.Heading",
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
        "Loan Type",
        "Loan Account No.",
        "Bank",
        "Principal",
        "Rate %",
        "EMI",
        "Start Date",
        "End Date",
        "Active",
    )
    tree = ttk.Treeview(
        tree_frame,
        columns=cols,
        show="headings",
        yscrollcommand=tree_scroll.set,
        style="LoanMgr.Treeview",
    )
    tree_scroll.config(command=tree.yview)

    columns_setup = {
        "ID": "ID",
        "Loan Type": "Loan Type",
        "Loan Account No.": "Loan Account No.",
        "Bank": "Bank",
        "Principal": "Principal (₹)",
        "Rate %": "Rate %",
        "EMI": "EMI (₹)",
        "Start Date": "Start Date",
        "End Date": "End Date",
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
    tree.column("Loan Type", width=140, anchor="w")
    tree.column("Loan Account No.", width=170, anchor="w")
    tree.column("Bank", width=160, anchor="w")
    tree.column("Principal", width=130, anchor="e")
    tree.column("Rate %", width=75, anchor="center")
    tree.column("EMI", width=120, anchor="e")
    tree.column("Start Date", width=105, anchor="center")
    tree.column("End Date", width=105, anchor="center")
    tree.column("Active", width=65, anchor="center")

    tree.pack(fill="both", expand=True)

    def load_data() -> None:
        """Clear the treeview and repopulate from loan_master."""
        for item in tree.get_children():
            tree.delete(item)
        try:
            with get_db_connection(BANK_DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT  lm.loan_master_id,
                            lm.loan_type,
                            lm.loan_account_number,
                            b.name,
                            lm.principal_amount,
                            lm.interest_rate,
                            lm.emi_amount,
                            lm.start_dt,
                            lm.end_dt,
                            lm.is_active
                    FROM    loan_master lm
                    JOIN    accounts a ON a.ac_id = lm.account_id
                    JOIN    banks    b ON b.b_id  = a.b_id
                    ORDER BY b.name, lm.loan_type, lm.loan_account_number
                """)
                for row in cursor.fetchall():
                    is_active = row[9]
                    row_tag = "active_row" if is_active else "inactive_row"
                    tree.insert(
                        "",
                        "end",
                        values=(
                            row[0],  # loan_master_id (hidden)
                            row[1],  # loan_type
                            row[2],  # loan_account_number
                            row[3],  # bank name
                            f"₹ {row[4]:,.2f}",  # principal_amount
                            f"{row[5]:.2f}",  # interest_rate
                            f"₹ {row[6]:,.2f}",  # emi_amount
                            row[7],  # start_dt
                            row[8],  # end_dt
                            "Yes" if is_active else "No",
                        ),
                        tags=(row_tag,),
                    )
        except sqlite3.Error as e:
            logger.error("Failed to load loan_master rows: %s", e)

    load_data()

    def _get_selected() -> tuple:
        """Return (loan_master_id, loan_account_number) or (None, None)."""
        selected = tree.selection()
        if not selected:
            show_colorful_error(
                mgr_win,
                "Selection Error",
                "Please select a loan from the list first.",
            )
            return None, None
        values = tree.item(selected[0])["values"]
        return values[0], values[2]

    def _on_edit() -> None:
        loan_id, _ = _get_selected()
        if loan_id is None:
            return
        show_colorful_info(
            mgr_win,
            "Edit Not Yet Available",
            "Inline editing of loan master records is not yet implemented.\n\n"
            "To correct a record, delete it and re-enter with the correct "
            "values.",
        )

    def _on_delete() -> None:
        loan_id, loan_acct = _get_selected()
        if loan_id is None:
            return

        tx_count = 0
        try:
            with get_db_connection(BANK_DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT COUNT(*) FROM loan_transactions "
                    "WHERE loan_master_id = ?",
                    (loan_id,),
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
                f"Loan '{loan_acct}' has {tx_count} linked transaction(s).\n\n"
                f"Delete all loan_transactions for this loan before removing "
                f"the loan record.",
            )
            return

        confirm = show_colorful_yesno(
            mgr_win,
            "Confirm Delete",
            f"Are you sure you want to permanently delete the loan:\n\n"
            f"  {loan_acct}\n\n"
            f"This action cannot be undone.",
        )
        if not confirm:
            return

        try:
            with get_db_connection(BANK_DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("PRAGMA foreign_keys = ON;")
                cur.execute(
                    "DELETE FROM loan_master WHERE loan_master_id = ?",
                    (loan_id,),
                )
                conn.commit()
            show_colorful_info(
                mgr_win,
                "Delete Successful",
                f"The loan '{loan_acct}' has been permanently deleted.",
            )
            load_data()
        except sqlite3.IntegrityError as e:
            show_colorful_error(
                mgr_win,
                "Delete Blocked",
                f"Could not delete loan '{loan_acct}' — it is still "
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
# 2.  show_loan_transactions_manager  --  loan_transactions rows
# ===========================================================================


def show_loan_transactions_manager(
    parent: Union[tk.Toplevel, tk.Tk],
    calling_button: tk.Widget | None = None,
) -> None:
    """Open a modal window showing all loan_transactions rows.

    Features
    --------
    * Sortable columns -- click any heading to toggle ascending/descending.
    * Colour-coded rows: credit rows in green, payment/EMI rows in red.
    * Hidden primary-key column used by Edit/Delete without exposing IDs.
    * Edit Selected   -- informs the user editing is not yet available.
    * Delete Selected -- removes the loan_transactions row and also:
        1. Finds the linked bank_transactions row
           (module_type='LOAN', module_ref_id=loan_trans_id) and deletes it.
        2. Nulls out pair_id references on the transfer counterpart.
        3. Recalculates balance_after for every subsequent transaction in
           the same bank account so the running total stays correct.
    * Escape key and window-close button invoke the safe-close helper.
    * grab_set is restored on *parent* after the modal closes.
    """
    disable_parent(parent, calling_button=calling_button)

    mgr_win = tk.Toplevel(parent)
    mgr_win.title("Loan Transactions Manager — Manage / View / Remove")
    mgr_win.geometry("1250x640")
    mgr_win.configure(bg=UI_THEME["bg_input"])
    mgr_win.transient(parent)
    mgr_win.grab_set()
    mgr_win.focus_set()
    push_window(mgr_win, parent)

    tk.Label(
        mgr_win,
        text="🏦  LOAN TRANSACTIONS MANAGER — MANAGE / VIEW / REMOVE",
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
        "LoanTxMgr.Treeview",
        background=UI_THEME.get("charcoal", "#334155"),
        foreground="white",
        fieldbackground=UI_THEME.get("charcoal", "#334155"),
        bordercolor=UI_THEME.get("slate_light", "#475569"),
        rowheight=30,
        font=UI_THEME.get("font_main", ("Helvetica", 12)),
    )
    style.configure(
        "LoanTxMgr.Treeview.Heading",
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
        "Loan Account",
        "Description",
        "Payment",
        "Principal",
        "Interest",
        "Charges",
        "Credit",
        "Principal Due",
    )
    tree = ttk.Treeview(
        tree_frame,
        columns=cols,
        show="headings",
        yscrollcommand=tree_scroll.set,
        style="LoanTxMgr.Treeview",
    )
    tree_scroll.config(command=tree.yview)

    columns_setup = {
        "ID": "ID",
        "Date": "Trans Date",
        "Loan Account": "Loan Account",
        "Description": "Description",
        "Payment": "Payment (DR)",
        "Principal": "Principal",
        "Interest": "Interest",
        "Charges": "Charges",
        "Credit": "Credit (CR)",
        "Principal Due": "Principal Due",
    }
    for col, heading_text in columns_setup.items():
        tree.heading(
            col,
            text=heading_text,
            command=lambda c=col: universal_tree_sort(tree, c, False),
        )

    # credit rows (loan_credit > 0) in green; repayment rows in red
    tree.tag_configure("credit_row", foreground="#4ade80")  # green
    tree.tag_configure("payment_row", foreground="#f87171")  # red

    tree.column("ID", width=0, stretch=tk.NO)
    tree.column("Date", width=105, anchor="center")
    tree.column("Loan Account", width=170, anchor="w")
    tree.column("Description", width=175, anchor="w")
    tree.column("Payment", width=115, anchor="e")
    tree.column("Principal", width=110, anchor="e")
    tree.column("Interest", width=110, anchor="e")
    tree.column("Charges", width=90, anchor="e")
    tree.column("Credit", width=110, anchor="e")
    tree.column("Principal Due", width=120, anchor="e")

    tree.pack(fill="both", expand=True)

    def load_data() -> None:
        """Clear the treeview and repopulate from loan_transactions."""
        for item in tree.get_children():
            tree.delete(item)
        try:
            with get_db_connection(BANK_DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT  lt.loan_trans_id,
                            lt.loan_trans_dt,
                            lm.loan_account_number,
                            COALESCE(lt.loan_description, ''),
                            lt.loan_payment,
                            lt.principal,
                            lt.interest,
                            lt.charges,
                            lt.loan_credit,
                            lt.principal_due
                    FROM    loan_transactions lt
                    JOIN    loan_master lm
                            ON lm.loan_master_id = lt.loan_master_id
                    ORDER BY lt.loan_trans_dt DESC, lt.loan_trans_id DESC
                """)
                for row in cursor.fetchall():
                    payment = row[4] or 0.0
                    principal = row[5] or 0.0
                    interest = row[6] or 0.0
                    charges = row[7] or 0.0
                    credit = row[8] or 0.0
                    prin_due = row[9] or 0.0
                    row_tag = (
                        "credit_row"
                        if credit > 0.0 and payment == 0.0
                        else "payment_row"
                    )
                    tree.insert(
                        "",
                        "end",
                        values=(
                            row[0],
                            row[1],
                            row[2],
                            row[3],
                            f"₹ {payment:,.2f}" if payment else "",
                            f"₹ {principal:,.2f}" if principal else "",
                            f"₹ {interest:,.2f}" if interest else "",
                            f"₹ {charges:,.2f}" if charges else "",
                            f"₹ {credit:,.2f}" if credit else "",
                            f"₹ {prin_due:,.2f}",
                        ),
                        tags=(row_tag,),
                    )
        except sqlite3.Error as e:
            logger.error("Failed to load loan_transactions rows: %s", e)

    load_data()

    def _get_selected() -> tuple:
        """Return (loan_trans_id, loan_account, description) or Nones."""
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
        loan_trans_id, _, _ = _get_selected()
        if loan_trans_id is None:
            return
        show_colorful_info(
            mgr_win,
            "Edit Not Yet Available",
            "Inline editing of loan transactions is not yet implemented.\n\n"
            "To correct a transaction, delete it and re-enter with the "
            "correct values.",
        )

    def _on_delete() -> None:
        loan_trans_id, loan_acct, description = _get_selected()
        if loan_trans_id is None:
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
                    WHERE   module_type   = 'LOAN'
                      AND   module_ref_id = ?
                    """,
                    (loan_trans_id,),
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
            f"Permanently delete this loan transaction?\n\n"
            f"  Loan   : {loan_acct}\n"
            f"  Narration: {description}"
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

                # 2d. Delete the loan_transactions row itself
                cur.execute(
                    "DELETE FROM loan_transactions WHERE loan_trans_id = ?",
                    (loan_trans_id,),
                )

                conn.commit()

            show_colorful_info(
                mgr_win,
                "Delete Successful",
                f"The loan transaction for '{loan_acct}' has been deleted"
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
