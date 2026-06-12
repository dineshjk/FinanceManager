# -*- coding: utf-8 -*-
# BankMan/loan_master_add.py

"""
Module for adding Loan Master records (loan_master table).

Pattern: coloured band frames, label_row / entry_row, F1/F2/Escape, central
entry theme (yellow-on-black), dark olive/moss-green chrome.
"""

from typing import Union
import tkinter as tk
from tkinter import ttk
from tkcalendar import DateEntry

from Shared.gui_utils import (
    apply_entry_theme,
    bind_tooltip,
    setup_footer_tooltip,
    flash_error,
    LOAN_MASTER_ADD_UI_THEME,
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
from .bank_db_utils import get_all_accounts, db_add_loan_master as _db_add_loan_master
from Shared.globals import logger
from Shared.gui_progressive import progressive_selection
from .accounts_add import add_account_main as _add_account

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_T = LOAN_MASTER_ADD_UI_THEME

_LOAN_TYPES = [
    "HOME LOAN",
    "PERSONAL LOAN",
    "AUTO LOAN",
    "CAR LOAN",
    "EDUCATION LOAN",
    "BUSINESS LOAN",
    "GOLD LOAN",
    "PROPERTY LOAN",
    "OTHER",
]

# ---------------------------------------------------------------------------
# Band helper
# ---------------------------------------------------------------------------


def _make_band(container, bg, relief="ridge", padx=10, pady=6):
    band = tk.Frame(
        container,
        bg=bg,
        relief=relief,
        bd=2,
        padx=padx,
        pady=pady,
    )
    label_row = tk.Frame(band, bg=bg)
    label_row.pack(fill="x", pady=(0, 2))
    entry_row = tk.Frame(band, bg=bg)
    entry_row.pack(fill="x", pady=(0, 2))
    return band, label_row, entry_row


def _band_label(parent, text, bg, font=("Helvetica", 14), padx=0):
    tk.Label(parent, text=text, font=font, bg=bg, fg=_T["label_fg"], anchor="w").pack(
        side="left", padx=(padx, 12)
    )


# ---------------------------------------------------------------------------
# Help window (F1)
# ---------------------------------------------------------------------------


def _show_help(win: tk.Toplevel, on_escape) -> None:
    win.unbind("<Escape>")

    hw = tk.Toplevel(win)
    try:
        hw.transient(win)
    except (tk.TclError, AttributeError) as exc:
        logger.debug("hw.transient failed: %s", exc)
    hw.title("Help — Add Loan Master")
    hw.configure(bg=_T["header_bg"])
    hw.geometry("700x660")
    hw.resizable(False, False)
    hw.grab_set()
    push_window(hw, win)
    try:
        hw.focus_set()
    except tk.TclError:
        pass

    tk.Label(
        hw,
        text="Add Loan Master  —  Help",
        font=("Helvetica", 16, "bold"),
        bg=_T["header_bg"],
        fg=_T["header_fg"],
        pady=8,
    ).pack(fill="x")

    body = tk.Frame(hw, bg=_T["main_bg"], padx=12, pady=12)
    body.pack(fill="both", expand=True)

    text = tk.Text(
        body,
        wrap="word",
        bg=_T["main_bg"],
        fg=_T["header_fg"],
        bd=0,
        padx=6,
        pady=6,
        font=("Helvetica", 11),
        height=32,
        insertbackground=_T["header_fg"],
    )
    text.pack(fill="both", expand=True)

    help_lines = [
        "\u2022 This form records a new loan facility in the loan_master table.",
        "",
        "Fields:",
        "  Linked Account    \u2014 Bank account through which EMIs are debited.",
        "  Loan Type         \u2014 Product category:",
        "                      HOME LOAN, PERSONAL LOAN, AUTO LOAN, CAR LOAN,",
        "                      EDUCATION LOAN, BUSINESS LOAN, etc.",
        "  Loan Account No.  \u2014 Bank-assigned loan reference number.",
        "  Principal Amount  \u2014 Original sanctioned loan amount (in \u20b9).",
        "  Interest Rate     \u2014 Annual rate at origination (%, e.g. 8.5).",
        "  EMI Amount        \u2014 Fixed monthly instalment (\u20b9).",
        "  Start Date        \u2014 Disbursement / first repayment date (dd-mm-yyyy).",
        "  End Date          \u2014 Scheduled final EMI / closure date (dd-mm-yyyy).",
        "  Is Active         \u2014 Tick if loan is still outstanding.",
        "",
        "Hotkeys:",
        "  F1  : This help screen",
        "  F2  : Session viewer (loans added this session)",
        "  Esc : Close without saving",
        "  Enter on last field : Submit",
    ]
    text.insert("1.0", "\n".join(help_lines))
    text.config(state="disabled")

    def close_help(_e=None):
        safe_close_modal(hw, win)
        win.bind("<Escape>", on_escape)
        return "break"

    hw.bind("<Escape>", close_help)
    hw.protocol("WM_DELETE_WINDOW", close_help)

    help_close_btn = tk.Button(
        hw,
        text="Close",
        command=close_help,
        font=("Helvetica", 11, "bold"),
        bg=_T.get("help_btn_bg", _T["button_bg"]),
        fg=_T.get("button_fg", "white"),
        activeforeground=_T.get("button_fg", "white"),
        padx=12,
        pady=6,
        cursor="hand2",
    )
    help_close_btn.pack(side="bottom", pady=10)
    apply_button_animations(
        help_close_btn,
        _T.get("help_btn_bg", _T["button_bg"]),
        _T.get("help_btn_hover_bg", "#115e59"),
    )


# ---------------------------------------------------------------------------
# Session viewer (F2)
# ---------------------------------------------------------------------------


def _show_session_viewer(win: tk.Toplevel, session_entries: list, on_escape) -> None:
    if not session_entries:
        try:
            show_colorful_info(
                win,
                "No Entries",
                "No loan master records have been added this session.",
            )
        except tk.TclError:
            pass
        return

    win.unbind("<Escape>")
    idx = {"i": 0}

    viewer = tk.Toplevel(win)
    viewer.title("Session — Loan Masters Added")
    viewer.transient(win)
    viewer.grab_set()
    viewer.resizable(False, False)
    viewer.geometry("580x380")
    viewer.configure(bg=_T["header_bg"])
    push_window(viewer, win)
    try:
        viewer.focus_set()
    except tk.TclError:
        pass

    tk.Label(
        viewer,
        text="Loan Masters Added This Session",
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
        bg=_T.get("session_btn_bg", _T["button_bg"]),
        fg=_T.get("button_fg", "white"),
        activeforeground=_T.get("button_fg", "white"),
        cursor="hand2",
    )
    left_btn.pack(side="left", padx=(6, 4), pady=6)
    apply_button_animations(
        left_btn,
        _T.get("session_btn_bg", _T["button_bg"]),
        _T.get("session_btn_hover_bg", "#115e59"),
    )
    right_btn = tk.Button(
        content,
        text="\u25ba",
        width=3,
        bg=_T.get("session_btn_bg", _T["button_bg"]),
        fg=_T.get("button_fg", "white"),
        activeforeground=_T.get("button_fg", "white"),
        cursor="hand2",
    )
    right_btn.pack(side="right", padx=(4, 6), pady=6)
    apply_button_animations(
        right_btn,
        _T.get("session_btn_bg", _T["button_bg"]),
        _T.get("session_btn_hover_bg", "#115e59"),
    )

    info_text = tk.Text(
        content,
        wrap="word",
        height=14,
        bg=_T.get("session_bg", _T["main_bg"]),
        fg=_T.get("session_value_fg", _T["header_fg"]),
        bd=0,
        relief="flat",
        font=("Helvetica", 11),
        insertbackground=_T.get("session_value_fg", _T["header_fg"]),
    )
    info_text.pack(fill="both", expand=True, padx=6, pady=4)
    info_text.tag_configure(
        "label",
        font=("Helvetica", 11, "bold"),
        foreground=_T.get("session_label_fg", _T["header_fg"]),
    )
    info_text.tag_configure(
        "value",
        font=("Helvetica", 11),
        foreground=_T.get("session_value_fg", "#93c5fd"),
    )
    info_text.config(state="disabled")

    status_label = tk.Label(
        content,
        text="",
        font=("Helvetica", 10, "bold"),
        bg=_T.get("session_bg", _T["header_bg"]),
        fg=_T.get("session_ok_fg", _T["header_fg"]),
    )
    status_label.pack(side="bottom", pady=(0, 4))

    def _update_view():
        i = idx["i"]
        rec = session_entries[i]
        total = len(session_entries)
        info_text.config(state="normal")
        info_text.delete("1.0", "end")
        fields = [
            ("Loan Type", rec.get("loan_type")),
            ("Account No.", rec.get("loan_account_number")),
            ("Principal (\u20b9)", f"{rec.get('principal_amount', 0.0):,.2f}"),
            ("Interest Rate (%)", f"{rec.get('interest_rate', 0.0):.2f}"),
            ("EMI (\u20b9)", f"{rec.get('emi_amount', 0.0):,.2f}"),
            ("Start Date", rec.get("start_dt")),
            ("End Date", rec.get("end_dt")),
            ("Is Active", "Yes" if rec.get("is_active") else "No"),
        ]
        for label, val in fields:
            info_text.insert("end", f"{label}: ", "label")
            info_text.insert("end", f"{val or chr(8212)}\n", "value")
        info_text.config(state="disabled")
        left_btn.config(state="disabled" if i == 0 else "normal")
        if i >= total - 1:
            right_btn.config(state="disabled")
            status_label.config(
                text="Last Entry", fg=_T.get("session_alert_fg", "#ef4444")
            )
        else:
            right_btn.config(state="normal")
            status_label.config(
                text=f"Entry {i + 1} of {total}",
                fg=_T.get("session_ok_fg", _T["header_fg"]),
            )

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
        bg=_T.get("session_btn_bg", _T["button_bg"]),
        fg=_T.get("button_fg", "white"),
        activeforeground=_T.get("button_fg", "white"),
        font=("Helvetica", 11, "bold"),
        cursor="hand2",
    )
    ok_btn.pack(side="bottom", pady=(0, 6))
    apply_button_animations(
        ok_btn,
        _T.get("session_btn_bg", _T["button_bg"]),
        _T.get("session_btn_hover_bg", "#115e59"),
    )
    try:
        ok_btn.focus_set()
    except tk.TclError:
        pass
    _update_view()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def add_loan_master_main(
    parent: Union[tk.Toplevel, tk.Tk],
    calling_button: tk.Widget | None = None,
) -> None:
    """Launch the Add Loan Master dialog."""

    # ── Lookup data ───────────────────────────────────────────────────────
    accounts = get_all_accounts()
    # label: "BankName  [AccType]  ac_number"  → ac_id
    account_map: dict[str, int] = {}
    for row in accounts:
        label = f"{row[1]}  [{row[2]}]  {row[3]}"
        account_map[label] = int(row[0])

    # ── Window setup ──────────────────────────────────────────────────────
    disable_parent(parent, calling_button=calling_button)
    session_records: list = []

    win = tk.Toplevel(parent)
    win.title("\U0001f4b3 Add Loan Master \U0001f4b3")
    win.geometry("1020x530")
    win.resizable(False, False)
    win.configure(bg=_T["main_bg"])
    win.transient(parent)
    win.grab_set()
    win.focus_set()
    try:
        push_window(win, parent)
    except (RuntimeError, tk.TclError) as exc:
        logger.debug("push_window failed: %s", exc)

    # ── Footer tooltip ────────────────────────────────────────────────────
    tooltip_var = setup_footer_tooltip(
        win, bg_color=_T["header_bg"], fg_color=_T["header_fg"]
    )

    # ── Closure helpers ───────────────────────────────────────────────────
    def cleanup_and_close(_event=None):
        return safe_close_modal(win, parent, calling_button)

    def on_escape(_event=None):
        return cleanup_and_close()

    win.bind("<F1>", lambda e: _show_help(win, on_escape))
    win.bind("<F2>", lambda e: _show_session_viewer(win, session_records, on_escape))
    win.bind("<Escape>", on_escape)
    win.protocol("WM_DELETE_WINDOW", on_escape)

    # ── Header ────────────────────────────────────────────────────────────
    header_frame = tk.Frame(win, bg=_T["header_bg"], relief="raised", bd=3)
    header_frame.pack(fill="x", padx=5, pady=0)
    tk.Label(
        header_frame,
        text="\U0001f4b3  Add Loan Master  \U0001f4b3",
        font=("Helvetica", 18, "bold"),
        bg=_T["header_bg"],
        fg=_T["header_fg"],
        relief="ridge",
        bd=2,
        pady=8,
    ).pack(fill="x")

    hint_frame = tk.Frame(win, bg=_T["main_bg"])
    hint_frame.pack(fill="x", padx=10, pady=(2, 0))
    for hint in ("F1: Help", "F2: Session Viewer", "Esc: Close"):
        tk.Label(
            hint_frame,
            text=hint,
            font=("Helvetica", 10, "italic"),
            bg=_T["main_bg"],
            fg="#b5f542",
        ).pack(side="left", padx=12)

    # ── Form body ─────────────────────────────────────────────────────────
    _F = ("Helvetica", 14)
    _FB = ("Helvetica", 14, "bold")

    _C_ACC = _T["band_account"]
    _C_LOAN = _T["band_loan"]
    _C_DATES = _T["band_dates"]

    form_body = tk.Frame(win, bg=_T["main_bg"])
    form_body.pack(fill="x", padx=12, pady=6)

    # ── Band 1: Account + Loan Type ───────────────────────────────────────
    acc_band, acc_lrow, acc_erow = _make_band(form_body, _C_ACC)
    acc_band.pack(fill="x", pady=(0, 5))

    _band_label(acc_lrow, "Linked Bank Account", _C_ACC, _F)
    _band_label(acc_lrow, "Loan Type", _C_ACC, _F, padx=110)

    account_combo = ttk.Combobox(
        acc_erow,
        width=42,
        values=list(account_map.keys()),
        font=_F,
    )
    account_combo.pack(side="left", padx=(0, 8))
    apply_entry_theme(account_combo)
    progressive_selection(account_combo, list(account_map.keys()))
    bind_tooltip(account_combo, tooltip_var, "Select the bank account for EMI debits.")

    def _refresh_account_combo():
        new_accounts = get_all_accounts()
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

    loan_type_combo = ttk.Combobox(
        acc_erow,
        width=22,
        values=_LOAN_TYPES,
        font=_F,
    )
    loan_type_combo.pack(side="left", padx=(18, 0))
    apply_entry_theme(loan_type_combo)
    progressive_selection(loan_type_combo, _LOAN_TYPES)
    bind_tooltip(loan_type_combo, tooltip_var, "Select the loan product category.")
    loan_type_combo.set("HOME LOAN")

    def on_loan_type_focus_out(_event=None):
        try:
            if not win.winfo_exists():
                return
        except (tk.TclError, NameError):
            return
        typed = loan_type_combo.get().strip()
        if typed and typed not in _LOAN_TYPES:
            show_colorful_error(
                win,
                "Invalid Loan Type",
                f"'{typed}' is not valid. Please choose from the list.",
            )
            flash_error(loan_type_combo)
            loan_type_combo.focus_set()

    loan_type_combo.bind("<FocusOut>", on_loan_type_focus_out, add="+")

    # ── Band 2: Loan Details ──────────────────────────────────────────────
    loan_band, loan_lrow, loan_erow = _make_band(form_body, _C_LOAN)
    loan_band.pack(fill="x", pady=(0, 5))

    _band_label(loan_lrow, "Loan Account Number", _C_LOAN, _F)
    _band_label(loan_lrow, "Principal Amount (\u20b9)", _C_LOAN, _F, padx=28)
    _band_label(loan_lrow, "Interest Rate (%)", _C_LOAN, _F, padx=28)
    _band_label(loan_lrow, "EMI Amount (\u20b9)", _C_LOAN, _F, padx=28)

    loan_acc_no_entry = tk.Entry(loan_erow, width=20, font=_FB)
    loan_acc_no_entry.pack(side="left", padx=(0, 8))
    apply_entry_theme(loan_acc_no_entry)
    bind_tooltip(
        loan_acc_no_entry, tooltip_var, "Bank-assigned loan account / reference number."
    )

    principal_entry = tk.Entry(loan_erow, width=14, font=_FB)
    principal_entry.pack(side="left", padx=(18, 8))
    principal_entry.insert(0, "0.00")
    apply_entry_theme(principal_entry)
    bind_tooltip(
        principal_entry, tooltip_var, "Original sanctioned loan amount in \u20b9."
    )

    interest_entry = tk.Entry(loan_erow, width=10, font=_FB)
    interest_entry.pack(side="left", padx=(18, 8))
    interest_entry.insert(0, "0.00")
    apply_entry_theme(interest_entry)
    bind_tooltip(
        interest_entry,
        tooltip_var,
        "Annual interest rate at origination (%, e.g. 8.5).",
    )

    emi_entry = tk.Entry(loan_erow, width=14, font=_FB)
    emi_entry.pack(side="left", padx=(18, 0))
    emi_entry.insert(0, "0.00")
    apply_entry_theme(emi_entry)
    bind_tooltip(emi_entry, tooltip_var, "Fixed monthly instalment amount in \u20b9.")

    # ── Band 3: Dates + Is Active ─────────────────────────────────────────
    date_band, date_lrow, date_erow = _make_band(form_body, _C_DATES)
    date_band.pack(fill="x", pady=(0, 5))

    _band_label(date_lrow, "Start Date", _C_DATES, _F)
    _band_label(date_lrow, "End Date", _C_DATES, _F, padx=60)
    _band_label(date_lrow, "Is Active", _C_DATES, _F, padx=60)

    start_dt = DateEntry(date_erow, date_pattern="dd-mm-yyyy", width=14, font=_F)
    start_dt.pack(side="left", padx=(0, 8))
    apply_entry_theme(start_dt)
    bind_tooltip(start_dt, tooltip_var, "Loan disbursement / first EMI date.")

    end_dt = DateEntry(date_erow, date_pattern="dd-mm-yyyy", width=14, font=_F)
    end_dt.pack(side="left", padx=(18, 8))
    apply_entry_theme(end_dt)
    bind_tooltip(end_dt, tooltip_var, "Scheduled final EMI / loan closure date.")

    bind_date_spin(start_dt)
    bind_date_spin(end_dt)

    is_active_var = tk.IntVar(value=1)
    tk.Checkbutton(
        date_erow,
        text="Active",
        variable=is_active_var,
        font=_F,
        bg=_C_DATES,
        fg=_T["label_fg"],
        selectcolor="#1a2800",
        activebackground=_C_DATES,
        activeforeground=_T["label_fg"],
    ).pack(side="left", padx=(18, 0))

    # ── Session count ─────────────────────────────────────────────────────
    session_count_var = tk.StringVar(value="Session: 0 saved")
    tk.Label(
        win,
        textvariable=session_count_var,
        font=("Helvetica", 11, "italic"),
        bg=_T["main_bg"],
        fg="#b5f542",
    ).pack(anchor="e", padx=16)

    # ── Buttons ───────────────────────────────────────────────────────────
    btn_frame = tk.Frame(win, bg=_T["main_bg"])
    btn_frame.pack(pady=8)

    def _reset_form():
        import datetime

        loan_acc_no_entry.delete(0, "end")
        for e, v in [
            (principal_entry, "0.00"),
            (interest_entry, "0.00"),
            (emi_entry, "0.00"),
        ]:
            e.delete(0, "end")
            e.insert(0, v)
        start_dt.set_date(datetime.date.today())
        end_dt.set_date(datetime.date.today())
        is_active_var.set(1)
        loan_acc_no_entry.focus_set()

    def _validate_and_save():
        # Account
        ac_label = account_combo.get()
        if not ac_label or ac_label not in account_map:
            flash_error(account_combo)
            show_colorful_error(
                win, "Validation Error", "Please select a bank account."
            )
            return
        ac_id = account_map[ac_label]

        # Loan type
        if not loan_type_combo.get():
            flash_error(loan_type_combo)
            show_colorful_error(win, "Validation Error", "Please select a loan type.")
            return

        # Loan account number
        acc_no = loan_acc_no_entry.get().strip()
        if not acc_no:
            flash_error(loan_acc_no_entry)
            show_colorful_error(
                win, "Validation Error", "Loan Account Number is required."
            )
            return

        # Numeric fields
        def _parse(entry, name, must_positive=True):
            try:
                v = float(entry.get().replace(",", "") or 0)
            except ValueError:
                flash_error(entry)
                show_colorful_error(
                    win, "Validation Error", f"{name} must be a number."
                )
                return None
            if must_positive and v <= 0:
                flash_error(entry)
                msg = f"{name} must be greater than 0."
                show_colorful_error(win, "Validation Error", msg)
                return None
            return v

        principal = _parse(principal_entry, "Principal Amount")
        if principal is None:
            return
        rate = _parse(interest_entry, "Interest Rate")
        if rate is None:
            return
        emi = _parse(emi_entry, "EMI Amount")
        if emi is None:
            return

        # Dates
        try:
            s_dt = start_dt.get_date().strftime("%Y-%m-%d")
            e_dt = end_dt.get_date().strftime("%Y-%m-%d")
        except Exception:  # noqa: BLE001
            show_colorful_error(win, "Validation Error", "Please enter valid dates.")
            return
        if e_dt <= s_dt:
            flash_error(end_dt)
            show_colorful_error(
                win, "Validation Error", "End Date must be after Start Date."
            )
            return

        data = {
            "account_id": ac_id,
            "loan_type": loan_type_combo.get(),
            "loan_account_number": acc_no,
            "principal_amount": principal,
            "interest_rate": rate,
            "emi_amount": emi,
            "start_dt": s_dt,
            "end_dt": e_dt,
            "is_active": is_active_var.get(),
        }

        try:
            lm_id = _db_add_loan_master(data)
        except Exception as exc:  # noqa: BLE001
            logger.error("add_loan_master failed: %s", exc)
            msg = f"Failed to save:\n{exc}"
            show_colorful_error(win, "Database Error", msg)
            return

        session_records.append({**data, "loan_master_id": lm_id})
        session_count_var.set(f"Session: {len(session_records)} saved")
        show_colorful_info(win, "Saved", f"Loan Master saved (ID {lm_id}).")
        _reset_form()

    save_btn = tk.Button(
        btn_frame,
        text="Save  [Enter]",
        command=_validate_and_save,
        font=("Helvetica", 13, "bold"),
        bg=_T.get("submit_bg", _T["button_bg"]),
        fg=_T.get("button_fg", "white"),
        activeforeground=_T.get("button_fg", "white"),
        padx=18,
        pady=6,
        cursor="hand2",
        relief="raised",
        bd=3,
    )
    save_btn.pack(side="left", padx=12)
    apply_button_animations(
        save_btn,
        _T.get("submit_bg", _T["button_bg"]),
        _T.get("submit_hover_bg", "#2563eb"),
    )

    close_btn = tk.Button(
        btn_frame,
        text="Close  [Esc]",
        command=cleanup_and_close,
        font=("Helvetica", 13, "bold"),
        bg=_T.get("cancel_bg", _T["button_bg"]),
        fg=_T.get("button_fg", "white"),
        activeforeground=_T.get("button_fg", "white"),
        padx=18,
        pady=6,
        cursor="hand2",
        relief="raised",
        bd=3,
    )
    close_btn.pack(side="left", padx=12)
    apply_button_animations(
        close_btn,
        _T.get("cancel_bg", _T["button_bg"]),
        _T.get("cancel_hover_bg", "#991b1b"),
    )

    # ── Return-key navigation ─────────────────────────────────────────────
    def _focus(w):
        def _h(_e=None):
            w.focus_set()
            return "break"

        return _h

    account_combo.bind("<Return>", _focus(loan_acc_no_entry))
    loan_acc_no_entry.bind("<Return>", _focus(loan_type_combo))
    loan_type_combo.bind("<Return>", _focus(principal_entry))
    principal_entry.bind("<Return>", _focus(interest_entry))
    interest_entry.bind("<Return>", _focus(emi_entry))
    emi_entry.bind("<Return>", _focus(start_dt))
    start_dt.bind("<Return>", _focus(end_dt))
    end_dt.bind("<Return>", _focus(save_btn))

    # ── Initial focus ─────────────────────────────────────────────────────
    if account_map:
        loan_acc_no_entry.focus_set()
    else:
        account_combo.focus_set()

    parent.wait_window(win)
