# -*- coding: utf-8 -*-
# C:\Data\Personal\Finance_and_Investment\finprog\FinanceManager\BankMan\ppf_master_add.py

"""
Module for adding new PPF (Public Provident Fund) master accounts.

Follows the same structural pattern as bank_transactions_add.py:
  - Coloured band frames, each with a label_row / entry_row
  - apply_entry_theme / bind_tooltip / setup_footer_tooltip from Shared.gui_utils
  - F1 = Help, F2 = Session viewer, Escape = close without saving
  - Yellow-on-black entry theme via centrally defined apply_entry_theme()
  - Distinct midnight/gold window theme (PPF_MASTER_ADD_UI_THEME)
"""

from dateutil.relativedelta import relativedelta
from typing import Union
import tkinter as tk
from tkinter import ttk
from tkcalendar import DateEntry

from Shared.gui_utils import (
    apply_entry_theme,
    bind_tooltip,
    setup_footer_tooltip,
    flash_error,
    PPF_MASTER_ADD_UI_THEME,
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
    get_all_accounts,
    db_add_ppf_master as _db_add_ppf_master,
)
from Shared.globals import logger
from Shared.gui_progressive import progressive_selection
from .accounts_add import add_account_main as _add_account

# ---------------------------------------------------------------------------
# Theme aliases (shorthand)
# ---------------------------------------------------------------------------
_T = PPF_MASTER_ADD_UI_THEME

# ---------------------------------------------------------------------------
# Band / label helpers (same pattern as bank_transactions_add.py)
# ---------------------------------------------------------------------------


def _make_band(container, bg, relief="ridge", padx=10, pady=6):
    """Create a coloured section band with stacked label_row / entry_row.

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
        fg=_T["label_fg"],  # gold on dark band
        anchor="w",
    ).pack(side="left", padx=(padx, 12))


# ---------------------------------------------------------------------------
# Help window (F1)
# ---------------------------------------------------------------------------


def _show_help(win: tk.Toplevel, on_escape) -> None:
    """Launch the Help sub-window for Add PPF Master."""
    win.unbind("<Escape>")

    help_win = tk.Toplevel(win)
    try:
        help_win.transient(win)
    except (tk.TclError, AttributeError) as exc:
        logger.debug("help_win.transient failed: %s", exc)
    help_win.title("Help — Add PPF Master Account")
    help_win.configure(bg="#013220")
    help_win.geometry("680x680")
    help_win.resizable(False, False)
    help_win.grab_set()
    push_window(help_win, win)
    try:
        help_win.focus_set()
    except tk.TclError:
        pass

    tk.Label(
        help_win,
        text="Add PPF Master Account  —  Help",
        font=("Helvetica", 16, "bold"),
        bg="#013220",
        fg="#FFD700",
        pady=8,
    ).pack(fill="x")

    body = tk.Frame(help_win, bg="#0D1117", padx=12, pady=12)
    body.pack(fill="both", expand=True)

    text = tk.Text(
        body,
        wrap="word",
        bg="#0D1117",
        fg="#FFD700",
        bd=0,
        padx=6,
        pady=6,
        font=("Helvetica", 11),
        height=28,
        insertbackground="#FFD700",
    )
    text.pack(fill="both", expand=True)

    help_lines = [
        "\u2022 This form registers a new PPF (Public Provident Fund) account.",
        "",
        "Fields:",
        "  Account         \u2014 The linked bank / post-office savings account",
        "                    through which PPF deposits are routed.",
        "  PPF Account No  \u2014 The PPF account number issued by the bank or",
        "                    post office (leading zeros are preserved).",
        "  Holder Name     \u2014 Full name of the PPF account holder.",
        "                    May differ from the primary account holder",
        "                    (e.g. for minor / HUF PPF accounts).",
        "  Open Date       \u2014 The date the PPF account was opened.",
        "  Maturity Date   \u2014 Automatically set to Open Date + 15 years.",
        "                    You may adjust it if the account has been",
        "                    extended in 5-year blocks.",
        "  Is Active       \u2014 Tick to mark the account as active (default).",
        "                    Untick only for closed / fully withdrawn accounts.",
        "",
        "PPF Rules (for reference):",
        "  \u2022 Lock-in period: 15 years from opening.",
        "  \u2022 Extension blocks: 5 years each, unlimited times.",
        "  \u2022 Minimum deposit: \u20b9500 per financial year.",
        "  \u2022 Maximum deposit: \u20b91,50,000 per financial year.",
        "  \u2022 Interest is tax-free under EEE (Exempt-Exempt-Exempt) status.",
        "",
        "Hotkeys:",
        "  F1  : This help screen",
        "  F2  : Session viewer (PPF accounts added in this session)",
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
    """Show PPF accounts added in this session."""
    if not session_entries:
        try:
            show_colorful_info(
                win,
                "No Entries",
                "No PPF master accounts have been added in this session yet.",
            )
        except tk.TclError:
            pass
        return

    win.unbind("<Escape>")

    idx = {"i": 0}

    viewer = tk.Toplevel(win)
    viewer.title("Session — PPF Accounts Added")
    viewer.transient(win)
    viewer.grab_set()
    viewer.resizable(False, False)
    viewer.geometry("580x380")
    viewer.configure(bg="#013220")
    push_window(viewer, win)
    try:
        viewer.focus_set()
    except tk.TclError:
        pass

    tk.Label(
        viewer,
        text="PPF Accounts Added This Session",
        font=("Helvetica", 14, "bold"),
        bg="#013220",
        fg="#FFD700",
        pady=6,
    ).pack(fill="x")

    content = tk.Frame(viewer, bg="#013220")
    content.pack(fill="both", expand=True, padx=10, pady=6)

    left_btn = tk.Button(content, text="\u25c4", width=3, bg="#00704A", fg="#FFD700")
    left_btn.pack(side="left", padx=(6, 4), pady=6)
    right_btn = tk.Button(content, text="\u25ba", width=3, bg="#00704A", fg="#FFD700")
    right_btn.pack(side="right", padx=(4, 6), pady=6)

    info_text = tk.Text(
        content,
        wrap="word",
        height=14,
        bg="#0D1117",
        fg="#FFD700",
        bd=0,
        relief="flat",
        font=("Helvetica", 11),
        insertbackground="#FFD700",
    )
    info_text.pack(fill="both", expand=True, padx=6, pady=4)
    info_text.tag_configure(
        "label", font=("Helvetica", 11, "bold"), foreground="#FFD700"
    )
    info_text.tag_configure("value", font=("Helvetica", 11), foreground="#e2e8f0")
    info_text.config(state="disabled")

    status_label = tk.Label(
        content, text="", font=("Helvetica", 10, "bold"), bg="#013220", fg="#FFD700"
    )
    status_label.pack(side="bottom", pady=(0, 4))

    def _update_view():
        i = idx["i"]
        rec = session_entries[i]
        info_text.config(state="normal")
        info_text.delete("1.0", "end")
        fields = [
            ("PPF Account No", rec.get("ppf_account_number")),
            ("Holder Name", rec.get("holder_name")),
            ("Linked Account", rec.get("account_label")),
            ("Open Date", rec.get("open_dt")),
            ("Maturity Date", rec.get("maturity_dt")),
            ("Is Active", "Yes" if rec.get("is_active") else "No"),
        ]
        for label, val in fields:
            info_text.insert("end", f"{label}: ", "label")
            info_text.insert("end", f"{val or '\u2014'}\n", "value")
        info_text.config(state="disabled")

        left_btn.config(state="disabled" if i == 0 else "normal")
        if i >= len(session_entries) - 1:
            right_btn.config(state="disabled")
            status_label.config(text="Last Entry", fg="#ef4444")
        else:
            right_btn.config(state="normal")
            status_label.config(text=f"Entry {i + 1} of {len(session_entries)}")

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


def add_ppf_master_main(
    parent: Union[tk.Toplevel, tk.Tk],
    calling_button: tk.Widget | None = None,
) -> None:
    """Launch the Add PPF Master Account dialog."""

    # ── Lookup data ───────────────────────────────────────────────────────
    accounts = get_all_accounts()
    # Display format: "BankName : [AC_Number]"
    account_map = {f"{a[1]} : [{a[3]}]": a[0] for a in accounts}

    # ── Window setup ──────────────────────────────────────────────────────
    disable_parent(parent, calling_button=calling_button)

    session_records: list = []  # records added this session (for F2 viewer)

    win = tk.Toplevel(parent)
    win.title("\U0001f4b0 Add PPF Master Account \U0001f4b0")
    win.geometry("900x540")
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

    # ── F1 / F2 bindings ─────────────────────────────────────────────────
    win.bind("<F1>", lambda e: _show_help(win, on_escape))
    win.bind("<F2>", lambda e: _show_session_viewer(win, session_records, on_escape))
    win.bind("<Escape>", on_escape)
    win.protocol("WM_DELETE_WINDOW", on_escape)

    # ── Header ────────────────────────────────────────────────────────────
    header_frame = tk.Frame(win, bg=_T["header_bg"], relief="raised", bd=3)
    header_frame.pack(fill="x", padx=5, pady=0)

    tk.Label(
        header_frame,
        text="\U0001f4b0  Add PPF Master Account  \U0001f4b0",
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
    for hint in ("F1: Help", "F2: Session Viewer", "Esc: Close"):
        tk.Label(
            hint_frame,
            text=hint,
            font=("Helvetica", 10, "italic"),
            bg=_T["main_bg"],
            fg="#4ade80",  # soft green hint text
        ).pack(side="left", padx=12)

    # ── Form body ─────────────────────────────────────────────────────────
    _F = ("Helvetica", 14)  # field font
    _FB = ("Helvetica", 14, "bold")  # bold variant

    _C_ACCT = _T["band_account"]  # Band 1: Linked Account + PPF Account No
    _C_HOLDER = _T["band_holder"]  # Band 2: Holder Name + Is Active
    _C_DATES = _T["band_dates"]  # Band 3: Open Date + Maturity Date

    form_body = tk.Frame(win, bg=_T["main_bg"])
    form_body.pack(fill="x", padx=12, pady=6)

    # ── Band 1: Linked Account + PPF Account Number ───────────────────────
    acct_band, acct_lrow, acct_erow = _make_band(form_body, _C_ACCT)
    acct_band.pack(fill="x", pady=(0, 5))

    _band_label(acct_lrow, "Linked Bank Account", _C_ACCT, _F)
    _band_label(acct_lrow, "PPF Account Number", _C_ACCT, _F, padx=100)

    account_combo = ttk.Combobox(
        acct_erow,
        width=28,
        values=list(account_map.keys()),
        font=_F,
    )
    account_combo.pack(side="left", padx=(0, 8))
    apply_entry_theme(account_combo)
    progressive_selection(account_combo, list(account_map.keys()))
    bind_tooltip(
        account_combo,
        tooltip_var,
        "The linked savings account through which PPF deposits are routed.",
    )

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

    ppf_acct_no_entry = tk.Entry(acct_erow, width=20, font=_FB)
    ppf_acct_no_entry.pack(side="left", padx=(20, 0))
    apply_entry_theme(ppf_acct_no_entry)
    bind_tooltip(
        ppf_acct_no_entry,
        tooltip_var,
        "PPF account number issued by the bank / post office (leading zeros "
        "are preserved).",
    )

    # ── Band 2: Holder Name + Is Active ──────────────────────────────────
    holder_band, holder_lrow, holder_erow = _make_band(form_body, _C_HOLDER)
    holder_band.pack(fill="x", pady=(0, 5))

    _band_label(holder_lrow, "Holder Name", _C_HOLDER, _F)
    _band_label(holder_lrow, "Is Active", _C_HOLDER, _F, padx=230)

    holder_name_entry = tk.Entry(holder_erow, width=34, font=_FB)
    holder_name_entry.pack(side="left", padx=(0, 8))
    apply_entry_theme(holder_name_entry)
    bind_tooltip(
        holder_name_entry,
        tooltip_var,
        "Full name of the PPF account holder (may differ for minor or HUF PPF "
        "accounts).",
    )

    is_active_var = tk.BooleanVar(value=True)
    is_active_chk = tk.Checkbutton(
        holder_erow,
        variable=is_active_var,
        text="Active",
        font=_F,
        bg=_C_HOLDER,
        fg=_T["label_fg"],
        selectcolor="#013220",
        activebackground=_C_HOLDER,
        activeforeground="#FFD700",
        cursor="hand2",
    )
    is_active_chk.pack(side="left", padx=(30, 0))
    bind_tooltip(
        is_active_chk,
        tooltip_var,
        "Tick = account is still active. Untick only for fully closed " "accounts.",
    )

    # ── Band 3: Open Date + Maturity Date ────────────────────────────────
    dates_band, dates_lrow, dates_erow = _make_band(form_body, _C_DATES)
    dates_band.pack(fill="x", pady=(0, 5))

    _band_label(dates_lrow, "Open Date", _C_DATES, _F)
    _band_label(dates_lrow, "Maturity Date", _C_DATES, _F, padx=160)
    _band_label(
        dates_lrow,
        "(auto: Open + 15 yrs — adjust for extensions)",
        _C_DATES,
        ("Helvetica", 10, "italic"),
        padx=20,
    )

    open_dt = DateEntry(dates_erow, date_pattern="dd-mm-yyyy", width=14, font=_F)
    open_dt.pack(side="left", padx=(0, 30))
    apply_entry_theme(open_dt)
    bind_tooltip(
        open_dt,
        tooltip_var,
        "Date the PPF account was opened (calendar picker).",
    )

    maturity_dt = DateEntry(dates_erow, date_pattern="dd-mm-yyyy", width=14, font=_F)
    maturity_dt.pack(side="left")
    apply_entry_theme(maturity_dt)
    bind_tooltip(
        maturity_dt,
        tooltip_var,
        "Original maturity date = Open + 15 years. Adjust if the account has "
        "been extended in 5-year blocks.",
    )

    # ── Auto-fill maturity date when open date changes ────────────────────
    def _sync_maturity_dt(*_):
        try:
            od = open_dt.get_date()
            md = od + relativedelta(years=15)
            maturity_dt.set_date(md)
        except Exception:  # noqa: BLE001
            pass

    open_dt.bind("<<DateEntrySelected>>", _sync_maturity_dt)
    open_dt.bind("<FocusOut>", _sync_maturity_dt)
    win.after(50, _sync_maturity_dt)  # initialise on open

    bind_date_spin(open_dt, callback=_sync_maturity_dt)
    bind_date_spin(maturity_dt)

    # ── Tab order: Return advances to next field ───────────────────────────
    ppf_acct_no_entry.bind("<Return>", lambda e: holder_name_entry.focus_set())
    holder_name_entry.bind("<Return>", lambda e: open_dt.focus_set())
    open_dt.bind("<Return>", lambda e: maturity_dt.focus_set())

    # ── Action buttons ────────────────────────────────────────────────────
    btn_frame = tk.Frame(win, bg=_T["main_bg"])
    btn_frame.pack(fill="x", padx=12, pady=(8, 4))

    _SUB_BG = _T["button_bg"]  # forest green
    _SUB_ACT = "#005a38"  # darker green on hover
    _CAN_BG = "#7f1d1d"  # dark red
    _CAN_ACT = "#450a0a"  # deeper dark red

    def _make_button(parent_frame, txt, cmd, bg_col, act_bg):
        btn = tk.Button(
            parent_frame,
            text=txt,
            width=18,
            font=("Helvetica", 12, "bold"),
            bg=bg_col,
            fg=_T.get("button_fg", "white"),
            activeforeground=_T.get("button_fg", "white"),
            relief="raised",
            bd=3,
            cursor="hand2",
            command=cmd,
        )
        btn.pack(side="left", padx=6)
        apply_button_animations(btn, bg_col, act_bg)
        return btn

    # ── Reset form helper ─────────────────────────────────────────────────
    def _reset_form():
        ppf_acct_no_entry.delete(0, tk.END)
        holder_name_entry.delete(0, tk.END)
        is_active_var.set(True)
        if account_map:
            account_combo.set(next(iter(account_map)))
        win.after(50, _sync_maturity_dt)
        ppf_acct_no_entry.focus_set()

    # ── Submit / validation ───────────────────────────────────────────────
    def on_submit(_event=None):
        account_label = account_combo.get().strip()
        if not account_label or account_label not in account_map:
            show_colorful_error(
                win, "Validation Error", "Please select a valid linked account."
            )
            flash_error(account_combo)
            account_combo.focus_set()
            return

        ppf_number = ppf_acct_no_entry.get().strip()
        if not ppf_number:
            show_colorful_error(
                win, "Validation Error", "PPF Account Number is required."
            )
            flash_error(ppf_acct_no_entry)
            ppf_acct_no_entry.focus_set()
            return

        holder = holder_name_entry.get().strip()
        if not holder:
            show_colorful_error(win, "Validation Error", "Holder Name is required.")
            flash_error(holder_name_entry)
            holder_name_entry.focus_set()
            return

        try:
            open_date_str = open_dt.get_date().strftime("%Y-%m-%d")
        except Exception:  # noqa: BLE001
            show_colorful_error(
                win, "Validation Error", "Please enter a valid Open Date."
            )
            open_dt.focus_set()
            return

        try:
            maturity_date_str = maturity_dt.get_date().strftime("%Y-%m-%d")
        except Exception:  # noqa: BLE001
            show_colorful_error(
                win, "Validation Error", "Please enter a valid Maturity Date."
            )
            maturity_dt.focus_set()
            return

        if maturity_date_str <= open_date_str:
            show_colorful_error(
                win,
                "Validation Error",
                "Maturity Date must be after Open Date.",
            )
            flash_error(maturity_dt)
            maturity_dt.focus_set()
            return

        is_active = 1 if is_active_var.get() else 0

        try:
            new_id = _db_add_ppf_master(
                {
                    "account_id": account_map[account_label],
                    "ppf_account_number": ppf_number,
                    "holder_name": holder,
                    "open_dt": open_date_str,
                    "maturity_dt": maturity_date_str,
                    "is_active": is_active,
                }
            )
        except Exception as exc:  # noqa: BLE001
            msg = f"Failed to save PPF account: {exc}"
            show_colorful_error(win, "Database Error", msg)
            return

        session_records.append(
            {
                "ppf_master_id": new_id,
                "ppf_account_number": ppf_number,
                "holder_name": holder,
                "account_label": account_label,
                "open_dt": open_date_str,
                "maturity_dt": maturity_date_str,
                "is_active": is_active,
            }
        )
        show_colorful_info(
            win,
            "Success",
            f"PPF account \u2018{ppf_number}\u2019 saved successfully (ID: "
            f"{new_id}).",
        )
        _reset_form()

    # ── Session summary label ─────────────────────────────────────────────
    session_var = tk.StringVar(value="Session: 0 account(s) added")

    def _update_session_label():
        n = len(session_records)
        msg = f"Session: {n} account{'s' if n != 1 else ''} added  (F2 to review)"
        session_var.set(msg)

    def _patched_submit(e=None):
        prev = len(session_records)
        on_submit(e)
        if len(session_records) > prev:
            _update_session_label()

    maturity_dt.bind("<Return>", _patched_submit)

    submit_btn = _make_button(
        btn_frame,
        "✅  Save PPF Account",
        _patched_submit,
        _T.get("submit_bg", _T.get("button_bg", "#22c55e")),
        _T.get("submit_hover_bg", "#2563eb"),
    )
    cancel_btn = _make_button(
        btn_frame,
        "❌  Close",
        on_escape,
        _T.get("cancel_bg", "#ef4444"),
        _T.get("cancel_hover_bg", "#991b1b"),
    )

    # Also bind Return on the submit button itself
    submit_btn.bind("<Return>", _patched_submit)
    cancel_btn.bind("<Return>", on_escape)

    submit_btn.bind("<Return>", _patched_submit)

    tk.Label(
        btn_frame,
        textvariable=session_var,
        font=("Helvetica", 10, "italic"),
        bg=_T["main_bg"],
        fg="#4ade80",
    ).pack(side="left", padx=20)

    # ── Initial focus ─────────────────────────────────────────────────────
    win.after(100, ppf_acct_no_entry.focus_set)
