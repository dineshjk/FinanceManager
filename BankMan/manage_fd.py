# -*- coding: utf-8 -*-
# File: FinanceManager/BankMan/manage_fd.py

"""
UI module for viewing and managing Fixed Deposit master records and transactions.

Mirrors the structure and features of StockMan/trade_manager.py and
BankMan/manage_bank.py:
  • Sortable treeview (click any heading to toggle ascending/descending).
  • Colour-coded rows.
  • Edit Selected — placeholder (inline editing not yet implemented).
  • Delete Selected — removes the row and cascades required changes.
  • Close / Escape — safe modal teardown via safe_close_modal.

Two public functions are exposed:

  show_fd_manager(parent, calling_button=None)
      Displays all fd_master rows.  Deleting an FD is blocked when
      fd_transactions reference it (ON DELETE RESTRICT in the schema).

  show_fd_transactions_manager(parent, calling_button=None)
      Displays all fd_transactions rows.  Deleting a row also:
        1. Finds and removes the linked bank_transactions row
           (module_type='FD', module_ref_id=fd_trans_id).
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
# 1.  show_fd_manager  —  fd_master rows
# ===========================================================================


def show_fd_manager(
    parent: Union[tk.Toplevel, tk.Tk],
    calling_button: tk.Widget | None = None,
) -> None:
    """Open a modal window showing all fd_master (Fixed Deposit) records.

    Features
    --------
    • Sortable columns — click any heading to toggle ascending / descending.
    • Colour-coded rows: active FDs in green, closed/matured FDs in red.
    • Hidden primary-key column used by Edit / Delete without exposing IDs.
    • Edit Selected    — informs the user that editing is not yet available.
    • Delete Selected  — removes the FD from fd_master.  If the FD has
                         associated fd_transactions the database RESTRICT
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
    mgr_win.title("FD Master Manager — Manage / View / Remove")
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
        text="🏦  FD MASTER MANAGER — MANAGE / VIEW / REMOVE",
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
        "FDMgr.Treeview",
        background=UI_THEME.get("charcoal", "#334155"),
        foreground="white",
        fieldbackground=UI_THEME.get("charcoal", "#334155"),
        bordercolor=UI_THEME.get("slate_light", "#475569"),
        rowheight=30,
        font=UI_THEME.get("font_main", ("Helvetica", 12)),
    )
    style.configure(
        "FDMgr.Treeview.Heading",
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
        "FD Number",
        "Bank",
        "Account",
        "Principal",
        "Rate %",
        "Open Date",
        "Maturity Date",
        "Active",
    )
    tree = ttk.Treeview(
        tree_frame,
        columns=cols,
        show="headings",
        yscrollcommand=tree_scroll.set,
        style="FDMgr.Treeview",
    )
    tree_scroll.config(command=tree.yview)

    columns_setup = {
        "ID": "ID",
        "FD Number": "FD Number",
        "Bank": "Bank",
        "Account": "Account No.",
        "Principal": "Principal (₹)",
        "Rate %": "Rate %",
        "Open Date": "Open Date",
        "Maturity Date": "Maturity Date",
        "Active": "Active",
    }
    for col, heading_text in columns_setup.items():
        tree.heading(
            col,
            text=heading_text,
            command=_make_sort_fn(tree, col, False),
        )

    # Row colour tags
    tree.tag_configure("active_row", foreground="#4ade80")  # green
    tree.tag_configure("inactive_row", foreground="#f87171")  # red

    # Column layout — ID is hidden (zero width)
    tree.column("ID", width=0, stretch=tk.NO)
    tree.column("FD Number", width=180, anchor="w")
    tree.column("Bank", width=180, anchor="w")
    tree.column("Account", width=140, anchor="center")
    tree.column("Principal", width=140, anchor="e")
    tree.column("Rate %", width=80, anchor="center")
    tree.column("Open Date", width=110, anchor="center")
    tree.column("Maturity Date", width=120, anchor="center")
    tree.column("Active", width=70, anchor="center")

    tree.pack(fill="both", expand=True)

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------
    def load_data() -> None:
        """Clear the treeview and repopulate from fd_master."""
        for item in tree.get_children():
            tree.delete(item)
        try:
            with get_db_connection(BANK_DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT  fm.fd_master_id,
                            fm.fd_number,
                            b.name,
                            a.ac_number,
                            fm.principal_amount,
                            fm.interest_rate,
                            fm.open_dt,
                            fm.maturity_dt,
                            fm.is_active
                    FROM    fd_master fm
                    JOIN    accounts a ON a.ac_id = fm.account_id
                    JOIN    banks    b ON b.b_id  = a.b_id
                    ORDER BY b.name, fm.fd_number
                """)
                for row in cursor.fetchall():
                    is_active = row[8]
                    row_tag = "active_row" if is_active else "inactive_row"
                    active_label = "Yes" if is_active else "No"
                    tree.insert(
                        "",
                        "end",
                        values=(
                            row[0],  # fd_master_id (hidden)
                            row[1],  # fd_number
                            row[2],  # bank name
                            row[3],  # ac_number
                            f"₹ {row[4]:,.2f}",  # principal_amount
                            f"{row[5]:.2f}",  # interest_rate
                            row[6],  # open_dt
                            row[7],  # maturity_dt
                            active_label,
                        ),
                        tags=(row_tag,),
                    )
        except sqlite3.Error as e:
            logger.error("Failed to load fd_master rows: %s", e)

    load_data()

    # ------------------------------------------------------------------
    # Selection helper
    # ------------------------------------------------------------------
    def _get_selected() -> tuple:
        """Return (fd_master_id, fd_number) or (None, None)."""
        selected = tree.selection()
        if not selected:
            show_colorful_error(
                mgr_win,
                "Selection Error",
                "Please select an FD from the list first.",
            )
            return None, None
        values = tree.item(selected[0])["values"]
        return values[0], values[1]

    # ------------------------------------------------------------------
    # Edit action
    # ------------------------------------------------------------------
    def _on_edit() -> None:
        fd_id, _ = _get_selected()
        if fd_id is None:
            return
        show_colorful_info(
            mgr_win,
            "Edit Not Yet Available",
            "Inline editing of FD master records is not yet implemented.\n\n"
            "To correct a record, delete it and re-enter with the correct "
            "values.",
        )

    # ------------------------------------------------------------------
    # Delete action
    # ------------------------------------------------------------------
    def _on_delete() -> None:
        fd_id, fd_number = _get_selected()
        if fd_id is None:
            return

        # Count linked fd_transactions so we can warn the user up-front.
        tx_count = 0
        try:
            with get_db_connection(BANK_DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT COUNT(*) FROM fd_transactions " "WHERE fd_master_id = ?",
                    (fd_id,),
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
                f"FD '{fd_number}' has {tx_count} linked transaction(s).\n\n"
                f"Delete or reassign all fd_transactions for this FD before "
                f"removing the FD record.",
            )
            return

        confirm = show_colorful_yesno(
            mgr_win,
            "Confirm Delete",
            f"Are you sure you want to permanently delete the FD:\n\n"
            f"  {fd_number}\n\n"
            f"This action cannot be undone.",
        )
        if not confirm:
            return

        try:
            with get_db_connection(BANK_DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("PRAGMA foreign_keys = ON;")
                cur.execute(
                    "DELETE FROM fd_master WHERE fd_master_id = ?",
                    (fd_id,),
                )
                conn.commit()

            show_colorful_info(
                mgr_win,
                "Delete Successful",
                f"The FD '{fd_number}' has been permanently deleted.",
            )
            load_data()

        except sqlite3.IntegrityError as e:
            show_colorful_error(
                mgr_win,
                "Delete Blocked",
                f"Could not delete FD '{fd_number}' — it is still referenced "
                f"by one or more transactions.\n\nDetail: {e}",
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
# 2.  show_fd_transactions_manager  —  fd_transactions rows
# ===========================================================================


def show_fd_transactions_manager(
    parent: Union[tk.Toplevel, tk.Tk],
    calling_button: tk.Widget | None = None,
) -> None:
    """Open a modal window showing all fd_transactions rows.

    Features
    --------
    • Sortable columns — click any heading to toggle ascending / descending.
    • Colour-coded rows: deposit/saving rows in green, withdrawal rows in red.
    • Hidden primary-key column used by Edit / Delete without exposing IDs.
    • Edit Selected    — informs the user that editing is not yet available.
    • Delete Selected  — removes the fd_transactions row and also:
        1. Finds the linked bank_transactions row
           (module_type='FD', module_ref_id=fd_trans_id) and deletes it.
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
    mgr_win.title("FD Transactions Manager — Manage / View / Remove")
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
        text="🏦  FD TRANSACTIONS MANAGER — MANAGE / VIEW / REMOVE",
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
        "FDTxMgr.Treeview",
        background=UI_THEME.get("charcoal", "#334155"),
        foreground="white",
        fieldbackground=UI_THEME.get("charcoal", "#334155"),
        bordercolor=UI_THEME.get("slate_light", "#475569"),
        rowheight=30,
        font=UI_THEME.get("font_main", ("Helvetica", 12)),
    )
    style.configure(
        "FDTxMgr.Treeview.Heading",
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
        "FD Number",
        "Description",
        "Deposit",
        "Withdrawal",
        "Principal",
        "Interest",
    )
    tree = ttk.Treeview(
        tree_frame,
        columns=cols,
        show="headings",
        yscrollcommand=tree_scroll.set,
        style="FDTxMgr.Treeview",
    )
    tree_scroll.config(command=tree.yview)

    columns_setup = {
        "ID": "ID",
        "Date": "Trans Date",
        "FD Number": "FD Number",
        "Description": "Description",
        "Deposit": "Deposit (CR)",
        "Withdrawal": "Withdrawal (DR)",
        "Principal": "Principal",
        "Interest": "Interest",
    }
    for col, heading_text in columns_setup.items():
        tree.heading(
            col,
            text=heading_text,
            command=_make_sort_fn(tree, col, False),
        )

    # Row colour tags
    tree.tag_configure("deposit_row", foreground="#4ade80")  # green
    tree.tag_configure("withdrawal_row", foreground="#f87171")  # red

    # Column layout — ID is hidden (zero width)
    tree.column("ID", width=0, stretch=tk.NO)
    tree.column("Date", width=110, anchor="center")
    tree.column("FD Number", width=180, anchor="w")
    tree.column("Description", width=210, anchor="w")
    tree.column("Deposit", width=130, anchor="e")
    tree.column("Withdrawal", width=130, anchor="e")
    tree.column("Principal", width=120, anchor="e")
    tree.column("Interest", width=120, anchor="e")

    tree.pack(fill="both", expand=True)

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------
    def load_data() -> None:
        """Clear the treeview and repopulate from fd_transactions."""
        for item in tree.get_children():
            tree.delete(item)
        try:
            with get_db_connection(BANK_DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT  ft.fd_trans_id,
                            ft.fd_trans_dt,
                            fm.fd_number,
                            COALESCE(ft.fd_description, ''),
                            ft.fd_saving,
                            ft.fd_withdrawal,
                            ft.fd_principal,
                            ft.fd_int
                    FROM    fd_transactions ft
                    JOIN    fd_master fm ON fm.fd_master_id = ft.fd_master_id
                    ORDER BY ft.fd_trans_dt DESC, ft.fd_trans_id DESC
                """)
                for row in cursor.fetchall():
                    saving = row[4] or 0.0
                    withdrawal = row[5] or 0.0
                    principal = row[6] or 0.0
                    interest = row[7] or 0.0
                    # Deposit row when fd_saving > 0 and no withdrawal
                    row_tag = (
                        "deposit_row"
                        if saving > 0.0 and withdrawal == 0.0
                        else "withdrawal_row"
                    )
                    tree.insert(
                        "",
                        "end",
                        values=(
                            row[0],  # fd_trans_id (hidden)
                            row[1],  # fd_trans_dt
                            row[2],  # fd_number
                            row[3],  # description
                            f"₹ {saving:,.2f}" if saving else "",
                            f"₹ {withdrawal:,.2f}" if withdrawal else "",
                            f"₹ {principal:,.2f}" if principal else "",
                            f"₹ {interest:,.2f}" if interest else "",
                        ),
                        tags=(row_tag,),
                    )
        except sqlite3.Error as e:
            logger.error("Failed to load fd_transactions rows: %s", e)

    load_data()

    # ------------------------------------------------------------------
    # Selection helper
    # ------------------------------------------------------------------
    def _get_selected() -> tuple:
        """Return (fd_trans_id, fd_number, description) or (None, None, None)."""
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
        fd_trans_id, _, _ = _get_selected()
        if fd_trans_id is None:
            return
        show_colorful_info(
            mgr_win,
            "Edit Not Yet Available",
            "Inline editing of FD transactions is not yet implemented.\n\n"
            "To correct a transaction, delete it and re-enter with the "
            "correct values.",
        )

    # ------------------------------------------------------------------
    # Delete action
    # ------------------------------------------------------------------
    def _on_delete() -> None:
        fd_trans_id, fd_number, description = _get_selected()
        if fd_trans_id is None:
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
                    WHERE   module_type   = 'FD'
                      AND   module_ref_id = ?
                    """,
                    (fd_trans_id,),
                )
                bank_row = cur.fetchone()
        except sqlite3.Error as e:
            show_colorful_error(
                mgr_win,
                "Error",
                f"Could not fetch linked bank transaction: {e}",
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
            f"  FD     : {fd_number}\n"
            f"  Narration: {description}"
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

                # 3d. Delete the fd_transactions row itself.
                cur.execute(
                    "DELETE FROM fd_transactions WHERE fd_trans_id = ?",
                    (fd_trans_id,),
                )

                conn.commit()

            show_colorful_info(
                mgr_win,
                "Delete Successful",
                f"The FD transaction for '{fd_number}' has been deleted"
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
