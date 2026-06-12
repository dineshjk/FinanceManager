# -*- coding: utf-8 -*-
# File: FinanceManager/BankMan/manage_bh.py

"""
UI module for viewing and managing Budget Head records.

Mirrors the structure and features of StockMan/trade_manager.py and
BankMan/manage_bank.py:
  * Sortable treeview (click any heading to toggle ascending/descending).
  * Colour-coded rows: INCOME rows in green, EXPENSE rows in red.
  * Edit Selected -- placeholder (inline editing not yet implemented).
  * Delete Selected -- removes the budget_head row.  Because the schema
    uses ON DELETE SET NULL for both the self-referential parent_bh_id FK
    and the bank_transactions.bh_id FK, deletion is always permitted;
    the database automatically nulls out affected references.  The user
    is warned of the downstream impact before confirming.
  * Close / Escape -- safe modal teardown via safe_close_modal.

One public function is exposed:

  show_bh_manager(parent, calling_button=None)
      Displays all budget_head rows.  Child rows are shown with their
      parent category name; top-level rows show '(Top Level)'.
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
# Internal sort helper
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
# show_bh_manager  --  budget_head rows
# ===========================================================================


def show_bh_manager(
    parent: Union[tk.Toplevel, tk.Tk],
    calling_button: tk.Widget | None = None,
) -> None:
    """Open a modal window showing all budget_head records.

    Features
    --------
    * Sortable columns -- click any heading to toggle ascending/descending.
    * Colour-coded rows: INCOME rows in green, EXPENSE rows in red.
    * Hidden primary-key column used by Edit/Delete without exposing IDs.
    * Edit Selected   -- informs the user editing is not yet available.
    * Delete Selected -- removes the budget_head row.  ON DELETE SET NULL
                         cascades automatically handle:
                           • child budget heads (parent_bh_id → NULL)
                           • bank_transactions rows (bh_id → NULL)
                         The user sees a warning showing the impact count
                         before confirming.
    * Escape key and window-close button invoke the safe-close helper.
    * grab_set is restored on *parent* after the modal closes.
    """
    disable_parent(parent, calling_button=calling_button)

    mgr_win = tk.Toplevel(parent)
    mgr_win.title("Budget Heads Manager — Manage / View / Remove")
    mgr_win.geometry("860x540")
    mgr_win.configure(bg=UI_THEME["bg_input"])
    mgr_win.transient(parent)
    mgr_win.grab_set()
    mgr_win.focus_set()
    push_window(mgr_win, parent)

    tk.Label(
        mgr_win,
        text="📂  BUDGET HEADS MANAGER — MANAGE / VIEW / REMOVE",
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
        "BHMgr.Treeview",
        background=UI_THEME.get("charcoal", "#334155"),
        foreground="white",
        fieldbackground=UI_THEME.get("charcoal", "#334155"),
        bordercolor=UI_THEME.get("slate_light", "#475569"),
        rowheight=30,
        font=UI_THEME.get("font_main", ("Helvetica", 12)),
    )
    style.configure(
        "BHMgr.Treeview.Heading",
        background=UI_THEME.get("dark_slate", "#1e293b"),
        foreground=UI_THEME.get("gold", "#FFD700"),
        font=UI_THEME.get("font_bold", ("Helvetica", 12, "bold")),
    )

    tree_frame = tk.Frame(mgr_win, bg=UI_THEME["bg_input"], bd=1, relief="ridge")
    tree_frame.pack(fill="both", expand=True, padx=15, pady=15)

    tree_scroll = ttk.Scrollbar(tree_frame)
    tree_scroll.pack(side="right", fill="y")

    cols = ("S.No.", "ID", "Description", "Parent Category", "Type")
    tree = ttk.Treeview(
        tree_frame,
        columns=cols,
        show="headings",
        yscrollcommand=tree_scroll.set,
        style="BHMgr.Treeview",
    )
    tree_scroll.config(command=tree.yview)

    columns_setup = {
        "S.No.": "S.No.",
        "ID": "ID",
        "Description": "Budget Head Description",
        "Parent Category": "Parent Category",
        "Type": "Type",
    }
    for col, heading_text in columns_setup.items():
        tree.heading(
            col,
            text=heading_text,
            command=_make_sort_fn(tree, col, False),
        )

    tree.tag_configure("income_row", foreground="#4ade80")  # green
    tree.tag_configure("expense_row", foreground="#f87171")  # red

    tree.column("S.No.", width=60, anchor="center")
    tree.column("ID", width=0, stretch=tk.NO)
    tree.column("Description", width=300, anchor="w")
    tree.column("Parent Category", width=280, anchor="w")
    tree.column("Type", width=110, anchor="center")

    tree.pack(fill="both", expand=True)

    def load_data() -> None:
        """Clear the treeview and repopulate from budget_head."""
        for item in tree.get_children():
            tree.delete(item)
        try:
            with get_db_connection(BANK_DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT  bh.bh_id,
                            bh.bh_description,
                            COALESCE(p.bh_description, '(Top Level)'),
                            bh.bh_type
                    FROM    budget_head bh
                    LEFT JOIN budget_head p
                              ON p.bh_id = bh.parent_bh_id
                    ORDER BY bh.bh_type, p.bh_description NULLS FIRST,
                             bh.bh_description
                """)
                for i, row in enumerate(cursor.fetchall(), 1):
                    bh_type = row[3]
                    row_tag = "income_row" if bh_type == "INCOME" else "expense_row"
                    tree.insert(
                        "",
                        "end",
                        values=(
                            i,  # Serial number
                            row[0],  # bh_id (hidden)
                            row[1],  # bh_description
                            row[2],  # parent category name
                            bh_type,
                        ),
                        tags=(row_tag,),
                    )
        except sqlite3.Error as e:
            logger.error("Failed to load budget_head rows: %s", e)

    load_data()

    def _get_selected() -> tuple:
        """Return (bh_id, description, bh_type) or (None, None, None)."""
        selected = tree.selection()
        if not selected:
            show_colorful_error(
                mgr_win,
                "Selection Error",
                "Please select a budget head from the list first.",
            )
            return None, None, None
        values = tree.item(selected[0])["values"]
        return values[1], values[2], values[4]

    def _on_edit() -> None:
        bh_id, _, _ = _get_selected()
        if bh_id is None:
            return
        show_colorful_info(
            mgr_win,
            "Edit Not Yet Available",
            "Inline editing of budget heads is not yet implemented.\n\n"
            "To correct a record, delete it and re-enter with the correct "
            "values.",
        )

    def _on_delete() -> None:
        bh_id, description, bh_type = _get_selected()
        if bh_id is None:
            return

        # Count downstream impact (SET NULL cascades, not RESTRICT)
        child_count = 0
        tx_count = 0
        try:
            with get_db_connection(BANK_DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT COUNT(*) FROM budget_head " "WHERE parent_bh_id = ?",
                    (bh_id,),
                )
                row = cur.fetchone()
                if row:
                    child_count = row[0]

                cur.execute(
                    "SELECT COUNT(*) FROM bank_transactions " "WHERE bh_id = ?",
                    (bh_id,),
                )
                row = cur.fetchone()
                if row:
                    tx_count = row[0]
        except sqlite3.Error as e:
            show_colorful_error(
                mgr_win,
                "Error",
                f"Could not check linked records: {e}",
            )
            return

        impact_lines = []
        if child_count > 0:
            impact_lines.append(
                f"  • {child_count} child budget head(s) will become "
                f"top-level (parent cleared)."
            )
        if tx_count > 0:
            impact_lines.append(
                f"  • {tx_count} bank transaction(s) will lose their "
                f"budget head label."
            )

        impact_note = (
            "\n\nImpact of deletion:\n" + "\n".join(impact_lines)
            if impact_lines
            else ""
        )

        confirm = show_colorful_yesno(
            mgr_win,
            "Confirm Delete",
            f"Permanently delete this budget head?\n\n"
            f"  Description : {description}\n"
            f"  Type        : {bh_type}"
            f"{impact_note}\n\n"
            f"This action cannot be undone.",
        )
        if not confirm:
            return

        try:
            with get_db_connection(BANK_DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("PRAGMA foreign_keys = ON;")
                cur.execute(
                    "DELETE FROM budget_head WHERE bh_id = ?",
                    (bh_id,),
                )
                conn.commit()
            show_colorful_info(
                mgr_win,
                "Delete Successful",
                f"Budget head '{description}' has been permanently deleted."
                + (
                    f"\n\n{child_count} child head(s) are now top-level."
                    if child_count > 0
                    else ""
                )
                + (
                    f"\n{tx_count} transaction(s) now have no budget head."
                    if tx_count > 0
                    else ""
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
