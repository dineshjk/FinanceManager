# -*- coding: utf-8 -*-
# BankMan/fd_master_add.py

"""
Module for adding new Fixed Deposit master records (fd_master table).

Structural pattern from cc_master_add.py / ppf_master_add.py:
  - Coloured band frames, each with a label_row / entry_row
  - apply_entry_theme / bind_tooltip / setup_footer_tooltip from Shared.gui_utils
  - F1 = Help, F2 = Session viewer, Escape = close without saving
  - Yellow-on-black entry theme via centrally defined apply_entry_theme()
  - Distinct dark navy/indigo window theme (FD_MASTER_ADD_UI_THEME)
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
    FD_MASTER_ADD_UI_THEME,
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
    db_add_fd_master as _db_add_fd_master,
)
from Shared.globals import logger
from Shared.gui_progressive import progressive_selection
from .accounts_add import add_account_main as _add_account

# ---------------------------------------------------------------------------
# Theme alias
# ---------------------------------------------------------------------------
_T = FD_MASTER_ADD_UI_THEME

# ---------------------------------------------------------------------------
# Band / label helpers
# ---------------------------------------------------------------------------


def _make_band(container, bg, relief="ridge", padx=10, pady=6):
    """Create a coloured section band with stacked label_row / entry_row."""  # Line 54
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
    """Launch the Help sub-window for Add FD Master."""
    win.unbind("<Escape>")

    help_win = tk.Toplevel(win)
    try:
        help_win.transient(win)
    except (tk.TclError, AttributeError) as exc:
        logger.debug("help_win.transient failed: %s", exc)
    help_win.title("Help — Add FD Master")
    help_win.configure(bg=_T["header_bg"])
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
        text="Add FD Master  —  Help",
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
        height=28,
        insertbackground=_T["header_fg"],
    )
    text.pack(fill="both", expand=True)

    help_lines = [
        "\u2022 This form registers a new Fixed Deposit (fd_master) record.",
        "",
        "Fields:",
        "  Linked Account     \u2014 The savings/current account from which this FD",
        "                       was funded and to which maturity proceeds",
        "                       are credited.",
        "  FD Number          \u2014 Bank-assigned FD reference or receipt number",
        "                       (e.g. 'FD/2024/00123'). Alphanumeric.",
        "  Principal (\u20b9)      \u2014 Amount originally deposited to open this FD.",
        "  Interest Rate (%)  \u2014 Annual interest rate, e.g. enter 7.25 for",
        "                       7.25% per annum.",
        "  Open Date          \u2014 Date on which the FD was opened.",
        "  Maturity Date      \u2014 Date on which the FD matures and proceeds",
        "                       are credited back to the linked account.",
        "  Is Active          \u2014 Tick = FD is currently active.",
        "                       Untick only for matured or prematurely",
        "                       closed FDs.",
        "",
        "Tips:",
        "  \u2022 One fd_master row per Fixed Deposit product.",
        "  \u2022 Periodic interest and maturity events are recorded in",
        "    fd_transactions.",
        "  \u2022 Maturity date must be later than the open date.",
        "",
        "Hotkeys:",
        "  F1  : This help screen",
        "  F2  : Session viewer (FDs added in this session)",
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
    """Show FD master records added in this session."""
    if not session_entries:
        try:
            show_colorful_info(
                win,
                "No Entries",
                "No FD master records have been added this session.",
            )
        except tk.TclError:
            pass
        return

    win.unbind("<Escape>")
    idx = {"i": 0}

    viewer = tk.Toplevel(win)
    viewer.title("Session — FD Masters Added")
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
        text="FD Masters Added This Session",
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
        height=12,
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
            ("FD Number", rec.get("fd_number")),
            ("Linked Account", rec.get("account_label")),
            ("Principal (\u20b9)", f"{rec.get('principal_amount', 0.0):,.2f}"),
            ("Interest Rate (%)", f"{rec.get('interest_rate', 0.0):.4f}"),
            ("Open Date", rec.get("open_dt")),
            ("Maturity Date", rec.get("maturity_dt")),
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


def add_fd_master_main(
    parent: Union[tk.Toplevel, tk.Tk],
    calling_button: tk.Widget | None = None,
) -> None:
    """Launch the Add FD Master dialog."""

    # ── Lookup data ───────────────────────────────────────────────────────
    accounts = get_all_accounts()
    # Display: "BankName : [AC_Number]"  →  ac_id
    account_map = {f"{a[1]} : [{a[3]}]": a[0] for a in accounts}

    # ── Window setup ──────────────────────────────────────────────────────
    disable_parent(parent, calling_button=calling_button)
    session_records: list = []

    win = tk.Toplevel(parent)
    win.title("\U0001f3e6 Add FD Master \U0001f3e6")
    win.geometry("960x520")
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
        text="\U0001f3e6  Add FD Master  \U0001f3e6",
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
            fg="#93c5fd",  # soft blue hint text
        ).pack(side="left", padx=12)

    # ── Form body ─────────────────────────────────────────────────────────
    _F = ("Helvetica", 14)
    _FB = ("Helvetica", 14, "bold")

    _C_ACCT = _T["band_account"]
    _C_FD = _T["band_fd"]
    _C_DATES = _T["band_dates"]

    form_body = tk.Frame(win, bg=_T["main_bg"])
    form_body.pack(fill="x", padx=12, pady=6)

    # ── Band 1: Linked Account + FD Number ───────────────────────────────
    acct_band, acct_lrow, acct_erow = _make_band(form_body, _C_ACCT)
    acct_band.pack(fill="x", pady=(0, 5))

    _band_label(acct_lrow, "Linked Bank Account", _C_ACCT, _F)
    _band_label(acct_lrow, "FD Number", _C_ACCT, _F, padx=110)

    account_combo = ttk.Combobox(
        acct_erow,
        width=36,
        values=list(account_map.keys()),
        font=_F,
    )
    account_combo.pack(side="left", padx=(0, 8))
    apply_entry_theme(account_combo)
    progressive_selection(account_combo, list(account_map.keys()))
    bind_tooltip(
        account_combo,
        tooltip_var,
        "Savings/current account this FD is funded from.",
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

    fd_number_entry = tk.Entry(acct_erow, width=22, font=_FB)
    fd_number_entry.pack(side="left", padx=(18, 0))
    apply_entry_theme(fd_number_entry)
    bind_tooltip(
        fd_number_entry,
        tooltip_var,
        "Bank-assigned FD reference or receipt number. If the UNIQUE "
        "constraint clashes, prefix with a bank code (e.g., SBI-FD1).",
    )

    # ── Band 2: Principal + Interest Rate + Is Active ─────────────────────
    fd_band, fd_lrow, fd_erow = _make_band(form_body, _C_FD)
    fd_band.pack(fill="x", pady=(0, 5))

    _band_label(fd_lrow, "Principal Amount (\u20b9)", _C_FD, _F)
    _band_label(fd_lrow, "Interest Rate (% p.a.)", _C_FD, _F, padx=60)
    _band_label(fd_lrow, "Is Active", _C_FD, _F, padx=60)

    principal_entry = tk.Entry(fd_erow, width=18, font=_FB)
    principal_entry.pack(side="left", padx=(0, 8))
    apply_entry_theme(principal_entry)
    bind_tooltip(
        principal_entry,
        tooltip_var,
        "Amount originally deposited to open this FD (in \u20b9).",
    )

    interest_entry = tk.Entry(fd_erow, width=12, font=_FB)
    interest_entry.pack(side="left", padx=(18, 8))
    apply_entry_theme(interest_entry)
    bind_tooltip(
        interest_entry,
        tooltip_var,
        "Annual interest rate, e.g. enter 7.25 for 7.25% p.a.",
    )

    is_active_var = tk.BooleanVar(value=True)
    is_active_cb = tk.Checkbutton(
        fd_erow,
        variable=is_active_var,
        text="Active",
        font=_F,
        bg=_C_FD,
        fg=_T["label_fg"],
        selectcolor="#001a50",
        activebackground=_C_FD,
        activeforeground=_T["label_fg"],
    )
    is_active_cb.pack(side="left", padx=(18, 0))
    bind_tooltip(
        is_active_cb,
        tooltip_var,
        "Tick = FD is currently active. Untick for matured or closed " "FDs.",
    )

    # ── Band 3: Open Date + Maturity Date ────────────────────────────────
    dates_band, dates_lrow, dates_erow = _make_band(form_body, _C_DATES)
    dates_band.pack(fill="x", pady=(0, 5))

    _band_label(dates_lrow, "Open Date", _C_DATES, _F)
    _band_label(dates_lrow, "Maturity Date", _C_DATES, _F, padx=80)

    open_dt = DateEntry(dates_erow, date_pattern="dd-mm-yyyy", width=14, font=_F)
    open_dt.pack(side="left", padx=(0, 8))
    apply_entry_theme(open_dt)
    bind_tooltip(open_dt, tooltip_var, "Date the FD was opened.")

    maturity_dt = DateEntry(dates_erow, date_pattern="dd-mm-yyyy", width=14, font=_F)
    maturity_dt.pack(side="left", padx=(18, 0))
    apply_entry_theme(maturity_dt)
    bind_tooltip(maturity_dt, tooltip_var, "Date the FD matures.")

    bind_date_spin(open_dt)
    bind_date_spin(maturity_dt)

    # ── Session count label ───────────────────────────────────────────────
    session_count_var = tk.StringVar(value="Session: 0 saved")
    tk.Label(
        win,
        textvariable=session_count_var,
        font=("Helvetica", 11, "italic"),
        bg=_T["main_bg"],
        fg="#93c5fd",
    ).pack(anchor="e", padx=16)

    # ── Buttons row ───────────────────────────────────────────────────────
    btn_frame = tk.Frame(win, bg=_T["main_bg"])
    btn_frame.pack(pady=8)

    def _reset_form():
        fd_number_entry.delete(0, "end")
        principal_entry.delete(0, "end")
        interest_entry.delete(0, "end")
        is_active_var.set(True)
        import datetime

        open_dt.set_date(datetime.date.today())
        maturity_dt.set_date(datetime.date.today())
        fd_number_entry.focus_set()

    def _validate_and_save():
        # Account
        acct_label = account_combo.get()
        if not acct_label or acct_label not in account_map:
            flash_error(account_combo)
            show_colorful_error(
                win, "Validation Error", "Please select a linked bank account."
            )
            return

        # FD Number
        fd_num = fd_number_entry.get().strip()
        if not fd_num:
            flash_error(fd_number_entry)
            show_colorful_error(win, "Validation Error", "FD Number cannot be blank.")
            return

        # Principal
        try:
            principal_str = principal_entry.get().strip().replace(",", "")
            principal = float(principal_str)
            if principal <= 0:
                raise ValueError
        except ValueError:
            flash_error(principal_entry)
            show_colorful_error(
                win,
                "Validation Error",
                "Principal amount must be a positive number.",
            )
            return

        # Interest Rate
        try:
            rate_str = interest_entry.get().strip().replace(",", "")
            interest_rate = float(rate_str)
            if interest_rate <= 0:
                raise ValueError
        except ValueError:
            flash_error(interest_entry)
            show_colorful_error(
                win,
                "Validation Error",
                "Interest rate must be a positive number (e.g. " "7.25).",
            )
            return

        # Dates
        try:
            open_date = open_dt.get_date()
            maturity_date = maturity_dt.get_date()
        except Exception:  # noqa: BLE001
            show_colorful_error(
                win, "Validation Error", "Please enter valid open and maturity dates."
            )
            return

        if maturity_date <= open_date:
            flash_error(maturity_dt)
            show_colorful_error(
                win,
                "Validation Error",
                "Maturity date must be later than the open date.",
            )
            return

        data = {
            "account_id": account_map[acct_label],
            "fd_number": fd_num,
            "principal_amount": principal,
            "interest_rate": interest_rate,
            "open_dt": open_date.strftime("%Y-%m-%d"),
            "maturity_dt": maturity_date.strftime("%Y-%m-%d"),
            "is_active": 1 if is_active_var.get() else 0,
        }

        try:
            fd_master_id = _db_add_fd_master(data)
        except Exception as exc:  # noqa: BLE001
            logger.error("add_fd_master failed: %s", exc)
            msg = f"Failed to save FD master:\n{exc}"
            show_colorful_error(win, "Database Error", msg)
            return

        session_records.append(
            {
                **data,
                "fd_master_id": fd_master_id,
                "account_label": acct_label,
            }
        )
        session_count_var.set(f"Session: {len(session_records)} saved")

        show_colorful_info(win, "Saved", f"FD Master saved (ID {fd_master_id}).")
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

    fd_number_entry.bind("<Return>", _focus_next(principal_entry))
    principal_entry.bind("<Return>", _focus_next(interest_entry))
    interest_entry.bind("<Return>", _focus_next(open_dt))
    open_dt.bind("<Return>", _focus_next(maturity_dt))
    maturity_dt.bind("<Return>", lambda _e: _validate_and_save())

    # ── Modal wait ────────────────────────────────────────────────────────
    fd_number_entry.focus_set()
    parent.wait_window(win)
