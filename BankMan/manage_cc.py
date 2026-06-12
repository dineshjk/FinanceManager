# -*- coding: utf-8 -*-
# File: FinanceManager/BankMan/manage_cc.py

"""
UI module for viewing and managing Credit Card master records and transactions.

Mirrors the structure and features of StockMan/trade_manager.py and
BankMan/manage_bank.py:
  • Sortable treeview (click any heading to toggle ascending/descending).
  • Colour-coded rows.
  • Edit Selected — placeholder (inline editing not yet implemented).
  • Delete Selected — removes the row and cascades required changes.
  • Close / Escape — safe modal teardown via safe_close_modal.

Two public functions are exposed:

  show_cc_manager(parent, calling_button=None)
      Displays all card_master rows.  Deleting a card is blocked when
      cc_transactions reference it (ON DELETE RESTRICT in the schema).

  show_cc_transactions_manager(parent, calling_button=None)
      Displays all cc_transactions rows.  Deleting a row also:
        1. Finds and removes the linked bank_transactions row
           (module_type='CC', module_ref_id=cc_trans_id).
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
from Shared.gui_utils import apply_button_animations

# ---------------------------------------------------------------------------
# Internal sort helper (shared by both managers)
# ---------------------------------------------------------------------------


def _make_sort_fn(tree: ttk.Treeview, col: str, descending: bool):
    """Return a command that sorts *tree* by *col* and flips direction."""

    def _sort():
        data = [(tree.set(child, col), child) for child in tree.get_children("")]

        def _coerce(val: str):
            try:
                return float(val.replace("₹", "").replace(",", "").strip())
            except ValueError:
                return val.lower()

        data.sort(key=lambda x: _coerce(x[0]), reverse=descending)

        for index, (_, child) in enumerate(data):
            tree.move(child, "", index)

        tree.heading(col, command=_make_sort_fn(tree, col, not descending))

    return _sort


# ===========================================================================
# 1.  show_cc_manager  —  card_master rows
# ===========================================================================


def show_cc_manager(
    parent: Union[tk.Toplevel, tk.Tk],
    calling_button: tk.Widget | None = None,
) -> None:
    """Open a modal window showing all card_master (Credit Card) records.

    Features
    --------
    • Sortable columns — click any heading to toggle ascending / descending.
    • Colour-coded rows: active cards in green, inactive cards in red.
    • Hidden primary-key column used by Edit / Delete without exposing IDs.
    • Edit Selected    — informs the user that editing is not yet available.
    • Delete Selected  — removes the card from card_master.  If the card has
                         associated cc_transactions the database RESTRICT
                         constraint will block the delete and the user is
                         informed of the reason.
    • Escape key and window-close button both invoke the safe-close helper.
    • grab_set is restored on *parent* after the modal closes.
    """
    # ------------------------------------------------------------------
    # Modal setup
    # ------------------------------------------------------------------
    disable_parent(parent, calling_button=calling_button)

    mgr_win = tk.Toplevel(parent)
    mgr_win.title("CC Card Manager — Manage / View / Remove")
    mgr_win.geometry("1050x560")
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
        text="💳  CC CARD MANAGER — MANAGE / VIEW / REMOVE",
        font=UI_THEME.get("font_bold", ("Helvetica", 14, "bold")),
        bg=UI_THEME.get("bg_header", "#1e293b"),
        fg=UI_THEME.get("fg_header", "#ffffff"),
        pady=10,
    ).pack(fill="x")

    # ------------------------------------------------------------------
    # Treeview style — distinct name so it won't clash with other managers
    # ------------------------------------------------------------------
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure(
        "CCMgr.Treeview",
        background=UI_THEME.get("charcoal", "#334155"),
        foreground="white",
        fieldbackground=UI_THEME.get("charcoal", "#334155"),
        bordercolor=UI_THEME.get("slate_light", "#475569"),
        rowheight=30,
        font=UI_THEME.get("font_main", ("Helvetica", 12)),
    )
    style.configure(
        "CCMgr.Treeview.Heading",
        background=UI_THEME.get("dark_slate", "#1e293b"),
        foreground=UI_THEME.get("gold", "#FFD700"),
        font=UI_THEME.get("font_bold", ("Helvetica", 12, "bold")),
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
        "Card Name",
        "Card Number",
        "Bank",
        "Account",
        "Credit Limit",
        "Billing Day",
        "Active",
    )
    tree = ttk.Treeview(
        tree_frame,
        columns=cols,
        show="headings",
        yscrollcommand=tree_scroll.set,
        style="CCMgr.Treeview",
    )
    tree_scroll.config(command=tree.yview)

    columns_setup = {
        "ID": "ID",
        "Card Name": "Card Name",
        "Card Number": "Card Number",
        "Bank": "Bank",
        "Account": "Account No.",
        "Credit Limit": "Credit Limit (₹)",
        "Billing Day": "Billing Day",
        "Active": "Active",
    }
    for col, heading_text in columns_setup.items():
        tree.heading(
            col,
            text=heading_text,
            command=_make_sort_fn(tree, col, False),
        )

    # Row colour tags
    tree.tag_configure("active_row", foreground="#4ade80")  # green — active card
    tree.tag_configure(
        "inactive_row", foreground="#f87171"
    )  # red   — cancelled / expired

    # Column layout — ID is hidden (zero width)
    tree.column("ID", width=0, stretch=tk.NO)
    tree.column("Card Name", width=220, anchor="w")
    tree.column("Card Number", width=130, anchor="center")
    tree.column("Bank", width=180, anchor="w")
    tree.column("Account", width=150, anchor="center")
    tree.column("Credit Limit", width=150, anchor="e")
    tree.column("Billing Day", width=100, anchor="center")
    tree.column("Active", width=70, anchor="center")

    tree.pack(fill="both", expand=True)

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------
    def load_data() -> None:
        """Clear the treeview and repopulate from card_master."""
        for item in tree.get_children():
            tree.delete(item)
        try:
            with get_db_connection(BANK_DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT  cm.card_master_id,
                            cm.card_name,
                            cm.card_number,
                            b.name,
                            a.ac_number,
                            cm.credit_limit,
                            cm.billing_cycle_day,
                            cm.is_active
                    FROM    card_master cm
                    JOIN    accounts a ON a.ac_id = cm.account_id
                    JOIN    banks    b ON b.b_id  = a.b_id
                    ORDER BY b.name, cm.card_name
                """)
                for row in cursor.fetchall():
                    is_active = row[7]
                    row_tag = "active_row" if is_active else "inactive_row"
                    active_label = "Yes" if is_active else "No"
                    tree.insert(
                        "",
                        "end",
                        values=(
                            row[0],  # card_master_id (hidden)
                            row[1],  # card_name
                            row[2],  # card_number
                            row[3],  # bank name
                            row[4],  # ac_number
                            f"₹ {row[5]:,.2f}",  # credit_limit
                            row[6],  # billing_cycle_day
                            active_label,
                        ),
                        tags=(row_tag,),
                    )
        except sqlite3.Error as e:
            logger.error("Failed to load card_master rows: %s", e)

    load_data()

    # ------------------------------------------------------------------
    # Selection helper
    # ------------------------------------------------------------------
    def _get_selected() -> tuple:
        """Return (card_master_id, card_name, is_active_str) or (None, None, None)."""
        selected = tree.selection()
        if not selected:
            show_colorful_error(
                mgr_win,
                "Selection Error",
                "Please select a card from the list first.",
            )
            return None, None, None
        values = tree.item(selected[0])["values"]
        return values[0], values[1], values[7]

    # ------------------------------------------------------------------
    # Edit action
    # ------------------------------------------------------------------
    def _on_edit() -> None:
        card_id, _, _ = _get_selected()
        if card_id is None:
            return
        show_colorful_info(
            mgr_win,
            "Edit Not Yet Available",
            "Inline editing of credit card master records is not yet "
            "implemented.\n\nTo correct a record, delete it and re-enter "
            "with the correct values.",
        )

    # ------------------------------------------------------------------
    # Delete action
    # ------------------------------------------------------------------
    def _on_delete() -> None:
        card_id, card_name, _ = _get_selected()
        if card_id is None:
            return

        # Count linked cc_transactions so we can warn the user up-front.
        tx_count = 0
        try:
            with get_db_connection(BANK_DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT COUNT(*) FROM cc_transactions WHERE card_master_id = ?",
                    (card_id,),
                )
                row = cur.fetchone()
                if row:
                    tx_count = row[0]
        except sqlite3.Error as e:
            show_colorful_error(
                mgr_win, "Error", f"Could not check linked transactions: {e}"
            )
            return

        if tx_count > 0:
            show_colorful_error(
                mgr_win,
                "Cannot Delete",
                f"'{card_name}' has {tx_count} linked transaction(s).\n\n"
                f"Delete or reassign all cc_transactions for this card "
                f"before removing the card record.",
            )
            return

        confirm = show_colorful_yesno(
            mgr_win,
            "Confirm Delete",
            f"Are you sure you want to permanently delete the card:\n\n"
            f"  {card_name}\n\n"
            f"This action cannot be undone.",
        )
        if not confirm:
            return

        try:
            with get_db_connection(BANK_DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("PRAGMA foreign_keys = ON;")
                cur.execute(
                    "DELETE FROM card_master WHERE card_master_id = ?",
                    (card_id,),
                )
                conn.commit()

            show_colorful_info(
                mgr_win,
                "Delete Successful",
                f"The card '{card_name}' has been permanently deleted.",
            )
            load_data()

        except sqlite3.IntegrityError as e:
            # Caught if a concurrent insert created transactions between the
            # count check above and the DELETE statement.
            show_colorful_error(
                mgr_win,
                "Delete Blocked",
                f"Could not delete '{card_name}' — it is still referenced by "
                f"one or more transactions.\n\nDetail: {e}",
            )
        except sqlite3.Error as e:
            show_colorful_error(mgr_win, "Delete Failed", f"Database error: {e}")

    # ------------------------------------------------------------------
    # Close helper
    # ------------------------------------------------------------------
    def close_manager() -> None:
        safe_close_modal(mgr_win, parent, calling_button)

    # ------------------------------------------------------------------
    # Footer buttons — same layout as trade_manager.py / manage_bank.py
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

    # CRITICAL: Restore grab to the caller so it stays in focus.
    try:
        if parent.winfo_exists():
            parent.grab_set()
    except tk.TclError:
        pass


# ===========================================================================
# 2.  show_cc_transactions_manager  —  cc_transactions rows
# ===========================================================================


def show_cc_transactions_manager(
    parent: Union[tk.Toplevel, tk.Tk],
    calling_button: tk.Widget | None = None,
) -> None:
    """Open a modal window showing all cc_transactions rows.

    Features
    --------
    • Sortable columns — click any heading to toggle ascending / descending.
    • Colour-coded rows: expense rows in red, credit rows (payment /
      cashback / reversal) in green.
    • Hidden primary-key column used by Edit / Delete without exposing IDs.
    • Edit Selected    — informs the user that editing is not yet available.
    • Delete Selected  — removes the cc_transactions row and also:
        1. Finds the linked bank_transactions row
           (module_type='CC', module_ref_id=cc_trans_id) and deletes it.
        2. Nulls out pair_id references on the transfer counterpart (if any).
        3. Recalculates balance_after for every subsequent transaction in
           the same bank account so the running total stays correct.
    • Escape key and window-close button both invoke the safe-close helper.
    • grab_set is restored on *parent* after the modal closes.
    """
    # ------------------------------------------------------------------
    # Modal setup
    # ------------------------------------------------------------------
    disable_parent(parent, calling_button=calling_button)

    mgr_win = tk.Toplevel(parent)
    mgr_win.title("CC Transactions Manager — Manage / View / Remove")
    mgr_win.geometry("1200x640")
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
        text="💳  CC TRANSACTIONS MANAGER — MANAGE / VIEW / REMOVE",
        font=UI_THEME.get("font_bold", ("Helvetica", 14, "bold")),
        bg=UI_THEME.get("bg_header", "#1e293b"),
        fg=UI_THEME.get("fg_header", "#ffffff"),
        pady=10,
    ).pack(fill="x")

    # ------------------------------------------------------------------
    # Treeview style — distinct name to avoid clashing with other managers
    # ------------------------------------------------------------------
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure(
        "CCTxMgr.Treeview",
        background=UI_THEME.get("charcoal", "#334155"),
        foreground="white",
        fieldbackground=UI_THEME.get("charcoal", "#334155"),
        bordercolor=UI_THEME.get("slate_light", "#475569"),
        rowheight=30,
        font=UI_THEME.get("font_main", ("Helvetica", 12)),
    )
    style.configure(
        "CCTxMgr.Treeview.Heading",
        background=UI_THEME.get("dark_slate", "#1e293b"),
        foreground=UI_THEME.get("gold", "#FFD700"),
        font=UI_THEME.get("font_bold", ("Helvetica", 12, "bold")),
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
        "Card",
        "Party",
        "Expense",
        "Credit",
        "Pts Earned",
        "Pts Balance",
        "Budget Head",
    )
    tree = ttk.Treeview(
        tree_frame,
        columns=cols,
        show="headings",
        yscrollcommand=tree_scroll.set,
        style="CCTxMgr.Treeview",
    )
    tree_scroll.config(command=tree.yview)

    columns_setup = {
        "ID": "ID",
        "Date": "Trans Date",
        "Card": "Card",
        "Party": "Party / Merchant",
        "Expense": "Expense (DR)",
        "Credit": "Credit (CR)",
        "Pts Earned": "Pts Earned",
        "Pts Balance": "Pts Balance",
        "Budget Head": "Budget Head",
    }
    for col, heading_text in columns_setup.items():
        tree.heading(
            col,
            text=heading_text,
            command=_make_sort_fn(tree, col, False),
        )

    # Row colour tags
    tree.tag_configure("expense_row", foreground="#f87171")  # red  — purchase / charge
    tree.tag_configure("credit_row", foreground="#4ade80")  # green — payment / cashback

    # Column layout — ID is hidden (zero width)
    tree.column("ID", width=0, stretch=tk.NO)
    tree.column("Date", width=110, anchor="center")
    tree.column("Card", width=200, anchor="w")
    tree.column("Party", width=230, anchor="w")
    tree.column("Expense", width=120, anchor="e")
    tree.column("Credit", width=120, anchor="e")
    tree.column("Pts Earned", width=90, anchor="e")
    tree.column("Pts Balance", width=100, anchor="e")
    tree.column("Budget Head", width=160, anchor="w")

    tree.pack(fill="both", expand=True)

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------
    def load_data() -> None:
        """Clear the treeview and repopulate from cc_transactions."""
        for item in tree.get_children():
            tree.delete(item)
        try:
            with get_db_connection(BANK_DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT  ct.cc_trans_id,
                            ct.cc_trans_dt,
                            cm.card_name,
                            ct.party,
                            ct.expense,
                            ct.cc_credit,
                            ct.point_earned,
                            ct.points_balance,
                            COALESCE(bh.bh_description, '')
                    FROM    cc_transactions ct
                    JOIN    card_master cm ON cm.card_master_id = ct.card_master_id
                    LEFT JOIN budget_head bh ON bh.bh_id = ct.bh_id
                    ORDER BY ct.cc_trans_dt DESC, ct.cc_trans_id DESC
                """)
                for row in cursor.fetchall():
                    expense = row[4] or 0.0
                    credit = row[5] or 0.0
                    # A row is a "credit" row when cc_credit > 0 and expense == 0
                    row_tag = (
                        "credit_row"
                        if credit > 0.0 and expense == 0.0
                        else "expense_row"
                    )
                    tree.insert(
                        "",
                        "end",
                        values=(
                            row[0],  # cc_trans_id (hidden)
                            row[1],  # cc_trans_dt
                            row[2],  # card_name
                            row[3],  # party
                            f"₹ {expense:,.2f}" if expense else "",
                            f"₹ {credit:,.2f}" if credit else "",
                            row[6] if row[6] else "",  # point_earned
                            row[7] if row[7] is not None else "",  # points_balance
                            row[8],  # bh_description
                        ),
                        tags=(row_tag,),
                    )
        except sqlite3.Error as e:
            logger.error("Failed to load cc_transactions rows: %s", e)

    load_data()

    # ------------------------------------------------------------------
    # Selection helper
    # ------------------------------------------------------------------
    def _get_selected() -> tuple:
        """Return (cc_trans_id, card_name, party) or (None, None, None)."""
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

    # ------------------------------------------------------------------
    # Edit action
    # ------------------------------------------------------------------
    def _on_edit() -> None:
        cc_trans_id, _, _ = _get_selected()
        if cc_trans_id is None:
            return
        show_colorful_info(
            mgr_win,
            "Edit Not Yet Available",
            "Inline editing of credit card transactions is not yet "
            "implemented.\n\nTo correct a transaction, delete it and "
            "re-enter with the correct values.",
        )

    # ------------------------------------------------------------------
    # Delete action
    # ------------------------------------------------------------------
    def _on_delete() -> None:
        cc_trans_id, card_name, party = _get_selected()
        if cc_trans_id is None:
            return

        # ── Step 1: fetch the linked bank_transactions row (if any) ───
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
                    WHERE   module_type    = 'CC'
                      AND   module_ref_id  = ?
                    """,
                    (cc_trans_id,),
                )
                bank_row = cur.fetchone()
        except sqlite3.Error as e:
            show_colorful_error(
                mgr_win, "Error", f"Could not fetch linked bank transaction: {e}"
            )
            return

        # ── Step 2: confirm ────────────────────────────────────────────
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
            f"Are you sure you want to permanently delete this transaction?\n\n"
            f"  Card : {card_name}\n"
            f"  Party: {party}\n"
            f"{linked_note}\n\n"
            f"This action cannot be undone.",
        )
        if not confirm:
            return

        # ── Step 3: execute all DB changes in one connection ───────────
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

                    # Net effect this row had on the running balance.
                    # +delta → account increased (subtract downstream).
                    # -delta → account decreased (add back downstream).
                    delta = (deposit_amt or 0.0) - (withdrawal_amt or 0.0)

                    # 3a. Null out pair_id references on counterpart rows.
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

                    # 3b. Delete the bank_transactions row.
                    cur.execute(
                        "DELETE FROM bank_transactions WHERE trans_id = ?",
                        (bt_trans_id,),
                    )

                    # 3c. Recalculate balance_after for subsequent rows
                    #     in the same account.
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
                            (delta, account_id, del_date, del_date, bt_trans_id),
                        )

                # 3d. Delete the cc_transactions row itself.
                cur.execute(
                    "DELETE FROM cc_transactions WHERE cc_trans_id = ?",
                    (cc_trans_id,),
                )

                conn.commit()

            show_colorful_info(
                mgr_win,
                "Delete Successful",
                f"The transaction for '{card_name}' — {party} —\n"
                f"has been deleted"
                + (
                    " and downstream balances have been recalculated."
                    if bank_row
                    else "."
                ),
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
    # Footer buttons — same layout as trade_manager.py / manage_bank.py
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

    _hdr = UI_THEME["bg_header"]
    _foc = UI_THEME["bg_focus"]
    apply_button_animations(edit_btn, _hdr, _foc)
    apply_button_animations(del_btn, _hdr, _foc)
    apply_button_animations(close_btn, _hdr, _foc)

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
