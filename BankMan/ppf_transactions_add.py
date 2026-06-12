# -*- coding: utf-8 -*-
# C:\Data\Personal\Finance_and_Investment\finprog\FinanceManager\BankMan\ppf_transactions_add.py

"""
GUI entry form for adding PPF (Public Provident Fund) transactions.

Follows the same structural pattern as bank_transactions_add.py:
  - Three coloured band frames: PPF Account / Transaction Details / Amounts
  - apply_entry_theme / bind_tooltip / setup_footer_tooltip from Shared.gui_utils
  - F1 = Help, F2 = Session viewer, Escape = close without saving
  - Yellow-on-black entry theme via centrally defined apply_entry_theme()
  - Distinct deep-amethyst / violet window theme (PPF_TRANS_ADD_UI_THEME)

This form writes directly to ppf_transactions for events that have no
corresponding bank-statement line (e.g. annual interest credits, balance
corrections).  Events triggered by a bank withdrawal/deposit are recorded
via bank_transactions_add with module_type='PPF'.
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
    PPF_TRANS_ADD_UI_THEME,
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
    get_all_ppf_masters,
    get_last_ppf_balance,
    db_add_ppf_transaction as _db_add_ppf_transaction,
)
from Shared.globals import logger
from Shared.gui_progressive import progressive_selection
from .ppf_master_add import add_ppf_master_main as _add_ppf

# ---------------------------------------------------------------------------
# Theme alias
# ---------------------------------------------------------------------------
_T = PPF_TRANS_ADD_UI_THEME

# ---------------------------------------------------------------------------
# PPF master map type  {display_label: (ppf_master_id, account_id, ...)}
# ---------------------------------------------------------------------------
#   display label: "AcctNo | HolderName | BankName [ac_number]"
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Band / label helpers (same pattern as bank_transactions_add.py)
# ---------------------------------------------------------------------------


def _make_band(container, bg, relief="ridge", padx=10, pady=6):
    """Coloured section band with stacked label_row / entry_row.

    Returns (band_frame, label_row, entry_row).
    """
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
    """Pack a gold field label into a band label_row."""
    tk.Label(
        parent,
        text=text,
        font=font,
        bg=bg,
        fg=_T["label_fg"],
        anchor="w",
    ).pack(side="left", padx=(padx, 12))


# ---------------------------------------------------------------------------
# Help window (F1)
# ---------------------------------------------------------------------------


def _show_help(win: tk.Toplevel, on_escape) -> None:
    """Help sub-window for Add PPF Transaction."""
    win.unbind("<Escape>")

    help_win = tk.Toplevel(win)
    try:
        help_win.transient(win)
    except (tk.TclError, AttributeError) as exc:
        logger.debug("help_win.transient failed: %s", exc)
    help_win.title("Help \u2014 Add PPF Transaction")
    help_win.configure(bg=_T["header_bg"])
    help_win.geometry("700x720")
    help_win.resizable(False, False)
    help_win.grab_set()
    push_window(help_win, win)
    try:
        help_win.focus_set()
    except tk.TclError:
        pass

    tk.Label(
        help_win,
        text="Add PPF Transaction \u2014 Help",
        font=("Helvetica", 16, "bold"),
        bg=_T["header_bg"],
        fg=_T["header_fg"],
        pady=8,
    ).pack(fill="x")

    body = tk.Frame(help_win, bg=_T["main_bg"], padx=12, pady=12)
    body.pack(fill="both", expand=True)

    text = tk.Text(
        body,
        wrap="word",
        bg=_T["main_bg"],
        fg="#FFD700",
        bd=0,
        padx=6,
        pady=6,
        font=("Helvetica", 11),
        height=30,
        insertbackground="#FFD700",
    )
    text.pack(fill="both", expand=True)

    help_lines = [
        "\u2022 This form records a direct PPF sub-ledger transaction.",
        "  Use it for events that have NO corresponding bank-statement line,",
        "  such as annual interest credits or balance corrections.",
        "  For PPF deposits/withdrawals visible on your bank statement,",
        "  use the Bank Transaction form with Module Type = PPF instead.",
        "",
        "Fields:",
        "  PPF Account     \u2014 Select the PPF account from the dropdown.",
        "                    Populated from the PPF master register.",
        "  Account (linked)\u2014 Auto-filled from the selected PPF account.",
        "                    Read-only; shown for reference only.",
        "  Transaction Date\u2014 Date of the PPF event (YYYY-MM-DD).",
        "  Transaction Type\u2014 DEPOSIT   : money added to the PPF account.",
        "                    INTEREST  : annual interest credited by the",
        "                                government (no bank debit).",
        "                    WITHDRAWAL: partial/full withdrawal from PPF.",
        "  Description     \u2014 Optional narration, e.g. 'FY2025 deposit',",
        "                    'Interest @ 7.1%', 'Partial withdrawal Yr 10'.",
        "  PPF Saving      \u2014 Amount deposited or interest credited (CR).",
        "                    Auto-filled for DEPOSIT / INTEREST type.",
        "  PPF Withdrawal  \u2014 Amount withdrawn from PPF (DR).",
        "                    Auto-filled for WITHDRAWAL type.",
        "  PPF Balance     \u2014 Account balance after this transaction.",
        "                    Auto-computed: prev balance + saving \u2212 withdrawal.",
        "                    You may override it to match the passbook.",
        "",
        "PPF Limits (for reference):",
        "  \u2022 Minimum annual deposit : \u20b9500",
        "  \u2022 Maximum annual deposit : \u20b91,50,000",
        "  \u2022 Withdrawals allowed    : after year 7 of each block,",
        "                             up to 50% of balance at end of",
        "                             year 4 or year preceding withdrawal.",
        "  \u2022 Interest rate          : declared by Govt. each quarter.",
        "",
        "Hotkeys:",
        "  F1  : This help screen",
        "  F2  : Session viewer (transactions added in this session)",
        "  Esc : Close without saving",
    ]
    text.insert("1.0", "\n".join(help_lines))
    text.config(state="disabled")

    def close_help(_e=None):
        safe_close_modal(help_win, win)
        win.bind("<Escape>", on_escape)
        return "break"

    help_win.bind("<Escape>", close_help)
    help_win.protocol("WM_DELETE_WINDOW", close_help)

    help_close_btn = tk.Button(
        help_win,
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


def _show_session_viewer(
    win: tk.Toplevel,
    session_records: list,
    on_escape,
) -> None:
    """Show PPF transactions added in this session."""
    if not session_records:
        try:
            show_colorful_info(
                win,
                "No Entries",
                "No PPF transactions have been added in this session yet.",
            )
        except tk.TclError:
            pass
        return

    win.unbind("<Escape>")
    idx = {"i": 0}

    viewer = tk.Toplevel(win)
    viewer.title("Session \u2014 PPF Transactions Added")
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
        text="PPF Transactions Added This Session",
        font=("Helvetica", 14, "bold"),
        bg=_T["header_bg"],
        fg=_T["header_fg"],
        pady=6,
    ).pack(fill="x")

    content = tk.Frame(viewer, bg=_T["header_bg"])
    content.pack(fill="both", expand=True, padx=10, pady=6)

    nav_frame = tk.Frame(content, bg=_T["header_bg"])
    nav_frame.pack(fill="x")
    left_btn = tk.Button(
        nav_frame,
        text="\u25c4",
        width=3,
        bg=_T.get("session_btn_bg", _T["button_bg"]),
        fg=_T.get("button_fg", "white"),
        activeforeground=_T.get("button_fg", "white"),
        cursor="hand2",
    )
    left_btn.pack(side="left", padx=(6, 4), pady=4)
    apply_button_animations(
        left_btn,
        _T.get("session_btn_bg", _T["button_bg"]),
        _T.get("session_btn_hover_bg", "#115e59"),
    )
    right_btn = tk.Button(
        nav_frame,
        text="\u25ba",
        width=3,
        bg=_T.get("session_btn_bg", _T["button_bg"]),
        fg=_T.get("button_fg", "white"),
        activeforeground=_T.get("button_fg", "white"),
        cursor="hand2",
    )
    right_btn.pack(side="right", padx=(4, 6), pady=4)
    apply_button_animations(
        right_btn,
        _T.get("session_btn_bg", _T["button_bg"]),
        _T.get("session_btn_hover_bg", "#115e59"),
    )
    status_label = tk.Label(
        nav_frame,
        text="",
        font=("Helvetica", 10, "bold"),
        bg=_T.get("session_bg", _T["header_bg"]),
        fg=_T.get("session_ok_fg", _T["header_fg"]),
    )
    status_label.pack(side="left", padx=10)

    info_text = tk.Text(
        content,
        wrap="word",
        height=16,
        bg=_T.get("session_bg", _T["main_bg"]),
        fg=_T.get("session_value_fg", "#FFD700"),
        bd=0,
        relief="flat",
        font=("Helvetica", 11),
        insertbackground=_T.get("session_value_fg", "#FFD700"),
    )
    info_text.pack(fill="both", expand=True, padx=4, pady=4)
    info_text.tag_configure(
        "label",
        font=("Helvetica", 11, "bold"),
        foreground=_T.get("session_label_fg", "#FFD700"),
    )
    info_text.tag_configure(
        "value",
        font=("Helvetica", 11),
        foreground=_T.get("session_value_fg", "#e2e8f0"),
    )
    info_text.config(state="disabled")

    def _update_view():
        i = idx["i"]
        rec = session_records[i]
        info_text.config(state="normal")
        info_text.delete("1.0", "end")
        rows = [
            ("PPF Account", rec.get("ppf_label")),
            ("Trans Date", rec.get("ppf_trans_dt")),
            ("Trans Type", rec.get("trans_type")),
            ("Description", rec.get("ppf_description") or "\u2014"),
            ("PPF Saving (\u20b9)", f"{rec.get('ppf_saving', 0.0):,.2f}"),
            ("PPF Withdrawal (\u20b9)", f"{rec.get('ppf_withdrawal', 0.0):,.2f}"),
            ("PPF Balance (\u20b9)", f"{rec.get('ppf_balance', 0.0):,.2f}"),
        ]
        for lbl, val in rows:
            info_text.insert("end", f"{lbl}: ", "label")
            info_text.insert("end", f"{val}\n", "value")
        info_text.config(state="disabled")

        left_btn.config(state="disabled" if i == 0 else "normal")
        total = len(session_records)
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
        if idx["i"] < len(session_records) - 1:
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
# Balance auto-fill helper
# ---------------------------------------------------------------------------


def _compute_balance(
    prev_balance: float,
    saving_entry: tk.Entry,
    withdrawal_entry: tk.Entry,
    balance_entry: tk.Entry,
    win: tk.Toplevel,
    _event=None,
) -> None:
    """Recompute ppf_balance = prev_balance + saving - withdrawal."""
    try:
        saving = float(saving_entry.get().strip().replace(",", "") or "0")
        withdrawal = float(withdrawal_entry.get().strip().replace(",", "") or "0")
    except ValueError:
        return
    computed = round(prev_balance + saving - withdrawal, 2)
    balance_entry.delete(0, tk.END)
    balance_entry.insert(0, str(computed))
    if computed < 0:
        show_colorful_error(
            win,
            "Balance Warning",
            f"Computed balance is negative (\u20b9{computed:,.2f}). "
            "Please verify the amounts.",
        )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def add_ppf_transaction_main(
    parent: Union[tk.Toplevel, tk.Tk],
    calling_button: tk.Widget | None = None,
) -> None:
    """Launch the Add PPF Transaction dialog."""

    # ── Lookup data ───────────────────────────────────────────────────────
    ppf_rows = get_all_ppf_masters()
    # display label → (ppf_master_id, account_id, holder_name)
    # label: "AcctNo  |  HolderName  [BankName]"
    ppf_map: dict[str, tuple[int, int, str]] = {}
    for row in ppf_rows:
        # row indices: 0=ppf_master_id, 1=ppf_account_number, 2=holder_name,
        #              3=open_dt, 4=maturity_dt, 5=is_active,
        #              6=bank_name, 7=ac_number, 8=account_id
        label = f"{row[1]}  |  {row[2]}  [{row[6]}]"
        ppf_map[label] = (row[0], row[8], row[2])

    # ── Mutable state shared across closures ──────────────────────────────
    _prev_balance: list[float] = [0.0]  # last ppf_balance for selected account

    # ── Window setup ──────────────────────────────────────────────────────
    disable_parent(parent, calling_button=calling_button)
    session_records: list = []

    win = tk.Toplevel(parent)
    win.title("\U0001f4b0 Add PPF Transaction \U0001f4b0")
    win.geometry("1000x600")
    win.resizable(False, False)
    win.configure(bg=_T["main_bg"])
    win.transient(parent)
    win.grab_set()
    win.focus_set()
    try:
        push_window(win, parent)
    except (RuntimeError, tk.TclError) as exc:
        logger.debug("push_window failed: %s", exc)

    # ── Footer tooltip (packed first — anchors to the bottom) ─────────────
    tooltip_var = setup_footer_tooltip(
        win, bg_color=_T["header_bg"], fg_color=_T["header_fg"]
    )

    # ── Close / Escape helpers ────────────────────────────────────────────
    def cleanup_and_close(_event=None):
        return safe_close_modal(win, parent, calling_button)

    def on_escape(_event=None):
        return cleanup_and_close()

    # ── F1 / F2 / Escape ─────────────────────────────────────────────────
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
        text="\U0001f4b0  Add PPF Transaction  \U0001f4b0",
        font=("Helvetica", 18, "bold"),
        bg=_T["header_bg"],
        fg=_T["header_fg"],
        relief="ridge",
        bd=2,
        pady=8,
    ).pack(fill="x")

    # Hotkey hint row
    hint_frame = tk.Frame(win, bg=_T["main_bg"])
    hint_frame.pack(fill="x", padx=10, pady=(2, 0))
    for hint_text in ("F1: Help", "F2: Session Viewer", "Esc: Close"):
        tk.Label(
            hint_frame,
            text=hint_text,
            font=("Helvetica", 10, "italic"),
            bg=_T["main_bg"],
            fg="#c084fc",  # soft violet hint text
        ).pack(side="left", padx=12)

    # ── Font constants ────────────────────────────────────────────────────
    _F = ("Helvetica", 14)
    _FB = ("Helvetica", 14, "bold")

    _C_MASTER = _T["band_master"]  # Band 1: PPF account selector
    _C_DETAIL = _T["band_details"]  # Band 2: date, type, description
    _C_AMT = _T["band_amounts"]  # Band 3: amounts + balance

    form_body = tk.Frame(win, bg=_T["main_bg"])
    form_body.pack(fill="x", padx=12, pady=6)

    # ── Band 1: PPF Account selector ──────────────────────────────────────
    master_band, master_lrow, master_erow = _make_band(form_body, _C_MASTER)
    master_band.pack(fill="x", pady=(0, 5))

    _band_label(master_lrow, "PPF Account", _C_MASTER, _F)
    _band_label(master_lrow, "Linked Bank Account (auto)", _C_MASTER, _F, padx=140)

    ppf_labels = list(ppf_map.keys())
    ppf_combo = ttk.Combobox(
        master_erow,
        width=40,
        values=ppf_labels,
        font=_F,
    )
    ppf_combo.pack(side="left", padx=(0, 12))
    apply_entry_theme(ppf_combo)
    progressive_selection(ppf_combo, ppf_labels)
    bind_tooltip(
        ppf_combo,
        tooltip_var,
        "Select the PPF account.  "
        "Linked bank account and last balance are auto-loaded.",
    )

    def _refresh_ppf_combo():
        new_rows = get_all_ppf_masters()
        ppf_map.clear()
        for row in new_rows:
            label = f"{row[1]}  |  {row[2]}  [{row[6]}]"
            ppf_map[label] = (row[0], row[8], row[2])
        ppf_labels.clear()
        ppf_labels.extend(ppf_map.keys())
        ppf_combo["values"] = list(ppf_labels)
        progressive_selection(ppf_combo, list(ppf_labels))

    def on_ppf_focus_out(_event=None):
        try:
            if not win.winfo_exists():
                return
        except (tk.TclError, NameError):
            return
        typed = ppf_combo.get().strip()
        if not typed:
            return
        if typed not in ppf_map:
            response = show_colorful_yesno(
                win,
                "PPF Account Not Found",
                f"'{typed}' was not found. Add a new PPF account " "now?",
            )
            if response:
                _add_ppf(win)
                _refresh_ppf_combo()
                ppf_combo.focus_set()
            else:
                show_colorful_error(
                    win,
                    "Invalid Selection",
                    "Please select a valid PPF account from the list.",
                )
                flash_error(ppf_combo)
                ppf_combo.focus_set()

    ppf_combo.bind("<FocusOut>", on_ppf_focus_out, add="+")

    if ppf_labels:
        ppf_combo.set(ppf_labels[0])

    linked_acct_var = tk.StringVar(value="\u2014")
    linked_acct_lbl = tk.Label(
        master_erow,
        textvariable=linked_acct_var,
        font=_F,
        bg=_C_MASTER,
        fg="#e2e8f0",
        width=30,
        anchor="w",
    )
    linked_acct_lbl.pack(side="left", padx=(8, 0))

    # ── Band 2: Transaction Date / Type / Description ─────────────────────
    detail_band, detail_lrow, detail_erow = _make_band(form_body, _C_DETAIL)
    detail_band.pack(fill="x", pady=(0, 5))

    _band_label(detail_lrow, "Trans Date", _C_DETAIL, _F)
    _band_label(detail_lrow, "Transaction Type", _C_DETAIL, _F, padx=106)
    _band_label(detail_lrow, "Description (optional)", _C_DETAIL, _F, padx=80)

    trans_dt = DateEntry(detail_erow, date_pattern="dd-mm-yyyy", width=14, font=_F)
    trans_dt.pack(side="left", padx=(0, 20))
    apply_entry_theme(trans_dt)
    bind_tooltip(trans_dt, tooltip_var, "Date of this PPF event (calendar picker).")
    bind_date_spin(trans_dt)

    # Transaction type radio buttons
    trans_type_var = tk.StringVar(value="DEPOSIT")
    _TYPES = [
        ("DEPOSIT", "Deposit to PPF"),
        ("INTEREST", "Interest Credit"),
        ("WITHDRAWAL", "Withdrawal from PPF"),
    ]
    type_frame = tk.Frame(detail_erow, bg=_C_DETAIL)
    type_frame.pack(side="left", padx=(0, 20))
    for val, label_text in _TYPES:
        tk.Radiobutton(
            type_frame,
            text=label_text,
            variable=trans_type_var,
            value=val,
            font=("Helvetica", 11),
            bg=_C_DETAIL,
            fg=_T["label_fg"],
            selectcolor="#3b0066",
            activebackground=_C_DETAIL,
            activeforeground="#FFD700",
            cursor="hand2",
        ).pack(side="left", padx=6)

    description_entry = tk.Entry(detail_erow, width=30, font=_F)
    description_entry.pack(side="left")
    apply_entry_theme(description_entry)
    bind_tooltip(
        description_entry,
        tooltip_var,
        "Optional narration, e.g. 'Annual deposit FY2025', "
        "'Interest @ 7.1%', 'Partial withdrawal'.",
    )

    # ── Band 3: Amounts + Balance ─────────────────────────────────────────
    amt_band, amt_lrow, amt_erow = _make_band(form_body, _C_AMT)
    amt_band.pack(fill="x", pady=(0, 5))

    _band_label(amt_lrow, "PPF Saving (\u20b9)", _C_AMT, _F)
    _band_label(amt_lrow, "PPF Withdrawal (\u20b9)", _C_AMT, _F, padx=60)
    _band_label(amt_lrow, "PPF Balance (\u20b9)", _C_AMT, _F, padx=60)
    _band_label(
        amt_lrow,
        "(prev balance + saving \u2212 withdrawal)",
        _C_AMT,
        ("Helvetica", 10, "italic"),
        padx=30,
    )

    saving_entry = tk.Entry(amt_erow, width=14, font=_FB)
    saving_entry.insert(0, "0.0")
    saving_entry.pack(side="left", padx=(0, 30))
    apply_entry_theme(saving_entry)
    bind_tooltip(
        saving_entry,
        tooltip_var,
        "Amount deposited into or interest credited to the PPF account. "
        "Zero for a withdrawal.",
    )

    withdrawal_entry = tk.Entry(amt_erow, width=14, font=_FB)
    withdrawal_entry.insert(0, "0.0")
    withdrawal_entry.pack(side="left", padx=(0, 30))
    apply_entry_theme(withdrawal_entry)
    bind_tooltip(
        withdrawal_entry,
        tooltip_var,
        "Amount withdrawn from the PPF account. "
        "Zero for a deposit or interest credit.",
    )

    balance_entry = tk.Entry(amt_erow, width=14, font=_FB)
    balance_entry.pack(side="left", padx=(0, 16))
    apply_entry_theme(balance_entry)
    bind_tooltip(
        balance_entry,
        tooltip_var,
        "Running PPF account balance after this event. "
        "Auto-computed; override if needed to match passbook.",
    )

    # Prev balance info label
    prev_bal_var = tk.StringVar(value="Prev balance: \u20b90.00")
    tk.Label(
        amt_erow,
        textvariable=prev_bal_var,
        font=("Helvetica", 11, "italic"),
        bg=_C_AMT,
        fg="#c084fc",
    ).pack(side="left", padx=4)

    # ── Transaction-type → auto-fill description & amount fields ──────────
    def _on_type_change(*_):
        t = trans_type_var.get()
        # Set a sensible default description if the field is blank/generic
        current_desc = description_entry.get().strip()
        generic = {"Deposit to PPF", "Interest Credit", "Withdrawal from PPF"}
        if not current_desc or current_desc in generic:
            description_entry.delete(0, tk.END)
            if t == "DEPOSIT":
                description_entry.insert(0, "Annual deposit")
            elif t == "INTEREST":
                description_entry.insert(0, "Interest credit")
            elif t == "WITHDRAWAL":
                description_entry.insert(0, "Partial withdrawal")
        # For WITHDRAWAL, suggest clearing saving to 0.0
        if t == "WITHDRAWAL":
            if saving_entry.get().strip() in ("0.0", "0", ""):
                pass  # already zero
            # Don't overwrite user-entered values
        # Refresh balance
        _refresh_balance()

    trans_type_var.trace_add("write", _on_type_change)

    # ── PPF account change → load prev balance ────────────────────────────
    def _on_ppf_change(*_):
        label = ppf_combo.get()
        if not label or label not in ppf_map:
            linked_acct_var.set("\u2014")
            _prev_balance[0] = 0.0
            prev_bal_var.set("Prev balance: \u20b90.00")
            return
        ppf_master_id, account_id, holder_name = ppf_map[label]
        linked_acct_var.set(f"ID={account_id}  ({holder_name})")
        try:
            bal = get_last_ppf_balance(ppf_master_id)
            _prev_balance[0] = bal
            prev_bal_var.set(f"Prev balance: \u20b9{bal:,.2f}")
        except Exception as exc:  # noqa: BLE001
            logger.debug("last ppf balance fetch failed: %s", exc)
            _prev_balance[0] = 0.0
            prev_bal_var.set("Prev balance: \u20b90.00")
        _refresh_balance()

    ppf_combo.bind("<<ComboboxSelected>>", _on_ppf_change)
    win.after(60, _on_ppf_change)  # initialise on open

    # ── Auto-compute balance on amount change ─────────────────────────────
    def _refresh_balance(_event=None):
        _compute_balance(
            _prev_balance[0],
            saving_entry,
            withdrawal_entry,
            balance_entry,
            win,
        )

    saving_entry.bind("<FocusOut>", _refresh_balance)
    withdrawal_entry.bind("<FocusOut>", _refresh_balance)

    # ── Tab / Return navigation ───────────────────────────────────────────
    ppf_combo.bind("<Return>", lambda e: trans_dt.focus_set())
    trans_dt.bind("<Return>", lambda e: description_entry.focus_set())
    description_entry.bind("<Return>", lambda e: saving_entry.focus_set())
    saving_entry.bind("<Return>", lambda e: withdrawal_entry.focus_set())
    withdrawal_entry.bind("<Return>", lambda e: balance_entry.focus_set())

    # ── Action buttons ────────────────────────────────────────────────────
    btn_frame = tk.Frame(win, bg=_T["main_bg"])
    btn_frame.pack(fill="x", padx=12, pady=(8, 4))

    def _make_btn(parent_frame, text, command, bg, act_bg):
        btn = tk.Button(
            parent_frame,
            text=text,
            command=command,
            font=("Helvetica", 12, "bold"),
            bg=bg,
            fg=_T.get("button_fg", "white"),
            activeforeground=_T.get("button_fg", "white"),
            cursor="hand2",
            padx=16,
            pady=6,
            relief="raised",
            bd=2,
        )
        btn.pack(side="left", padx=6)
        apply_button_animations(btn, bg, act_bg)
        return btn

    # ── Reset form ────────────────────────────────────────────────────────
    def _reset_form():
        trans_type_var.set("DEPOSIT")
        description_entry.delete(0, tk.END)
        description_entry.insert(0, "Annual deposit")
        saving_entry.delete(0, tk.END)
        saving_entry.insert(0, "0.0")
        withdrawal_entry.delete(0, tk.END)
        withdrawal_entry.insert(0, "0.0")
        _on_ppf_change()  # reload balance from DB
        saving_entry.focus_set()

    # ── Validate & submit ─────────────────────────────────────────────────
    def on_submit(_event=None):
        ppf_label = ppf_combo.get().strip()
        if not ppf_label or ppf_label not in ppf_map:
            show_colorful_error(
                win, "Validation Error", "Please select a valid PPF account."
            )
            flash_error(ppf_combo)
            ppf_combo.focus_set()
            return

        ppf_master_id, account_id, _holder = ppf_map[ppf_label]

        try:
            trans_date_str = trans_dt.get_date().strftime("%Y-%m-%d")
        except Exception:  # noqa: BLE001
            show_colorful_error(
                win, "Validation Error", "Please enter a valid transaction date."
            )
            trans_dt.focus_set()
            return

        trans_type = trans_type_var.get()
        description = description_entry.get().strip() or None

        try:
            saving_str = saving_entry.get().strip().replace(",", "")
            saving = float(saving_str or "0")
            if saving < 0:
                raise ValueError
        except ValueError:
            show_colorful_error(
                win,
                "Validation Error",
                "PPF Saving must be a non-negative number.",
            )
            flash_error(saving_entry)
            saving_entry.focus_set()
            return

        try:
            withdrawal_str = withdrawal_entry.get().strip().replace(",", "")
            withdrawal = float(withdrawal_str or "0")
            if withdrawal < 0:
                raise ValueError
        except ValueError:
            show_colorful_error(
                win,
                "Validation Error",
                "PPF Withdrawal must be a non-negative number.",
            )
            flash_error(withdrawal_entry)
            withdrawal_entry.focus_set()
            return

        if saving == 0.0 and withdrawal == 0.0:
            show_colorful_error(
                win,
                "Validation Error",
                "At least one of PPF Saving or PPF Withdrawal must be " "non-zero.",
            )
            flash_error(saving_entry)
            return

        if saving > 0.0 and withdrawal > 0.0:
            show_colorful_error(
                win,
                "Validation Error",
                "Only one of PPF Saving or PPF Withdrawal can be "
                "non-zero per transaction.",
            )
            flash_error(saving_entry)
            flash_error(withdrawal_entry)
            return

        # Enforce type consistency
        if trans_type == "WITHDRAWAL" and withdrawal == 0.0:
            show_colorful_error(
                win,
                "Validation Error",
                "Transaction type is WITHDRAWAL but PPF Withdrawal is " "zero.",
            )
            flash_error(withdrawal_entry)
            withdrawal_entry.focus_set()
            return

        if trans_type in ("DEPOSIT", "INTEREST") and saving == 0.0:
            show_colorful_error(
                win,
                "Validation Error",
                f"Transaction type is {trans_type} but PPF Saving is zero.",
            )
            flash_error(saving_entry)
            saving_entry.focus_set()
            return

        try:
            balance_str = balance_entry.get().strip().replace(",", "")
            balance = float(balance_str or "0")
        except ValueError:
            show_colorful_error(
                win,
                "Validation Error",
                "PPF Balance must be a valid number.",
            )
            flash_error(balance_entry)
            balance_entry.focus_set()
            return

        if balance < 0:
            show_colorful_error(
                win,
                "Validation Error",
                f"PPF Balance cannot be negative (\u20b9{balance:,.2f}).",
            )
            flash_error(balance_entry)
            balance_entry.focus_set()
            return

        try:
            new_id = _db_add_ppf_transaction(
                {
                    "ppf_master_id": ppf_master_id,
                    "account_id": account_id,
                    "ppf_trans_dt": trans_date_str,
                    "ppf_description": description,
                    "ppf_saving": saving,
                    "ppf_withdrawal": withdrawal,
                    "ppf_balance": balance,
                }
            )
        except Exception as exc:  # noqa: BLE001
            msg = f"Failed to save transaction: {exc}"
            show_colorful_error(win, "Database Error", msg)
            return

        session_records.append(
            {
                "ppf_trans_id": new_id,
                "ppf_label": ppf_label,
                "ppf_trans_dt": trans_date_str,
                "trans_type": trans_type,
                "ppf_description": description,
                "ppf_saving": saving,
                "ppf_withdrawal": withdrawal,
                "ppf_balance": balance,
            }
        )
        _session_count_var.set(
            f"Session: {len(session_records)} "
            f"transaction{'s' if len(session_records) != 1 else ''} "
            "added  (F2 to review)"
        )
        show_colorful_info(
            win,
            "Success",
            f"PPF transaction saved successfully (ID: {new_id}).",
        )
        _reset_form()

    balance_entry.bind("<Return>", on_submit)

    submit_btn = _make_btn(
        btn_frame,
        "\u2705  Save Transaction",
        on_submit,
        _T.get("submit_bg", _T.get("button_bg", "#4a007a")),
        _T.get("submit_hover_bg", "#6b21a8"),
    )
    _make_btn(
        btn_frame,
        "\u274c  Close",
        on_escape,
        _T.get("cancel_bg", "#7f1d1d"),
        _T.get("cancel_hover_bg", "#450a0a"),
    )

    submit_btn.bind("<Return>", on_submit)

    # ── Session counter label ─────────────────────────────────────────────
    _session_count_var = tk.StringVar(
        value="Session: 0 transactions added  (F2 to review)"
    )
    tk.Label(
        btn_frame,
        textvariable=_session_count_var,
        font=("Helvetica", 10, "italic"),
        bg=_T["main_bg"],
        fg="#c084fc",
    ).pack(side="left", padx=20)

    # ── Initial focus ─────────────────────────────────────────────────────
    win.after(120, ppf_combo.focus_set)
