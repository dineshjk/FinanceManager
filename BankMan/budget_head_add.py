# -*- coding: utf-8 -*-
# C:\Data\Personal\Finance_and_Investment\finprog\FinanceManager\
# BankMan\budget_head_add.py

"""Module for adding budget head (income/expense category) entries.

The legacy ``AccountTypes`` table has been removed from the BankMan schema.
Account types are now a fixed enumeration stored as a CHECK constraint on
the ``accounts.type`` column (``'SAVINGS'``, ``'CURRENT'``, ``'OVERDRAFT'``).

This module is repurposed to manage the ``budget_head`` table, which provides
a hierarchical chart of income/expense categories for labelling transactions.

A top-level budget head has ``parent_bh_id = NULL``.
A sub-category points to an existing ``budget_head.bh_id`` as its parent,
forming an adjacency-list hierarchy of arbitrary depth.

The public entry-point ``add_account_type_main`` is retained under its
original name so that ``bank_data_entry_menu`` requires no import changes.
"""

from typing import Union
import tkinter as tk
from tkinter import ttk
from Shared.gui_utils import (
    apply_entry_theme,
    bind_tooltip,
    setup_footer_tooltip,
    flash_error,
    ACCOUNT_TYPE_ADD_UI_THEME,
    apply_button_animations,  # <-- Added missing import
)
from Shared.dialog_utils import (
    show_colorful_info,
    show_colorful_error,
    show_colorful_yesno,
)
from Shared.modal_utils import disable_parent
from Shared.window_manager import push_window, safe_close_modal
from .bank_db_utils import (
    add_budget_head as _db_add_budget_head,
    get_all_budget_heads as _db_get_budget_heads,
)
from Shared.globals import logger
from Shared.gui_progressive import progressive_selection

# Valid values for the bh_type column (mirrors the DB CHECK constraint).
_BH_TYPES = ["INCOME", "EXPENSE"]

# Label shown in the parent-category dropdown when no parent is chosen.
_NO_PARENT_LABEL = "(None \u2014 top level)"


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------


def _load_parent_choices() -> list[tuple[str, int | None]]:
    """Return ``[(display_label, bh_id | None), …]`` for the parent
    dropdown.

    The first entry is always the sentinel ``(None — top level, None)``
    which maps to ``parent_bh_id = NULL`` in the database.  Subsequent
    entries are fetched from ``budget_head`` ordered by type then name.
    """
    choices: list[tuple[str, int | None]] = [(_NO_PARENT_LABEL, None)]
    try:
        for bh_id, desc, bh_type in _db_get_budget_heads():
            choices.append((f"{desc}  [{bh_type}]", bh_id))
    except Exception:  # noqa: BLE001
        pass  # Return only the sentinel entry on any DB error
    return choices


# ---------------------------------------------------------------------------
# Module-level helpers (no closure variables; receive all context as params)
# ---------------------------------------------------------------------------


def show_help(win: tk.Toplevel, on_escape) -> None:
    """Launch the help sub-window for the Budget Category Entry dialog."""
    win.unbind("<Escape>")

    help_win = tk.Toplevel(win)
    try:
        help_win.transient(win)
    except (tk.TclError, AttributeError) as _exc:
        logger.debug("help_win.transient failed: %s", _exc)
    help_win.title("Help — Budget Category Entry")
    help_win.configure(bg=ACCOUNT_TYPE_ADD_UI_THEME["help_bg"])
    help_win.geometry("660x600")
    help_win.resizable(False, False)
    help_win.grab_set()
    push_window(help_win, win)
    try:
        help_win.focus_set()
    except tk.TclError:
        pass

    tk.Label(
        help_win,
        text="Budget Category Entry Help",
        font=("Helvetica", 16, "bold"),
        bg=ACCOUNT_TYPE_ADD_UI_THEME["help_header_bg"],
        fg="white",
        pady=8,
    ).pack(fill="x")
    body = tk.Frame(
        help_win,
        bg=ACCOUNT_TYPE_ADD_UI_THEME["help_bg"],
        padx=12,
        pady=12,
    )
    body.pack(fill="both", expand=True)

    text = tk.Text(
        body,
        wrap="word",
        bg=ACCOUNT_TYPE_ADD_UI_THEME["help_bg"],
        bd=0,
        padx=6,
        pady=6,
        font=("Helvetica", 11),
        height=16,
    )
    text.pack(fill="both", expand=True)

    help_lines = [
        "• This form adds a new budget category to the database.",
        "• Budget categories label transactions as INCOME or EXPENSE.",
        "• Categories can be nested: choose a Parent Category to create a "
        "sub-category under an existing top-level entry.",
        "",
        "Fields:",
        "  Description (required): Name of the category,",
        "    e.g. 'Salary', 'Freelance', 'Groceries', 'Dining Out'.",
        "  Type (required): INCOME or EXPENSE.",
        "  Parent Category (optional): Leave as '(None — top level)'",
        "    for a root category, or pick a parent for a sub-category.",
        "",
        "Hotkeys:",
        "  F1: This screen (Help)",
        "  F2: Session Budget Categories",
        "  Escape: Close this window without saving",
        "  Enter: Advance to next field / activate button",
    ]
    text.insert("1.0", "\n".join(help_lines))
    text.config(state="disabled")

    def close_help(_e=None):
        safe_close_modal(help_win, win)
        win.bind("<Escape>", on_escape)
        return "break"

    help_win.bind("<Escape>", close_help)
    help_win.protocol("WM_DELETE_WINDOW", close_help)

    tk.Button(
        help_win,
        text="Close",
        command=close_help,
        font=("Helvetica", 11, "bold"),
        bg=ACCOUNT_TYPE_ADD_UI_THEME["help_btn_bg"],
        fg="white",
        padx=12,
        pady=6,
        cursor="hand2",
    ).pack(side="bottom", pady=10)


def show_session_budget_heads(
    win: tk.Toplevel,
    current_session_heads: dict,
    on_escape,
) -> None:
    """Launch the session budget categories viewer sub-window."""
    if not current_session_heads:
        try:
            show_colorful_info(
                win,
                "No Budget Categories",
                "No budget categories recorded in this session yet.",
            )
        except tk.TclError:
            pass
        return

    win.unbind("<Escape>")

    session_entries = list(current_session_heads.items())
    idx = {"i": 0}

    viewer = tk.Toplevel(win)
    viewer.title("Session Budget Categories Viewer")
    viewer.transient(win)
    viewer.grab_set()
    viewer.resizable(False, False)
    viewer.geometry("520x280")
    push_window(viewer, win)
    try:
        viewer.focus_set()
    except tk.TclError:
        pass

    content = tk.Frame(viewer)
    content.pack(fill="both", expand=True, padx=10, pady=10)

    left_btn = tk.Button(content, text="\u25c4", width=3)
    left_btn.pack(side="left", padx=(10, 5), pady=6)
    right_btn = tk.Button(content, text="\u25ba", width=3)
    right_btn.pack(side="right", padx=(5, 10), pady=6)

    info_text = tk.Text(
        content,
        wrap="word",
        height=7,
        bg=ACCOUNT_TYPE_ADD_UI_THEME["session_bg"],
        bd=0,
        relief="flat",
    )
    info_text.pack(fill="both", expand=True, padx=10, pady=6)
    info_text.tag_configure(
        "label",
        font=("Helvetica", 11, "bold"),
        foreground=ACCOUNT_TYPE_ADD_UI_THEME["session_label_fg"],
    )
    info_text.tag_configure(
        "value",
        font=("Helvetica", 11),
        foreground=ACCOUNT_TYPE_ADD_UI_THEME["session_value_fg"],
    )
    info_text.config(state="disabled")

    status_label = tk.Label(
        content,
        text="",
        font=("Helvetica", 10, "bold"),
        bg=ACCOUNT_TYPE_ADD_UI_THEME["session_bg"],
    )
    status_label.pack(side="bottom", pady=(0, 6))

    def update_view():
        i = idx["i"]
        sr, t = session_entries[i]
        info_text.config(state="normal")
        info_text.delete("1.0", "end")
        info_text.insert("end", "Sr. No: ", "label")
        info_text.insert("end", f"{sr}\n", "value")
        info_text.insert("end", "Description: ", "label")
        info_text.insert("end", f"{t.get('Description')}\n", "value")
        info_text.insert("end", "Type: ", "label")
        info_text.insert("end", f"{t.get('Type')}\n", "value")
        info_text.insert("end", "Parent: ", "label")
        info_text.insert("end", f"{t.get('Parent') or '\u2014'}\n", "value")
        info_text.config(state="disabled")

        left_btn.config(state="disabled" if i == 0 else "normal")
        if i >= len(session_entries) - 1:
            right_btn.config(state="disabled")
            status_label.config(
                text="Last Entry",
                fg=ACCOUNT_TYPE_ADD_UI_THEME["session_alert_fg"],
                font=("Helvetica", 10, "bold"),
            )
        else:
            right_btn.config(state="normal")
            status_label.config(
                text="",
                fg=ACCOUNT_TYPE_ADD_UI_THEME["session_ok_fg"]
            )

    def go_prev(_event=None):
        if idx["i"] > 0:
            idx["i"] -= 1
            update_view()

    def go_next(_event=None):
        if idx["i"] < len(session_entries) - 1:
            idx["i"] += 1
            update_view()

    left_btn.config(command=go_prev)
    right_btn.config(command=go_next)
    viewer.bind("<Left>", lambda e: go_prev())
    viewer.bind("<Right>", lambda e: go_next())

    def close_viewer(_event=None):
        safe_close_modal(viewer, win)
        win.bind("<Escape>", on_escape)
        return "break"

    viewer.bind("<Escape>", close_viewer)
    viewer.protocol("WM_DELETE_WINDOW", close_viewer)
    viewer.bind("<Return>", close_viewer)

    ok_btn = tk.Button(content, text="OK", width=10, command=close_viewer)
    ok_btn.pack(side="bottom", pady=(0, 8))
    try:
        ok_btn.focus_set()
    except tk.TclError:
        pass
    update_view()


def on_submit(
    desc_entry: tk.Entry,
    type_combo: ttk.Combobox,
    parent_combo: ttk.Combobox,
    parent_choices: list,
    win: tk.Toplevel,
    current_session_heads: dict,
    refresh_callback,
) -> None:
    """Validate inputs, persist the new budget head, and reset the form."""
    description = desc_entry.get().strip()
    bh_type = type_combo.get().strip()
    parent_label = parent_combo.get().strip()

    if not description:
        show_colorful_error(
            win,
            "Validation Error",
            "Description is required."
        )
        flash_error(desc_entry)
        return

    if bh_type not in _BH_TYPES:
        show_colorful_error(
            win,
            "Validation Error",
            "Please select a valid Type: INCOME or EXPENSE.",
        )
        return

    # Resolve the selected parent label back to its bh_id (or None).
    parent_bh_id: int | None = None
    parent_display: str | None = None
    is_valid_parent = False

    for label, bh_id in parent_choices:
        if label == parent_label:
            parent_bh_id = bh_id
            parent_display = None if bh_id is None else label
            is_valid_parent = True
            break

    if not is_valid_parent:
        show_colorful_error(
            win,
            "Validation Error",
            "Please select a valid Parent Category from the list.",
        )
        flash_error(parent_combo)
        return

    try:
        _db_add_budget_head(description, bh_type, parent_bh_id)
        sr_no = len(current_session_heads) + 1
        current_session_heads[sr_no] = {
            "Description": description,
            "Type": bh_type,
            "Parent": parent_display,
        }
        show_colorful_info(
            win,
            "Success",
            f"Budget category '{description}' added successfully.",
        )
        desc_entry.delete(0, tk.END)
        type_combo.set("")
        refresh_callback()
        parent_combo.set(_NO_PARENT_LABEL)
        desc_entry.focus_set()
    except Exception as e:  # noqa: BLE001
        msg = f"Failed to add budget category: {e}"
        show_colorful_error(win, "Error", msg)


# ---------------------------------------------------------------------------
# Entry point
# (name retained for backward compatibility with bank_data_entry_menu)
# ---------------------------------------------------------------------------


def add_account_type_main(
    parent: Union[tk.Toplevel, tk.Tk],
    calling_button: tk.Widget | None = None,
) -> None:
    """Launch the Add Budget Category window.

    The function name is kept for compatibility with ``bank_data_entry_menu``;
    it now manages ``budget_head`` entries instead of the legacy AccountTypes
    table (which no longer exists in the BankMan schema).
    """
    # --- Button colour constants ---
    submitusualbg = "#22c55e"
    submitactivebg = "#16a34a"
    cancelusualbg = "#ef4444"
    cancelactivebg = "#b91c1c"

    # --- Window setup ---
    disable_parent(parent, calling_button=calling_button)

    current_session_heads: dict = {}
    win = tk.Toplevel(parent)
    win.title("\U0001f4ca Budget Category Entry \U0001f4ca")
    win.geometry("720x390")
    win.resizable(False, False)
    win.configure(bg=ACCOUNT_TYPE_ADD_UI_THEME["main_bg"])
    win.transient(parent)
    win.grab_set()
    win.focus_set()
    try:
        push_window(win, parent)
    except (RuntimeError, tk.TclError) as _exc:
        logger.debug("push_window failed: %s", _exc)

    # Footer tooltip (packed first so it anchors to the absolute bottom).
    tooltip_var = setup_footer_tooltip(win)

    # --- Closure helpers (capture win / parent / calling_button) ---
    def cleanup_and_close(_event=None):
        return safe_close_modal(win, parent, calling_button)

    def on_escape(_event=None):
        return cleanup_and_close()

    # --- Header ---
    header_frame = tk.Frame(
        win,
        bg=ACCOUNT_TYPE_ADD_UI_THEME["header_bg"],
        relief="raised",
        bd=3,
    )
    header_frame.pack(fill="x", padx=5, pady=0)

    tk.Label(
        header_frame,
        text="\u2795 Add Budget Category \u2795",
        font=("Helvetica", 18, "bold"),
        bg=ACCOUNT_TYPE_ADD_UI_THEME["header_bg"],
        fg=ACCOUNT_TYPE_ADD_UI_THEME["header_fg"],
        relief="ridge",
        bd=2,
    ).pack(fill="x", pady=10)

    # --- Form ---
    form_frame = tk.Frame(win, bg=ACCOUNT_TYPE_ADD_UI_THEME["main_bg"])
    form_frame.pack(pady=10, padx=10)

    # Row 0 — Description (required)
    ttk.Label(
        form_frame,
        text="Description:",
        font=("Helvetica", 14),
        background=ACCOUNT_TYPE_ADD_UI_THEME["label_bg"],
    ).grid(row=0, column=0, sticky="w", padx=5, pady=5)
    desc_entry = tk.Entry(form_frame, width=55)
    desc_entry.grid(row=0, column=1, padx=5, pady=5)
    apply_entry_theme(desc_entry)
    tip_desc = "Category name, e.g. 'Salary', 'Groceries' (required)."
    bind_tooltip(desc_entry, tooltip_var, tip_desc)

    # Row 1 — Type: INCOME or EXPENSE (required)
    ttk.Label(
        form_frame,
        text="Type:",
        font=("Helvetica", 14),
        background=ACCOUNT_TYPE_ADD_UI_THEME["label_bg"],
    ).grid(row=1, column=0, sticky="w", padx=5, pady=5)
    type_combo = ttk.Combobox(form_frame, values=_BH_TYPES, width=53)
    type_combo.grid(row=1, column=1, padx=5, pady=5)
    apply_entry_theme(type_combo)
    progressive_selection(type_combo, _BH_TYPES)
    tip_type = "INCOME for money received; EXPENSE for money spent (required)."
    bind_tooltip(type_combo, tooltip_var, tip_type)

    def on_type_focus_out(_event=None):
        try:
            if not win.winfo_exists():
                return
        except (tk.TclError, NameError):
            return
        typed = type_combo.get().strip()
        if typed and typed not in _BH_TYPES:
            show_colorful_error(
                win,
                "Invalid Type",
                f"'{typed}' is not valid. Please choose INCOME or EXPENSE.",
            )
            flash_error(type_combo)
            type_combo.focus_set()

    type_combo.bind("<FocusOut>", on_type_focus_out, add="+")

    # Row 2 — Parent Category (optional; first choice = top-level / NULL)
    parent_choices = _load_parent_choices()
    parent_labels = [label for label, _ in parent_choices]

    ttk.Label(
        form_frame,
        text="Parent Category:",
        font=("Helvetica", 14),
        background=ACCOUNT_TYPE_ADD_UI_THEME["label_bg"],
    ).grid(row=2, column=0, sticky="w", padx=5, pady=5)
    parent_combo = ttk.Combobox(form_frame, values=parent_labels, width=53)
    parent_combo.set(_NO_PARENT_LABEL)
    parent_combo.grid(row=2, column=1, padx=5, pady=5)
    apply_entry_theme(parent_combo)
    progressive_selection(parent_combo, parent_labels)
    tip_parent = "Optional: pick a parent to nest this as a sub-category."
    bind_tooltip(parent_combo, tooltip_var, tip_parent)

    def _refresh_parent_combo():
        new_choices = _load_parent_choices()
        parent_choices.clear()
        parent_choices.extend(new_choices)
        parent_labels.clear()
        parent_labels.extend(label for label, _ in new_choices)
        parent_combo["values"] = list(parent_labels)
        progressive_selection(parent_combo, list(parent_labels))

    def on_parent_focus_out(_event=None):
        try:
            if not win.winfo_exists():
                return
        except (tk.TclError, NameError):
            return
        typed = parent_combo.get().strip()
        if not typed or typed == _NO_PARENT_LABEL:
            return
        if typed not in parent_labels:
            response = show_colorful_yesno(
                win,
                "Category Not Found",
                f"'{typed}' was not found. Add a new budget category " "now?",
            )
            if response:
                add_account_type_main(win)
                _refresh_parent_combo()
                parent_combo.focus_set()
            else:
                show_colorful_error(
                    win,
                    "Invalid Selection",
                    "Please select a valid category from the list.",
                )
                flash_error(parent_combo)
                parent_combo.focus_set()

    parent_combo.bind("<FocusOut>", on_parent_focus_out, add="+")

    # --- Button frame ---
    btn_frame = tk.Frame(
        win,
        pady=10,
        bg=ACCOUNT_TYPE_ADD_UI_THEME["main_bg"],
        relief="ridge",
        bd=2,
    )
    btn_frame.pack(fill="x", anchor="e", padx=10)

    # Using Theme Dictionary for Button Backgrounds
    submit_button = tk.Button(
        btn_frame,
        text="✅ SUBMIT ✅",
        width=12,
        font=("Comic Sans MS", 12, "bold"),
        bg=ACCOUNT_TYPE_ADD_UI_THEME["submit_bg"],
        fg="white",
        activeforeground="white",
        relief="raised",
        bd=3,
        cursor="hand2",
        command=lambda: on_submit(
            desc_entry,
            type_combo,
            parent_combo,
            parent_choices,
            win,
            current_session_heads,
            _refresh_parent_combo,
        ),
    )
    submit_button.pack(side="right", padx=5)

    # Using Theme Dictionary for Button Backgrounds
    cancel_btn = tk.Button(
        btn_frame,
        text="❌ Cancel ❌",
        width=12,
        font=("Comic Sans MS", 12, "bold"),
        bg=ACCOUNT_TYPE_ADD_UI_THEME["cancel_bg"],
        fg="white",
        activeforeground="white",
        relief="raised",
        bd=3,
        cursor="hand2",
        command=cleanup_and_close,
    )
    cancel_btn.pack(side="right", padx=5)

    # --- Hint frame ---
    hint_frame = tk.Frame(
        win,
        pady=10,
        bg=ACCOUNT_TYPE_ADD_UI_THEME["main_bg"],
        relief="ridge",
        bd=2
    )
    hint_frame.pack(fill="x", anchor="e", padx=10)

    hint_text = "Press F1 for help, F2 for session entries, Esc to close."
    tk.Label(
        hint_frame,
        text=hint_text,
        font=("Helvetica", 16),
        bg=ACCOUNT_TYPE_ADD_UI_THEME["main_bg"],
    ).pack(side="left", padx=8)

    # --- Bindings (Cleaned up using DRY helper function) ---
    apply_button_animations(
        submit_button,
        ACCOUNT_TYPE_ADD_UI_THEME["submit_bg"],
        ACCOUNT_TYPE_ADD_UI_THEME["submit_hover_bg"],
    )
    apply_button_animations(
        cancel_btn,
        ACCOUNT_TYPE_ADD_UI_THEME["cancel_bg"],
        ACCOUNT_TYPE_ADD_UI_THEME["cancel_hover_bg"],
    )

    # --- Tab-order key bindings ---
    desc_entry.bind("<Return>", lambda e: type_combo.focus_set())
    type_combo.bind("<Return>", lambda e: parent_combo.focus_set())
    parent_combo.bind("<Return>", lambda e: submit_button.focus_set())
    submit_button.bind(
        "<Return>",
        lambda e: on_submit(
            desc_entry,
            type_combo,
            parent_combo,
            parent_choices,
            win,
            current_session_heads,
            _refresh_parent_combo,
        ),
    )

    win.bind("<F1>", lambda e: show_help(win, on_escape))
    win.bind(
        "<F2>",
        lambda e: show_session_budget_heads(
            win, current_session_heads, on_escape
        ),
    )
    win.bind("<Escape>", on_escape)
    win.protocol("WM_DELETE_WINDOW", cleanup_and_close)

    win.after(100, desc_entry.focus_set)
