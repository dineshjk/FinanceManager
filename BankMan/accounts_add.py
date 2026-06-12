# -*- coding: utf-8 -*-
# C:\Data\Personal\Finance_and_Investment\finprog\FinanceManager\BankMan\accounts_add.py

"""
Module for adding new accounts to the database.
"""

# pylint: disable=too-many-locals,too-many-statements,too-many-arguments,too-many-positional-arguments

from datetime import date
from typing import Union
import tkinter as tk
from tkinter import ttk
from tkcalendar import DateEntry

from Shared.globals import logger
from Shared.gui_progressive import progressive_selection
from Shared.gui_utils import (
    apply_entry_theme,
    bind_tooltip,
    setup_footer_tooltip,
    flash_error,
    ACCOUNTS_ADD_UI_THEME,
    apply_button_animations,
    bind_date_spin,
)
from Shared.dialog_utils import (
    show_colorful_info,
    show_colorful_error,
    show_colorful_yesno,
)
from Shared.modal_utils import disable_parent
from Shared.window_manager import push_window, safe_close_modal
from .bank_db_utils import (
    add_account as _db_add_account,
    get_all_banks,
)
from .banks_add import add_bank as _add_bank

_ACCOUNT_TYPES = ["SAVINGS", "CURRENT", "OVERDRAFT", "CREDIT_CARD"]

# ---------------------------------------------------------------------------
# Module-level helpers (no closure variables; receive all context as params)
# ---------------------------------------------------------------------------


def show_help(win: tk.Toplevel, on_escape) -> None:
    """Launch the help sub-window for the Add Account dialog."""
    win.unbind("<Escape>")

    help_win = tk.Toplevel(win)
    try:
        help_win.transient(win)
    except (tk.TclError, AttributeError) as _exc:
        logger.debug("help_win.transient failed: %s", _exc)
    help_win.title("Help — Add Account")
    help_win.configure(bg=ACCOUNTS_ADD_UI_THEME["help_bg"])
    help_win.geometry("640x600")
    help_win.resizable(False, False)
    help_win.grab_set()
    push_window(help_win, win)
    try:
        help_win.focus_set()
    except tk.TclError:
        pass

    tk.Label(
        help_win,
        text="Add Account Help",
        font=("Helvetica", 16, "bold"),
        bg=ACCOUNTS_ADD_UI_THEME["help_header_bg"],
        fg="white",
        pady=8,
    ).pack(fill="x")

    body = tk.Frame(
        help_win, bg=ACCOUNTS_ADD_UI_THEME["help_bg"], padx=12, pady=12
    )
    body.pack(fill="both", expand=True)

    text = tk.Text(
        body,
        wrap="word",
        bg=ACCOUNTS_ADD_UI_THEME["help_bg"],
        bd=0,
        padx=6,
        pady=6,
        font=("Helvetica", 11),
        height=14,
    )
    text.pack(fill="both", expand=True)

    help_lines = [
        "• This form adds a new bank or credit card account to the database.",
        "• Once added, you can post transactions, record interests, "
        "or track EMIs on it.",
        "",
        "Fields:",
        "  Select Bank (required): Pick the institution (e.g. SBI, HDFC).",
        "    If the bank is not in the list, type it to add it.",
        "  Select Account Type (required): SAVINGS, CURRENT, OVERDRAFT, "
        "or CREDIT_CARD.",
        "  Account Number (required): Unique identifier within the bank.",
        "  Opening Date (required): Date the account was opened.",
        "  Current Balance (required): Starting balance snapshot (INR).",
        "  Balance Date (required): Date of the balance snapshot.",
        "  Joint Account (optional): Check if this is a joint account.",
        "  Active Account (optional): Keep checked. Uncheck only if closed.",
        "",
        "Hotkeys:",
        "  F1: This screen (Help)",
        "  F2: Session Accounts",
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
        bg=ACCOUNTS_ADD_UI_THEME["help_btn_bg"],
        fg="white",
        padx=12,
        pady=6,
        cursor="hand2",
    ).pack(side="bottom", pady=10)


def show_session_accounts(
    win: tk.Toplevel,
    current_session_accounts: dict,
    on_escape,
) -> None:
    """Launch the session accounts viewer sub-window."""
    if not current_session_accounts:
        try:
            show_colorful_info(
                win,
                "No Accounts",
                "No accounts have been recorded in this session yet.",
            )
        except tk.TclError:
            pass
        return

    win.unbind("<Escape>")

    session_entries = list(current_session_accounts.items())
    idx = {"i": 0}

    viewer = tk.Toplevel(win)
    viewer.title("Session Accounts Viewer")
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

    left_btn = tk.Button(content, text="◀", width=3)
    left_btn.pack(side="left", padx=(10, 5), pady=6)
    right_btn = tk.Button(content, text="▶", width=3)
    right_btn.pack(side="right", padx=(5, 10), pady=6)

    info_text = tk.Text(
        content,
        wrap="word",
        height=9,
        bg=ACCOUNTS_ADD_UI_THEME["session_bg"],
        bd=0,
        relief="flat",
    )
    info_text.pack(fill="both", expand=True, padx=10, pady=6)
    info_text.tag_configure(
        "label",
        font=("Helvetica", 11, "bold"),
        foreground=ACCOUNTS_ADD_UI_THEME["session_label_fg"],
    )
    info_text.tag_configure(
        "value",
        font=("Helvetica", 11),
        foreground=ACCOUNTS_ADD_UI_THEME["session_value_fg"],
    )
    info_text.config(state="disabled")

    status_label = tk.Label(
        content,
        text="",
        font=("Helvetica", 10, "bold"),
        bg=ACCOUNTS_ADD_UI_THEME["session_bg"],
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
        info_text.insert("end", "Account Type: ", "label")
        info_text.insert("end", f"{t.get('AccountType')}\n", "value")
        info_text.insert("end", "Account No: ", "label")
        info_text.insert("end", f"{t.get('Number')}\n", "value")
        info_text.insert("end", "Open Date: ", "label")
        info_text.insert("end", f"{t.get('OpenDate')}\n", "value")
        info_text.insert("end", "Balance: ", "label")
        info_text.insert("end", f"{t.get('Balance')}\n", "value")
        info_text.insert("end", "Balance Date: ", "label")
        info_text.insert("end", f"{t.get('BalanceDt', '')}\n", "value")
        info_text.insert("end", "Joint: ", "label")
        info_text.insert(
            "end", f"{'Yes' if t.get('IsJoint') else 'No'}\n", "value"
        )
        info_text.config(state="disabled")

        left_btn.config(state="disabled" if i == 0 else "normal")
        if i >= len(session_entries) - 1:
            right_btn.config(state="disabled")
            status_label.config(
                text="Last Entry",
                fg=ACCOUNTS_ADD_UI_THEME["session_alert_fg"],
                font=("Helvetica", 10, "bold"),
            )
        else:
            right_btn.config(state="normal")
            status_label.config(
                text="", fg=ACCOUNTS_ADD_UI_THEME["session_ok_fg"]
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
    bank_combo: ttk.Combobox,
    type_combo: ttk.Combobox,
    number_entry: tk.Entry,
    open_dt_entry: DateEntry,
    balance_entry: tk.Entry,
    curr_balance_dt_entry: DateEntry,
    is_joint_var: tk.BooleanVar,
    is_active_var: tk.BooleanVar,
    bank_map: dict,
    win: tk.Toplevel,
    current_session_accounts: dict,
) -> None:
    """Validate inputs, persist the new account, and reset the form."""
    try:
        bank_name = bank_combo.get()
        type_name = type_combo.get().strip()
        number = number_entry.get().strip()
        open_dt = open_dt_entry.get_date().strftime("%Y-%m-%d")
        balance_str = balance_entry.get().strip().replace(",", "")

        if not bank_name or bank_name not in bank_map:
            show_colorful_error(
                win, "Validation Error", "Please select a valid bank."
            )
            flash_error(bank_combo)
            return
        if not type_name or type_name not in _ACCOUNT_TYPES:
            show_colorful_error(
                win, "Validation Error", "Please select a valid account type."
            )
            flash_error(type_combo)
            return
        if not number:
            show_colorful_error(
                win, "Validation Error", "Account Number is required."
            )
            flash_error(number_entry)
            return

        balance = float(balance_str) if balance_str else 0.0
        curr_balance_dt = curr_balance_dt_entry.get_date().strftime("%Y-%m-%d")
        is_joint = is_joint_var.get()
        is_active = is_active_var.get()

        data = {
            "bank_id": bank_map[bank_name],
            "open_dt": open_dt,
            "number": number,
            "type": type_name,
            "balance": balance,
            "curr_balance_dt": curr_balance_dt,
            "is_joint": is_joint,
            "is_active": is_active,
        }
        _db_add_account(data)

        sr_no = len(current_session_accounts) + 1
        current_session_accounts[sr_no] = {
            "Bank": bank_name,
            "AccountType": type_name,
            "Number": number,
            "OpenDate": open_dt,
            "Balance": balance,
            "BalanceDt": curr_balance_dt,
            "IsJoint": is_joint,
            "IsActive": is_active,
        }
        show_colorful_info(win, "Success", "Account added successfully.")

        bank_combo.set("")
        type_combo.set("")
        number_entry.delete(0, tk.END)
        open_dt_entry.delete(0, tk.END)
        open_dt_entry.insert(0, str(date.today()))
        balance_entry.delete(0, tk.END)
        curr_balance_dt_entry.set_date(date.today())
        is_joint_var.set(False)
        is_active_var.set(True)
        bank_combo.focus_set()

    except ValueError:
        show_colorful_error(
            win, "Validation Error", "Current Balance must be a valid number."
        )
        flash_error(balance_entry)
    except Exception as e:  # noqa: BLE001 # pylint: disable=W0718
        show_colorful_error(win, "Error", f"Failed to add account: {e}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def add_account_main(
    parent: Union[tk.Toplevel, tk.Tk], calling_button: tk.Widget | None = None
) -> None:
    """Main function to launch the Add Account window."""

    # --- Lookup data (fetched once at window open) ---
    banks = get_all_banks()
    bank_map = {b[1]: b[0] for b in banks}

    # --- Window setup ---
    disable_parent(parent, calling_button=calling_button)

    current_session_accounts: dict = {}
    win = tk.Toplevel(parent)
    win.title("🏦 Add Account 🏦")
    win.geometry("720x510")
    win.resizable(False, False)
    win.configure(bg=ACCOUNTS_ADD_UI_THEME["main_bg"])
    win.transient(parent)
    win.grab_set()
    win.focus_set()
    try:
        push_window(win, parent)
    except (RuntimeError, tk.TclError) as _exc:
        logger.debug("push_window failed: %s", _exc)

    # --- Footer tooltip (packed first to anchor to the bottom) ---
    tooltip_var = setup_footer_tooltip(win)

    # --- Closure helpers (capture win / parent / calling_button) ---
    def cleanup_and_close(_event=None):
        return safe_close_modal(win, parent, calling_button)

    def on_escape(_event=None):
        return cleanup_and_close()

    # --- Header ---
    header_frame = tk.Frame(
        win, bg=ACCOUNTS_ADD_UI_THEME["header_bg"], relief="raised", bd=3
    )
    header_frame.pack(fill="x", padx=5, pady=0)

    tk.Label(
        header_frame,
        text="➕ Add New Account ➕",
        font=("Helvetica", 18, "bold"),
        bg=ACCOUNTS_ADD_UI_THEME["header_bg"],
        fg=ACCOUNTS_ADD_UI_THEME["header_fg"],
        relief="ridge",
        bd=2,
    ).pack(fill="x", pady=10)

    # --- Form ---
    form_frame = tk.Frame(win, bg=ACCOUNTS_ADD_UI_THEME["main_bg"])
    form_frame.pack(pady=10, padx=10)

    is_joint_var = tk.BooleanVar()
    is_active_var = tk.BooleanVar(value=True)

    # Bank
    ttk.Label(
        form_frame,
        text="Select Bank:",
        font=("Helvetica", 14),
        background=ACCOUNTS_ADD_UI_THEME["label_bg"],
    ).grid(row=0, column=0, sticky="w", padx=5, pady=5)
    bank_combo = ttk.Combobox(
        form_frame, width=48, values=list(bank_map.keys())
    )
    bank_combo.grid(row=0, column=1, padx=5, pady=5)
    progressive_selection(bank_combo, list(bank_map.keys()))

    def _refresh_bank_combo():
        new_banks = get_all_banks()
        bank_map.clear()
        bank_map.update({b[1]: b[0] for b in new_banks})
        bank_combo["values"] = list(bank_map.keys())
        progressive_selection(bank_combo, list(bank_map.keys()))

    def on_bank_focus_out(_event=None):
        try:
            if not win.winfo_exists():
                return
        except (tk.TclError, NameError):
            return
        typed = bank_combo.get().strip()
        if not typed:
            return
        if typed not in bank_map:
            response = show_colorful_yesno(
                win,
                "Bank Not Found",
                f"'{typed}' was not found. Add a new bank " "now?",
            )
            if response:
                _add_bank(win)
                _refresh_bank_combo()
                bank_combo.focus_set()
            else:
                show_colorful_error(
                    win,
                    "Invalid Selection",
                    "Please select a valid bank from the list.",
                )
                flash_error(bank_combo)
                bank_combo.focus_set()

    bank_combo.bind("<FocusOut>", on_bank_focus_out, add="+")

    # Account Type
    ttk.Label(
        form_frame,
        text="Select Account Type:",
        font=("Helvetica", 14),
        background=ACCOUNTS_ADD_UI_THEME["label_bg"],
    ).grid(row=1, column=0, sticky="w", padx=5, pady=5)
    type_combo = ttk.Combobox(form_frame, width=48, values=_ACCOUNT_TYPES)
    type_combo.grid(row=1, column=1, padx=5, pady=5)
    progressive_selection(type_combo, _ACCOUNT_TYPES)

    def on_type_focus_out(_event=None):
        try:
            if not win.winfo_exists():
                return
        except (tk.TclError, NameError):
            return
        typed = type_combo.get().strip()
        if typed and typed not in _ACCOUNT_TYPES:
            show_colorful_error(
                win,
                "Invalid Account Type",
                f"'{typed}' is not valid. "
                "Please choose SAVINGS, CURRENT, or OVERDRAFT.",
            )
            flash_error(type_combo)
            type_combo.focus_set()

    type_combo.bind("<FocusOut>", on_type_focus_out, add="+")

    # Account Number
    ttk.Label(
        form_frame,
        text="Account Number:",
        font=("Helvetica", 14),
        background=ACCOUNTS_ADD_UI_THEME["label_bg"],
    ).grid(row=2, column=0, sticky="w", padx=5, pady=5)
    number_entry = tk.Entry(form_frame, width=50)
    number_entry.grid(row=2, column=1, padx=5, pady=5)

    # Opening Date
    ttk.Label(
        form_frame,
        text="Opening Date (DD-MM-YYYY):",
        font=("Helvetica", 14),
        background=ACCOUNTS_ADD_UI_THEME["label_bg"],
    ).grid(row=3, column=0, sticky="w", padx=5, pady=5)
    open_dt_entry = DateEntry(
        form_frame, date_pattern="dd-mm-yyyy", width=18, font=("Helvetica", 14)
    )
    open_dt_entry.grid(row=3, column=1, padx=5, pady=5, sticky="w")
    bind_date_spin(open_dt_entry)

    # Current Balance
    ttk.Label(
        form_frame,
        text="Current Balance:",
        font=("Helvetica", 14),
        background=ACCOUNTS_ADD_UI_THEME["label_bg"],
    ).grid(row=4, column=0, sticky="w", padx=5, pady=5)
    balance_entry = tk.Entry(form_frame, width=50)
    balance_entry.grid(row=4, column=1, padx=5, pady=5)

    # Balance Date
    ttk.Label(
        form_frame,
        text="Balance Date (DD-MM-YYYY):",
        font=("Helvetica", 14),
        background=ACCOUNTS_ADD_UI_THEME["label_bg"],
    ).grid(row=5, column=0, sticky="w", padx=5, pady=5)
    curr_balance_dt_entry = DateEntry(
        form_frame, date_pattern="dd-mm-yyyy", width=18, font=("Helvetica", 14)
    )
    curr_balance_dt_entry.grid(row=5, column=1, padx=5, pady=5, sticky="w")
    bind_date_spin(curr_balance_dt_entry)

    # Joint Account checkbox
    ttk.Label(
        form_frame,
        text="Joint Account:",
        font=("Helvetica", 14),
        background=ACCOUNTS_ADD_UI_THEME["label_bg"],
    ).grid(row=6, column=0, sticky="w", padx=5, pady=5)
    joint_check = ttk.Checkbutton(
        form_frame, text="Yes", variable=is_joint_var
    )
    joint_check.grid(row=6, column=1, sticky="w", padx=5, pady=5)

    # Active Status checkbox
    ttk.Label(
        form_frame,
        text="Active Account:",
        font=("Helvetica", 14),
        background=ACCOUNTS_ADD_UI_THEME["label_bg"],
    ).grid(row=7, column=0, sticky="w", padx=5, pady=5)
    is_active_check = ttk.Checkbutton(
        form_frame, text="Yes", variable=is_active_var
    )
    is_active_check.grid(row=7, column=1, sticky="w", padx=5, pady=5)

    apply_entry_theme(bank_combo)
    apply_entry_theme(type_combo)
    apply_entry_theme(number_entry)
    apply_entry_theme(open_dt_entry)
    apply_entry_theme(balance_entry)
    apply_entry_theme(curr_balance_dt_entry)

    bind_tooltip(bank_combo, tooltip_var, "Select the bank for this account.")
    bind_tooltip(
        type_combo,
        tooltip_var,
        "Select the account type (SAVINGS, CURRENT, OVERDRAFT).",
    )
    bind_tooltip(number_entry, tooltip_var, "Enter the account number.")
    bind_tooltip(
        open_dt_entry, tooltip_var, "Enter the date the account was opened."
    )
    bind_tooltip(
        balance_entry, tooltip_var, "Enter the current opening balance."
    )
    bind_tooltip(
        curr_balance_dt_entry,
        tooltip_var,
        "Date of the current balance snapshot (usually today/statement date).",
    )
    bind_tooltip(joint_check, tooltip_var, "Check if this is a joint account.")
    bind_tooltip(
        is_active_check,
        tooltip_var,
        "Uncheck if recording a closed or inactive account.",
    )

    # --- Button frame ---
    btn_frame = tk.Frame(
        win, pady=10, bg=ACCOUNTS_ADD_UI_THEME["main_bg"], relief="ridge", bd=2
    )
    btn_frame.pack(fill="x", anchor="e", padx=10)

    submit_button = tk.Button(
        btn_frame,
        text="✅ SUBMIT ✅",
        width=12,
        font=("Comic Sans MS", 12, "bold"),
        bg=ACCOUNTS_ADD_UI_THEME["submit_bg"],
        fg="white",
        activeforeground="white",
        relief="raised",
        bd=3,
        cursor="hand2",
        command=lambda: on_submit(
            bank_combo,
            type_combo,
            number_entry,
            open_dt_entry,
            balance_entry,
            curr_balance_dt_entry,
            is_joint_var,
            is_active_var,
            bank_map,
            win,
            current_session_accounts,
        ),
    )
    submit_button.pack(side="right", padx=5)

    cancel_btn = tk.Button(
        btn_frame,
        text="❌ Cancel ❌",
        width=12,
        font=("Comic Sans MS", 12, "bold"),
        bg=ACCOUNTS_ADD_UI_THEME["cancel_bg"],
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
        win, pady=10, bg=ACCOUNTS_ADD_UI_THEME["main_bg"], relief="ridge", bd=2
    )
    hint_frame.pack(fill="x", anchor="e", padx=10)

    tk.Label(
        hint_frame,
        text="Press F1 for help, F2 for session accounts, Esc to close.",
        font=("Helvetica", 16),
        bg=ACCOUNTS_ADD_UI_THEME["main_bg"],
    ).pack(side="left", padx=8)

    # --- Bindings (Cleaned up using DRY helper function) ---
    apply_button_animations(
        submit_button,
        ACCOUNTS_ADD_UI_THEME["submit_bg"],
        ACCOUNTS_ADD_UI_THEME["submit_hover_bg"],
    )
    apply_button_animations(
        cancel_btn,
        ACCOUNTS_ADD_UI_THEME["cancel_bg"],
        ACCOUNTS_ADD_UI_THEME["cancel_hover_bg"],
    )

    bank_combo.bind("<Return>", lambda e: type_combo.focus_set())
    type_combo.bind("<Return>", lambda e: number_entry.focus_set())
    number_entry.bind("<Return>", lambda e: open_dt_entry.focus_set())
    open_dt_entry.bind("<Return>", lambda e: balance_entry.focus_set())
    balance_entry.bind("<Return>", lambda e: curr_balance_dt_entry.focus_set())
    curr_balance_dt_entry.bind("<Return>", lambda e: joint_check.focus_set())
    joint_check.bind("<Return>", lambda e: is_active_check.focus_set())
    is_active_check.bind("<Return>", lambda e: submit_button.focus_set())
    submit_button.bind(
        "<Return>",
        lambda e: on_submit(
            bank_combo,
            type_combo,
            number_entry,
            open_dt_entry,
            balance_entry,
            curr_balance_dt_entry,
            is_joint_var,
            is_active_var,
            bank_map,
            win,
            current_session_accounts,
        ),
    )

    win.bind("<F1>", lambda e: show_help(win, on_escape))
    win.bind(
        "<F2>",
        lambda e: show_session_accounts(
            win, current_session_accounts, on_escape
        ),
    )
    win.bind("<Escape>", on_escape)
    win.protocol("WM_DELETE_WINDOW", cleanup_and_close)

    win.after(100, bank_combo.focus_set)
