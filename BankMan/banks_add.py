# -*- coding: utf-8 -*-
# C:\Data\Personal\Finance_and_Investment\finprog\FinanceManager\BankMan\banks_add.py

"""
Module for adding new banks to the database.
"""

from typing import Union
import tkinter as tk
from tkinter import ttk
from Shared.gui_utils import (
    apply_entry_theme,
    bind_tooltip,
    setup_footer_tooltip,
    flash_error,
    BANK_ADD_UI_THEME,
    apply_button_animations,  # <-- Added the animation helper import
)
from Shared.dialog_utils import show_colorful_info, show_colorful_error
from Shared.modal_utils import disable_parent
from Shared.window_manager import push_window, safe_close_modal
from .bank_db_utils import db_add_bank as _db_add_bank
from Shared.globals import logger

# ---------------------------------------------------------------------------
# Module-level helpers (no closure variables; receive all context as params)
# ---------------------------------------------------------------------------


def show_help(ba_win: tk.Toplevel, on_escape) -> None:
    """Launch the help sub-window for the Bank Entry dialog."""
    ba_win.unbind("<Escape>")

    help_win = tk.Toplevel(ba_win)
    try:
        help_win.transient(ba_win)
    except (tk.TclError, AttributeError) as _exc:
        logger.debug("help_win.transient failed: %s", _exc)
    help_win.title("Help — Bank Entry")

    # Using Theme Dictionary
    help_win.configure(bg=BANK_ADD_UI_THEME["help_bg"])
    help_win.geometry("640x620")
    help_win.resizable(False, False)
    help_win.grab_set()
    push_window(help_win, ba_win)
    try:
        help_win.focus_set()
    except tk.TclError:
        pass

    tk.Label(
        help_win,
        text="Bank Entry Help",
        font=("Helvetica", 16, "bold"),
        bg=BANK_ADD_UI_THEME["help_header_bg"],  # Using Theme Dictionary
        fg="white",
        pady=8,
    ).pack(fill="x")

    body = tk.Frame(
        help_win, bg=BANK_ADD_UI_THEME["help_bg"], padx=12, pady=12
    )  # Using Theme Dictionary
    body.pack(fill="both", expand=True)

    text = tk.Text(
        body,
        wrap="word",
        bg=BANK_ADD_UI_THEME["help_bg"],  # Using Theme Dictionary
        bd=0,
        padx=6,
        pady=6,
        font=("Helvetica", 11),
        height=12,
    )
    text.pack(fill="both", expand=True)

    help_lines = [
        "• This is a data entry form for a new bank.",
        "",
        "Fields:",
        "  Bank Name (required): Full legal name of the institution.",
        "  Branch (optional): Branch name or location.",
        "  IFSC (optional): 11-character RBI code, e.g. SBIN0001234.",
        "  MICR (optional): 9-digit code printed on cheque leaves.",
        "",
        "Hotkeys:",
        "  F1: This screen (Help)",
        "  F2: Session Banks",
        "  Escape: Rollback the Current Bank Entry and Close",
        "  Enter/Space: Execute button or Advance field",
    ]
    text.insert("1.0", "\n".join(help_lines))
    text.config(state="disabled")

    def close_help(_e=None):
        safe_close_modal(help_win, ba_win)
        ba_win.bind("<Escape>", on_escape)
        return "break"

    help_win.bind("<Escape>", close_help)
    help_win.protocol("WM_DELETE_WINDOW", close_help)

    btn = tk.Button(
        help_win,
        text="Close",
        command=close_help,
        font=("Helvetica", 11, "bold"),
        bg=BANK_ADD_UI_THEME["help_btn_bg"],  # Using Theme Dictionary
        fg="white",
        padx=12,
        pady=6,
        cursor="hand2",
    )
    btn.pack(side="bottom", pady=10)
    try:
        btn.focus_set()
    except tk.TclError:
        pass


def show_session_banks(
    ba_win: tk.Toplevel,
    current_session_banks: dict,
    on_escape,
) -> None:
    """Launch the session-banks viewer sub-window."""
    if not current_session_banks:
        try:
            show_colorful_info(
                ba_win,
                "No Banks",
                "No banks have been recorded in this session yet.",
            )
        except tk.TclError:
            pass
        return

    ba_win.unbind("<Escape>")

    session_entries = list(current_session_banks.items())
    idx = {"i": 0}

    viewer = tk.Toplevel(ba_win)
    viewer.title("Session Banks Viewer")
    viewer.transient(ba_win)
    viewer.grab_set()
    viewer.resizable(False, False)
    viewer.geometry("520x260")
    push_window(viewer, ba_win)
    try:
        viewer.focus_set()
    except tk.TclError:
        pass

    content = tk.Frame(viewer)
    content.pack(fill="both", expand=True, padx=10, pady=10)

    left_btn = tk.Button(content, text="◀", width=3)
    left_btn.pack(side="left", padx=(10, 5), pady=6)
    right_btn = tk.Button(content, text="▶", width=3)
    right_btn.pack(side="right", padx=(5, 10), pady=6)

    info_text = tk.Text(
        content,
        wrap="word",
        height=8,
        bg=BANK_ADD_UI_THEME["session_bg"],
        bd=0,
        relief="flat",  # Using Theme Dictionary
    )
    info_text.pack(fill="both", expand=True, padx=10, pady=6)

    # Using Theme Dictionary for all tags
    info_text.tag_configure(
        "label",
        font=("Helvetica", 11, "bold"),
        foreground=BANK_ADD_UI_THEME["session_label_fg"],
    )
    info_text.tag_configure(
        "value",
        font=("Helvetica", 11),
        foreground=BANK_ADD_UI_THEME["session_value_fg"],
    )
    info_text.tag_configure(
        "net",
        font=("Helvetica", 11, "bold"),
        foreground=BANK_ADD_UI_THEME["session_alert_fg"],
    )
    info_text.config(state="disabled")

    status_label = tk.Label(
        content,
        text="",
        font=("Helvetica", 10, "bold"),
        bg=BANK_ADD_UI_THEME["session_bg"],  # Using Theme Dictionary
    )
    status_label.pack(side="bottom", pady=(0, 6))

    def update_view():
        i = idx["i"]
        sr, t = session_entries[i]
        info_text.config(state="normal")
        info_text.delete("1.0", "end")
        info_text.insert("end", "Sr. No: ", "label")
        info_text.insert("end", f"{sr}\n", "value")
        info_text.insert("end", "Bank: ", "label")
        info_text.insert("end", f"{t.get('Bank')}\n", "value")
        info_text.insert("end", "Branch: ", "label")
        info_text.insert("end", f"{t.get('Branch') or '—'}\n", "value")
        info_text.insert("end", "IFSC: ", "label")
        info_text.insert("end", f"{t.get('IFSC') or '—'}\n", "value")
        info_text.insert("end", "MICR: ", "label")
        info_text.insert("end", f"{t.get('MICR') or '—'}\n", "value")
        info_text.config(state="disabled")

        left_btn.config(state="disabled" if i == 0 else "normal")
        if i >= len(session_entries) - 1:
            right_btn.config(state="disabled")
            status_label.config(
                text="Last Bank",
                fg=BANK_ADD_UI_THEME["session_alert_fg"],  # Using Theme Dictionary
                font=("Helvetica", 10, "bold"),
            )
        else:
            right_btn.config(state="normal")
            status_label.config(
                text="", fg=BANK_ADD_UI_THEME["session_ok_fg"]
            )  # Using Theme Dictionary

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
        safe_close_modal(viewer, ba_win)
        ba_win.bind("<Escape>", on_escape)
        return "break"

    viewer.bind("<Escape>", close_viewer)
    viewer.protocol("WM_DELETE_WINDOW", close_viewer)
    viewer.bind("<Return>", close_viewer)

    ok_btn_viewer = tk.Button(content, text="OK", width=10, command=close_viewer)
    ok_btn_viewer.pack(side="bottom", pady=(0, 8))
    try:
        ok_btn_viewer.focus_set()
    except tk.TclError:
        pass
    update_view()


def on_submit(
    bank_name_entry: tk.Entry,
    branch_entry: tk.Entry,
    ifsc_entry: tk.Entry,
    micr_entry: tk.Entry,
    ba_win: tk.Toplevel,
    current_session_banks: dict,
) -> None:
    """Validate inputs, persist the new bank, and reset the form."""
    name = bank_name_entry.get().strip()
    branch = branch_entry.get().strip() or None
    ifsc = ifsc_entry.get().strip() or None
    micr = micr_entry.get().strip() or None

    if not name:
        show_colorful_error(ba_win, "Validation Error", "Bank Name is required.")
        flash_error(bank_name_entry)
        return

    try:
        _db_add_bank(name, branch, ifsc, micr)
        sr_no = len(current_session_banks) + 1
        current_session_banks[sr_no] = {
            "Bank": name,
            "Branch": branch,
            "IFSC": ifsc,
            "MICR": micr,
        }
        show_colorful_info(ba_win, "Success", f"Bank '{name}' added successfully.")
        bank_name_entry.delete(0, tk.END)
        branch_entry.delete(0, tk.END)
        ifsc_entry.delete(0, tk.END)
        micr_entry.delete(0, tk.END)
        bank_name_entry.focus_set()
    except Exception as e:  # noqa: BLE001
        show_colorful_error(ba_win, "Error", f"Failed to add bank: {e}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def add_bank(
    parent: Union[tk.Toplevel, tk.Tk], calling_button: tk.Widget | None = None
) -> None:
    """Main function to launch the add bank window."""

    # --- Window setup ---
    disable_parent(parent, calling_button=calling_button)

    current_session_banks: dict = {}
    ba_win = tk.Toplevel(parent)
    ba_win.title("🏧 Bank Entry 🏧")
    ba_win.geometry("750x440")
    ba_win.resizable(False, False)
    ba_win.configure(bg=BANK_ADD_UI_THEME["main_bg"])
    ba_win.transient(parent)
    ba_win.grab_set()
    ba_win.focus_set()
    try:
        push_window(ba_win, parent)
    except (RuntimeError, tk.TclError) as _exc:
        logger.debug("push_window failed: %s", _exc)

    # --- Footer tooltip (packed first so it anchors to the absolute bottom) ---
    tooltip_var = setup_footer_tooltip(ba_win)

    # --- Closure helpers (capture ba_win / parent / calling_button) ---
    def cleanup_and_close(_event=None):
        return safe_close_modal(ba_win, parent, calling_button)

    def on_escape(_event=None):
        return cleanup_and_close()

    # --- Header ---
    header_frame = tk.Frame(
        ba_win, bg=BANK_ADD_UI_THEME["header_bg"], relief="raised", bd=3
    )
    header_frame.pack(fill="x", padx=5, pady=0)

    tk.Label(
        header_frame,
        text="➕ Add New Bank ➕",
        font=("Helvetica", 18, "bold"),
        bg=BANK_ADD_UI_THEME["header_bg"],
        fg=BANK_ADD_UI_THEME["header_fg"],
        relief="ridge",
        bd=2,
    ).pack(fill="x", pady=10)

    # --- Form ---
    ba_frame = tk.Frame(ba_win, bg=BANK_ADD_UI_THEME["main_bg"])
    ba_frame.pack(pady=10, padx=10)

    ttk.Label(
        ba_frame,
        text="Bank Name:",
        font=("Helvetica", 14),
        background=BANK_ADD_UI_THEME["label_bg"],
    ).grid(row=0, column=0, sticky="w", padx=5, pady=5)
    bank_name_entry = tk.Entry(ba_frame, width=70)
    bank_name_entry.grid(row=0, column=1, padx=5, pady=5)

    ttk.Label(
        ba_frame,
        text="Branch:",
        font=("Helvetica", 14),
        background=BANK_ADD_UI_THEME["label_bg"],
    ).grid(row=1, column=0, sticky="w", padx=5, pady=5)
    branch_entry = tk.Entry(ba_frame, width=70)
    branch_entry.grid(row=1, column=1, padx=5, pady=5)

    ttk.Label(
        ba_frame,
        text="IFSC:",
        font=("Helvetica", 14),
        background=BANK_ADD_UI_THEME["label_bg"],
    ).grid(row=2, column=0, sticky="w", padx=5, pady=5)
    ifsc_entry = tk.Entry(ba_frame, width=70)
    ifsc_entry.grid(row=2, column=1, padx=5, pady=5)

    ttk.Label(
        ba_frame,
        text="MICR:",
        font=("Helvetica", 14),
        background=BANK_ADD_UI_THEME["label_bg"],
    ).grid(row=3, column=0, sticky="w", padx=5, pady=5)
    micr_entry = tk.Entry(ba_frame, width=70)
    micr_entry.grid(row=3, column=1, padx=5, pady=5)

    apply_entry_theme(bank_name_entry)
    apply_entry_theme(branch_entry)
    apply_entry_theme(ifsc_entry)
    apply_entry_theme(micr_entry)

    bind_tooltip(
        bank_name_entry,
        tooltip_var,
        "Enter the full legal name of the bank (required).",
    )
    bind_tooltip(
        branch_entry,
        tooltip_var,
        "Enter the branch name or location (optional).",
    )
    bind_tooltip(
        ifsc_entry,
        tooltip_var,
        "Enter the 11-character IFSC code, e.g. SBIN0001234 (optional).",
    )
    bind_tooltip(
        micr_entry,
        tooltip_var,
        "Enter the 9-digit MICR code from cheque leaves (optional).",
    )

    # --- Button frame ---
    btn_frame = tk.Frame(
        ba_win, pady=10, bg=BANK_ADD_UI_THEME["main_bg"], relief="ridge", bd=2
    )
    btn_frame.pack(fill="x", anchor="e", padx=10)

    # Using Theme Dictionary for Button Backgrounds
    submit_button = tk.Button(
        btn_frame,
        text="✅ SUBMIT ✅",
        width=12,
        font=("Comic Sans MS", 12, "bold"),
        bg=BANK_ADD_UI_THEME["submit_bg"],
        fg="white",
        activeforeground="white",
        relief="raised",
        bd=3,
        cursor="hand2",
        command=lambda: on_submit(
            bank_name_entry,
            branch_entry,
            ifsc_entry,
            micr_entry,
            ba_win,
            current_session_banks,
        ),
    )
    submit_button.pack(side="right", padx=5)

    # Using Theme Dictionary for Button Backgrounds
    cancel_btn = tk.Button(
        btn_frame,
        text="❌ Cancel ❌",
        width=12,
        font=("Comic Sans MS", 12, "bold"),
        bg=BANK_ADD_UI_THEME["cancel_bg"],
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
        ba_win, pady=10, bg=BANK_ADD_UI_THEME["main_bg"], relief="ridge", bd=2
    )
    hint_frame.pack(fill="x", anchor="e", padx=10)

    tk.Label(
        hint_frame,
        text="Press F1 for help, F2 for session banks, Esc to close.",
        font=("Helvetica", 16),
        bg=BANK_ADD_UI_THEME["main_bg"],
    ).pack(side="left", padx=8)

    # --- Bindings (Cleaned up using DRY helper function) ---
    apply_button_animations(
        submit_button,
        BANK_ADD_UI_THEME["submit_bg"],
        BANK_ADD_UI_THEME["submit_hover_bg"],
    )
    apply_button_animations(
        cancel_btn, BANK_ADD_UI_THEME["cancel_bg"], BANK_ADD_UI_THEME["cancel_hover_bg"]
    )

    bank_name_entry.bind("<Return>", lambda e: branch_entry.focus_set())
    branch_entry.bind("<Return>", lambda e: ifsc_entry.focus_set())
    ifsc_entry.bind("<Return>", lambda e: micr_entry.focus_set())
    micr_entry.bind("<Return>", lambda e: submit_button.focus_set())
    submit_button.bind(
        "<Return>",
        lambda e: on_submit(
            bank_name_entry,
            branch_entry,
            ifsc_entry,
            micr_entry,
            ba_win,
            current_session_banks,
        ),
    )

    ba_win.bind("<F1>", lambda e: show_help(ba_win, on_escape))
    ba_win.bind(
        "<F2>",
        lambda e: show_session_banks(ba_win, current_session_banks, on_escape),
    )
    ba_win.bind("<Escape>", on_escape)
    ba_win.protocol("WM_DELETE_WINDOW", cleanup_and_close)

    ba_win.after(100, bank_name_entry.focus_set)
