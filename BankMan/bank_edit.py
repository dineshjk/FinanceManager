# -*- coding: utf-8 -*-
# C:\Data\Personal\Finance_and_Investment\finprog\FinanceManager\BankMan\bank_edit.py

"""
Module for editing existing bank records in the ``banks`` table.

Layout
------
The window is split into two sections:

1. **Bank list** — a sortable Treeview showing all banks (Name, Branch,
   IFSC, MICR).  Click a row to load it into the edit form.

2. **Edit form** — four Entry widgets (Bank Name, Branch, IFSC, MICR)
   mirroring the layout of ``banks_add.py``.  Fields are disabled until a
   bank is selected.  Pressing *Save Changes* (or Enter in the last field)
   runs the UPDATE query.

Theme
-----
Uses ``BANK_EDIT_UI_THEME`` — a rose / magenta palette that is visually
distinct from ``BANK_ADD_UI_THEME`` (blue) while sharing the same structural
key names so all the ``apply_entry_theme`` / ``bind_tooltip`` helpers work
without modification.
"""

from typing import Union
import sqlite3
import tkinter as tk
from tkinter import ttk

from Shared.gui_utils import (
    apply_button_animations,
    apply_entry_theme,
    BANK_EDIT_UI_THEME,
    bind_tooltip,
    flash_error,
    setup_footer_tooltip,
    universal_tree_sort,
)
from Shared.dialog_utils import show_colorful_error, show_colorful_info
from Shared.modal_utils import disable_parent
from Shared.window_manager import push_window, safe_close_modal
from .bank_db_utils import db_update_bank, get_all_banks
from Shared.globals import logger

_T = BANK_EDIT_UI_THEME


# ---------------------------------------------------------------------------



# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def edit_bank(
    parent: Union[tk.Toplevel, tk.Tk],
    calling_button: tk.Widget | None = None,
) -> None:
    """Open the Edit Bank modal window.

    The window shows all banks in a sortable list.  Selecting a row
    pre-fills the edit form below.  *Save Changes* persists the update
    via ``db_update_bank``; the list refreshes automatically.
    """
    disable_parent(parent, calling_button=calling_button)

    eb_win = tk.Toplevel(parent)
    eb_win.title("✏️  Edit Bank  ✏️")
    eb_win.geometry("780x585")
    eb_win.resizable(False, False)
    eb_win.configure(bg=_T["main_bg"])
    eb_win.transient(parent)
    eb_win.grab_set()
    eb_win.focus_set()
    try:
        push_window(eb_win, parent)
    except (RuntimeError, tk.TclError) as exc:
        logger.debug("push_window failed: %s", exc)

    # Footer tooltip — packed first so it anchors to the absolute bottom.
    tooltip_var = setup_footer_tooltip(eb_win)

    # ------------------------------------------------------------------
    # Close helper
    # ------------------------------------------------------------------
    def cleanup_and_close(_event=None):
        return safe_close_modal(eb_win, parent, calling_button)

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------
    header_frame = tk.Frame(eb_win, bg=_T["header_bg"], relief="raised", bd=3)
    header_frame.pack(fill="x", padx=5, pady=(5, 0))

    tk.Label(
        header_frame,
        text="✏️   Edit Bank   ✏️",
        font=("Helvetica", 18, "bold"),
        bg=_T["header_bg"],
        fg=_T["header_fg"],
        relief="ridge",
        bd=2,
    ).pack(fill="x", pady=10)

    # ------------------------------------------------------------------
    # Instruction row
    # ------------------------------------------------------------------
    instr_frame = tk.Frame(eb_win, bg=_T["header_bg"])
    instr_frame.pack(fill="x", padx=5, pady=(0, 2))

    tk.Label(
        instr_frame,
        text="Click a bank row below to load it into the edit form.",
        font=("Helvetica", 11, "italic"),
        bg=_T["header_bg"],
        fg="#FFD1E8",
    ).pack(anchor="w", padx=10, pady=4)

    # ------------------------------------------------------------------
    # Treeview — bank list
    # ------------------------------------------------------------------
    tree_frame = tk.Frame(eb_win, bg=_T["main_bg"], bd=1, relief="ridge")
    tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 4))

    tree_scroll = ttk.Scrollbar(tree_frame)
    tree_scroll.pack(side="right", fill="y")

    style = ttk.Style()
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure(
        "BankEdit.Treeview",
        background="#FFF5F8",
        foreground="#2C0015",
        fieldbackground="#FFF5F8",
        rowheight=26,
        font=("Helvetica", 11),
    )
    style.configure(
        "BankEdit.Treeview.Heading",
        background=_T["header_bg"],
        foreground="white",
        font=("Helvetica", 11, "bold"),
    )
    style.map(
        "BankEdit.Treeview",
        background=[("selected", _T["hover_bg"])],
        foreground=[("selected", "white")],
    )

    cols = ("ID", "Name", "Branch", "IFSC", "MICR")
    tree = ttk.Treeview(
        tree_frame,
        columns=cols,
        show="headings",
        yscrollcommand=tree_scroll.set,
        style="BankEdit.Treeview",
        height=5,
    )
    tree_scroll.config(command=tree.yview)

    col_setup = {
        "ID": (0, tk.NO, "center"),
        "Name": (250, tk.YES, "w"),
        "Branch": (200, tk.YES, "w"),
        "IFSC": (130, tk.NO, "center"),
        "MICR": (120, tk.NO, "center"),
    }
    for col, (width, stretch, anchor) in col_setup.items():
        tree.heading(
            col,
            text=col,
            command=lambda c=col: universal_tree_sort(tree, c, False),
        )
        tree.column(col, width=width, stretch=stretch, anchor=anchor)

    tree.pack(fill="both", expand=True)

    # ------------------------------------------------------------------
    # Data load / reload
    # ------------------------------------------------------------------
    def load_banks() -> None:
        """Clear the treeview and repopulate from the database."""
        for item in tree.get_children():
            tree.delete(item)
        try:
            for row in get_all_banks():
                # row = (b_id, name, branch, IFSC, MICR)
                tree.insert("", "end", values=row)
        except sqlite3.Error as exc:
            logger.error("edit_bank: failed to load banks: %s", exc)

    load_banks()

    # ------------------------------------------------------------------
    # Divider and "selected bank" status label
    # ------------------------------------------------------------------
    tk.Frame(eb_win, height=2, bg=_T["header_bg"]).pack(fill="x", padx=5, pady=(2, 0))

    sel_label_frame = tk.Frame(eb_win, bg=_T["header_bg"])
    sel_label_frame.pack(fill="x", padx=5, pady=0)

    sel_status_var = tk.StringVar(
        value="No bank selected — click a row in the list above."
    )
    tk.Label(
        sel_label_frame,
        textvariable=sel_status_var,
        font=("Helvetica", 11, "bold"),
        bg=_T["header_bg"],
        fg="#FFD1E8",
    ).pack(anchor="w", padx=10, pady=4)

    # ------------------------------------------------------------------
    # Edit form
    # ------------------------------------------------------------------
    selected_id: dict[str, int | None] = {"b_id": None}

    form_frame = tk.Frame(eb_win, bg=_T["main_bg"])
    form_frame.pack(fill="x", padx=10, pady=4)

    name_var = tk.StringVar()
    branch_var = tk.StringVar()
    ifsc_var = tk.StringVar()
    micr_var = tk.StringVar()

    def _make_field(
        row: int,
        label_text: str,
        str_var: tk.StringVar,
        tip: str,
    ) -> tk.Entry:
        ttk.Label(
            form_frame,
            text=label_text,
            font=("Helvetica", 13),
            background=_T["label_bg"],
        ).grid(row=row, column=0, sticky="w", padx=5, pady=4)
        entry = tk.Entry(form_frame, width=65, textvariable=str_var)
        entry.grid(row=row, column=1, padx=5, pady=4, sticky="w")
        apply_entry_theme(entry)
        bind_tooltip(entry, tooltip_var, tip)
        return entry

    name_entry = _make_field(
        0, "Bank Name:", name_var, "Full legal name of the institution (required)."
    )
    branch_entry = _make_field(
        1, "Branch:", branch_var, "Branch name or location (optional)."
    )
    ifsc_entry = _make_field(
        2, "IFSC:", ifsc_var, "11-character IFSC code, e.g. SBIN0001234 (optional)."
    )
    micr_entry = _make_field(
        3, "MICR:", micr_var, "9-digit MICR code from cheque leaves (optional)."
    )

    all_entries = (name_entry, branch_entry, ifsc_entry, micr_entry)
    for e in all_entries:
        e.config(state="disabled")

    # ------------------------------------------------------------------
    # Treeview selection handler
    # ------------------------------------------------------------------
    def on_tree_select(_event=None) -> None:
        sel = tree.selection()
        if not sel:
            return
        vals = tree.item(sel[0])["values"]
        b_id, name, branch, ifsc, micr = (vals + [None] * 5)[:5]

        selected_id["b_id"] = b_id
        name_var.set(name or "")
        branch_var.set(branch or "")
        ifsc_var.set(ifsc or "")
        micr_var.set(micr or "")

        for e in all_entries:
            e.config(state="normal")
        save_btn.config(state="normal")
        sel_status_var.set(f"Editing:  {name}")
        name_entry.focus_set()

    tree.bind("<<TreeviewSelect>>", on_tree_select)
    tree.bind("<Double-1>", on_tree_select)

    # ------------------------------------------------------------------
    # Tab-order within the form
    # ------------------------------------------------------------------
    name_entry.bind("<Return>", lambda _e: branch_entry.focus_set())
    branch_entry.bind("<Return>", lambda _e: ifsc_entry.focus_set())
    ifsc_entry.bind("<Return>", lambda _e: micr_entry.focus_set())
    micr_entry.bind("<Return>", lambda _e: save_btn.focus_set())

    # ------------------------------------------------------------------
    # Save handler
    # ------------------------------------------------------------------
    def on_save(_event=None) -> None:
        if selected_id["b_id"] is None:
            show_colorful_error(
                eb_win,
                "No Selection",
                "Please select a bank from the list first.",
            )
            return

        name = name_var.get().strip()
        branch = branch_var.get().strip() or None
        ifsc = ifsc_var.get().strip() or None
        micr = micr_var.get().strip() or None

        if not name:
            show_colorful_error(
                eb_win,
                "Validation Error",
                "Bank Name is required.",
            )
            flash_error(name_entry)
            return

        try:
            db_update_bank(selected_id["b_id"], name, branch, ifsc, micr)
        except Exception as exc:
            show_colorful_error(
                eb_win,
                "Error",
                f"Failed to update bank:\n{exc}",
            )
            logger.exception(
                "edit_bank: UPDATE failed for b_id=%s", selected_id["b_id"]
            )
            return

        show_colorful_info(
            eb_win,
            "Success",
            f"Bank '{name}' updated successfully.",
        )
        # Refresh list and reset form
        load_banks()
        selected_id["b_id"] = None
        for var in (name_var, branch_var, ifsc_var, micr_var):
            var.set("")
        for e in all_entries:
            e.config(state="disabled")
        save_btn.config(state="disabled")
        sel_status_var.set("Saved — select another bank or close.")

    save_btn: tk.Button  # forward declaration for on_tree_select closure

    # ------------------------------------------------------------------
    # Button frame
    # ------------------------------------------------------------------
    btn_frame = tk.Frame(eb_win, bg=_T["main_bg"], relief="ridge", bd=2, pady=6)
    btn_frame.pack(fill="x", padx=10, pady=(4, 6))

    save_btn = tk.Button(
        btn_frame,
        text="💾  SAVE CHANGES  💾",
        command=on_save,
        font=("Comic Sans MS", 12, "bold"),
        bg=_T["submit_bg"],
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
        bg=_T["cancel_bg"],
        fg="white",
        activeforeground="white",
        relief="raised",
        bd=3,
        padx=8,
        pady=4,
        cursor="hand2",
    )
    cancel_btn.pack(side="right", padx=4)

    apply_button_animations(save_btn, _T["submit_bg"], _T["submit_hover_bg"])
    apply_button_animations(cancel_btn, _T["cancel_bg"], _T["cancel_hover_bg"])

    # ------------------------------------------------------------------
    # Window-level bindings
    # ------------------------------------------------------------------
    eb_win.bind("<Escape>", cleanup_and_close)
    eb_win.protocol("WM_DELETE_WINDOW", cleanup_and_close)

    parent.wait_window(eb_win)

    # Restore grab to caller so it doesn't fall out of focus.
    try:
        if parent.winfo_exists():
            parent.grab_set()
    except tk.TclError:
        pass
