# -*- coding: utf-8 -*-
# BankMan/budget_head_edit.py

"""
Edit form for the ``budget_head`` table.
Presents a list of budget heads in a Treeview and lets the user edit or delete them.
"""

from typing import Union
import sqlite3
import tkinter as tk
from tkinter import ttk

from Shared.gui_utils import (
    apply_button_animations,
    apply_entry_theme,
    ACCOUNT_TYPE_ADD_UI_THEME as _T,
    bind_tooltip,
    flash_error,
    setup_footer_tooltip,
    universal_tree_sort,
)
from Shared.dialog_utils import show_colorful_error, show_colorful_info, show_colorful_yesno
from Shared.modal_utils import disable_parent
from Shared.window_manager import push_window, safe_close_modal
from Shared.help_utils import show_standard_help
from Shared.globals import logger, get_db_connection, BANK_DB_PATH
from Shared.gui_progressive import progressive_selection
from .bank_db_utils import get_all_budget_heads as _db_get_budget_heads

_BH_TYPES = ["INCOME", "EXPENSE"]
_NO_PARENT_LABEL = "(None \u2014 top level)"

def _load_parent_choices(filter_type: str | None = None, exclude_bh_id: int | None = None) -> list[tuple[str, int | None]]:
    choices: list[tuple[str, int | None]] = [(_NO_PARENT_LABEL, None)]
    try:
        for bh_id, desc, bh_type in _db_get_budget_heads():
            if exclude_bh_id is not None and bh_id == exclude_bh_id:
                continue
            if not filter_type or bh_type == filter_type:
                choices.append((f"{desc}  [{bh_type}]", bh_id))
    except Exception:
        pass
    return choices

def edit_budget_head(
    parent: Union[tk.Toplevel, tk.Tk],
    calling_button: tk.Widget | None = None,
) -> None:
    disable_parent(parent, calling_button=calling_button)

    win = tk.Toplevel(parent)
    win.title("✏️  Edit Budget Head  ✏️")
    win.geometry("950x660")
    win.resizable(False, False)
    
    bg_color = _T.get("main_bg", "#f8fafc")
    header_bg = _T.get("header_bg", "#1e293b")
    header_fg = _T.get("header_fg", "#ffffff")
    label_bg = _T.get("label_bg", "#f8fafc")
    
    win.configure(bg=bg_color)
    win.transient(parent)
    win.grab_set()
    win.focus_set()
    try:
        push_window(win, parent)
    except (RuntimeError, tk.TclError) as exc:
        logger.debug("push_window failed: %s", exc)

    tooltip_var = setup_footer_tooltip(win)

    def cleanup_and_close(_event=None):
        return safe_close_modal(win, parent, calling_button)

    def show_help(win: tk.Toplevel) -> None:
        guide_lines = [
            "This screen allows you to modify the details of your Budget Heads.",
            "",
            "• Selection: Click any row in the top grid to load its details into the editable form below.",
            "• Fields: You can modify the Description, Type, and Parent Category.",
        ]
        show_standard_help(
            parent=win,
            title="Budget Head Edit Help",
            guide_lines=guide_lines,
            faq_data=[]
        )

    # Header
    header_frame = tk.Frame(win, bg=header_bg, relief="raised", bd=3)
    header_frame.pack(fill="x", padx=5, pady=(5, 0))

    tk.Label(
        header_frame,
        text="✏️   Edit Budget Head   ✏️",
        font=("Helvetica", 18, "bold"),
        bg=header_bg,
        fg=header_fg,
        relief="ridge",
        bd=2,
    ).pack(fill="x", pady=10)

    # Instruction row
    instr_frame = tk.Frame(win, bg=header_bg)
    instr_frame.pack(fill="x", padx=5, pady=(0, 2))

    tk.Label(
        instr_frame,
        text="Click a budget head row below to load it into the edit form.",
        font=("Helvetica", 11, "italic"),
        bg=header_bg,
        fg="#FFD1D1",
    ).pack(anchor="w", padx=10, pady=4)

    # Treeview
    tree_frame = tk.Frame(win, bg=bg_color, bd=1, relief="ridge")
    tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 4))

    tree_scroll = ttk.Scrollbar(tree_frame)
    tree_scroll.pack(side="right", fill="y")

    style = ttk.Style()
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure(
        "BHEdit.Treeview",
        background="#FFF5F5",
        foreground="#4A0000",
        fieldbackground="#FFF5F5",
        rowheight=26,
        font=("Helvetica", 11),
    )
    style.configure(
        "BHEdit.Treeview.Heading",
        background=header_bg,
        foreground=header_fg,
        font=("Helvetica", 11, "bold"),
    )
    style.map(
        "BHEdit.Treeview",
        background=[("selected", "#7b0000")],
        foreground=[("selected", "white")],
    )

    cols = ("ID", "Description", "Type", "Parent ID", "Parent Category")
    tree = ttk.Treeview(
        tree_frame,
        columns=cols,
        show="headings",
        yscrollcommand=tree_scroll.set,
        style="BHEdit.Treeview",
        height=5,
    )
    tree_scroll.config(command=tree.yview)

    col_setup = {
        "ID": (0, tk.NO, "center"),
        "Description": (250, tk.YES, "w"),
        "Type": (100, tk.NO, "center"),
        "Parent ID": (0, tk.NO, "center"),
        "Parent Category": (250, tk.YES, "w"),
    }
    for col, (width, stretch, anchor) in col_setup.items():
        tree.heading(
            col,
            text=col,
            command=lambda c=col: universal_tree_sort(tree, c, False),
        )
        tree.column(col, width=width, stretch=stretch, anchor=anchor)

    tree.pack(fill="both", expand=True)

    def load_data() -> None:
        for item in tree.get_children():
            tree.delete(item)
        try:
            with get_db_connection(BANK_DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT  bh.bh_id,
                            bh.bh_description,
                            bh.bh_type,
                            bh.parent_bh_id,
                            COALESCE(p.bh_description, '(Top Level)')
                    FROM    budget_head bh
                    LEFT JOIN budget_head p ON p.bh_id = bh.parent_bh_id
                    ORDER BY bh.bh_type, p.bh_description NULLS FIRST, bh.bh_description
                """)
                for row in cursor.fetchall():
                    tree.insert(
                        "",
                        "end",
                        values=(
                            row[0],  # ID
                            row[1],  # Description
                            row[2],  # Type
                            row[3] if row[3] is not None else "",  # Parent ID
                            row[4],  # Parent Category
                        ),
                    )
        except sqlite3.Error as exc:
            logger.error("edit_budget_head: failed to load budget heads: %s", exc)

    load_data()

    tk.Frame(win, height=2, bg=header_bg).pack(fill="x", padx=5, pady=(2, 0))

    sel_label_frame = tk.Frame(win, bg=header_bg)
    sel_label_frame.pack(fill="x", padx=5, pady=0)

    sel_status_var = tk.StringVar(
        value="No category selected — click a row in the list above."
    )
    tk.Label(
        sel_label_frame,
        textvariable=sel_status_var,
        font=("Helvetica", 11, "bold"),
        bg=header_bg,
        fg="#FFD1D1",
    ).pack(anchor="w", padx=10, pady=4)

    selected_id = {"bh_id": None}

    form_frame = tk.Frame(win, bg=bg_color)
    form_frame.pack(fill="x", padx=10, pady=4)

    # Row 0: Description
    tk.Label(
        form_frame,
        text="Description:",
        font=("Helvetica", 13),
        bg=label_bg,
        fg=_T.get("label_fg", "black"),
    ).grid(row=0, column=0, sticky="w", padx=5, pady=4)
    
    desc_var = tk.StringVar()
    desc_entry = tk.Entry(form_frame, width=65, textvariable=desc_var, font=("Helvetica", 13, "bold"))
    desc_entry.grid(row=0, column=1, sticky="w", padx=5, pady=4)
    desc_entry.config(state="disabled")
    apply_entry_theme(desc_entry)
    bind_tooltip(desc_entry, tooltip_var, "Category name (required).")

    # Row 1: Type
    tk.Label(
        form_frame,
        text="Type:",
        font=("Helvetica", 13),
        bg=label_bg,
        fg=_T.get("label_fg", "black"),
    ).grid(row=1, column=0, sticky="w", padx=5, pady=4)
    
    type_combo = ttk.Combobox(
        form_frame,
        values=_BH_TYPES,
        width=63,
        font=("Helvetica", 13, "bold"),
        state="disabled",
    )
    type_combo.grid(row=1, column=1, sticky="w", padx=5, pady=4)
    apply_entry_theme(type_combo)
    progressive_selection(type_combo, _BH_TYPES)
    bind_tooltip(type_combo, tooltip_var, "INCOME or EXPENSE (required).")

    # Row 2: Parent Category
    parent_choices = _load_parent_choices()
    parent_labels = [label for label, _ in parent_choices]

    tk.Label(
        form_frame,
        text="Parent Category:",
        font=("Helvetica", 13),
        bg=label_bg,
        fg=_T.get("label_fg", "black"),
    ).grid(row=2, column=0, sticky="w", padx=5, pady=4)
    
    parent_combo = ttk.Combobox(
        form_frame,
        values=parent_labels,
        width=63,
        font=("Helvetica", 13, "bold"),
        state="disabled",
    )
    parent_combo.grid(row=2, column=1, sticky="w", padx=5, pady=4)
    apply_entry_theme(parent_combo)
    progressive_selection(parent_combo, parent_labels)
    bind_tooltip(parent_combo, tooltip_var, "Optional parent category.")

    def _refresh_parent_combo(event=None):
        typed_type = type_combo.get().strip().upper()
        filter_type = typed_type if typed_type in _BH_TYPES else None
        new_choices = _load_parent_choices(filter_type, selected_id["bh_id"])
        parent_choices.clear()
        parent_choices.extend(new_choices)
        parent_labels.clear()
        parent_labels.extend(label for label, _ in new_choices)
        parent_combo["values"] = list(parent_labels)
        progressive_selection(parent_combo, list(parent_labels))
        
        curr_val = parent_combo.get()
        if curr_val not in parent_labels:
            parent_combo.set(_NO_PARENT_LABEL)

    type_combo.bind("<<ComboboxSelected>>", _refresh_parent_combo, add="+")
    def on_type_focus_out(_event=None):
        try:
            if not win.winfo_exists():
                return
        except (tk.TclError, NameError):
            return
        typed = type_combo.get().strip().upper()
        if typed and typed not in _BH_TYPES:
            show_colorful_error(win, "Invalid Type", f"'{typed}' is not valid.")
            flash_error(type_combo)
            type_combo.focus_set()
        else:
            _refresh_parent_combo()
    type_combo.bind("<FocusOut>", on_type_focus_out, add="+")

    def on_tree_select(_event=None) -> None:
        sel = tree.selection()
        if not sel:
            return
        vals = tree.item(sel[0])["values"]
        bh_id = vals[0]
        desc = vals[1]
        bh_type = vals[2]
        parent_bh_id = vals[3] if vals[3] != "" else None

        selected_id["bh_id"] = bh_id
        
        desc_var.set(desc)
        type_combo.set(bh_type)
        
        _refresh_parent_combo()
        
        parent_label = _NO_PARENT_LABEL
        for lbl, p_id in parent_choices:
            if p_id == parent_bh_id:
                parent_label = lbl
                break
        parent_combo.set(parent_label)

        desc_entry.config(state="normal")
        type_combo.config(state="normal")
        parent_combo.config(state="normal")

        save_btn.config(state="normal")
        delete_btn.config(state="normal")
        sel_status_var.set(f"Editing:  {desc}")
        desc_entry.focus_set()

    tree.bind("<<TreeviewSelect>>", on_tree_select)
    tree.bind("<Double-1>", on_tree_select)

    desc_entry.bind("<Return>", lambda _e: type_combo.focus_set())
    type_combo.bind("<Return>", lambda _e: parent_combo.focus_set())
    parent_combo.bind("<Return>", lambda _e: save_btn.focus_set())

    def on_save(_event=None) -> None:
        bh_id = selected_id["bh_id"]
        if bh_id is None:
            show_colorful_error(win, "No Selection", "Please select a budget head from the list first.")
            return

        description = desc_var.get().strip()
        bh_type = type_combo.get().strip().upper()
        parent_label = parent_combo.get().strip()

        if not description:
            show_colorful_error(win, "Validation Error", "Description is required.")
            flash_error(desc_entry)
            return

        if bh_type not in _BH_TYPES:
            show_colorful_error(win, "Validation Error", "Please select a valid Type: INCOME or EXPENSE.")
            flash_error(type_combo)
            return

        parent_bh_id: int | None = None
        is_valid_parent = False
        for lbl, p_id in parent_choices:
            if lbl == parent_label:
                parent_bh_id = p_id
                is_valid_parent = True
                break

        if not is_valid_parent:
            show_colorful_error(win, "Validation Error", "Please select a valid Parent Category from the list.")
            flash_error(parent_combo)
            return
            
        if parent_bh_id == bh_id:
            show_colorful_error(win, "Validation Error", "A category cannot be its own parent.")
            flash_error(parent_combo)
            return

        try:
            with get_db_connection(BANK_DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("""
                    UPDATE budget_head
                    SET    bh_description = ?,
                           bh_type = ?,
                           parent_bh_id = ?
                    WHERE  bh_id = ?
                """, (description, bh_type, parent_bh_id, bh_id))
                conn.commit()

            show_colorful_info(win, "Success", f"Budget category '{description}' updated successfully.")
            load_data()
            _reset_form()
            sel_status_var.set("Saved — select another category or close.")
        except sqlite3.IntegrityError as exc:
            show_colorful_error(win, "Integrity Error", f"Cannot update category.\nDetail: {exc}")
        except Exception as exc:
            show_colorful_error(win, "Error", f"Failed to update budget category:\n{exc}")
            logger.exception("edit_budget_head: UPDATE failed for bh_id=%s", bh_id)

    def on_delete(_event=None) -> None:
        bh_id = selected_id["bh_id"]
        if bh_id is None:
            show_colorful_error(win, "No Selection", "Please select a budget head first.")
            return

        description = desc_var.get().strip()

        child_count = 0
        tx_count = 0
        try:
            with get_db_connection(BANK_DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM budget_head WHERE parent_bh_id = ?", (bh_id,))
                row = cur.fetchone()
                if row:
                    child_count = row[0]

                cur.execute("SELECT COUNT(*) FROM bank_transactions WHERE bh_id = ?", (bh_id,))
                row = cur.fetchone()
                if row:
                    tx_count = row[0]
        except sqlite3.Error as e:
            show_colorful_error(win, "Error", f"Could not check linked records: {e}")
            return

        impact_lines = []
        if child_count > 0:
            impact_lines.append(f"  • {child_count} child budget head(s) will become top-level (parent cleared).")
        if tx_count > 0:
            impact_lines.append(f"  • {tx_count} bank transaction(s) will lose their budget head label.")

        impact_note = "\n\nImpact of deletion:\n" + "\n".join(impact_lines) if impact_lines else ""

        confirm = show_colorful_yesno(
            win,
            "Confirm Delete",
            f"Are you sure you want to permanently delete:\n\n"
            f"  {description}{impact_note}\n\n"
            f"This action cannot be undone.",
        )
        if not confirm:
            return

        try:
            with get_db_connection(BANK_DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("PRAGMA foreign_keys = ON;")
                cur.execute("DELETE FROM budget_head WHERE bh_id = ?", (bh_id,))
                conn.commit()

            show_colorful_info(win, "Success", f"Budget head '{description}' deleted successfully.")
            load_data()
            _reset_form()
            sel_status_var.set("Deleted — select another category or close.")
        except sqlite3.Error as e:
            show_colorful_error(win, "Delete Failed", f"Database error: {e}")

    def _reset_form() -> None:
        selected_id["bh_id"] = None
        desc_var.set("")
        type_combo.set("")
        parent_combo.set("")

        desc_entry.config(state="disabled")
        type_combo.config(state="disabled")
        parent_combo.config(state="disabled")

        save_btn.config(state="disabled")
        delete_btn.config(state="disabled")

    btn_frame = tk.Frame(win, bg=bg_color, relief="ridge", bd=2, pady=6)
    btn_frame.pack(fill="x", padx=10, pady=(4, 6))

    submit_bg = _T.get("submit_bg", "#22c55e")
    submit_hover_bg = _T.get("submit_hover_bg", "#16a34a")
    cancel_bg = _T.get("cancel_bg", "#ef4444")
    cancel_hover_bg = _T.get("cancel_hover_bg", "#b91c1c")

    delete_btn = tk.Button(
        btn_frame,
        text="🗑️  DELETE SELECTED  🗑️",
        command=on_delete,
        font=("Comic Sans MS", 12, "bold"),
        bg=cancel_bg,
        fg="white",
        activeforeground="white",
        relief="raised",
        bd=3,
        padx=8,
        pady=4,
        cursor="hand2",
        state="disabled",
    )
    delete_btn.pack(side="left", padx=8)

    save_btn = tk.Button(
        btn_frame,
        text="💾  SAVE CHANGES  💾",
        command=on_save,
        font=("Comic Sans MS", 12, "bold"),
        bg=submit_bg,
        fg="white",
        activeforeground="white",
        relief="raised",
        bd=3,
        padx=8,
        pady=4,
        cursor="hand2",
        state="disabled",
    )
    save_btn.pack(side="right", padx=8)

    cancel_btn = tk.Button(
        btn_frame,
        text="❌  Cancel / Close  ❌",
        command=cleanup_and_close,
        font=("Comic Sans MS", 12, "bold"),
        bg=cancel_bg,
        fg="white",
        activeforeground="white",
        relief="raised",
        bd=3,
        padx=8,
        pady=4,
        cursor="hand2",
    )
    cancel_btn.pack(side="right", padx=4)

    apply_button_animations(delete_btn, cancel_bg, cancel_hover_bg)
    apply_button_animations(save_btn, submit_bg, submit_hover_bg)
    apply_button_animations(cancel_btn, cancel_bg, cancel_hover_bg)

    win.bind("<Control-Return>", lambda e: save_btn.invoke())
    win.bind("<Escape>", cleanup_and_close)
    win.protocol("WM_DELETE_WINDOW", cleanup_and_close)
    win.bind("<F1>", lambda e: None if (getattr(e, "state", 0) & 0x0004) else (show_help(win)))

    parent.wait_window(win)

    try:
        if parent.winfo_exists():
            try:
                parent.grab_set()
            except Exception:
                pass
    except tk.TclError:
        pass
