# -*- coding: utf-8 -*-
# BankMan/fd_master_edit.py

"""
Module for editing an existing Fixed Deposit master record.
"""

from typing import Union
import tkinter as tk
from tkinter import ttk
from tkcalendar import DateEntry
from datetime import datetime
import sqlite3

from Shared.gui_utils import (
    apply_entry_theme,
    bind_tooltip,
    setup_footer_tooltip,
    flash_error,
    FD_MASTER_ADD_UI_THEME as _T,
    apply_button_animations,
    bind_date_spin,
)
from Shared.dialog_utils import (
    show_colorful_info,
    show_colorful_error,
)
from Shared.modal_utils import disable_parent
from Shared.window_manager import push_window, safe_close_modal
from Shared.help_utils import show_standard_help
from .bank_db_utils import (
    get_all_accounts,
)
from Shared.globals import logger, get_db_connection, BANK_DB_PATH


def _make_band(container, bg, relief="ridge", padx=10, pady=6):
    band = tk.Frame(container, bg=bg, relief=relief, bd=2, padx=padx, pady=pady)
    label_row = tk.Frame(band, bg=bg)
    label_row.pack(fill="x", pady=(0, 2))
    entry_row = tk.Frame(band, bg=bg)
    entry_row.pack(fill="x", pady=(0, 2))
    return band, label_row, entry_row


def _band_label(parent, text, bg, font=("Helvetica", 14), padx=0):
    tk.Label(
        parent, text=text, font=font, bg=bg, fg=_T.get("label_fg", "white"), anchor="w"
    ).pack(side="left", padx=(padx, 12))


def edit_fd_master(parent: Union[tk.Toplevel, tk.Tk], fd_master_id: int):
    """Launch the Edit FD Master dialog."""
    # Lookup data
    accounts = get_all_accounts()
    account_map = {f"{a[1]} : [{a[3]}]": a[0] for a in accounts}
    account_id_to_label = {v: k for k, v in account_map.items()}

    # Modal setup
    disable_parent(parent)

    win = tk.Toplevel(parent)
    win.title("✏️ Edit FD Master")
    win.geometry("960x450")
    win.resizable(False, False)
    win.configure(bg=_T["main_bg"])
    win.transient(parent)
    win.grab_set()
    win.focus_set()
    try:
        push_window(win, parent)
    except (RuntimeError, tk.TclError):
        pass

    tooltip_var = setup_footer_tooltip(
        win, bg_color=_T["header_bg"], fg_color=_T.get("header_fg", "white")
    )

    def cleanup_and_close(_event=None):
        return safe_close_modal(win, parent)

    def on_escape(_event=None):
        return cleanup_and_close()

    win.bind("<Escape>", on_escape)
    win.protocol("WM_DELETE_WINDOW", on_escape)

    header_frame = tk.Frame(win, bg=_T["header_bg"], relief="raised", bd=3)
    header_frame.pack(fill="x", padx=5, pady=0)
    tk.Label(
        header_frame,
        text="✏️  Edit FD Master  ✏️",
        font=("Helvetica", 18, "bold"),
        bg=_T["header_bg"],
        fg=_T.get("header_fg", "white"),
        relief="ridge",
        bd=2,
        pady=8,
    ).pack(fill="x")
    
    # ── Form body ─────────────────────────────────────────────────────────
    _F = ("Helvetica", 14)
    _FB = ("Helvetica", 14, "bold")

    _C_ACCT = _T["band_account"]
    _C_FD = _T["band_fd"]
    _C_DATES = _T["band_dates"]

    form_body = tk.Frame(win, bg=_T["main_bg"])
    form_body.pack(fill="x", padx=12, pady=6)

    # Band 1
    acct_band, acct_lrow, acct_erow = _make_band(form_body, _C_ACCT)
    acct_band.pack(fill="x", pady=(0, 5))

    _band_label(acct_lrow, "Linked Bank Account", _C_ACCT, _F)
    _band_label(acct_lrow, "FD Number", _C_ACCT, _F, padx=110)

    account_combo = ttk.Combobox(acct_erow, width=36, values=list(account_map.keys()), font=_F, state="readonly")
    account_combo.pack(side="left", padx=(0, 8))
    apply_entry_theme(account_combo)

    fd_number_entry = tk.Entry(acct_erow, width=22, font=_FB)
    fd_number_entry.pack(side="left", padx=(18, 0))
    apply_entry_theme(fd_number_entry)

    # Band 2
    fd_band, fd_lrow, fd_erow = _make_band(form_body, _C_FD)
    fd_band.pack(fill="x", pady=(0, 5))

    _band_label(fd_lrow, "Principal Amount (₹)", _C_FD, _F)
    _band_label(fd_lrow, "Interest Rate (% p.a.)", _C_FD, _F, padx=60)
    _band_label(fd_lrow, "Is Active", _C_FD, _F, padx=60)

    principal_entry = tk.Entry(fd_erow, width=18, font=_FB)
    principal_entry.pack(side="left", padx=(0, 8))
    apply_entry_theme(principal_entry)

    interest_entry = tk.Entry(fd_erow, width=12, font=_FB)
    interest_entry.pack(side="left", padx=(18, 8))
    apply_entry_theme(interest_entry)

    is_active_var = tk.BooleanVar()
    is_active_cb = tk.Checkbutton(
        fd_erow, variable=is_active_var, text="Active", font=_F, bg=_C_FD,
        fg=_T.get("label_fg", "white"), selectcolor="#001a50", activebackground=_C_FD,
        activeforeground=_T.get("label_fg", "white")
    )
    is_active_cb.pack(side="left", padx=(18, 0))

    # Band 3
    dates_band, dates_lrow, dates_erow = _make_band(form_body, _C_DATES)
    dates_band.pack(fill="x", pady=(0, 5))

    _band_label(dates_lrow, "Open Date", _C_DATES, _F)
    _band_label(dates_lrow, "Maturity Date", _C_DATES, _F, padx=80)

    open_dt = DateEntry(dates_erow, date_pattern="dd-mm-yyyy", width=14, font=_F)
    open_dt.pack(side="left", padx=(0, 8))
    apply_entry_theme(open_dt)
    bind_date_spin(open_dt)

    maturity_dt = DateEntry(dates_erow, date_pattern="dd-mm-yyyy", width=14, font=_F)
    maturity_dt.pack(side="left", padx=(18, 0))
    apply_entry_theme(maturity_dt)
    bind_date_spin(maturity_dt)

    # Load data
    try:
        with get_db_connection(BANK_DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT account_id, fd_number, principal_amount, interest_rate, open_dt, maturity_dt, is_active
                FROM fd_master
                WHERE fd_master_id = ?
            """, (fd_master_id,))
            row = cur.fetchone()
            if row:
                account_id, fd_number, principal, interest, o_dt, m_dt, is_active = row
                
                if account_id in account_id_to_label:
                    account_combo.set(account_id_to_label[account_id])
                
                fd_number_entry.insert(0, str(fd_number))
                principal_entry.insert(0, str(principal))
                interest_entry.insert(0, str(interest))
                
                try:
                    open_dt.set_date(datetime.strptime(o_dt, "%Y-%m-%d").date())
                except Exception:
                    pass
                try:
                    maturity_dt.set_date(datetime.strptime(m_dt, "%Y-%m-%d").date())
                except Exception:
                    pass
                
                is_active_var.set(bool(is_active))
            else:
                show_colorful_error(win, "Error", "FD master record not found.")
                win.after(100, cleanup_and_close)
    except Exception as e:
        logger.error("Failed to load fd_master_id %s: %s", fd_master_id, e)

    # Save button
    btn_frame = tk.Frame(win, bg=_T["main_bg"])
    btn_frame.pack(pady=8)

    def _validate_and_save():
        acct_label = account_combo.get()
        if not acct_label or acct_label not in account_map:
            flash_error(account_combo)
            show_colorful_error(win, "Validation Error", "Please select a linked bank account.")
            return

        fd_num = fd_number_entry.get().strip()
        if not fd_num:
            flash_error(fd_number_entry)
            show_colorful_error(win, "Validation Error", "FD Number cannot be blank.")
            return

        try:
            principal_val = float(principal_entry.get().strip().replace(",", ""))
            if principal_val <= 0:
                raise ValueError
        except ValueError:
            flash_error(principal_entry)
            show_colorful_error(win, "Validation Error", "Principal amount must be a positive number.")
            return

        try:
            interest_rate = float(interest_entry.get().strip().replace(",", ""))
            if interest_rate <= 0:
                raise ValueError
        except ValueError:
            flash_error(interest_entry)
            show_colorful_error(win, "Validation Error", "Interest rate must be a positive number.")
            return

        try:
            open_date = open_dt.get_date()
            maturity_date = maturity_dt.get_date()
        except Exception:
            show_colorful_error(win, "Validation Error", "Please enter valid dates.")
            return

        if maturity_date <= open_date:
            flash_error(maturity_dt)
            show_colorful_error(win, "Validation Error", "Maturity date must be later than the open date.")
            return

        try:
            with get_db_connection(BANK_DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("""
                    UPDATE fd_master
                    SET account_id = ?, fd_number = ?, principal_amount = ?, interest_rate = ?, open_dt = ?, maturity_dt = ?, is_active = ?
                    WHERE fd_master_id = ?
                """, (
                    account_map[acct_label],
                    fd_num,
                    principal_val,
                    interest_rate,
                    open_date.strftime("%Y-%m-%d"),
                    maturity_date.strftime("%Y-%m-%d"),
                    1 if is_active_var.get() else 0,
                    fd_master_id
                ))
                conn.commit()
            show_colorful_info(win, "Success", "FD Master updated successfully.")
            cleanup_and_close()
        except sqlite3.IntegrityError as e:
            show_colorful_error(win, "Integrity Error", f"Database error (possibly duplicate FD Number):\n{e}")
        except Exception as e:
            logger.error("Failed to update fd_master_id %s: %s", fd_master_id, e)
            show_colorful_error(win, "Database Error", f"Failed to update FD master:\n{e}")

    save_btn = tk.Button(
        btn_frame,
        text="Save",
        command=_validate_and_save,
        font=("Helvetica", 13, "bold"),
        bg=_T.get("submit_bg", _T.get("button_bg", "#1e40af")),
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
        _T.get("submit_bg", _T.get("button_bg", "#1e40af")),
        _T.get("submit_hover_bg", "#2563eb"),
    )

    cancel_btn = tk.Button(
        btn_frame,
        text="Cancel",
        command=cleanup_and_close,
        font=("Helvetica", 13, "bold"),
        bg=_T.get("cancel_bg", _T.get("button_bg", "#991b1b")),
        fg=_T.get("button_fg", "white"),
        activeforeground=_T.get("button_fg", "white"),
        padx=18,
        pady=6,
        cursor="hand2",
        relief="raised",
        bd=3,
    )
    cancel_btn.pack(side="left", padx=12)
    apply_button_animations(
        cancel_btn,
        _T.get("cancel_bg", _T.get("button_bg", "#991b1b")),
        _T.get("cancel_hover_bg", "#991b1b"),
    )

    win.bind("<Control-Return>", lambda e: _validate_and_save())

    parent.wait_window(win)
