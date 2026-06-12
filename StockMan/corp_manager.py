# -*- coding: utf-8 -*-
# StockMan/corp_manager.py

"""
UI module for viewing historical corporate actions and triggering safe database rollbacks.
"""

import tkinter as tk
from tkinter import ttk
import sqlite3

# Local imports
from Shared.globals import get_db_connection, logger, UI_THEME
from Shared.dialog_utils import (
    show_colorful_yesno,
    show_colorful_info,
    show_colorful_error,
)
from .rollback_manager import (
    delete_bonus,
    delete_split,
    delete_merger,
    delete_demerger,
)
from Shared.window_manager import push_window, pop_window, safe_close_modal
from Shared.gui_utils import apply_button_animations, universal_tree_sort


def show_corp_manager(parent: tk.Toplevel | tk.Tk) -> None:
    """
    Opens a modal window displaying all corporate actions with options to delete/rollback.
    """
    mgr_win = tk.Toplevel(parent)
    mgr_win.title("Corporate Action History & Rollback")
    mgr_win.geometry("950x600")
    mgr_win.configure(bg=UI_THEME["bg_input"])
    mgr_win.transient(parent)
    mgr_win.grab_set()
    mgr_win.focus_set()
    push_window(mgr_win, parent)

    # --- Header ---
    tk.Label(
        mgr_win,
        text="🏛️ CORPORATE ACTION EDIT & ROLLBACK MANAGER",
        font=("Helvetica", 16, "bold"),
        bg="#1e293b",
        fg="white",
        pady=10,
    ).pack(fill="x")

    # --- Treeview Theming ---
    style = ttk.Style()
    if "clam" not in style.theme_names():
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

    style.configure(
        "Dark.Treeview",
        background=UI_THEME["bg_input"],
        foreground=UI_THEME["fg_input"],
        fieldbackground=UI_THEME["bg_input"],
        bordercolor="#475569",
        rowheight=30,
        font=UI_THEME["font_main"],
    )
    style.map(
        "Dark.Treeview",
        background=[("selected", UI_THEME["bg_focus"])],
        foreground=[("selected", UI_THEME["fg_input"])],
    )
    style.configure(
        "Dark.Treeview.Heading",
        background="#334155",
        foreground="white",
        font=UI_THEME["font_bold"],
    )

    # --- Treeview Setup ---
    tree_frame = tk.Frame(
        mgr_win, bg=UI_THEME["bg_input"], bd=1, relief="ridge"
    )
    tree_frame.pack(fill="both", expand=True, padx=15, pady=15)

    tree_scroll = ttk.Scrollbar(tree_frame)
    tree_scroll.pack(side="right", fill="y")

    cols = ("ID", "Date", "Company", "Type", "Details", "Notes")
    tree = ttk.Treeview(
        tree_frame,
        columns=cols,
        show="headings",
        yscrollcommand=tree_scroll.set,
        style="Dark.Treeview",
    )
    tree_scroll.config(command=tree.yview)

    for col, text in [
        ("ID", "ID"),
        ("Date", "Record/Ex Date"),
        ("Company", "Target Company"),
        ("Type", "Action Type"),
        ("Details", "Ratio / Details"),
        ("Notes", "Remarks"),
    ]:
        tree.heading(col, text=text, command=lambda _c=col: universal_tree_sort(tree, _c, False))

    # Hide the ID column
    tree.column("ID", width=0, stretch=tk.NO)
    tree.column("Date", width=120, anchor="center")
    tree.column("Company", width=220, anchor="w")
    tree.column("Type", width=100, anchor="center")
    tree.column("Details", width=180, anchor="w")
    tree.column("Notes", width=200, anchor="w")

    tree.pack(fill="both", expand=True)

    # --- Data Loading Logic ---
    def load_data():
        for item in tree.get_children():
            tree.delete(item)
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT c.id_act, c.act_dt, s.company_name, c.type_act, c.details_act, c.note_act
                    FROM corp_acts c
                    JOIN stocks s ON c.id_stk = s.id_stk
                    ORDER BY c.act_dt DESC, c.id_act DESC
                """)
                for row in cursor.fetchall():
                    tree.insert(
                        "",
                        "end",
                        values=(
                            row[0],
                            row[1],
                            row[2],
                            row[3],
                            row[4],
                            row[5] or "",
                        ),
                    )
        except sqlite3.Error as e:
            logger.error(f"Failed to load corporate actions: {e}")

    load_data()

    def edit_selected_action():
        selected_item = tree.selection()
        if not selected_item:
            show_colorful_error(
                mgr_win,
                "Selection Error",
                "Please select a corporate action to edit.",
            )
            return

        item_values = tree.item(selected_item[0], "values")
        action_id = item_values[0]
        action_type = item_values[3]

        if "BONUS" in str(action_type).upper():
            from .bonus_entry import bonus_shares

            bonus_shares(mgr_win, calling_button=btn_edit, edit_id=action_id)
            load_data()

        elif "SPLIT" in str(action_type).upper():
            from .split_entry import add_split_share

            add_split_share(
                mgr_win, calling_button=btn_edit, edit_id=action_id
            )
            load_data()

        elif "DIVIDEND" in str(action_type).upper():
            from .dividend import add_dividend

            add_dividend(mgr_win, calling_button=btn_edit, edit_id=action_id)
            load_data()

        else:
            show_colorful_info(
                mgr_win,
                "Not Implemented",
                f"The Update Engine for {action_type} is not yet built!",
            )

    # --- Action Logic ---
    def _on_delete():
        selected = tree.selection()
        if not selected:
            show_colorful_error(
                mgr_win,
                "Selection Error",
                "Please select a corporate action from the list to delete.",
            )
            return

        item = tree.item(selected[0])
        act_id = item["values"][0]
        comp_name = item["values"][2]
        act_type = str(item["values"][3]).upper()

        confirm = show_colorful_yesno(
            mgr_win,
            "Confirm Rollback",
            f"Are you sure you want to permanently delete this {act_type} for {comp_name}?\n\nThis will safely reverse all allotted shares, deducted shares, and recompute your averages.",
        )

        if confirm:
            # Route to the correct rollback engine based on the Type column
            success = False
            msg = ""

            if act_type == "BONUS":
                success, msg = delete_bonus(act_id)
            elif act_type == "SPLIT":
                success, msg = delete_split(act_id)
            elif act_type == "MERGER":
                success, msg = delete_merger(act_id)
            elif act_type == "DEMERGER":
                success, msg = delete_demerger(act_id)
            else:
                show_colorful_error(
                    mgr_win,
                    "Unknown Type",
                    f"Cannot rollback unknown action type: {act_type}",
                )
                return

            if success:
                show_colorful_info(
                    mgr_win,
                    "Rollback Successful",
                    f"The {act_type} for {comp_name} has been successfully rolled back.",
                )
                load_data()  # Refresh table
            else:
                show_colorful_error(mgr_win, "Rollback Failed", msg)

    def _close_manager(event=None):
        safe_close_modal(mgr_win, parent)

    # --- Footer Buttons ---
    btn_frame = tk.Frame(mgr_win, bg=UI_THEME["bg_input"])
    btn_frame.pack(fill="x", padx=15, pady=(0, 15))

    btn_edit = tk.Button(
        btn_frame,
        text="✏️ Edit Selected Action",
        command=edit_selected_action,
        bg="#0284c7",  # A nice blue to distinguish from the red delete button
        fg="white",
        font=("Helvetica", 12, "bold"),
        width=25,
        cursor="hand2",
    )
    btn_edit.pack(side="left", padx=(0, 10))

    del_btn = tk.Button(
        btn_frame,
        text="🗑️ Rollback Selected Action",
        command=_on_delete,
        bg="#b91c1c",
        fg="white",
        font=("Helvetica", 12, "bold"),
        width=28,
        cursor="hand2",
    )
    del_btn.pack(side="left")

    close_btn = tk.Button(
        btn_frame,
        text="Close",
        command=_close_manager,
        bg="#475569",
        fg="white",
        font=("Helvetica", 12, "bold"),
        width=15,
        cursor="hand2",
    )
    close_btn.pack(side="right")

    apply_button_animations(del_btn, "#b91c1c", "#991b1b")
    apply_button_animations(close_btn, "#475569", "#334155")

    mgr_win.bind("<Escape>", _close_manager)
    mgr_win.protocol("WM_DELETE_WINDOW", _close_manager)

    mgr_win.wait_window()
