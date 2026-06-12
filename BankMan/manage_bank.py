# -*- coding: utf-8 -*-
# File: FinanceManager/BankMan/manage_bank.py

"""
UI module for viewing bank transactions and triggering safe database deletions.

Mirrors the structure and features of StockMan/trade_manager.py:
  • Sortable treeview of all bank_transactions rows.
  • Color-coded rows by entry type (INCOME / EXPENSE / TRANSFER).
  • Edit Selected  — placeholder (inline editing not yet implemented).
  • Delete Selected — removes the main row and its sub-ledger row (if any).
  • Close / Escape  — safe modal teardown.
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
from Shared.gui_utils import apply_button_animations
from .bank_edit import edit_bank
from .bank_transaction_edit import edit_bank_transaction


def show_bank_manager(
    parent: Union[tk.Toplevel, tk.Tk],
    calling_button: tk.Widget | None = None,
) -> None:
    """Open a modal window showing all bank transactions.

    Provides sortable columns, colour-coded entry types, and a Delete
    action that also removes the linked sub-ledger row when present.
    """
    # ------------------------------------------------------------------
    # Modal setup — disable parent so the user cannot interact behind us
    # ------------------------------------------------------------------
    disable_parent(parent, calling_button=calling_button)

    mgr_win = tk.Toplevel(parent)
    mgr_win.title("Bank Manager — Manage / View / Remove")
    mgr_win.geometry("1150x640")
    mgr_win.configure(bg=UI_THEME["bg_input"])
    mgr_win.transient(parent)
    mgr_win.grab_set()
    mgr_win.focus_set()
    push_window(mgr_win, parent)

    # ------------------------------------------------------------------
    # Header banner
    # ------------------------------------------------------------------
    tk.Label(
        mgr_win,
        text="🏦  BANK MANAGER — MANAGE / VIEW / REMOVE",
        font=UI_THEME.get("font_bold", ("Helvetica", 14, "bold")),
        bg=UI_THEME.get("bg_header", "#1e293b"),
        fg=UI_THEME.get("fg_header", "#ffffff"),
        pady=10,
    ).pack(fill="x")

    # ------------------------------------------------------------------
    # Treeview style — reuse the same high-contrast dark palette as
    # trade_manager.py, but under a distinct style name ("BankMgr.*")
    # so the two managers can co-exist without stomping each other's
    # style settings.
    # ------------------------------------------------------------------
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure(
        "BankMgr.Treeview",
        background=UI_THEME.get("charcoal", "#334155"),
        foreground="white",
        fieldbackground=UI_THEME.get("charcoal", "#334155"),
        bordercolor=UI_THEME.get("slate_light", "#475569"),
        rowheight=30,
        font=UI_THEME.get("font_main", ("Helvetica", 12)),
    )
    style.configure(
        "BankMgr.Treeview.Heading",
        background=UI_THEME.get("dark_slate", "#1e293b"),
        foreground=UI_THEME.get("gold", "#FFD700"),
        font=UI_THEME.get("font_bold", ("Helvetica", 12, "bold")),
    )

    # ------------------------------------------------------------------
    # Column-sort helper (click a heading to toggle ascending/descending)
    # ------------------------------------------------------------------
    def sort_by_column(tree: ttk.Treeview, col: str, descending: bool) -> None:
        """Sort *tree* by *col*; toggle direction on next click."""
        data = [(tree.set(child, col), child) for child in tree.get_children("")]

        def _coerce(val: str):
            try:
                # Strip rupee symbol and commas so monetary columns sort
                # numerically rather than lexicographically.
                return float(val.replace("₹", "").replace(",", "").strip())
            except ValueError:
                return val.lower()

        data.sort(key=lambda x: _coerce(x[0]), reverse=descending)

        for index, (_, child) in enumerate(data):
            tree.move(child, "", index)

        # Flip the sort direction for the next click on this heading.
        tree.heading(col, command=lambda c=col: sort_by_column(tree, c, not descending))

    # ------------------------------------------------------------------
    # Treeview and scrollbar
    # ------------------------------------------------------------------
    tree_frame = tk.Frame(mgr_win, bg=UI_THEME["bg_input"], bd=1, relief="ridge")
    tree_frame.pack(fill="both", expand=True, padx=15, pady=15)

    tree_scroll = ttk.Scrollbar(tree_frame)
    tree_scroll.pack(side="right", fill="y")

    cols = (
        "ID",
        "Date",
        "Account",
        "Description",
        "DR",
        "CR",
        "Balance",
        "Type",
    )
    tree = ttk.Treeview(
        tree_frame,
        columns=cols,
        show="headings",
        yscrollcommand=tree_scroll.set,
        style="BankMgr.Treeview",
    )
    tree_scroll.config(command=tree.yview)

    columns_setup = {
        "ID": "ID",
        "Date": "Trans Date",
        "Account": "Account",
        "Description": "Description",
        "DR": "Withdrawal (DR)",
        "CR": "Deposit (CR)",
        "Balance": "Balance After",
        "Type": "Type",
    }
    for col, heading_text in columns_setup.items():
        tree.heading(
            col,
            text=heading_text,
            command=lambda c=col: sort_by_column(tree, c, False),
        )

    # Row colour tags
    tree.tag_configure("income_row", foreground="#4ade80")  # Soft green
    tree.tag_configure("expense_row", foreground="#f87171")  # Soft red
    tree.tag_configure("transfer_row", foreground="#fbbf24")  # Amber

    # Column layout — ID is hidden (zero width)
    tree.column("ID", width=0, stretch=tk.NO)
    tree.column("Date", width=110, anchor="center")
    tree.column("Account", width=240, anchor="w")
    tree.column("Description", width=255, anchor="w")
    tree.column("DR", width=130, anchor="e")
    tree.column("CR", width=130, anchor="e")
    tree.column("Balance", width=130, anchor="e")
    tree.column("Type", width=90, anchor="center")

    tree.pack(fill="both", expand=True)

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------
    def load_data() -> None:
        """Clear the treeview and repopulate from the database."""
        for item in tree.get_children():
            tree.delete(item)
        try:
            with get_db_connection(BANK_DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT  bt.trans_id,
                            bt.trans_date,
                            b.name || '  —  ' || a.ac_number,
                            COALESCE(bt.bank_desc, bt.user_desc, ''),
                            bt.withdrawal_amount,
                            bt.deposit_amount,
                            bt.balance_after,
                            bt.entry_type
                    FROM    bank_transactions bt
                    JOIN    accounts a ON bt.account_id = a.ac_id
                    JOIN    banks    b ON a.b_id = b.b_id
                    ORDER BY bt.trans_date DESC, bt.trans_id DESC
                """)
                for row in cursor.fetchall():
                    entry_type = row[7]
                    if entry_type == "INCOME":
                        row_tag = "income_row"
                    elif entry_type == "EXPENSE":
                        row_tag = "expense_row"
                    else:
                        row_tag = "transfer_row"

                    dr = row[4] or 0.0
                    cr = row[5] or 0.0
                    bal = row[6] or 0.0

                    tree.insert(
                        "",
                        "end",
                        values=(
                            row[0],  # trans_id (hidden)
                            row[1],  # trans_date
                            row[2],  # account label
                            row[3],  # description
                            f"₹ {dr:,.2f}" if dr else "",  # DR (blank when 0)
                            f"₹ {cr:,.2f}" if cr else "",  # CR (blank when 0)
                            f"₹ {bal:,.2f}",  # running balance
                            entry_type,
                        ),
                        tags=(row_tag,),
                    )
        except sqlite3.Error as e:
            logger.error("Failed to load bank transactions: %s", e)

    load_data()

    # ------------------------------------------------------------------
    # Selection helper
    # ------------------------------------------------------------------
    def _get_selected() -> tuple:
        """Return (trans_id, account_label, entry_type) or (None, None, None)."""
        selected = tree.selection()
        if not selected:
            show_colorful_error(
                mgr_win,
                "Selection Error",
                "Please select a transaction from the list first.",
            )
            return None, None, None
        values = tree.item(selected[0])["values"]
        return values[0], values[2], values[7]

    # ------------------------------------------------------------------
    # Edit action — opens the bank master editor
    # ------------------------------------------------------------------
    def _on_edit() -> None:
        edit_bank(mgr_win)

    # ------------------------------------------------------------------
    # Delete action
    # ------------------------------------------------------------------
    def _on_delete() -> None:
        trans_id, account_label, entry_type = _get_selected()
        if trans_id is None:
            return

        # Fetch module linkage before asking the user to confirm — this
        # lets us cascade the delete to the sub-ledger row in one atomic
        # transaction if the user says Yes.
        module_type = module_ref_id = None
        try:
            with get_db_connection(BANK_DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT module_type, module_ref_id "
                    "FROM bank_transactions WHERE trans_id = ?",
                    (trans_id,),
                )
                row = cur.fetchone()
                if row:
                    module_type, module_ref_id = row
        except sqlite3.Error:
            pass

        confirm = show_colorful_yesno(
            mgr_win,
            "Confirm Delete",
            f"Are you sure you want to permanently delete this "
            f"{entry_type} transaction for:\n\n{account_label}?\n\n"
            f"This action cannot be undone.",
        )
        if not confirm:
            return

        try:
            with get_db_connection(BANK_DB_PATH) as conn:
                cur = conn.cursor()

                # Remove the sub-ledger row first (foreign-key cascade is
                # not relied upon here — we do it explicitly so the intent
                # is clear).
                _SUB_LEDGER = {
                    "FD": ("fd_transactions", "fd_trans_id"),
                    "CC": ("cc_transactions", "cc_trans_id"),
                    "LOAN": ("loan_transactions", "loan_trans_id"),
                    "PPF": ("ppf_transactions", "ppf_trans_id"),
                }
                if module_type in _SUB_LEDGER and module_ref_id:
                    tbl, pk = _SUB_LEDGER[module_type]
                    cur.execute(
                        f"DELETE FROM {tbl} WHERE {pk} = ?",
                        (module_ref_id,),
                    )

                # Remove the main transaction row.
                cur.execute(
                    "DELETE FROM bank_transactions WHERE trans_id = ?",
                    (trans_id,),
                )
                conn.commit()

            show_colorful_info(
                mgr_win,
                "Delete Successful",
                f"The {entry_type} transaction for\n{account_label}\n"
                f"has been permanently deleted.",
            )
            load_data()

        except sqlite3.Error as e:
            show_colorful_error(mgr_win, "Delete Failed", f"Database error: {e}")

    # ------------------------------------------------------------------
    # Close helper
    # ------------------------------------------------------------------
    def close_manager() -> None:
        safe_close_modal(mgr_win, parent, calling_button)

    # ------------------------------------------------------------------
    # Footer buttons — same layout as trade_manager.py
    # ------------------------------------------------------------------
    btn_frame = tk.Frame(mgr_win, bg=UI_THEME["bg_input"])
    btn_frame.pack(fill="x", padx=15, pady=(0, 15))

    edit_btn = tk.Button(
        btn_frame,
        text="✏️ Edit Bank",
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

    # ------------------------------------------------------------------
    # Keyboard and window-close bindings
    # ------------------------------------------------------------------
    def on_esc(_event=None):
        close_manager()
        return "break"

    mgr_win.bind("<Escape>", on_esc)
    mgr_win.protocol("WM_DELETE_WINDOW", close_manager)

    parent.wait_window(mgr_win)

    # CRITICAL: Restore grab to the caller so it doesn't fall out of focus.
    try:
        if parent.winfo_exists():
            parent.grab_set()
    except tk.TclError:
        pass


# ---------------------------------------------------------------------------
# Bank Transactions Manager
# ---------------------------------------------------------------------------


def show_bank_transactions_manager(
    parent: Union[tk.Toplevel, tk.Tk],
    calling_button: tk.Widget | None = None,
) -> None:
    """Open a modal window showing all bank_transactions rows.

    Full feature parity with StockMan/trade_manager.show_trade_manager:
      • Sortable columns (click any heading to toggle asc/desc).
      • Colour-coded rows: INCOME green, EXPENSE red, TRANSFER amber.
      • Hidden primary-key column used by Edit/Delete without showing the ID.
      • Edit Selected — informs the user editing is not yet implemented.
      • Delete Selected —
          1. Removes the linked sub-ledger row (FD / CC / LOAN / PPF).
          2. Nulls out pair_id on every row that referenced the deleted
             trans_id (either as a direct pointer or as a shared group id).
          3. Recalculates balance_after for every subsequent transaction
             in the same account so the running total stays correct.
      • Escape key and window-close button both call the safe-close helper.
      • grab_set restored on parent after the modal closes.
    """
    # ------------------------------------------------------------------
    # Modal setup
    # ------------------------------------------------------------------
    disable_parent(parent, calling_button=calling_button)

    mgr_win = tk.Toplevel(parent)
    mgr_win.title("Bank Transactions Manager — Manage / Edit / Remove")
    mgr_win.geometry("1150x640")
    mgr_win.configure(bg=UI_THEME["bg_input"])
    mgr_win.transient(parent)
    mgr_win.grab_set()
    mgr_win.focus_set()
    push_window(mgr_win, parent)

    # ------------------------------------------------------------------
    # Header banner
    # ------------------------------------------------------------------
    tk.Label(
        mgr_win,
        text="🏦  BANK TRANSACTIONS MANAGER — MANAGE / EDIT / REMOVE",
        font=UI_THEME.get("font_bold", ("Helvetica", 14, "bold")),
        bg=UI_THEME.get("bg_header", "#1e293b"),
        fg=UI_THEME.get("fg_header", "#ffffff"),
        pady=10,
    ).pack(fill="x")

    # ------------------------------------------------------------------
    # Treeview theming (distinct style name so it won't clash with
    # BankMgr.Treeview defined in show_bank_manager above).
    # ------------------------------------------------------------------
    style = ttk.Style()
    if "clam" not in style.theme_names():
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

    style.configure(
        "BankTxMgr.Treeview",
        background=UI_THEME.get("charcoal", "#334155"),
        foreground="white",
        fieldbackground=UI_THEME.get("charcoal", "#334155"),
        bordercolor=UI_THEME.get("slate_light", "#475569"),
        rowheight=30,
        font=UI_THEME.get("font_main", ("Helvetica", 12)),
    )
    style.configure(
        "BankTxMgr.Treeview.Heading",
        background=UI_THEME.get("dark_slate", "#1e293b"),
        foreground=UI_THEME.get("gold", "#FFD700"),
        font=UI_THEME.get("font_bold", ("Helvetica", 12, "bold")),
    )

    # ------------------------------------------------------------------
    # Column-sort helper — mirrors trade_manager exactly
    # ------------------------------------------------------------------
    def sort_by_column(tree: ttk.Treeview, col: str, descending: bool) -> None:
        """Sort *tree* by *col*; toggle direction on next click."""
        data = [(tree.set(child, col), child) for child in tree.get_children("")]

        def _coerce(val: str):
            try:
                # Strip ₹ / commas so monetary columns sort numerically.
                return float(val.replace("₹", "").replace(",", "").strip())
            except ValueError:
                return val.lower()

        data.sort(key=lambda x: _coerce(x[0]), reverse=descending)

        for index, (_, child) in enumerate(data):
            tree.move(child, "", index)

        tree.heading(
            col,
            command=lambda c=col: sort_by_column(tree, c, not descending),
        )

    # ------------------------------------------------------------------
    # Treeview + scrollbar
    # ------------------------------------------------------------------
    tree_frame = tk.Frame(mgr_win, bg=UI_THEME["bg_input"], bd=1, relief="ridge")
    tree_frame.pack(fill="both", expand=True, padx=15, pady=15)

    tree_scroll = ttk.Scrollbar(tree_frame)
    tree_scroll.pack(side="right", fill="y")

    cols = (
        "ID",
        "Date",
        "Account",
        "Description",
        "DR",
        "CR",
        "Balance",
        "Type",
    )
    tree = ttk.Treeview(
        tree_frame,
        columns=cols,
        show="headings",
        yscrollcommand=tree_scroll.set,
        style="BankTxMgr.Treeview",
    )
    tree_scroll.config(command=tree.yview)

    columns_setup = {
        "ID": "ID",
        "Date": "Trans Date",
        "Account": "Account",
        "Description": "Description / Narration",
        "DR": "Withdrawal (DR)",
        "CR": "Deposit (CR)",
        "Balance": "Balance After",
        "Type": "Type",
    }
    for col, heading_text in columns_setup.items():
        tree.heading(
            col,
            text=heading_text,
            command=lambda c=col: sort_by_column(tree, c, False),
        )

    # Row colour tags — same palette as trade_manager
    tree.tag_configure("income_row", foreground="#4ade80")  # green
    tree.tag_configure("expense_row", foreground="#f87171")  # red
    tree.tag_configure("transfer_row", foreground="#fbbf24")  # amber

    # Column widths — ID hidden
    tree.column("ID", width=0, stretch=tk.NO)
    tree.column("Date", width=110, anchor="center")
    tree.column("Account", width=235, anchor="w")
    tree.column("Description", width=255, anchor="w")
    tree.column("DR", width=125, anchor="e")
    tree.column("CR", width=125, anchor="e")
    tree.column("Balance", width=130, anchor="e")
    tree.column("Type", width=90, anchor="center")

    tree.pack(fill="both", expand=True)

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------
    def load_data() -> None:
        """Clear the treeview and repopulate from bank_transactions."""
        for item in tree.get_children():
            tree.delete(item)
        try:
            with get_db_connection(BANK_DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT  bt.trans_id,
                            bt.trans_date,
                            b.name || '  —  ' || a.ac_number,
                            COALESCE(bt.bank_desc, bt.user_desc, ''),
                            bt.withdrawal_amount,
                            bt.deposit_amount,
                            bt.balance_after,
                            bt.entry_type
                    FROM    bank_transactions bt
                    JOIN    accounts a ON bt.account_id = a.ac_id
                    JOIN    banks    b ON a.b_id = b.b_id
                    ORDER BY bt.trans_date DESC, bt.trans_id DESC
                """)
                for row in cursor.fetchall():
                    entry_type = row[7]
                    if entry_type == "INCOME":
                        row_tag = "income_row"
                    elif entry_type == "EXPENSE":
                        row_tag = "expense_row"
                    else:
                        row_tag = "transfer_row"

                    dr = row[4] or 0.0
                    cr = row[5] or 0.0
                    bal = row[6] or 0.0

                    tree.insert(
                        "",
                        "end",
                        values=(
                            row[0],
                            row[1],
                            row[2],
                            row[3],
                            f"₹ {dr:,.2f}" if dr else "",
                            f"₹ {cr:,.2f}" if cr else "",
                            f"₹ {bal:,.2f}",
                            entry_type,
                        ),
                        tags=(row_tag,),
                    )
        except sqlite3.Error as e:
            logger.error("Failed to load bank transactions: %s", e)

    load_data()

    # ------------------------------------------------------------------
    # Selection helper — mirrors _get_selected_trd_id in trade_manager
    # ------------------------------------------------------------------
    def _get_selected() -> tuple:
        """Return (trans_id, account_label, entry_type) or (None, None, None)."""
        selected = tree.selection()
        if not selected:
            show_colorful_error(
                mgr_win,
                "Selection Error",
                "Please select a transaction from the list first.",
            )
            return None, None, None
        values = tree.item(selected[0])["values"]
        return values[0], values[2], values[7]

    # ------------------------------------------------------------------
    # Edit action
    # ------------------------------------------------------------------
    def _on_edit() -> None:
        trans_id, _, _ = _get_selected()
        if trans_id is None:
            return
        edit_bank_transaction(mgr_win, trans_id)
        load_data()  # refresh treeview after the edit modal closes

    # ------------------------------------------------------------------
    # Delete action
    # ------------------------------------------------------------------
    def _on_delete() -> None:
        trans_id, account_label, entry_type = _get_selected()
        if trans_id is None:
            return

        # ── Step 1: fetch everything we need before touching the DB ────
        row_data = None
        try:
            with get_db_connection(BANK_DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT account_id,
                           trans_date,
                           deposit_amount,
                           withdrawal_amount,
                           pair_id,
                           module_type,
                           module_ref_id
                    FROM   bank_transactions
                    WHERE  trans_id = ?
                    """,
                    (trans_id,),
                )
                row_data = cur.fetchone()
        except sqlite3.Error as e:
            show_colorful_error(
                mgr_win, "Error", f"Could not fetch transaction details: {e}"
            )
            return

        if row_data is None:
            show_colorful_error(
                mgr_win, "Error", "Transaction not found in the database."
            )
            return

        (
            account_id,
            del_date,
            deposit_amt,
            withdrawal_amt,
            row_pair_id,
            module_type,
            module_ref_id,
        ) = row_data

        # Net effect this row had on the running balance.
        # Positive  → account went up   (we must subtract it downstream).
        # Negative  → account went down (we must add it back downstream).
        delta = (deposit_amt or 0.0) - (withdrawal_amt or 0.0)

        # ── Step 2: confirm ────────────────────────────────────────────
        confirm = show_colorful_yesno(
            mgr_win,
            "Confirm Delete",
            f"Are you sure you want to permanently delete this "
            f"{entry_type} transaction for:\n\n"
            f"{account_label}\n\n"
            f"This will also:\n"
            f"  • Remove any linked sub-ledger entry (FD / CC / Loan / PPF).\n"
            f"  • Clear pair references on the transfer counterpart.\n"
            f"  • Recalculate all subsequent balances for this account.\n\n"
            f"This action cannot be undone.",
        )
        if not confirm:
            return

        # ── Step 3: execute all DB changes in one connection ───────────
        _SUB_LEDGER = {
            "FD": ("fd_transactions", "fd_trans_id"),
            "CC": ("cc_transactions", "cc_trans_id"),
            "LOAN": ("loan_transactions", "loan_trans_id"),
            "PPF": ("ppf_transactions", "ppf_trans_id"),
        }

        try:
            with get_db_connection(BANK_DB_PATH) as conn:
                cur = conn.cursor()

                # 3a. Remove the sub-ledger row (if any).
                if module_type in _SUB_LEDGER and module_ref_id:
                    tbl, pk = _SUB_LEDGER[module_type]
                    cur.execute(
                        f"DELETE FROM {tbl} WHERE {pk} = ?",
                        (module_ref_id,),
                    )

                # 3b. Null out pair_id references.
                #
                # Two cases handled:
                #   (i)  Another row has pair_id = deleted trans_id  → direct
                #        pointer to this specific row (common convention).
                #   (ii) This row's own pair_id is non-NULL          → both
                #        sides share the same group value; orphan the partner.
                cur.execute(
                    "UPDATE bank_transactions "
                    "SET    pair_id = NULL "
                    "WHERE  pair_id = ?",
                    (trans_id,),
                )
                if row_pair_id is not None:
                    cur.execute(
                        "UPDATE bank_transactions "
                        "SET    pair_id = NULL "
                        "WHERE  pair_id = ? AND trans_id != ?",
                        (row_pair_id, trans_id),
                    )

                # 3c. Delete the main row.
                cur.execute(
                    "DELETE FROM bank_transactions WHERE trans_id = ?",
                    (trans_id,),
                )

                # 3d. Recalculate balance_after for every subsequent
                #     transaction in the same account.
                #
                #     "Subsequent" is defined by the natural ledger order:
                #     (trans_date ASC, trans_id ASC).  Any row that comes
                #     after the deleted one is affected by exactly `delta`.
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
                        (delta, account_id, del_date, del_date, trans_id),
                    )

                conn.commit()

            show_colorful_info(
                mgr_win,
                "Delete Successful",
                f"The {entry_type} transaction for\n{account_label}\n"
                f"has been deleted and downstream balances have been "
                f"recalculated.",
            )
            load_data()

        except sqlite3.Error as e:
            show_colorful_error(mgr_win, "Delete Failed", f"Database error: {e}")

    # ------------------------------------------------------------------
    # Close helper
    # ------------------------------------------------------------------
    def close_manager() -> None:
        safe_close_modal(mgr_win, parent, calling_button)

    # ------------------------------------------------------------------
    # Footer buttons — same layout as trade_manager.py
    # ------------------------------------------------------------------
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

    apply_button_animations(edit_btn, UI_THEME["bg_header"], UI_THEME["bg_focus"])
    apply_button_animations(del_btn, UI_THEME["bg_header"], UI_THEME["bg_focus"])
    apply_button_animations(close_btn, UI_THEME["bg_header"], UI_THEME["bg_focus"])

    # ------------------------------------------------------------------
    # Keyboard and window-close bindings — mirrors trade_manager exactly
    # ------------------------------------------------------------------
    def on_esc(_event=None):
        close_manager()
        return "break"  # stop the event reaching the parent window

    mgr_win.bind("<Escape>", on_esc)
    mgr_win.protocol("WM_DELETE_WINDOW", close_manager)

    parent.wait_window(mgr_win)

    # CRITICAL: Restore grab to the calling window so it stays in focus.
    try:
        if parent.winfo_exists():
            parent.grab_set()
    except tk.TclError:
        pass
