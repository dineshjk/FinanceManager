# -*- coding: utf-8 -*-
# C:\Data\Personal\Finance_and_Investment\finprog\FinanceManager\BankMan\cc_master_add.py

"""
Module for adding new Credit Card master records (card_master table).

Structural pattern from bank_transactions_add.py / ppf_master_add.py:
  - Coloured band frames, each with a label_row / entry_row
  - apply_entry_theme / bind_tooltip / setup_footer_tooltip from Shared.gui_utils
  - F1 = Help, F2 = Session viewer, Escape = close without saving
  - Yellow-on-black entry theme via centrally defined apply_entry_theme()
  - Distinct deep-crimson / ruby-red window theme (CC_MASTER_ADD_UI_THEME)
"""

from typing import Union
import tkinter as tk
from tkinter import ttk

from Shared.gui_utils import (
    apply_entry_theme,
    bind_tooltip,
    setup_footer_tooltip,
    flash_error,
    CC_MASTER_ADD_UI_THEME,
    apply_button_animations,
)
from Shared.dialog_utils import (
    show_colorful_info,
    show_colorful_error,
    show_colorful_yesno,
)
from Shared.modal_utils import disable_parent
from Shared.window_manager import push_window, safe_close_modal
from .bank_db_utils import (
    get_all_accounts,
    add_card_master as _db_add_card_master,
)
from Shared.globals import logger
from Shared.gui_progressive import progressive_selection
from .accounts_add import add_account_main as _add_account

# ---------------------------------------------------------------------------
# Theme alias
# ---------------------------------------------------------------------------
_T = CC_MASTER_ADD_UI_THEME

# ---------------------------------------------------------------------------
# Band / label helpers
# ---------------------------------------------------------------------------


def _make_section(container, title, bg, relief="groove", padx=12, pady=8):
    """Create a named LabelFrame section with an inner entry row.

    Returns (label_frame, entry_row).
    """
    lf = tk.LabelFrame(
        container,
        text=f"  {title}  ",
        font=("Helvetica", 13, "bold"),
        bg=bg,
        fg=_T["header_bg"],
        relief=relief,
        bd=2,
        padx=padx,
        pady=pady,
    )
    row = tk.Frame(lf, bg=bg)
    row.pack(fill="x", pady=2)
    return lf, row


def _field_label(parent, text, bg, font=("Helvetica", 13)):
    """Pack an inline field label into a section entry row."""
    tk.Label(
        parent,
        text=text,
        font=font,
        bg=bg,
        fg=_T["label_fg"],
        anchor="w",
    ).pack(side="left", padx=(0, 6))


# ---------------------------------------------------------------------------
# Help window (F1)
# ---------------------------------------------------------------------------


def _show_help(win: tk.Toplevel, on_escape) -> None:
    """Launch the Help sub-window for Add CC Master."""
    win.unbind("<Escape>")

    help_win = tk.Toplevel(win)
    try:
        help_win.transient(win)
    except (tk.TclError, AttributeError) as exc:
        logger.debug("help_win.transient failed: %s", exc)
    help_win.title("Help — Add Credit Card Master")
    help_win.configure(bg=_T["help_bg"])
    help_win.geometry("700x620")
    help_win.resizable(False, False)
    help_win.grab_set()
    push_window(help_win, win)
    try:
        help_win.focus_set()
    except tk.TclError:
        pass

    tk.Label(
        help_win,
        text="Add Credit Card Master  —  Help",
        font=("Helvetica", 16, "bold"),
        bg=_T["header_bg"],
        fg=_T["header_fg"],
        pady=8,
    ).pack(fill="x")

    body = tk.Frame(help_win, bg=_T["help_bg"], padx=12, pady=12)
    body.pack(fill="both", expand=True)

    text = tk.Text(
        body,
        wrap="word",
        bg=_T["help_bg"],
        fg=_T.get("help_text_fg", "#2d0000"),
        bd=0,
        padx=6,
        pady=6,
        font=("Helvetica", 11),
        height=28,
        insertbackground=_T.get("help_text_fg", "#2d0000"),
    )
    text.pack(fill="both", expand=True)

    help_lines = [
        "\u2022 This form registers a new Credit Card (card_master) record.",
        "",
        "Fields:",
        "  Linked Account     \u2014 The bank account to which this card's monthly",
        "                       bill payments are debited (e.g. the salary",
        "                       account linked to the card).",
        "  Card Name          \u2014 Descriptive product name, e.g. 'HDFC Regalia',",
        "                       'SBI SimplyCLICK', 'Axis Magnus'.",
        "  Card Number        \u2014 For security, store only the last 4 digits",
        "                       (e.g. '4321'). Full 16-digit numbers are",
        "                       accepted but not recommended.",
        "  Credit Limit (\u20b9)   \u2014 Approved credit limit on this card in INR.",
        "  Billing Cycle Day  \u2014 Day of the month (1\u201331) on which the billing",
        "                       cycle closes and the statement is generated.",
        "                       E.g. enter 20 if your statement date is the",
        "                       20th of each month.",
        "  Is Active          \u2014 Tick = card is valid and in use.",
        "                       Untick only for cancelled/expired cards.",
        "",
        "Tips:",
        "  \u2022 One card_master row per physical card product.",
        "  \u2022 Spending transactions are recorded in cc_transactions.",
        "  \u2022 The Billing Cycle Day drives automatic due-date reminders.",
        "",
        "Hotkeys:",
        "  F1  : This help screen",
        "  F2  : Session viewer (cards added in this session)",
        "  Esc : Close without saving",
        "  Enter on last field : Submit",
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
        bg=_T["button_bg"],
        fg=_T["button_fg"],
        padx=12,
        pady=6,
        cursor="hand2",
    ).pack(side="bottom", pady=10)


# ---------------------------------------------------------------------------
# Session viewer (F2)
# ---------------------------------------------------------------------------


def _show_session_viewer(
    win: tk.Toplevel,
    session_entries: list,
    on_escape,
) -> None:
    """Show credit cards added in this session."""
    if not session_entries:
        try:
            show_colorful_info(
                win,
                "No Entries",
                "No credit card master records have been added this session.",
            )
        except tk.TclError:
            pass
        return

    win.unbind("<Escape>")
    idx = {"i": 0}

    viewer = tk.Toplevel(win)
    viewer.title("Session — Credit Cards Added")
    viewer.transient(win)
    viewer.grab_set()
    viewer.resizable(False, False)
    viewer.geometry("580x360")
    viewer.configure(bg=_T["header_bg"])
    push_window(viewer, win)
    try:
        viewer.focus_set()
    except tk.TclError:
        pass

    tk.Label(
        viewer,
        text="Credit Cards Added This Session",
        font=("Helvetica", 14, "bold"),
        bg=_T["header_bg"],
        fg=_T["header_fg"],
        pady=6,
    ).pack(fill="x")

    content = tk.Frame(viewer, bg=_T["header_bg"])
    content.pack(fill="both", expand=True, padx=10, pady=6)

    left_btn = tk.Button(
        content,
        text="\u25c4",
        width=3,
        bg=_T["button_bg"],
        fg=_T["button_fg"],
    )
    left_btn.pack(side="left", padx=(6, 4), pady=6)
    right_btn = tk.Button(
        content,
        text="\u25ba",
        width=3,
        bg=_T["button_bg"],
        fg=_T["button_fg"],
    )
    right_btn.pack(side="right", padx=(4, 6), pady=6)

    info_text = tk.Text(
        content,
        wrap="word",
        height=12,
        bg=_T["header_bg"],
        fg=_T["header_fg"],
        bd=0,
        relief="flat",
        font=("Helvetica", 11),
        insertbackground=_T["header_fg"],
    )
    info_text.pack(fill="both", expand=True, padx=6, pady=4)
    info_text.tag_configure(
        "label", font=("Helvetica", 11, "bold"), foreground=_T["header_fg"]
    )
    info_text.tag_configure("value", font=("Helvetica", 11), foreground="#ffd700")
    info_text.config(state="disabled")

    status_label = tk.Label(
        content,
        text="",
        font=("Helvetica", 10, "bold"),
        bg=_T["header_bg"],
        fg=_T["header_fg"],
    )
    status_label.pack(side="bottom", pady=(0, 4))

    def _update_view():
        i = idx["i"]
        rec = session_entries[i]
        total = len(session_entries)
        info_text.config(state="normal")
        info_text.delete("1.0", "end")
        fields = [
            ("Card Name", rec.get("card_name")),
            ("Card Number", rec.get("card_number")),
            ("Linked Account", rec.get("account_label")),
            ("Credit Limit (\u20b9)", f"{rec.get('credit_limit', 0.0):,.2f}"),
            ("Billing Cycle Day", str(rec.get("billing_cycle_day"))),
            ("Is Active", "Yes" if rec.get("is_active") else "No"),
        ]
        for label, val in fields:
            info_text.insert("end", f"{label}: ", "label")
            info_text.insert("end", f"{val or chr(8212)}\n", "value")
        info_text.config(state="disabled")
        left_btn.config(state="disabled" if i == 0 else "normal")
        if i >= total - 1:
            right_btn.config(state="disabled")
            status_label.config(text="Last Entry", fg="#ef4444")
        else:
            right_btn.config(state="normal")
            status_label.config(text=f"Entry {i + 1} of {total}", fg=_T["header_fg"])

    def _go_prev(_e=None):
        if idx["i"] > 0:
            idx["i"] -= 1
            _update_view()

    def _go_next(_e=None):
        if idx["i"] < len(session_entries) - 1:
            idx["i"] += 1
            _update_view()

    left_btn.config(command=_go_prev)
    right_btn.config(command=_go_next)
    viewer.bind("<Left>", lambda e: _go_prev())
    viewer.bind("<Right>", lambda e: _go_next())

    def _close_viewer(_e=None):
        safe_close_modal(viewer, win)
        win.bind("<Escape>", on_escape)
        return "break"

    viewer.bind("<Escape>", _close_viewer)
    viewer.protocol("WM_DELETE_WINDOW", _close_viewer)
    viewer.bind("<Return>", _close_viewer)

    ok_btn = tk.Button(
        content,
        text="OK",
        width=10,
        command=_close_viewer,
        bg=_T["button_bg"],
        fg=_T["button_fg"],
        font=("Helvetica", 11, "bold"),
        cursor="hand2",
    )
    ok_btn.pack(side="bottom", pady=(0, 6))
    try:
        ok_btn.focus_set()
    except tk.TclError:
        pass
    _update_view()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def add_cc_master_main(
    parent: Union[tk.Toplevel, tk.Tk],
    calling_button: tk.Widget | None = None,
) -> None:
    """Launch the Add Credit Card Master dialog."""

    # ── Lookup data ───────────────────────────────────────────────────────
    accounts = get_all_accounts("CREDIT_CARD")
    # Display: "BankName : [AC_Number]"  →  ac_id
    account_map = {f"{a[1]} : [{a[3]}]": a[0] for a in accounts}

    # ── Window setup ──────────────────────────────────────────────────────
    disable_parent(parent, calling_button=calling_button)
    session_records: list = []

    win = tk.Toplevel(parent)
    win.title("\U0001f4b3 Add Credit Card Master \U0001f4b3")
    win.geometry("950x540")
    win.resizable(False, False)
    win.configure(bg=_T["main_bg"])
    win.transient(parent)
    win.grab_set()
    win.focus_set()
    try:
        push_window(win, parent)
    except (RuntimeError, tk.TclError) as exc:
        logger.debug("push_window failed: %s", exc)

    # ── Footer tooltip (packed first → anchors to the bottom) ─────────────
    tooltip_var = setup_footer_tooltip(
        win, bg_color=_T["header_bg"], fg_color=_T["header_fg"]
    )

    # ── Closure helpers ───────────────────────────────────────────────────
    def cleanup_and_close(_event=None):
        return safe_close_modal(win, parent, calling_button)

    def on_escape(_event=None):
        return cleanup_and_close()

    # ── F1 / F2 / Escape bindings ─────────────────────────────────────────
    win.bind("<F1>", lambda e: _show_help(win, on_escape))
    win.bind(
        "<F2>",
        lambda e: _show_session_viewer(win, session_records, on_escape),
    )
    win.bind("<Escape>", on_escape)
    win.protocol("WM_DELETE_WINDOW", on_escape)

    # ── Header ────────────────────────────────────────────────────────────
    header_frame = tk.Frame(win, bg=_T["header_bg"], relief="raised", bd=3)
    header_frame.pack(fill="x", padx=5, pady=0)
    tk.Label(
        header_frame,
        text="\U0001f4b3  Add Credit Card Master  \U0001f4b3",
        font=("Helvetica", 18, "bold"),
        bg=_T["header_bg"],
        fg=_T["header_fg"],
        relief="ridge",
        bd=2,
        pady=8,
    ).pack(fill="x")

    # ── Form body ─────────────────────────────────────────────────────────
    _F = ("Helvetica", 14)
    _FB = ("Helvetica", 14, "bold")
    _FL = ("Helvetica", 13)  # inline field-label font

    _C_ACCT = _T["band_account"]
    _C_CARD = _T["band_card"]
    _C_FIN = _T["band_financial"]

    form_body = tk.Frame(win, bg=_T["main_bg"])
    form_body.pack(fill="x", padx=12, pady=6)

    # ── Section 1: Linked Account ─────────────────────────────────────────
    acct_section, acct_row = _make_section(form_body, "Linked Bank Account", _C_ACCT)
    acct_section.pack(fill="x", pady=(0, 8))

    account_combo = ttk.Combobox(
        acct_row,
        width=38,
        values=list(account_map.keys()),
        font=_F,
    )
    account_combo.pack(side="left", padx=(0, 8))
    apply_entry_theme(account_combo)
    progressive_selection(account_combo, list(account_map.keys()))
    bind_tooltip(
        account_combo,
        tooltip_var,
        "Bank account to which this card's bill payments are debited.",
    )

    def _refresh_account_combo():
        new_accounts = get_all_accounts("CREDIT_CARD")
        account_map.clear()
        account_map.update({f"{a[1]} : [{a[3]}]": a[0] for a in new_accounts})
        account_combo["values"] = list(account_map.keys())
        progressive_selection(account_combo, list(account_map.keys()))

    def on_account_focus_out(_event=None):
        try:
            if not win.winfo_exists():
                return
        except (tk.TclError, NameError):
            return
        typed = account_combo.get().strip()
        if not typed:
            return
        if typed not in account_map:
            response = show_colorful_yesno(
                win,
                "Account Not Found",
                f"'{typed}' was not found. Add a new bank account " "now?",
            )
            if response:
                _add_account(win)
                _refresh_account_combo()
                account_combo.focus_set()
            else:
                show_colorful_error(
                    win,
                    "Invalid Selection",
                    "Please select a valid account from the list.",
                )
                flash_error(account_combo)
                account_combo.focus_set()

    account_combo.bind("<FocusOut>", on_account_focus_out, add="+")

    if account_map:
        account_combo.set(next(iter(account_map)))

    # ── Section 2: Card Details ───────────────────────────────────────────
    card_section, card_row = _make_section(form_body, "Card Details", _C_CARD)
    card_section.pack(fill="x", pady=(0, 8))

    _field_label(card_row, "Card Name", _C_CARD, _FL)
    card_name_entry = tk.Entry(card_row, width=28, font=_FB)
    card_name_entry.pack(side="left", padx=(0, 16))
    apply_entry_theme(card_name_entry)
    bind_tooltip(
        card_name_entry,
        tooltip_var,
        "Descriptive product name, e.g. 'HDFC Regalia', 'Axis Magnus'.",
    )

    _field_label(card_row, "Card Number (last 4 digits)", _C_CARD, _FL)
    card_number_entry = tk.Entry(card_row, width=8, font=_FB)
    card_number_entry.pack(side="left", padx=(0, 0))
    apply_entry_theme(card_number_entry)
    bind_tooltip(
        card_number_entry,
        tooltip_var,
        "Last 4 digits of the card number (for security). Full 16-digit "
        "number is also accepted. If the UNIQUE constraint clashes, prefix "
        "with a bank code (e.g., SBI-4321).",
    )
    # ── Section 3: Financial Settings ────────────────────────────────────
    fin_section, fin_row = _make_section(form_body, "Financial Settings", _C_FIN)
    fin_section.pack(fill="x", pady=(0, 8))

    _field_label(fin_row, "Credit Limit (\u20b9)", _C_FIN, _FL)
    credit_limit_entry = tk.Entry(fin_row, width=16, font=_FB)
    credit_limit_entry.pack(side="left", padx=(0, 16))
    apply_entry_theme(credit_limit_entry)
    bind_tooltip(
        credit_limit_entry,
        tooltip_var,
        "Approved credit limit on this card in INR (e.g. 150000).",
    )

    _field_label(fin_row, "Billing Cycle Day (1\u201331)", _C_FIN, _FL)
    billing_day_spin = ttk.Spinbox(
        fin_row,
        from_=1,
        to=31,
        width=5,
        font=_FB,
    )
    billing_day_spin.pack(side="left", padx=(0, 16))
    billing_day_spin.set(1)
    apply_entry_theme(billing_day_spin)
    bind_tooltip(
        billing_day_spin,
        tooltip_var,
        "Day of the month (1\u201331) on which the billing cycle closes and "
        "the statement is generated.",
    )

    is_active_var = tk.BooleanVar(value=True)
    is_active_chk = tk.Checkbutton(
        fin_row,
        variable=is_active_var,
        text="Active",
        font=_F,
        bg=_C_FIN,
        fg=_T["label_fg"],
        selectcolor=_T["header_bg"],
        activebackground=_C_FIN,
        activeforeground=_T["label_fg"],
        cursor="hand2",
    )
    is_active_chk.pack(side="left", padx=(16, 0))
    bind_tooltip(
        is_active_chk,
        tooltip_var,
        "Tick = card is valid and in use. Untick only for cancelled or "
        "expired cards.",
    )

    # ── Return-key navigation ─────────────────────────────────────────────
    account_combo.bind("<Return>", lambda e: card_name_entry.focus_set())
    card_name_entry.bind("<Return>", lambda e: card_number_entry.focus_set())
    card_number_entry.bind("<Return>", lambda e: credit_limit_entry.focus_set())
    credit_limit_entry.bind("<Return>", lambda e: billing_day_spin.focus_set())

    # ── Action buttons ────────────────────────────────────────────────────
    btn_frame = tk.Frame(win, pady=10, bg=_T["main_bg"], relief="ridge", bd=2)
    btn_frame.pack(fill="x", anchor="e", padx=10)

    def _make_button(parent_frame, text, command, bg, act_bg, fg="#FFD700"):
        btn = tk.Button(
            parent_frame,
            text=text,
            command=command,
            font=("Helvetica", 12, "bold"),
            bg=bg,
            fg=fg,
            cursor="hand2",
            padx=16,
            pady=6,
            relief="raised",
            bd=2,
        )
        btn.pack(side="right", padx=6)
        apply_button_animations(btn, bg, act_bg)
        return btn

    # ── Session count label (left side of button row) ─────────────────────
    _session_count_var = tk.StringVar(value="Cards added this session: 0")
    tk.Label(
        btn_frame,
        textvariable=_session_count_var,
        font=("Helvetica", 11, "italic"),
        bg=_T["main_bg"],
        fg=_T["label_fg"],
    ).pack(side="left", padx=10)

    # ── Reset form ────────────────────────────────────────────────────────
    def _reset_form():
        card_name_entry.delete(0, tk.END)
        card_number_entry.delete(0, tk.END)
        credit_limit_entry.delete(0, tk.END)
        billing_day_spin.set(1)
        is_active_var.set(True)
        if account_map:
            account_combo.set(next(iter(account_map)))
        card_name_entry.focus_set()

    # ── Submit / validation ───────────────────────────────────────────────
    def on_submit(_event=None):
        # --- Linked account ---
        account_label = account_combo.get().strip()
        if not account_label or account_label not in account_map:
            show_colorful_error(
                win,
                "Validation Error",
                "Please select a valid linked bank account.",
            )
            flash_error(account_combo)
            account_combo.focus_set()
            return

        # --- Card Name ---
        card_name = card_name_entry.get().strip()
        if not card_name:
            show_colorful_error(win, "Validation Error", "Card Name is required.")
            flash_error(card_name_entry)
            card_name_entry.focus_set()
            return

        # --- Card Number ---
        card_number = card_number_entry.get().strip()
        if not card_number:
            show_colorful_error(win, "Validation Error", "Card Number is required.")
            flash_error(card_number_entry)
            card_number_entry.focus_set()
            return

        # --- Credit Limit ---
        try:
            limit_str = credit_limit_entry.get().strip().replace(",", "")
            credit_limit = float(limit_str)
            if credit_limit <= 0:
                raise ValueError
        except ValueError:
            show_colorful_error(
                win,
                "Validation Error",
                "Credit Limit must be a positive number.",
            )
            flash_error(credit_limit_entry)
            credit_limit_entry.focus_set()
            return

        # --- Billing Cycle Day ---
        try:
            billing_day = int(billing_day_spin.get())
            if not 1 <= billing_day <= 31:
                raise ValueError
        except ValueError:
            show_colorful_error(
                win,
                "Validation Error",
                "Billing Cycle Day must be between 1 and 31.",
            )
            flash_error(billing_day_spin)
            billing_day_spin.focus_set()
            return

        account_id = account_map[account_label]
        data = {
            "account_id": account_id,
            "card_name": card_name,
            "card_number": card_number,
            "credit_limit": credit_limit,
            "billing_cycle_day": billing_day,
            "is_active": 1 if is_active_var.get() else 0,
        }

        try:
            new_id = _db_add_card_master(data)
            session_records.append({**data, "account_label": account_label})
            _session_count_var.set(f"Cards added this session: {len(session_records)}")
            show_colorful_info(
                win,
                "Saved",
                f"Credit card '{card_name}' saved successfully "
                f"(card_master_id = {new_id}).",
            )
            _reset_form()
        except Exception as exc:  # noqa: BLE001
            logger.exception("add_card_master failed: %s", exc)
            msg = f"Failed to save credit card master record.\n{exc}"
            show_colorful_error(win, "Database Error", msg)

    # Enter on billing_day_spin triggers submit
    billing_day_spin.bind("<Return>", on_submit)

    # Pack order with side="right": last packed = far right → Save on far right
    _make_button(
        btn_frame, "Close  [Esc]", on_escape, _T["cancel_bg"], _T["cancel_hover_bg"]
    )
    _make_button(btn_frame, "Reset", _reset_form, "#6b2121", "#4a1515")
    _make_button(
        btn_frame, "Save  [Enter]", on_submit, _T["submit_bg"], _T["submit_hover_bg"]
    )

    # ── Hotkey hint ───────────────────────────────────────────────────────
    hint_frame = tk.Frame(win, pady=10, bg=_T["main_bg"], relief="ridge", bd=2)
    hint_frame.pack(fill="x", anchor="e", padx=10)
    tk.Label(
        hint_frame,
        text="Press F1 for help, F2 for session cards, Esc to " "close.",
        font=("Helvetica", 14),
        bg=_T["main_bg"],
        fg=_T["label_fg"],
    ).pack(side="left", padx=8)

    # ── Initial focus ─────────────────────────────────────────────────────
    win.after(50, account_combo.focus_set)
