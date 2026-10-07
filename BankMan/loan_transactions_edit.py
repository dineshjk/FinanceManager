# -*- coding: utf-8 -*-
# BankMan/loan_transactions_edit.py

"""
Module for editing Loan Transaction records (loan_transactions table).
"""

from typing import Union
import sqlite3
import tkinter as tk
from tkinter import ttk
from tkcalendar import DateEntry
from datetime import datetime

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
)
from Shared.modal_utils import disable_parent
from Shared.window_manager import push_window, safe_close_modal
from Shared.globals import logger, get_db_connection, BANK_DB_PATH
from Shared.help_utils import show_standard_help

_T = LOAN_TRANS_ADD_UI_THEME
_HINT_FG = "#fda4af"

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

def _fetch_transaction(loan_trans_id: int) -> dict | None:
    try:
        with get_db_connection(BANK_DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT lt.loan_trans_id,
                       lt.loan_master_id,
                       lt.account_id,
                       lt.loan_trans_dt,
                       lt.loan_description,
                       lt.prevailing_interest_rate,
                       lt.principal,
                       lt.interest,
                       lt.charges,
                       lt.loan_payment,
                       lt.loan_credit,
                       lt.principal_due,
                       lm.loan_type,
                       lm.loan_account_number,
                       b.name AS bank_name,
                       a.ac_number
                FROM loan_transactions lt
                JOIN loan_master lm ON lt.loan_master_id = lm.loan_master_id
                JOIN accounts a ON lm.account_id = a.ac_id
                JOIN banks b ON a.b_id = b.b_id
                WHERE lt.loan_trans_id = ?
                """,
                (loan_trans_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            keys = [
                "loan_trans_id", "loan_master_id", "account_id", "loan_trans_dt",
                "loan_description", "prevailing_interest_rate", "principal",
                "interest", "charges", "loan_payment", "loan_credit",
                "principal_due", "loan_type", "loan_account_number", "bank_name", "ac_number"
            ]
            return dict(zip(keys, row))
    except sqlite3.Error as exc:
        logger.error("_fetch_transaction(%s): %s", loan_trans_id, exc)
        return None

def edit_loan_transaction(
    parent: Union[tk.Toplevel, tk.Tk],
    loan_trans_id: int,
    calling_button: tk.Widget | None = None,
) -> None:
    """Launch the Edit Loan Transaction dialog."""

    data = _fetch_transaction(loan_trans_id)
    if data is None:
        show_colorful_error(
            parent,
            "Load Error",
            f"Could not load transaction #{loan_trans_id} from the database.",
        )
        return

    _state: dict = {
        "prev_principal_due": 0.0,
    }

    disable_parent(parent, calling_button=calling_button)

    win = tk.Toplevel(parent)
    win.title(f"✏️ Edit Loan Transaction #{loan_trans_id} ✏️")
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

    tooltip_var = setup_footer_tooltip(
        win, bg_color=_T["header_bg"], fg_color=_T["header_fg"]
    )

    def cleanup_and_close(_event=None):
        return safe_close_modal(win, parent, calling_button)

    def on_escape(_event=None):
        return cleanup_and_close()

    win.bind("<Control-Return>", lambda e: None)
    win.bind("<Escape>", on_escape)
    win.protocol("WM_DELETE_WINDOW", on_escape)

    header_frame = tk.Frame(win, bg=_T["header_bg"], relief="raised", bd=3)
    header_frame.pack(fill="x", padx=5, pady=0)
    tk.Label(
        header_frame,
        text=f"✏️  Edit Loan Transaction #{loan_trans_id}  ✏️",
        font=("Helvetica", 18, "bold"),
        bg=_T["header_bg"],
        fg=_T["header_fg"],
        relief="ridge",
        bd=2,
        pady=8,
    ).pack(fill="x")

    hint_frame = tk.Frame(win, bg=_T["main_bg"])
    hint_frame.pack(fill="x", padx=10, pady=(2, 0))
    tk.Label(
        hint_frame,
        text="Esc: Close | Ctrl+Enter: Save",
        font=("Helvetica", 10, "italic"),
        bg=_T["main_bg"],
        fg=_HINT_FG,
    ).pack(side="left", padx=12)

    _F = ("Helvetica", 14)
    _FB = ("Helvetica", 14, "bold")

    _C_MST = _T["band_master"]
    _C_DET = _T["band_details"]
    _C_AMT = _T["band_amounts"]
    _C_BAL = _T["band_balance"]

    form_body = tk.Frame(win, bg=_T["main_bg"])
    form_body.pack(fill="x", padx=12, pady=6)

    mst_band, mst_lrow, mst_erow = _make_band(form_body, _C_MST)
    mst_band.pack(fill="x", pady=(0, 5))

    _band_label(mst_lrow, "Loan Account", _C_MST, _F)
    _band_label(mst_lrow, "Account / Principal Info", _C_MST, _F, padx=100)

    loan_label = f"{data['loan_type']} [{data['loan_account_number']}] - {data['bank_name']}"
    loan_var = tk.StringVar(value=loan_label)
    loan_entry = tk.Entry(mst_erow, textvariable=loan_var, width=44, font=_F, state="readonly")
    loan_entry.pack(side="left", padx=(0, 8))
    apply_entry_theme(loan_entry, is_readonly=True)
    bind_tooltip(loan_entry, tooltip_var, "The loan account for this transaction (read-only).")

    prev_due = (data["principal_due"] or 0) + (data["principal"] or 0) - (data["loan_credit"] or 0)
    _state["prev_principal_due"] = prev_due

    loan_info_var = tk.StringVar(value=f"Account ID = {data['account_id']}")
    tk.Label(
        mst_erow,
        textvariable=loan_info_var,
        font=_F,
        bg=_C_MST,
        fg=_HINT_FG,
        width=34,
        anchor="w",
    ).pack(side="left", padx=(18, 0))

    det_band, det_lrow, det_erow = _make_band(form_body, _C_DET)
    det_band.pack(fill="x", pady=(0, 5))

    _band_label(det_lrow, "Trans Date", _C_DET, _F)
    _band_label(det_lrow, "Description (optional)", _C_DET, _F, padx=42)
    _band_label(det_lrow, "Prevailing Rate (%)", _C_DET, _F, padx=42)

    trans_dt = DateEntry(det_erow, date_pattern="dd-mm-yyyy", width=14, font=_F)
    trans_dt.set_date(datetime.strptime(data["loan_trans_dt"], "%Y-%m-%d"))
    trans_dt.pack(side="left", padx=(0, 8))
    apply_entry_theme(trans_dt)
    bind_tooltip(trans_dt, tooltip_var, "Date of this EMI / repayment event.")
    bind_date_spin(trans_dt)

    description_entry = tk.Entry(det_erow, width=28, font=_FB)
    description_entry.pack(side="left", padx=(18, 8))
    description_entry.insert(0, data["loan_description"] or "")
    apply_entry_theme(description_entry)
    bind_tooltip(
        description_entry,
        tooltip_var,
        "Optional narration, e.g. 'EMI #12', 'Prepayment'.",
    )

    rate_entry = tk.Entry(det_erow, width=10, font=_FB)
    rate_entry.pack(side="left", padx=(18, 0))
    rate_entry.insert(0, f"{data['prevailing_interest_rate']:.2f}")
    apply_entry_theme(rate_entry)
    bind_tooltip(
        rate_entry,
        tooltip_var,
        "Prevailing annual interest rate for this instalment (%).",
    )

    amt_band, amt_lrow, amt_erow = _make_band(form_body, _C_AMT)
    amt_band.pack(fill="x", pady=(0, 5))

    _band_label(amt_lrow, "Principal (\u20b9)", _C_AMT, _F)
    _band_label(amt_lrow, "Interest (\u20b9)", _C_AMT, _F, padx=22)
    _band_label(amt_lrow, "Charges (\u20b9)", _C_AMT, _F, padx=22)
    _band_label(amt_lrow, "Loan Payment (\u20b9)", _C_AMT, _F, padx=22)
    _band_label(amt_lrow, "Loan Credit (\u20b9)", _C_AMT, _F, padx=22)

    principal_entry = tk.Entry(amt_erow, width=14, font=_FB)
    principal_entry.pack(side="left", padx=(0, 8))
    principal_entry.insert(0, f"{data['principal'] or 0:.2f}")
    apply_entry_theme(principal_entry)

    interest_entry = tk.Entry(amt_erow, width=14, font=_FB)
    interest_entry.pack(side="left", padx=(18, 8))
    interest_entry.insert(0, f"{data['interest'] or 0:.2f}")
    apply_entry_theme(interest_entry)

    charges_entry = tk.Entry(amt_erow, width=14, font=_FB)
    charges_entry.pack(side="left", padx=(18, 8))
    charges_entry.insert(0, f"{data['charges'] or 0:.2f}")
    apply_entry_theme(charges_entry)

    payment_entry = tk.Entry(amt_erow, width=14, font=_FB)
    payment_entry.pack(side="left", padx=(18, 8))
    payment_entry.insert(0, f"{data['loan_payment'] or 0:.2f}")
    apply_entry_theme(payment_entry)

    credit_entry = tk.Entry(amt_erow, width=14, font=_FB)
    credit_entry.pack(side="left", padx=(18, 0))
    credit_entry.insert(0, f"{data['loan_credit'] or 0:.2f}")
    apply_entry_theme(credit_entry)

    bal_band, bal_lrow, bal_erow = _make_band(form_body, _C_BAL)
    bal_band.pack(fill="x", pady=(0, 5))

    _band_label(bal_lrow, "Previous Principal Due (\u20b9)", _C_BAL, _F)
    _band_label(bal_lrow, "New Principal Due (\u20b9)", _C_BAL, _F, padx=80)

    prev_due_var = tk.StringVar(value=f"\u20b9{prev_due:,.2f}")
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
    new_due_entry.insert(0, f"{data['principal_due'] or 0:.2f}")
    apply_entry_theme(new_due_entry)

    def _recompute_payment(*_args):
        try:
            p = float(principal_entry.get().replace(",", "") or 0)
            i = float(interest_entry.get().replace(",", "") or 0)
            c = float(charges_entry.get().replace(",", "") or 0)
            payment_entry.delete(0, "end")
            payment_entry.insert(0, f"{p + i + c:.2f}")
        except ValueError:
            pass

    def _recompute_due(*_args):
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

    btn_frame = tk.Frame(win, bg=_T["main_bg"])
    btn_frame.pack(pady=8)

    def _validate_and_save():
        try:
            loan_trans_dt = trans_dt.get_date().strftime("%Y-%m-%d")
        except Exception:
            flash_error(trans_dt)
            show_colorful_error(
                win, "Validation Error", "Please enter a valid transaction date."
            )
            return

        try:
            rate_str = rate_entry.get().strip().replace(",", "")
            prev_rate = float(rate_str or "0")
        except ValueError:
            flash_error(rate_entry)
            show_colorful_error(
                win, "Validation Error", "Prevailing Rate must be a number."
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
        if principal is None: return
        interest = _parse(interest_entry, "Interest")
        if interest is None: return
        charges = _parse(charges_entry, "Charges")
        if charges is None: return
        loan_payment = _parse(payment_entry, "Loan Payment")
        if loan_payment is None: return
        loan_credit = _parse(credit_entry, "Loan Credit")
        if loan_credit is None: return
        principal_due = _parse(new_due_entry, "New Principal Due")
        if principal_due is None: return

        if principal <= 0 and interest <= 0 and charges <= 0 and loan_credit <= 0:
            flash_error(principal_entry)
            show_colorful_error(
                win,
                "Validation Error",
                "At least one of Principal / Interest / Charges / Loan Credit must be > 0.",
            )
            return

        try:
            with get_db_connection(BANK_DB_PATH) as conn:
                cur = conn.cursor()
                
                cur.execute(
                    """
                    SELECT trans_id, withdrawal_amount, deposit_amount
                    FROM bank_transactions
                    WHERE module_type = 'LOAN' AND module_ref_id = ?
                    """,
                    (loan_trans_id,)
                )
                linked_bank_tx = cur.fetchone()

                new_drcr = "DR" if loan_payment > 0 else "CR"

                cur.execute(
                    """
                    UPDATE loan_transactions
                    SET loan_trans_dt = ?,
                        loan_description = ?,
                        prevailing_interest_rate = ?,
                        loan_credit = ?,
                        principal = ?,
                        interest = ?,
                        charges = ?,
                        loan_payment = ?,
                        principal_due = ?,
                        drcr = ?
                    WHERE loan_trans_id = ?
                    """,
                    (
                        loan_trans_dt,
                        description_entry.get().strip() or None,
                        prev_rate,
                        loan_credit,
                        principal,
                        interest,
                        charges,
                        loan_payment,
                        principal_due,
                        new_drcr,
                        loan_trans_id
                    )
                )

                if linked_bank_tx:
                    b_trans_id, old_w_amt, old_d_amt = linked_bank_tx
                    new_w_amt = loan_payment if loan_payment > 0 else 0.0
                    new_d_amt = loan_credit if loan_credit > 0 else 0.0

                    delta = (new_d_amt - old_d_amt) - (new_w_amt - old_w_amt)

                    cur.execute(
                        """
                        UPDATE bank_transactions
                        SET trans_date = ?,
                            withdrawal_amount = ?,
                            deposit_amount = ?,
                            balance_after = balance_after + ?
                        WHERE trans_id = ?
                        """,
                        (loan_trans_dt, new_w_amt, new_d_amt, delta, b_trans_id)
                    )

                    if delta != 0.0:
                        cur.execute(
                            """
                            UPDATE bank_transactions
                            SET balance_after = balance_after + ?
                            WHERE account_id = ?
                              AND (
                                trans_date > ?
                                OR (trans_date = ? AND trans_id > ?)
                              )
                            """,
                            (delta, data["account_id"], loan_trans_dt, loan_trans_dt, b_trans_id)
                        )
                
                principal_delta = (data["principal"] or 0) - principal
                credit_delta = loan_credit - (data["loan_credit"] or 0)
                due_delta = principal_delta - credit_delta
                
                if due_delta != 0.0:
                    cur.execute(
                        """
                        UPDATE loan_transactions
                        SET principal_due = principal_due + ?
                        WHERE loan_master_id = ?
                          AND (
                            loan_trans_dt > ?
                            OR (loan_trans_dt = ? AND loan_trans_id > ?)
                          )
                        """,
                        (due_delta, data["loan_master_id"], loan_trans_dt, loan_trans_dt, loan_trans_id)
                    )

                conn.commit()
            
            show_colorful_info(
                win, "Saved", f"Loan Transaction #{loan_trans_id} updated successfully."
            )
            cleanup_and_close()

        except Exception as exc:
            logger.error("update_loan_transaction failed: %s", exc)
            show_colorful_error(
                win, "Database Error", f"Failed to save transaction:\n{exc}"
            )

    submit_button = tk.Button(
        btn_frame,
        text="💾  SAVE CHANGES  💾",
        command=_validate_and_save,
        font=("Comic Sans MS", 12, "bold"),
        bg=_T.get("submit_bg", _T["button_bg"]),
        fg="white",
        activeforeground="white",
        relief="raised",
        bd=3,
        padx=8,
        pady=4,
        cursor="hand2",
    )
    submit_button.pack(side="right", padx=8)

    cancel_btn = tk.Button(
        btn_frame,
        text="❌  Cancel / Close  ❌",
        command=cleanup_and_close,
        font=("Comic Sans MS", 12, "bold"),
        bg=_T.get("cancel_bg", "#ef4444"),
        fg="white",
        activeforeground="white",
        relief="raised",
        bd=3,
        padx=8,
        pady=4,
        cursor="hand2",
    )
    cancel_btn.pack(side="right", padx=4)

    apply_button_animations(
        submit_button, _T.get("submit_bg", _T["button_bg"]), _T.get("submit_hover_bg", "#115e59")
    )
    apply_button_animations(
        cancel_btn, _T.get("cancel_bg", "#ef4444"), _T.get("cancel_hover_bg", "#b91c1c")
    )

    win.bind("<Control-Return>", lambda e: _validate_and_save())
