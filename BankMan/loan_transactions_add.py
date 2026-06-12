# -*- coding: utf-8 -*-
# BankMan/loan_transactions_add.py

"""
Module for adding Loan Transaction records (loan_transactions table).

Pattern: coloured band frames, label_row / entry_row, F1/F2/Escape, central
entry theme (yellow-on-black), dark maroon/wine chrome.

Auto-logic:
  - Selecting a loan pre-fills Prevailing Rate from loan_master.interest_rate
    and fetches the last principal_due as the opening balance.
  - Changing Principal / Interest / Charges auto-computes Loan Payment.
  - Changing Principal auto-computes New Principal Due =
    previous_principal_due − principal.
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
    LOAN_TRANS_ADD_UI_THEME,
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
    get_all_loan_masters_for_display,
    get_last_loan_principal_due,
    db_add_loan_transaction as _db_add_loan_transaction,
)
from Shared.globals import logger
from Shared.gui_progressive import progressive_selection
from .loan_master_add import add_loan_master_main as _add_loan

# ---------------------------------------------------------------------------
# Theme alias and constants
# ---------------------------------------------------------------------------
_T = LOAN_TRANS_ADD_UI_THEME

_HINT_FG = "#fda4af"  # Soft rose — matches dark maroon theme

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
    hw.title("Help — Add Loan Transaction")
    hw.configure(bg=_T["header_bg"])
    hw.geometry("740x720")
    hw.resizable(False, False)
    hw.grab_set()
    push_window(hw, win)
    try:
        hw.focus_set()
    except tk.TclError:
        pass

    tk.Label(
        hw,
        text="Add Loan Transaction  —  Help",
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
        height=36,
        insertbackground=_T["header_fg"],
    )
    text.pack(fill="both", expand=True)

    help_lines = [
        "\u2022 This form records a repayment event in loan_transactions.",
        "",
        "Fields:",
        "  Loan Account       \u2014 Select the loan from the dropdown.",
        "                       Only active loans are listed.",
        "  Linked Account     \u2014 Auto-filled from the selected loan master.",
        "  Trans Date         \u2014 Date of this EMI / repayment event.",
        "  Description        \u2014 Optional narration, e.g. 'EMI #12', 'Prepayment'.",
        "  Prevailing Rate(%) \u2014 Interest rate for this instalment.",
        "                       Pre-filled from the loan master; edit if the",
        "                       rate changed (floating-rate loans).",
        "  Principal (\u20b9)      \u2014 Principal component repaid in this instalment.",
        "  Interest (\u20b9)       \u2014 Interest charged for this instalment period.",
        "  Charges (\u20b9)        \u2014 Processing fees, late-payment penalties, etc.",
        "  Loan Payment (\u20b9)   \u2014 Total cash outflow (auto-computed as",
        "                       Principal + Interest + Charges; can be edited).",
        "  Loan Credit (\u20b9)    \u2014 Amount credited to the loan (subsidy, reversal).",
        "                       Leave 0 for normal EMI rows.",
        "  Prev. Principal Due\u2014 Outstanding balance fetched from last transaction.",
        "  New Principal Due  \u2014 Auto-computed as Prev. Due \u2212 Principal repaid.",
        "                       Edit manually if the bank statement differs.",
        "",
        "Hotkeys:",
        "  F1  : This help screen",
        "  F2  : Session viewer (transactions added this session)",
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
                "No loan transactions have been added this session.",
            )
        except tk.TclError:
            pass
        return

    win.unbind("<Escape>")
    idx = {"i": 0}

    viewer = tk.Toplevel(win)
    viewer.title("Session — Loan Transactions Added")
    viewer.transient(win)
    viewer.grab_set()
    viewer.resizable(False, False)
    viewer.geometry("600x420")
    viewer.configure(bg=_T["header_bg"])
    push_window(viewer, win)
    try:
        viewer.focus_set()
    except tk.TclError:
        pass

    tk.Label(
        viewer,
        text="Loan Transactions Added This Session",
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
        height=16,
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
            ("Loan", rec.get("loan_label")),
            ("Trans Date", rec.get("loan_trans_dt")),
            ("Description", rec.get("loan_description") or "\u2014"),
            ("Prev. Rate (%)", f"{rec.get('prevailing_interest_rate', 0.0):.2f}"),
            ("Principal (\u20b9)", f"{rec.get('principal', 0.0):,.2f}"),
            ("Interest (\u20b9)", f"{rec.get('interest', 0.0):,.2f}"),
            ("Charges (\u20b9)", f"{rec.get('charges', 0.0):,.2f}"),
            ("Loan Payment (\u20b9)", f"{rec.get('loan_payment', 0.0):,.2f}"),
            ("Loan Credit (\u20b9)", f"{rec.get('loan_credit', 0.0):,.2f}"),
            ("New Principal Due (\u20b9)", f"{rec.get('principal_due', 0.0):,.2f}"),
        ]
        for label, val in fields:
            info_text.insert("end", f"{label}: ", "label")
            info_text.insert("end", f"{val}\n", "value")
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


def add_loan_transaction_main(
    parent: Union[tk.Toplevel, tk.Tk],
    calling_button: tk.Widget | None = None,
) -> None:
    """Launch the Add Loan Transaction dialog."""

    # ── Lookup data ───────────────────────────────────────────────────────
    loans = get_all_loan_masters_for_display()
    # label: "LoanType  [BankName]  AccNo"  →  (loan_master_id, account_id, interest_rate)
    loan_map: dict[str, tuple[int, int, float]] = {}
    for row in loans:
        label = f"{row[1]}  [{row[5]}]  {row[2]}"
        loan_map[label] = (int(row[0]), int(row[4]), float(row[6]))

    _state: dict = {
        "loan_master_id": None,
        "account_id": None,
        "interest_rate": 0.0,
        "prev_principal_due": 0.0,
    }

    # ── Window setup ──────────────────────────────────────────────────────
    disable_parent(parent, calling_button=calling_button)
    session_records: list = []

    win = tk.Toplevel(parent)
    win.title("\U0001f4b0 Add Loan Transaction \U0001f4b0")
    win.geometry("1100x640")
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
        text="\U0001f4b0  Add Loan Transaction  \U0001f4b0",
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
            fg=_HINT_FG,
        ).pack(side="left", padx=12)

    # ── Form body ─────────────────────────────────────────────────────────
    _F = ("Helvetica", 14)
    _FB = ("Helvetica", 14, "bold")

    _C_MST = _T["band_master"]
    _C_DET = _T["band_details"]
    _C_AMT = _T["band_amounts"]
    _C_BAL = _T["band_balance"]

    form_body = tk.Frame(win, bg=_T["main_bg"])
    form_body.pack(fill="x", padx=12, pady=6)

    # ── Band 1: Loan selector + info ──────────────────────────────────────
    mst_band, mst_lrow, mst_erow = _make_band(form_body, _C_MST)
    mst_band.pack(fill="x", pady=(0, 5))

    _band_label(mst_lrow, "Loan Account", _C_MST, _F)
    _band_label(mst_lrow, "Account / Principal Info", _C_MST, _F, padx=100)

    loan_combo = ttk.Combobox(
        mst_erow,
        width=44,
        values=list(loan_map.keys()),
        font=_F,
    )
    loan_combo.pack(side="left", padx=(0, 8))
    apply_entry_theme(loan_combo)
    progressive_selection(loan_combo, list(loan_map.keys()))
    bind_tooltip(loan_combo, tooltip_var, "Select the loan for this transaction.")

    def _refresh_loan_combo():
        new_loans = get_all_loan_masters_for_display()
        loan_map.clear()
        for row in new_loans:
            label = f"{row[1]}  [{row[5]}]  {row[2]}"
            loan_map[label] = (int(row[0]), int(row[4]), float(row[6]))
        loan_combo["values"] = list(loan_map.keys())
        progressive_selection(loan_combo, list(loan_map.keys()))

    def on_loan_focus_out(_event=None):
        try:
            if not win.winfo_exists():
                return
        except (tk.TclError, NameError):
            return
        typed = loan_combo.get().strip()
        if not typed:
            return
        if typed not in loan_map:
            response = show_colorful_yesno(
                win,
                "Loan Not Found",
                f"'{typed}' was not found. Add a new loan account " "now?",
            )
            if response:
                _add_loan(win)
                _refresh_loan_combo()
                loan_combo.focus_set()
            else:
                show_colorful_error(
                    win,
                    "Invalid Selection",
                    "Please select a valid loan from the list.",
                )
                flash_error(loan_combo)
                loan_combo.focus_set()

    loan_combo.bind("<FocusOut>", on_loan_focus_out, add="+")

    if loan_map:
        loan_combo.set(next(iter(loan_map)))

    loan_info_var = tk.StringVar(value="\u2014")
    tk.Label(
        mst_erow,
        textvariable=loan_info_var,
        font=_F,
        bg=_C_MST,
        fg=_HINT_FG,
        width=34,
        anchor="w",
    ).pack(side="left", padx=(18, 0))

    # ── Band 2: Trans Date + Description + Prevailing Rate ────────────────
    det_band, det_lrow, det_erow = _make_band(form_body, _C_DET)
    det_band.pack(fill="x", pady=(0, 5))

    _band_label(det_lrow, "Trans Date", _C_DET, _F)
    _band_label(det_lrow, "Description (optional)", _C_DET, _F, padx=42)
    _band_label(det_lrow, "Prevailing Rate (%)", _C_DET, _F, padx=42)

    trans_dt = DateEntry(det_erow, date_pattern="dd-mm-yyyy", width=14, font=_F)
    trans_dt.pack(side="left", padx=(0, 8))
    apply_entry_theme(trans_dt)
    bind_tooltip(trans_dt, tooltip_var, "Date of this EMI / repayment event.")
    bind_date_spin(trans_dt)

    description_entry = tk.Entry(det_erow, width=28, font=_FB)
    description_entry.pack(side="left", padx=(18, 8))
    apply_entry_theme(description_entry)
    bind_tooltip(
        description_entry,
        tooltip_var,
        "Optional narration, e.g. 'EMI #12', 'Prepayment'.",
    )

    rate_entry = tk.Entry(det_erow, width=10, font=_FB)
    rate_entry.pack(side="left", padx=(18, 0))
    rate_entry.insert(0, "0.00")
    apply_entry_theme(rate_entry)
    bind_tooltip(
        rate_entry,
        tooltip_var,
        "Prevailing annual interest rate for this instalment (%). Pre-filled "
        "from loan master; edit for floating-rate loans.",
    )

    # ── Band 3: Payment amounts ───────────────────────────────────────────
    amt_band, amt_lrow, amt_erow = _make_band(form_body, _C_AMT)
    amt_band.pack(fill="x", pady=(0, 5))

    _band_label(amt_lrow, "Principal (\u20b9)", _C_AMT, _F)
    _band_label(amt_lrow, "Interest (\u20b9)", _C_AMT, _F, padx=22)
    _band_label(amt_lrow, "Charges (\u20b9)", _C_AMT, _F, padx=22)
    _band_label(amt_lrow, "Loan Payment (\u20b9)", _C_AMT, _F, padx=22)
    _band_label(amt_lrow, "Loan Credit (\u20b9)", _C_AMT, _F, padx=22)

    principal_entry = tk.Entry(amt_erow, width=14, font=_FB)
    principal_entry.pack(side="left", padx=(0, 8))
    principal_entry.insert(0, "0.00")
    apply_entry_theme(principal_entry)
    bind_tooltip(
        principal_entry, tooltip_var, "Principal component repaid in this instalment."
    )

    interest_entry = tk.Entry(amt_erow, width=14, font=_FB)
    interest_entry.pack(side="left", padx=(18, 8))
    interest_entry.insert(0, "0.00")
    apply_entry_theme(interest_entry)
    bind_tooltip(
        interest_entry, tooltip_var, "Interest charged for this instalment period."
    )

    charges_entry = tk.Entry(amt_erow, width=14, font=_FB)
    charges_entry.pack(side="left", padx=(18, 8))
    charges_entry.insert(0, "0.00")
    apply_entry_theme(charges_entry)
    bind_tooltip(
        charges_entry, tooltip_var, "Processing fees, late-payment penalties, etc."
    )

    payment_entry = tk.Entry(amt_erow, width=14, font=_FB)
    payment_entry.pack(side="left", padx=(18, 8))
    payment_entry.insert(0, "0.00")
    apply_entry_theme(payment_entry)
    bind_tooltip(
        payment_entry,
        tooltip_var,
        "Total cash outflow (auto-computed = Principal + Interest + Charges). "
        "Edit if the actual payment differs.",
    )

    credit_entry = tk.Entry(amt_erow, width=14, font=_FB)
    credit_entry.pack(side="left", padx=(18, 0))
    credit_entry.insert(0, "0.00")
    apply_entry_theme(credit_entry)
    bind_tooltip(
        credit_entry,
        tooltip_var,
        "Amount credited to the loan account (subsidy, reversal). Leave 0 for "
        "normal EMI rows.",
    )

    # ── Band 4: Principal Due tracking ───────────────────────────────────
    bal_band, bal_lrow, bal_erow = _make_band(form_body, _C_BAL)
    bal_band.pack(fill="x", pady=(0, 5))

    _band_label(bal_lrow, "Previous Principal Due (\u20b9)", _C_BAL, _F)
    _band_label(bal_lrow, "New Principal Due (\u20b9)", _C_BAL, _F, padx=80)

    prev_due_var = tk.StringVar(value="\u2014")
    tk.Label(
        bal_erow,
        textvariable=prev_due_var,
        font=_FB,
        bg=_C_BAL,
        fg=_HINT_FG,
        width=20,
        anchor="w",
    ).pack(side="left", padx=(0, 8))

    new_due_entry = tk.Entry(bal_erow, width=18, font=_FB)
    new_due_entry.pack(side="left", padx=(18, 0))
    new_due_entry.insert(0, "0.00")
    apply_entry_theme(new_due_entry)
    bind_tooltip(
        new_due_entry,
        tooltip_var,
        "Outstanding principal after this instalment (auto-computed as Prev. "
        "Due \u2212 Principal). Edit if needed.",
    )

    # ── Auto-logic helpers ────────────────────────────────────────────────
    def _recompute_payment(*_args):
        """Auto-compute Loan Payment = Principal + Interest + Charges."""
        try:
            p = float(principal_entry.get().replace(",", "") or 0)
            i = float(interest_entry.get().replace(",", "") or 0)
            c = float(charges_entry.get().replace(",", "") or 0)
            payment_entry.delete(0, "end")
            payment_entry.insert(0, f"{p + i + c:.2f}")
        except ValueError:
            pass

    def _recompute_due(*_args):
        """Auto-compute New Principal Due = Prev Due − Principal."""
        try:
            prev = _state["prev_principal_due"]
            p = float(principal_entry.get().replace(",", "") or 0)
            new_due_entry.delete(0, "end")
            new_due_entry.insert(0, f"{max(0.0, prev - p):.2f}")
        except ValueError:
            pass

    def _recompute_all(*_args):
        _recompute_payment()
        _recompute_due()

    for entry in (principal_entry, interest_entry, charges_entry):
        entry.bind("<KeyRelease>", _recompute_all)
        entry.bind("<FocusOut>", _recompute_all)

    def _on_loan_selected(_event=None):
        label = loan_combo.get()
        if label not in loan_map:
            return
        lm_id, ac_id, interest_rate = loan_map[label]
        _state["loan_master_id"] = lm_id
        _state["account_id"] = ac_id
        _state["interest_rate"] = interest_rate

        # Fetch last principal_due
        try:
            prev_due = get_last_loan_principal_due(lm_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("get_last_loan_principal_due failed: %s", exc)
            prev_due = 0.0
        _state["prev_principal_due"] = prev_due

        # Update display
        loan_info_var.set(f"Account ID = {ac_id}  |  Rate: {interest_rate:.2f}%")
        prev_due_var.set(f"\u20b9{prev_due:,.2f}")

        # Pre-fill prevailing rate
        rate_entry.delete(0, "end")
        rate_entry.insert(0, f"{interest_rate:.2f}")

        # Re-compute derived fields
        _recompute_all()

    loan_combo.bind("<<ComboboxSelected>>", _on_loan_selected)
    if loan_map:
        _on_loan_selected()

    # ── Session count ─────────────────────────────────────────────────────
    session_count_var = tk.StringVar(value="Session: 0 saved")
    tk.Label(
        win,
        textvariable=session_count_var,
        font=("Helvetica", 11, "italic"),
        bg=_T["main_bg"],
        fg=_HINT_FG,
    ).pack(anchor="e", padx=16)

    # ── Buttons ───────────────────────────────────────────────────────────
    btn_frame = tk.Frame(win, bg=_T["main_bg"])
    btn_frame.pack(pady=8)

    def _reset_form():
        import datetime

        trans_dt.set_date(datetime.date.today())
        description_entry.delete(0, "end")
        for e in (
            principal_entry,
            interest_entry,
            charges_entry,
            payment_entry,
            credit_entry,
        ):
            e.delete(0, "end")
            e.insert(0, "0.00")
        # Re-seed prevailing rate and due from state
        rate_entry.delete(0, "end")
        rate_entry.insert(0, f"{_state['interest_rate']:.2f}")
        prev_due = _state["prev_principal_due"]
        prev_due_var.set(f"\u20b9{prev_due:,.2f}")
        new_due_entry.delete(0, "end")
        new_due_entry.insert(0, f"{prev_due:.2f}")
        trans_dt.focus_set()

    def _validate_and_save():
        # Loan selected?
        loan_label = loan_combo.get()
        if not loan_label or loan_label not in loan_map:
            flash_error(loan_combo)
            show_colorful_error(win, "Validation Error", "Please select a loan.")
            return

        # Date
        try:
            loan_trans_dt = trans_dt.get_date().strftime("%Y-%m-%d")
        except Exception:  # noqa: BLE001
            flash_error(trans_dt)
            show_colorful_error(
                win, "Validation Error", "Please enter a valid transaction date."
            )
            return

        # Prevailing rate
        try:
            rate_str = rate_entry.get().strip().replace(",", "")
            prev_rate = float(rate_str or "0")
        except ValueError:
            flash_error(rate_entry)
            show_colorful_error(
                win, "Validation Error", "Prevailing Rate must be a number."
            )
            return
        if prev_rate <= 0:
            flash_error(rate_entry)
            show_colorful_error(
                win, "Validation Error", "Prevailing Interest Rate must be > 0."
            )
            return

        def _parse(entry, name):
            try:
                val_str = entry.get().strip().replace(",", "")
                return float(val_str or 0)
            except ValueError:
                flash_error(entry)
                show_colorful_error(
                    win, "Validation Error", f"{name} must be a number."
                )
                return None

        principal = _parse(principal_entry, "Principal")
        if principal is None:
            return
        interest = _parse(interest_entry, "Interest")
        if interest is None:
            return
        charges = _parse(charges_entry, "Charges")
        if charges is None:
            return
        loan_payment = _parse(payment_entry, "Loan Payment")
        if loan_payment is None:
            return
        loan_credit = _parse(credit_entry, "Loan Credit")
        if loan_credit is None:
            return
        principal_due = _parse(new_due_entry, "New Principal Due")
        if principal_due is None:
            return

        # At least one of principal / interest / charges should be > 0
        if principal <= 0 and interest <= 0 and charges <= 0 and loan_credit <= 0:
            flash_error(principal_entry)
            show_colorful_error(
                win,
                "Validation Error",
                "At least one of Principal / Interest / Charges / Loan Credit "
                "must be > 0.",
            )
            return

        lm_id, ac_id, _ = loan_map[loan_label]

        data = {
            "loan_master_id": lm_id,
            "account_id": ac_id,
            "loan_trans_dt": loan_trans_dt,
            "loan_description": description_entry.get().strip() or None,
            "prevailing_interest_rate": prev_rate,
            "loan_credit": loan_credit,
            "principal": principal,
            "interest": interest,
            "charges": charges,
            "loan_payment": loan_payment,
            "principal_due": principal_due,
        }

        try:
            lt_id = _db_add_loan_transaction(data)
        except Exception as exc:  # noqa: BLE001
            logger.error("add_loan_transaction failed: %s", exc)
            msg = f"Failed to save transaction:\n{exc}"
            show_colorful_error(win, "Database Error", msg)
            return

        # Update prev_principal_due for next entry in same session
        _state["prev_principal_due"] = principal_due

        session_records.append(
            {
                **data,
                "loan_trans_id": lt_id,
                "loan_label": loan_label,
            }
        )
        session_count_var.set(f"Session: {len(session_records)} saved")
        show_colorful_info(win, "Saved", f"Loan Transaction saved (ID {lt_id}).")
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

    loan_combo.bind("<Return>", _focus(trans_dt))
    trans_dt.bind("<Return>", _focus(description_entry))
    description_entry.bind("<Return>", _focus(rate_entry))
    rate_entry.bind("<Return>", _focus(principal_entry))
    principal_entry.bind("<Return>", _focus(interest_entry))
    interest_entry.bind("<Return>", _focus(charges_entry))
    charges_entry.bind("<Return>", _focus(payment_entry))
    payment_entry.bind("<Return>", _focus(credit_entry))
    credit_entry.bind("<Return>", _focus(new_due_entry))
    new_due_entry.bind("<Return>", lambda _e: _validate_and_save())

    # ── Initial focus ─────────────────────────────────────────────────────
    if loan_map:
        trans_dt.focus_set()
    else:
        loan_combo.focus_set()

    parent.wait_window(win)
