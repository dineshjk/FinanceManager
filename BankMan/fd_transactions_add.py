# -*- coding: utf-8 -*-
# C:\Data\Personal\Finance_and_Investment\finprog\FinanceManager\BankMan\fd_transactions_add.py

"""
Module for adding Fixed Deposit transaction records (fd_transactions table).

Structural pattern from cc_transactions_add.py / ppf_transactions_add.py:
  - Coloured band frames, each with a label_row / entry_row
  - apply_entry_theme / bind_tooltip / setup_footer_tooltip from Shared.gui_utils
  - F1 = Help, F2 = Session viewer, Escape = close without saving
  - Yellow-on-black entry theme via centrally defined apply_entry_theme()
  - Distinct dark copper/bronze window theme (FD_TRANS_ADD_UI_THEME)
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
    FD_TRANS_ADD_UI_THEME,
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
    get_all_fd_masters_for_display,
    db_add_fd_transaction as _db_add_fd_transaction,
)
from Shared.globals import logger
from Shared.gui_progressive import progressive_selection
from .fd_master_add import add_fd_master_main as _add_fd

# ---------------------------------------------------------------------------
# Theme alias and constants
# ---------------------------------------------------------------------------
_T = FD_TRANS_ADD_UI_THEME

_TRANS_TYPES = ["DEPOSIT", "INTEREST_CREDIT", "MATURITY", "PREMATURE_CLOSURE"]
_DEFAULT_DESC = {
    "DEPOSIT": "FD Deposit",
    "INTEREST_CREDIT": "FD Interest Credit",
    "MATURITY": "FD Maturity Proceeds",
    "PREMATURE_CLOSURE": "FD Premature Closure",
}

# ---------------------------------------------------------------------------
# Band / label helpers
# ---------------------------------------------------------------------------


def _make_band(container, bg, relief="ridge", padx=10, pady=6):
    """Create a coloured section band with stacked label_row / entry_row."""
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
    """Launch the Help sub-window for Add FD Transaction."""
    win.unbind("<Escape>")

    help_win = tk.Toplevel(win)
    try:
        help_win.transient(win)
    except (tk.TclError, AttributeError) as exc:
        logger.debug("help_win.transient failed: %s", exc)
    help_win.title("Help — Add FD Transaction")
    help_win.configure(bg=_T["header_bg"])
    help_win.geometry("720x680")
    help_win.resizable(False, False)
    help_win.grab_set()
    push_window(help_win, win)
    try:
        help_win.focus_set()
    except tk.TclError:
        pass

    tk.Label(
        help_win,
        text="Add FD Transaction  —  Help",
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
        "\u2022 This form records a new entry in the fd_transactions table.",
        "",
        "Fields:",
        "  FD Account       \u2014 Select the Fixed Deposit from the dropdown.",
        "                     Only active FDs are listed.",
        "  Linked Account   \u2014 Auto-filled from the selected FD master.",
        "  Trans Date       \u2014 Date of this FD event (DD-MM-YYYY).",
        "  Trans Type       \u2014 DEPOSIT         : Initial deposit or top-up.",
        "                     INTEREST_CREDIT : Periodic interest payout.",
        "                     MATURITY        : FD matured; proceeds credited.",
        "                     PREMATURE_CLOSURE: Closed before maturity.",
        "  FD Saving (\u20b9)    \u2014 Amount deposited / added to the FD.",
        "                     Fill for DEPOSIT. Leave 0 otherwise.",
        "  FD Withdrawal(\u20b9) \u2014 Amount withdrawn (MATURITY / PREMATURE_CLOSURE).",
        "  FD Principal(\u20b9)  \u2014 Principal component of this event.",
        "                     Fill for MATURITY / PREMATURE_CLOSURE breakdowns.",
        "  FD Interest (\u20b9)  \u2014 Interest component credited in this event.",
        "                     Fill for INTEREST_CREDIT and MATURITY.",
        "",
        "Typical patterns:",
        "  DEPOSIT          : fd_saving > 0, others 0.",
        "  INTEREST_CREDIT  : fd_int > 0, others 0.",
        "  MATURITY         : fd_withdrawal = principal + interest;",
        "                     fd_principal + fd_int filled for breakdown.",
        "  PREMATURE_CLOSURE: fd_withdrawal > 0; fd_principal filled.",
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
    session_entries: list,
    on_escape,
) -> None:
    """Show FD transactions added in this session."""
    if not session_entries:
        try:
            show_colorful_info(
                win,
                "No Entries",
                "No FD transactions have been added this session.",
            )
        except tk.TclError:
            pass
        return

    win.unbind("<Escape>")
    idx = {"i": 0}

    viewer = tk.Toplevel(win)
    viewer.title("Session — FD Transactions Added")
    viewer.transient(win)
    viewer.grab_set()
    viewer.resizable(False, False)
    viewer.geometry("600x380")
    viewer.configure(bg=_T["header_bg"])
    push_window(viewer, win)
    try:
        viewer.focus_set()
    except tk.TclError:
        pass

    tk.Label(
        viewer,
        text="FD Transactions Added This Session",
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
            ("FD", rec.get("fd_label")),
            ("Trans Date", rec.get("fd_trans_dt")),
            ("Trans Type", rec.get("trans_type")),
            ("FD Saving (\u20b9)", f"{rec.get('fd_saving', 0.0):,.2f}"),
            ("FD Withdrawal (\u20b9)", f"{rec.get('fd_withdrawal', 0.0):,.2f}"),
            ("FD Principal (\u20b9)", f"{rec.get('fd_principal', 0.0):,.2f}"),
            ("FD Interest (\u20b9)", f"{rec.get('fd_int', 0.0):,.2f}"),
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


def add_fd_transaction_main(
    parent: Union[tk.Toplevel, tk.Tk],
    calling_button: tk.Widget | None = None,
) -> None:
    """Launch the Add FD Transaction dialog."""

    # ── Lookup data ───────────────────────────────────────────────────────
    fds = get_all_fd_masters_for_display()
    # label: "FDNumber  [BankName]  @rate%"  →  (fd_master_id, account_id, principal)
    fd_map: dict[str, tuple[int, int, float]] = {}
    for row in fds:
        label = f"{row[1]}  [{row[4]}]  @{row[5]:.2f}%"
        fd_map[label] = (int(row[0]), int(row[3]), float(row[2]))

    _state: dict = {
        "fd_master_id": None,
        "account_id": None,
        "principal": 0.0,
    }

    # ── Window setup ──────────────────────────────────────────────────────
    disable_parent(parent, calling_button=calling_button)
    session_records: list = []

    win = tk.Toplevel(parent)
    win.title("\U0001f3e6 Add FD Transaction \U0001f3e6")
    win.geometry("1060x580")
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
        text="\U0001f3e6  Add FD Transaction  \U0001f3e6",
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
            fg="#fdba74",  # soft copper hint text
        ).pack(side="left", padx=12)

    # ── Form body ─────────────────────────────────────────────────────────
    _F = ("Helvetica", 14)
    _FB = ("Helvetica", 14, "bold")

    _C_MASTER = _T["band_master"]
    _C_DETAIL = _T["band_details"]
    _C_AMT = _T["band_amounts"]

    form_body = tk.Frame(win, bg=_T["main_bg"])
    form_body.pack(fill="x", padx=12, pady=6)

    # ── Band 1: FD selector + Linked Account info ─────────────────────────
    mst_band, mst_lrow, mst_erow = _make_band(form_body, _C_MASTER)
    mst_band.pack(fill="x", pady=(0, 5))

    _band_label(mst_lrow, "Fixed Deposit", _C_MASTER, _F)
    _band_label(mst_lrow, "Linked Account / Principal", _C_MASTER, _F, padx=110)

    fd_combo = ttk.Combobox(
        mst_erow,
        width=40,
        values=list(fd_map.keys()),
        font=_F,
    )
    fd_combo.pack(side="left", padx=(0, 8))
    apply_entry_theme(fd_combo)
    progressive_selection(fd_combo, list(fd_map.keys()))
    bind_tooltip(
        fd_combo, tooltip_var, "Select the Fixed Deposit for this transaction."
    )

    def _refresh_fd_combo():
        new_fds = get_all_fd_masters_for_display()
        fd_map.clear()
        for row in new_fds:
            label = f"{row[1]}  [{row[4]}]  @{row[5]:.2f}%"
            fd_map[label] = (int(row[0]), int(row[3]), float(row[2]))
        fd_combo["values"] = list(fd_map.keys())
        progressive_selection(fd_combo, list(fd_map.keys()))

    def on_fd_focus_out(_event=None):
        try:
            if not win.winfo_exists():
                return
        except (tk.TclError, NameError):
            return
        typed = fd_combo.get().strip()
        if not typed:
            return
        if typed not in fd_map:
            response = show_colorful_yesno(
                win,
                "FD Not Found",
                f"'{typed}' was not found. Add a new Fixed Deposit " "now?",
            )
            if response:
                _add_fd(win)
                _refresh_fd_combo()
                fd_combo.focus_set()
            else:
                show_colorful_error(
                    win,
                    "Invalid Selection",
                    "Please select a valid Fixed Deposit from the list.",
                )
                flash_error(fd_combo)
                fd_combo.focus_set()

    fd_combo.bind("<FocusOut>", on_fd_focus_out, add="+")

    if fd_map:
        fd_combo.set(next(iter(fd_map)))

    fd_info_var = tk.StringVar(value="—")
    tk.Label(
        mst_erow,
        textvariable=fd_info_var,
        font=_F,
        bg=_C_MASTER,
        fg="#fdba74",
        width=34,
        anchor="w",
    ).pack(side="left", padx=(18, 0))

    # ── Band 2: Trans Date + Trans Type ──────────────────────────────────
    det_band, det_lrow, det_erow = _make_band(form_body, _C_DETAIL)
    det_band.pack(fill="x", pady=(0, 5))

    _band_label(det_lrow, "Trans Date", _C_DETAIL, _F)
    _band_label(det_lrow, "Transaction Type", _C_DETAIL, _F, padx=50)

    trans_dt = DateEntry(det_erow, date_pattern="dd-mm-yyyy", width=14, font=_F)
    trans_dt.pack(side="left", padx=(0, 8))
    apply_entry_theme(trans_dt)
    bind_tooltip(trans_dt, tooltip_var, "Date of this FD event.")
    bind_date_spin(trans_dt)

    trans_type_var = tk.StringVar(value="INTEREST_CREDIT")

    type_frame = tk.Frame(det_erow, bg=_C_DETAIL)
    type_frame.pack(side="left", padx=(18, 0))
    for ttype in _TRANS_TYPES:
        rb = tk.Radiobutton(
            type_frame,
            text=ttype.replace("_", " "),
            variable=trans_type_var,
            value=ttype,
            font=("Helvetica", 12),
            bg=_C_DETAIL,
            fg=_T["label_fg"],
            selectcolor="#3d1a00",
            activebackground=_C_DETAIL,
            activeforeground=_T["label_fg"],
        )
        rb.pack(side="left", padx=4)

    # ── Band 3: Amount fields ─────────────────────────────────────────────
    amt_band, amt_lrow, amt_erow = _make_band(form_body, _C_AMT)
    amt_band.pack(fill="x", pady=(0, 5))

    _band_label(amt_lrow, "FD Saving (\u20b9)", _C_AMT, _F)
    _band_label(amt_lrow, "FD Withdrawal (\u20b9)", _C_AMT, _F, padx=30)
    _band_label(amt_lrow, "FD Principal (\u20b9)", _C_AMT, _F, padx=30)
    _band_label(amt_lrow, "FD Interest (\u20b9)", _C_AMT, _F, padx=30)

    fd_saving_entry = tk.Entry(amt_erow, width=14, font=_FB)
    fd_saving_entry.pack(side="left", padx=(0, 8))
    fd_saving_entry.insert(0, "0.00")
    apply_entry_theme(fd_saving_entry)
    bind_tooltip(
        fd_saving_entry,
        tooltip_var,
        "Amount deposited / added to the FD (DEPOSIT). Enter 0 otherwise.",
    )

    fd_withdrawal_entry = tk.Entry(amt_erow, width=14, font=_FB)
    fd_withdrawal_entry.pack(side="left", padx=(18, 8))
    fd_withdrawal_entry.insert(0, "0.00")
    apply_entry_theme(fd_withdrawal_entry)
    bind_tooltip(
        fd_withdrawal_entry,
        tooltip_var,
        "Amount withdrawn (MATURITY / PREMATURE_CLOSURE). Enter 0 otherwise.",
    )

    fd_principal_entry = tk.Entry(amt_erow, width=14, font=_FB)
    fd_principal_entry.pack(side="left", padx=(18, 8))
    fd_principal_entry.insert(0, "0.00")
    apply_entry_theme(fd_principal_entry)
    bind_tooltip(
        fd_principal_entry,
        tooltip_var,
        "Principal component of this event's proceeds (for breakdowns).",
    )

    fd_int_entry = tk.Entry(amt_erow, width=14, font=_FB)
    fd_int_entry.pack(side="left", padx=(18, 0))
    fd_int_entry.insert(0, "0.00")
    apply_entry_theme(fd_int_entry)
    bind_tooltip(
        fd_int_entry,
        tooltip_var,
        "Interest component of this event (INTEREST_CREDIT / MATURITY).",
    )

    # ── Auto-logic: FD selection ──────────────────────────────────────────
    def _on_fd_selected(_event=None):
        label = fd_combo.get()
        if label not in fd_map:
            return
        fm_id, ac_id, principal = fd_map[label]
        _state["fd_master_id"] = fm_id
        _state["account_id"] = ac_id
        _state["principal"] = principal
        fd_info_var.set(f"Account ID = {ac_id}  |  Principal: \u20b9{principal:,.2f}")
        _on_type_change()  # Sync amounts if MATURITY or PREMATURE_CLOSURE is already selected

    fd_combo.bind("<<ComboboxSelected>>", _on_fd_selected)
    if fd_map:
        _on_fd_selected()

    # ── Auto-logic: trans type pre-fills amounts ──────────────────────────
    def _on_type_change(*_args):
        ttype = trans_type_var.get()
        # MATURITY: pre-fill withdrawal = principal
        if ttype == "MATURITY":
            p = _state.get("principal", 0.0)
            fd_withdrawal_entry.delete(0, "end")
            fd_withdrawal_entry.insert(0, f"{p:.2f}")
            fd_principal_entry.delete(0, "end")
            fd_principal_entry.insert(0, f"{p:.2f}")
            fd_saving_entry.delete(0, "end")
            fd_saving_entry.insert(0, "0.00")
            fd_int_entry.delete(0, "end")
            fd_int_entry.insert(0, "0.00")
        elif ttype == "DEPOSIT":
            fd_withdrawal_entry.delete(0, "end")
            fd_withdrawal_entry.insert(0, "0.00")
            fd_principal_entry.delete(0, "end")
            fd_principal_entry.insert(0, "0.00")
            fd_int_entry.delete(0, "end")
            fd_int_entry.insert(0, "0.00")
        elif ttype == "INTEREST_CREDIT":
            fd_saving_entry.delete(0, "end")
            fd_saving_entry.insert(0, "0.00")
            fd_withdrawal_entry.delete(0, "end")
            fd_withdrawal_entry.insert(0, "0.00")
            fd_principal_entry.delete(0, "end")
            fd_principal_entry.insert(0, "0.00")
        elif ttype == "PREMATURE_CLOSURE":
            fd_saving_entry.delete(0, "end")
            fd_saving_entry.insert(0, "0.00")
            fd_principal_entry.delete(0, "end")
            fd_principal_entry.insert(0, f"{_state.get('principal', 0.0):.2f}")

    trans_type_var.trace_add("write", _on_type_change)

    # ── Session count label ───────────────────────────────────────────────
    session_count_var = tk.StringVar(value="Session: 0 saved")
    tk.Label(
        win,
        textvariable=session_count_var,
        font=("Helvetica", 11, "italic"),
        bg=_T["main_bg"],
        fg="#fdba74",
    ).pack(anchor="e", padx=16)

    # ── Buttons row ───────────────────────────────────────────────────────
    btn_frame = tk.Frame(win, bg=_T["main_bg"])
    btn_frame.pack(pady=8)

    def _reset_form():
        import datetime

        trans_dt.set_date(datetime.date.today())
        trans_type_var.set("INTEREST_CREDIT")
        for entry in (
            fd_saving_entry,
            fd_withdrawal_entry,
            fd_principal_entry,
            fd_int_entry,
        ):
            entry.delete(0, "end")
            entry.insert(0, "0.00")
        trans_dt.focus_set()

    def _validate_and_save():
        # FD selected?
        fd_label = fd_combo.get()
        if not fd_label or fd_label not in fd_map:
            flash_error(fd_combo)
            show_colorful_error(
                win, "Validation Error", "Please select a Fixed Deposit."
            )
            return

        # Date
        try:
            fd_trans_dt = trans_dt.get_date().strftime("%Y-%m-%d")
        except Exception:  # noqa: BLE001
            flash_error(trans_dt)
            show_colorful_error(
                win, "Validation Error", "Please enter a valid transaction date."
            )
            return

        # Amounts
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

        fd_saving = _parse(fd_saving_entry, "FD Saving")
        if fd_saving is None:
            return
        fd_withdrawal = _parse(fd_withdrawal_entry, "FD Withdrawal")
        if fd_withdrawal is None:
            return
        fd_principal = _parse(fd_principal_entry, "FD Principal")
        if fd_principal is None:
            return
        fd_int = _parse(fd_int_entry, "FD Interest")
        if fd_int is None:
            return

        ttype = trans_type_var.get()

        # Type-specific validation
        if ttype == "DEPOSIT" and fd_saving <= 0:
            flash_error(fd_saving_entry)
            show_colorful_error(
                win,
                "Validation Error",
                "FD Saving must be > 0 for DEPOSIT " "transactions.",
            )
            return
        if ttype == "INTEREST_CREDIT" and fd_int <= 0:
            flash_error(fd_int_entry)
            show_colorful_error(
                win,
                "Validation Error",
                "FD Interest must be > 0 for INTEREST_CREDIT " "transactions.",
            )
            return
        if ttype in ("MATURITY", "PREMATURE_CLOSURE") and fd_withdrawal <= 0:
            flash_error(fd_withdrawal_entry)
            show_colorful_error(
                win,
                "Validation Error",
                f"FD Withdrawal must be > 0 for {ttype} " "transactions.",
            )
            return

        fm_id, ac_id, _ = fd_map[fd_label]

        data = {
            "fd_master_id": fm_id,
            "account_id": ac_id,
            "fd_trans_dt": fd_trans_dt,
            "fd_description": _DEFAULT_DESC.get(ttype, "FD Transaction"),
            "fd_saving": fd_saving,
            "fd_withdrawal": fd_withdrawal,
            "fd_principal": fd_principal,
            "fd_int": fd_int,
        }

        try:
            fd_trans_id = _db_add_fd_transaction(data)
        except Exception as exc:  # noqa: BLE001
            logger.error("add_fd_transaction failed: %s", exc)
            msg = f"Failed to save transaction:\n{exc}"
            show_colorful_error(win, "Database Error", msg)
            return

        session_records.append(
            {
                **data,
                "fd_trans_id": fd_trans_id,
                "fd_label": fd_label,
                "trans_type": ttype,
            }
        )
        session_count_var.set(f"Session: {len(session_records)} saved")

        show_colorful_info(win, "Saved", f"FD Transaction saved (ID {fd_trans_id}).")
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
    def _focus_next(w):
        def _h(_e=None):
            w.focus_set()
            return "break"

        return _h

    trans_dt.bind("<Return>", _focus_next(fd_saving_entry))
    fd_saving_entry.bind("<Return>", _focus_next(fd_withdrawal_entry))
    fd_withdrawal_entry.bind("<Return>", _focus_next(fd_principal_entry))
    fd_principal_entry.bind("<Return>", _focus_next(fd_int_entry))
    fd_int_entry.bind("<Return>", lambda _e: _validate_and_save())

    # ── Modal wait ────────────────────────────────────────────────────────
    if fd_map:
        trans_dt.focus_set()
    else:
        fd_combo.focus_set()

    parent.wait_window(win)
