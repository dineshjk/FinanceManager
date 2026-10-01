# -*- coding: utf-8 -*-
# BankMan/bank_transaction_edit.py

"""
Edit-form for a single ``bank_transactions`` row.
Opened from the Bank Transactions Manager.

This is visually and functionally consistent with the Add Bank Transaction form,
except that it pre-populates all inputs and keeps the Account field read-only.
"""

from datetime import datetime
from typing import Union
import sqlite3
import tkinter as tk
from tkinter import ttk
from tkcalendar import DateEntry

from Shared.gui_utils import (
    apply_button_animations,
    apply_entry_theme,
    BANK_TRANSACTION_ADD_UI_THEME as _THEME,
    bind_tooltip,
    flash_error,
    setup_footer_tooltip,
    bind_date_spin,
)
from Shared.dialog_utils import show_colorful_error, show_colorful_info, show_colorful_yesno
from Shared.modal_utils import disable_parent
from Shared.window_manager import push_window, safe_close_modal
from Shared.help_utils import show_standard_help
from Shared.globals import get_db_connection, BANK_DB_PATH, logger
from Shared.gui_progressive import progressive_selection
from .bank_db_utils import (
    db_update_bank_transaction,
    get_all_budget_heads,
    get_all_user_descriptions,
    get_active_fd_masters,
    get_all_card_masters as _db_get_all_card_masters,
    get_active_ppf_masters as get_all_ppf_masters,
    get_all_loan_masters_for_display,
    get_stock_computed_bank_entries,
    get_stock_actual_bank_entries,
    get_active_mf_masters,
    get_active_ins_masters,
    get_budget_heads_with_parents as _db_get_bh_with_parents,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MODULE_TYPES = [
    "NONE",
    "FD",
    "CC",
    "LOAN",
    "PPF",
    "STOCK_COMP",
    "STOCK_ACTU",
    "MF",
    "INS",
]
_ENTRY_TYPES = ["INCOME", "EXPENSE", "TRANSFER"]

_F = ("Helvetica", 14)  # standard field font
_FB = ("Helvetica", 14, "bold")  # bold for amounts
_FH = ("Helvetica", 18, "bold")  # header title


# ---------------------------------------------------------------------------
# DB read helper — loads a single transaction row
# ---------------------------------------------------------------------------


def _fetch_transaction(trans_id: int) -> dict | None:
    """Return all editable fields for *trans_id* as a dict, or None."""
    try:
        with get_db_connection(BANK_DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT bt.trans_id,
                       bt.account_id,
                       b.name || '  —  ' || a.ac_number  AS account_label,
                       bt.serial_no,
                       bt.value_date,
                       bt.trans_date,
                       bt.cheque_no,
                       bt.bank_desc,
                       bt.user_desc,
                       bt.withdrawal_amount,
                       bt.deposit_amount,
                       bt.balance_after,
                       bt.pair_id,
                       bt.bh_id,
                       bt.module_type,
                       bt.module_ref_id,
                       bt.entry_type
                FROM   bank_transactions bt
                JOIN   accounts a ON bt.account_id = a.ac_id
                JOIN   banks    b ON a.b_id = b.b_id
                WHERE  bt.trans_id = ?
                """,
                (trans_id,),
            )
            row = cursor.fetchone()
    except sqlite3.Error as exc:
        logger.error("_fetch_transaction(%s): %s", trans_id, exc)
        return None

    if row is None:
        return None

    keys = [
        "trans_id",
        "account_id",
        "account_label",
        "serial_no",
        "value_date",
        "trans_date",
        "cheque_no",
        "bank_desc",
        "user_desc",
        "withdrawal_amount",
        "deposit_amount",
        "balance_after",
        "pair_id",
        "bh_id",
        "module_type",
        "module_ref_id",
        "entry_type",
    ]
    return dict(zip(keys, row))


# ---------------------------------------------------------------------------
# Form Layout Helpers
# ---------------------------------------------------------------------------


def _make_band(container, bg, relief="ridge", padx=10, pady=6):
    band = tk.Frame(container, bg=bg, relief=relief, bd=2, padx=padx, pady=pady)
    label_row = tk.Frame(band, bg=bg)
    label_row.pack(fill="x", pady=(0, 2))
    entry_row = tk.Frame(band, bg=bg)
    entry_row.pack(fill="x", pady=(0, 2))
    return band, label_row, entry_row


def _band_label(parent, text, bg, font=("Helvetica", 14), padx=0):
    tk.Label(parent, text=text, font=font, bg=bg, fg="#1e293b", anchor="w").pack(
        side="left", padx=(padx, 12)
    )


def _fmt_amount_on_focus_out(entry: tk.Entry, _event=None) -> None:
    try:
        val_str = entry.get().strip().replace(",", "")
        if not val_str:
            val_str = "0.00"
        val = float(val_str)
        entry.delete(0, tk.END)
        entry.insert(0, f"{val:.2f}")
    except ValueError:
        pass


def _create_subledger_row(conn, module_type, master_id, account_id, trans_date, withdrawal_amount, deposit_amount, bank_desc) -> int:
    cursor = conn.conn.cursor() if hasattr(conn, "conn") else conn.cursor()
    if module_type == "FD":
        cursor.execute(
            """
            INSERT INTO fd_transactions 
            (fd_master_id, account_id, fd_trans_dt, fd_saving, fd_withdrawal, fd_principal, fd_int)
            VALUES (?, ?, ?, ?, ?, 0.0, 0.0)
            """,
            (master_id, account_id, trans_date, deposit_amount, withdrawal_amount),
        )
        return cursor.lastrowid
    elif module_type == "CC":
        drcr = "CR" if withdrawal_amount > 0 else "DR"
        party = bank_desc or "N/A"
        cursor.execute(
            """
            INSERT INTO cc_transactions (card_master_id, account_id, cc_trans_dt, expense, cc_credit, drcr, party)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                master_id,
                account_id,
                trans_date,
                withdrawal_amount,
                deposit_amount,
                drcr,
                party,
            ),
        )
        return cursor.lastrowid
    elif module_type == "LOAN":
        drcr = "DR" if withdrawal_amount > 0 else "CR"
        cursor.execute(
            """
            INSERT INTO loan_transactions (loan_master_id, account_id, loan_trans_dt, loan_payment, loan_credit, drcr)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                master_id,
                account_id,
                trans_date,
                withdrawal_amount,
                deposit_amount,
                drcr,
            ),
        )
        return cursor.lastrowid
    elif module_type == "PPF":
        ppf_saving = withdrawal_amount if withdrawal_amount > 0 else 0.0
        ppf_withdrawal = deposit_amount if deposit_amount > 0 else 0.0
        cursor.execute(
            """
            INSERT INTO ppf_transactions (ppf_master_id, account_id, ppf_trans_dt, ppf_saving, ppf_withdrawal, ppf_balance)
            VALUES (?, ?, ?, ?, ?, 0.0)
            """,
            (master_id, account_id, trans_date, ppf_saving, ppf_withdrawal),
        )
        return cursor.lastrowid
    elif module_type == "MF":
        mf_purchase = withdrawal_amount if withdrawal_amount > 0 else 0.0
        mf_redemption = deposit_amount if deposit_amount > 0 else 0.0
        cursor.execute(
            """
            INSERT INTO mf_transactions (mf_master_id, account_id, mf_trans_dt, mf_purchase, mf_redemption, nav, units, balance_units)
            VALUES (?, ?, ?, ?, ?, 0.0, 0.0, 0.0)
            """,
            (master_id, account_id, trans_date, mf_purchase, mf_redemption),
        )
        return cursor.lastrowid
    elif module_type == "INS":
        ins_premium = withdrawal_amount if withdrawal_amount > 0 else 0.0
        ins_payout = deposit_amount if deposit_amount > 0 else 0.0
        cursor.execute(
            """
            INSERT INTO ins_transactions (ins_master_id, account_id, ins_trans_dt, ins_premium, ins_payout)
            VALUES (?, ?, ?, ?, ?)
            """,
            (master_id, account_id, trans_date, ins_premium, ins_payout),
        )
        return cursor.lastrowid
    elif module_type in ("STOCK_COMP", "STOCK_ACTU"):
        return master_id
    return None


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def edit_bank_transaction(
    parent: Union[tk.Toplevel, tk.Tk],
    trans_id: int,
    calling_button: tk.Widget | None = None,
) -> None:
    """Open a modal edit form pre-populated with the selected transaction."""

    # ── Fetch current data ────────────────────────────────────────────────
    data = _fetch_transaction(trans_id)
    if data is None:
        show_colorful_error(
            parent,
            "Load Error",
            f"Could not load transaction #{trans_id} from the database.",
        )
        return

    # ── Lookup data ───────────────────────────────────────────────────────
    bh_rows = sorted(get_all_budget_heads(), key=lambda r: r[1])
    budget_map = {r[1]: r[0] for r in bh_rows}
    {r[1]: r[2] for r in bh_rows}
    bh_id_to_name = {r[0]: r[1] for r in bh_rows}
    bh_values = ["(none)"] + [r[1] for r in bh_rows]

    fd_map: dict = {}  # fd_number → fd_master_id
    cc_map: dict = {}
    ppf_map: dict = {}
    loan_map: dict = {}
    stock_comp_map: dict = {}
    stock_actu_map: dict = {}
    mf_map: dict = {}
    ins_map: dict = {}

    # Find initial FD / CC selections if applicable
    initial_fd_number = ""
    if data["module_type"] == "FD" and data["module_ref_id"]:
        try:
            with get_db_connection(BANK_DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT fm.fd_number
                    FROM fd_transactions ft
                    JOIN fd_master fm ON ft.fd_master_id = fm.fd_master_id
                    WHERE ft.fd_trans_id = ?
                    """,
                    (data["module_ref_id"],),
                )
                row = cursor.fetchone()
                if row:
                    initial_fd_number = row[0]
        except Exception as exc:
            logger.debug("Failed to fetch initial FD: %s", exc)

    initial_cc_label = ""
    if data["module_type"] == "CC" and data["module_ref_id"]:
        try:
            with get_db_connection(BANK_DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT cm.card_name, cm.card_number
                    FROM cc_transactions ct
                    JOIN card_master cm ON ct.card_master_id = cm.card_master_id
                    WHERE ct.cc_trans_id = ?
                    """,
                    (data["module_ref_id"],),
                )
                row = cursor.fetchone()
                if row:
                    name, num = row
                    initial_cc_label = f"{name} ({str(num)[-4:] if num else 'N/A'})"
        except Exception as exc:
            logger.debug("Failed to fetch initial CC: %s", exc)

    initial_ppf_label = ""
    if data["module_type"] == "PPF" and data["module_ref_id"]:
        try:
            with get_db_connection(BANK_DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT pm.ppf_account_number, pm.holder_name, pm.is_active FROM ppf_transactions pt JOIN ppf_master pm ON pt.ppf_master_id = pm.ppf_master_id WHERE pt.ppf_trans_id = ?",
                    (data["module_ref_id"],)
                )
                r = cursor.fetchone()
                if r:
                    initial_ppf_label = f"{r[0]} - {r[1]} ({'Active' if r[2] else 'Closed'})"
        except Exception:
            pass

    initial_loan_label = ""
    if data["module_type"] == "LOAN" and data["module_ref_id"]:
        try:
            with get_db_connection(BANK_DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT lm.loan_type, lm.loan_account_number, b.name FROM loan_transactions lt JOIN loan_master lm ON lt.loan_master_id = lm.loan_master_id JOIN accounts a ON lm.loan_account_id = a.ac_id JOIN banks b ON a.b_id = b.b_id WHERE lt.loan_trans_id = ?",
                    (data["module_ref_id"],)
                )
                r = cursor.fetchone()
                if r:
                    initial_loan_label = f"{r[0]} [{r[1]}] - {r[2]}"
        except Exception:
            pass

    initial_stock_comp_label = ""
    if data["module_type"] == "STOCK_COMP" and data["module_ref_id"]:
        from Shared.globals import STOCK_DB_PATH
        import os
        if os.path.exists(STOCK_DB_PATH):
            try:
                with get_db_connection(STOCK_DB_PATH) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT id_comp_bt, comp_bt_dt, comp_bt_type, comp_bt_amt, cont_no, comp_bt_desc FROM computed_bank WHERE id_comp_bt = ?",
                        (data["module_ref_id"],)
                    )
                    r = cursor.fetchone()
                    if r:
                        initial_stock_comp_label = f"#{r[0]} | {r[1]} | {r[2]} \u20b9{r[3]:.2f} | {r[4] or ''} {r[5] or ''}".strip()
            except Exception:
                pass

    initial_stock_actu_label = ""
    if data["module_type"] == "STOCK_ACTU" and data["module_ref_id"]:
        from Shared.globals import STOCK_DB_PATH
        import os
        if os.path.exists(STOCK_DB_PATH):
            try:
                with get_db_connection(STOCK_DB_PATH) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT id_actu_bt, actu_bt_dt, actu_bt_type, actu_bt_amt, actu_bt_desc FROM actual_bank WHERE id_actu_bt = ?",
                        (data["module_ref_id"],)
                    )
                    r = cursor.fetchone()
                    if r:
                        initial_stock_actu_label = f"#{r[0]} | {r[1]} | {r[2]} \u20b9{r[3]:.2f} | {r[4] or ''}".strip()
            except Exception:
                pass

    initial_mf_label = ""
    if data["module_type"] == "MF" and data["module_ref_id"]:
        try:
            with get_db_connection(BANK_DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT mm.amc_name, mm.scheme_name, mm.folio_number, mm.rta_name FROM mf_transactions mt JOIN mf_master mm ON mt.mf_master_id = mm.mf_master_id WHERE mt.mf_trans_id = ?",
                    (data["module_ref_id"],)
                )
                r = cursor.fetchone()
                if r:
                    initial_mf_label = f"{r[0]} | {r[1]} [Folio: {r[2]} - {r[3]}]"
        except Exception:
            pass

    initial_ins_label = ""
    if data["module_type"] == "INS" and data["module_ref_id"]:
        try:
            with get_db_connection(BANK_DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT im.company_name, im.ins_category, im.policy_number, im.assured_item FROM ins_transactions it JOIN ins_master im ON it.ins_master_id = im.ins_master_id WHERE it.ins_trans_id = ?",
                    (data["module_ref_id"],)
                )
                r = cursor.fetchone()
                if r:
                    initial_ins_label = f"{r[0]} ({r[1]}) | Pol: {r[2]} | Assured: {r[3]}"
        except Exception:
            pass


    # ── Modal window ──────────────────────────────────────────────────────
    disable_parent(parent, calling_button=calling_button)

    win = tk.Toplevel(parent)
    win.title(f"✏️  Edit Bank Transaction  #{trans_id}  ✏️")
    win.geometry("1100x680")
    win.resizable(False, False)
    win.configure(bg=_THEME["main_bg"])
    win.transient(parent)
    win.grab_set()
    win.focus_set()
    try:
        push_window(win, parent)
    except (RuntimeError, tk.TclError) as exc:
        logger.debug("push_window failed: %s", exc)

    # Footer tooltip — packed FIRST (anchors to absolute bottom)
    tooltip_var = setup_footer_tooltip(win)

    def cleanup_and_close(_event=None):
        return safe_close_modal(win, parent, calling_button)

    def on_escape(_event=None):
        return cleanup_and_close()

    # ── Header ────────────────────────────────────────────────────────────
    hdr = tk.Frame(win, bg=_THEME["header_bg"], relief="raised", bd=3)
    hdr.pack(fill="x", padx=5, pady=0)

    tk.Label(
        hdr,
        text=f"✏️  Edit Bank Transaction  #{trans_id}  ✏️",
        font=_FH,
        bg=_THEME["header_bg"],
        fg=_THEME["header_fg"],
        relief="ridge",
        bd=2,
    ).pack(fill="x", pady=10)

    # ── Main form ─────────────────────────────────────────────────────────
    form_body = tk.Frame(win, bg=_THEME["main_bg"])
    form_body.pack(fill="x", padx=12, pady=4)

    # Band colors
    _C_ACCT = "#e0f2fe"  # sky-blue
    _C_REMARK = "#fef3c7"  # amber-100
    _C_AMT = "#ede9fe"  # violet-100
    _C_MOD = "#d1fae5"  # emerald-100

    # ── Band 1: Account, Serial, Cheque, Dates ────────────────────────────
    acct_band, acct_lrow, acct_erow = _make_band(form_body, _C_ACCT)
    acct_band.pack(fill="x", pady=(0, 4))

    _band_label(acct_lrow, "Account", _C_ACCT, _F)
    _band_label(acct_lrow, "Sr No.", _C_ACCT, _F, padx=230)
    _band_label(acct_lrow, "Cheque No", _C_ACCT, _F, padx=20)
    _band_label(acct_lrow, "Value Dt", _C_ACCT, _F, padx=20)
    _band_label(acct_lrow, "Trans Dt", _C_ACCT, _F, padx=90)

    # Account is immutable on edit
    acct_var = tk.StringVar(value=data["account_label"])
    acct_entry = tk.Entry(acct_erow, textvariable=acct_var, width=25, font=_F, state="readonly")
    acct_entry.pack(side="left", padx=(0, 4))
    apply_entry_theme(acct_entry, is_readonly=True)
    bind_tooltip(acct_entry, tooltip_var, "The bank account for this transaction (read-only).")

    # Serial No
    serial_no_entry = tk.Entry(acct_erow, width=5, font=_F)
    serial_no_entry.insert(0, str(data["serial_no"]) if data["serial_no"] else "")
    serial_no_entry.pack(side="left", padx=(20, 0))
    apply_entry_theme(serial_no_entry)
    bind_tooltip(serial_no_entry, tooltip_var, "Optional bank serial / reference number. Leave blank for NULL.")

    # Cheque No
    cheque_no_entry = tk.Entry(acct_erow, width=10, font=_F)
    cheque_no_entry.insert(0, data["cheque_no"] or "")
    cheque_no_entry.pack(side="left", padx=(20, 0))
    apply_entry_theme(cheque_no_entry)
    bind_tooltip(cheque_no_entry, tooltip_var, "Cheque number for cheque-based transactions.")

    # Dates
    value_dt = DateEntry(acct_erow, date_pattern="dd-mm-yyyy", width=14, font=_F)
    value_dt.set_date(datetime.strptime(data["value_date"], "%Y-%m-%d"))
    value_dt.pack(side="left", padx=(20, 0))
    apply_entry_theme(value_dt)
    bind_tooltip(value_dt, tooltip_var, "Value date — bank effective date (calendar picker).")

    trans_dt = DateEntry(acct_erow, date_pattern="dd-mm-yyyy", width=14, font=_F)
    trans_dt.set_date(datetime.strptime(data["trans_date"], "%Y-%m-%d"))
    trans_dt.pack(side="left", padx=(20, 0))
    apply_entry_theme(trans_dt)
    bind_tooltip(trans_dt, tooltip_var, "Transaction date — calendar date the event was initiated.")

    # ── Value Dt → Trans Dt sync helper ───────────────────────────────────
    def _sync_trans_dt(*_):
        try:
            trans_dt.set_date(value_dt.get_date())
        except Exception:
            pass

    value_dt.bind("<<DateEntrySelected>>", _sync_trans_dt)
    value_dt.bind("<FocusOut>", _sync_trans_dt)
    bind_date_spin(value_dt, callback=_sync_trans_dt)
    bind_date_spin(trans_dt)

    # ── Band 2: Remarks ───────────────────────────────────────────────────
    remark_band, remark_lrow, remark_erow = _make_band(form_body, _C_REMARK)
    remark_band.pack(fill="x", pady=(0, 4))

    _band_label(remark_lrow, "Bank Remark", _C_REMARK, _F)
    bank_remark_entry = tk.Entry(remark_erow, width=60, font=_F)
    bank_remark_entry.insert(0, data["bank_desc"] or "")
    bank_remark_entry.pack(side="left")
    apply_entry_theme(bank_remark_entry)
    bind_tooltip(bank_remark_entry, tooltip_var, "Narration as it appears on the bank statement.")

    # ── Band 3: Amounts ───────────────────────────────────────────────────
    amt_band, amt_lrow, amt_erow = _make_band(form_body, _C_AMT)
    amt_band.pack(fill="x", pady=(0, 4))

    _band_label(amt_lrow, "Withdrawal", _C_AMT, _F)
    _band_label(amt_lrow, "Deposit", _C_AMT, _F, padx=45)
    _band_label(amt_lrow, "Balance", _C_AMT, _F, padx=70)
    _band_label(amt_lrow, "Pair ID", _C_AMT, _F, padx=80)
    _band_label(amt_lrow, "Budget Head", _C_AMT, _F, padx=190)

    withdrawal_entry = tk.Entry(amt_erow, width=11, font=_FB)
    withdrawal_entry.insert(0, f"{data['withdrawal_amount']:.2f}")
    withdrawal_entry.pack(side="left", padx=(0, 30))
    apply_entry_theme(withdrawal_entry)
    bind_tooltip(withdrawal_entry, tooltip_var, "Amount leaving the account (debit). Enter 0 if N/A.")

    deposit_entry = tk.Entry(amt_erow, width=11, font=_FB)
    deposit_entry.insert(0, f"{data['deposit_amount']:.2f}")
    deposit_entry.pack(side="left", padx=(0, 30))
    apply_entry_theme(deposit_entry)
    bind_tooltip(deposit_entry, tooltip_var, "Amount entering the account (credit). Enter 0 if N/A.")

    balance_entry = tk.Entry(amt_erow, width=11, font=_FB)
    balance_entry.insert(0, f"{data['balance_after']:.2f}")
    balance_entry.pack(side="left", padx=(0, 30))
    apply_entry_theme(balance_entry)
    bind_tooltip(balance_entry, tooltip_var, "Running account balance after this transaction.")

    pair_id_var = tk.StringVar(value=str(data["pair_id"]) if data["pair_id"] else "")
    pair_id_display = tk.Entry(amt_erow, textvariable=pair_id_var, width=14, font=_F, state="readonly")
    pair_id_display.pack(side="left", padx=(0, 4))
    apply_entry_theme(pair_id_display, is_readonly=True)
    bind_tooltip(pair_id_display, tooltip_var, "ID of the paired transfer transaction. Click Select to browse.")

    def _open_pair_modal():
        from .bank_transactions_add import show_pair_select_modal
        show_pair_select_modal(win, data["account_id"], pair_id_var, on_escape)

    select_pair_btn = tk.Button(
        amt_erow,
        text="Select",
        command=_open_pair_modal,
        font=("Helvetica", 11, "bold"),
        bg=_THEME["button_bg"],
        fg=_THEME["button_fg"],
        cursor="hand2",
        padx=6,
        pady=1,
        relief="raised",
        bd=2,
    )
    select_pair_btn.pack(side="left", padx=(0, 40))
    apply_button_animations(select_pair_btn, _THEME["button_bg"], _THEME["hover_bg"])

    budget_head_combo = ttk.Combobox(amt_erow, width=15, values=bh_values, font=_F)
    budget_head_combo.set(bh_id_to_name.get(data["bh_id"], "(none)"))
    budget_head_combo.pack(side="left")
    apply_entry_theme(budget_head_combo)
    progressive_selection(budget_head_combo, bh_values)
    bind_tooltip(budget_head_combo, tooltip_var, "Budget category for analysis reports.")

    # amount formatting focus binds
    withdrawal_entry.bind("<FocusOut>", lambda e: _fmt_amount_on_focus_out(withdrawal_entry), add="+")
    deposit_entry.bind("<FocusOut>", lambda e: _fmt_amount_on_focus_out(deposit_entry), add="+")
    balance_entry.bind("<FocusOut>", lambda e: _fmt_amount_on_focus_out(balance_entry), add="+")

    # ── Band 4: Module Type & Sub-Ledger ──────────────────────────────────
    mod_band = tk.Frame(form_body, bg=_C_MOD, relief="ridge", bd=2, padx=10, pady=6)
    mod_band.pack(fill="x", pady=(0, 4))

    # Entry Type
    entry_type_lrow = tk.Frame(mod_band, bg=_C_MOD)
    entry_type_lrow.pack(fill="x", pady=(0, 2))
    entry_type_erow = tk.Frame(mod_band, bg=_C_MOD)
    entry_type_erow.pack(fill="x", pady=(0, 6))

    _band_label(entry_type_lrow, "Entry Type", _C_MOD, _F)
    _band_label(entry_type_lrow, "User Desc", _C_MOD, _F, padx=250)

    entry_type_var = tk.StringVar(value=data["entry_type"] or "TRANSFER")
    et_radios = []
    for et_val in _ENTRY_TYPES:
        rb = tk.Radiobutton(
            entry_type_erow,
            text=et_val,
            variable=entry_type_var,
            value=et_val,
            font=("Helvetica", 11),
            bg=_C_MOD,
        )
        rb.pack(side="left", padx=8)
        et_radios.append(rb)

    user_desc_combo = ttk.Combobox(entry_type_erow, width=58, font=_F)
    user_desc_combo.insert(0, data["user_desc"] or "")
    user_desc_combo.pack(side="left", padx=(20, 0))
    apply_entry_theme(user_desc_combo)
    bind_tooltip(user_desc_combo, tooltip_var, "Your own note or description for this transaction.")

    def _on_user_desc_focus(*_):
        try:
            descs = get_all_user_descriptions()
            user_desc_combo["values"] = descs
            progressive_selection(user_desc_combo, descs)
        except Exception as exc:
            logger.debug("Failed to fetch user descriptions: %s", exc)

    user_desc_combo.bind("<FocusIn>", _on_user_desc_focus, add="+")

    # Module Type
    mod_type_lrow = tk.Frame(mod_band, bg=_C_MOD)
    mod_type_lrow.pack(fill="x", pady=(0, 2))
    mod_type_erow = tk.Frame(mod_band, bg=_C_MOD)
    mod_type_erow.pack(fill="x", pady=(0, 6))

    _band_label(mod_type_lrow, "Module Type", _C_MOD, _F)

    module_type_var = tk.StringVar(value=data["module_type"] or "NONE")
    mt_radios = []
    for mt in _MODULE_TYPES[:4]:
        rb = tk.Radiobutton(
            mod_type_erow,
            text=mt,
            variable=module_type_var,
            value=mt,
            font=("Helvetica", 11),
            bg=_C_MOD,
        )
        rb.pack(side="left", padx=8)
        mt_radios.append(rb)

    tk.Frame(mod_type_erow, bg=_C_MOD, width=20).pack(side="left")
    for mt in _MODULE_TYPES[4:]:
        rb = tk.Radiobutton(
            mod_type_erow,
            text=mt,
            variable=module_type_var,
            value=mt,
            font=("Helvetica", 11),
            bg=_C_MOD,
        )
        rb.pack(side="left", padx=8)
        mt_radios.append(rb)

    # Module Ref Entry / Combobox layout
    mod_ref_lrow = tk.Frame(mod_band, bg=_C_MOD)
    mod_ref_lrow.pack(fill="x", pady=(0, 2))
    mod_ref_erow = tk.Frame(mod_band, bg=_C_MOD)
    mod_ref_erow.pack(fill="x", pady=(0, 2))

    _band_label(mod_ref_lrow, "Module Ref / Master ID", _C_MOD, _F)

    module_ref_cell = tk.Frame(mod_ref_erow, bg=_C_MOD)
    module_ref_cell.pack(side="left", fill="x", expand=True)

    # Plain entry - disabled placeholder when Module Type is NONE
    module_ref_entry = tk.Entry(module_ref_cell, width=50, font=_F)
    module_ref_entry.pack(side="left")
    apply_entry_theme(module_ref_entry, is_readonly=True)
    module_ref_entry.config(state="disabled")
    bind_tooltip(
        module_ref_entry,
        tooltip_var,
        "Not required when Module Type is NONE. Select a Module Type above to choose from a dropdown.",
    )

    # FD sub-frame
    fd_cell = tk.Frame(module_ref_cell, bg=_C_MOD)
    fd_combo = ttk.Combobox(fd_cell, width=40)
    fd_combo.pack(side="left", padx=(0, 6))
    apply_entry_theme(fd_combo)
    bind_tooltip(fd_combo, tooltip_var, "Select an active Fixed Deposit product.")

    def _rebuild_fd_combo():
        nonlocal fd_map
        fd_rows = get_active_fd_masters()
        fd_map = {r[1]: r[0] for r in fd_rows}
        fd_combo["values"] = list(fd_map.keys())
        progressive_selection(fd_combo, list(fd_map.keys()))

    # CC sub-frame
    cc_cell = tk.Frame(module_ref_cell, bg=_C_MOD)
    cc_combo = ttk.Combobox(cc_cell, width=40)
    cc_combo.pack(side="left", padx=(0, 6))
    apply_entry_theme(cc_combo)
    bind_tooltip(cc_combo, tooltip_var, "Select an active Credit Card.")

    def _rebuild_cc_combo():
        nonlocal cc_map
        cc_rows = _db_get_all_card_masters()
        cc_map = {f"{r[1]} ({str(r[2])[-4:] if r[2] else 'N/A'})": r[0] for r in cc_rows}
        cc_combo["values"] = list(cc_map.keys())
        progressive_selection(cc_combo, list(cc_map.keys()))

    # PPF sub-frame
    ppf_cell = tk.Frame(module_ref_cell, bg=_C_MOD)
    ppf_combo = ttk.Combobox(ppf_cell, width=40)
    ppf_combo.pack(side="left", padx=(0, 6))
    apply_entry_theme(ppf_combo)
    bind_tooltip(ppf_combo, tooltip_var, "Select an active PPF Account.")

    def _rebuild_ppf_combo():
        nonlocal ppf_map
        ppf_rows = get_all_ppf_masters()
        ppf_map = {
            f"{r[1]} - {r[2]} ({'Active' if r[4] else 'Closed'})": r[0] for r in ppf_rows
        }
        ppf_combo["values"] = list(ppf_map.keys())
        progressive_selection(ppf_combo, list(ppf_map.keys()))

    # LOAN sub-frame
    loan_cell = tk.Frame(module_ref_cell, bg=_C_MOD)
    loan_combo = ttk.Combobox(loan_cell, width=40)
    loan_combo.pack(side="left", padx=(0, 6))
    apply_entry_theme(loan_combo)
    bind_tooltip(loan_combo, tooltip_var, "Select an active Loan Account.")

    def _rebuild_loan_combo():
        nonlocal loan_map
        loan_rows = get_all_loan_masters_for_display()
        loan_map = {
            f"{r[1]} [{r[2]}] - {r[5]}": r[0] for r in loan_rows
        }
        loan_combo["values"] = list(loan_map.keys())
        progressive_selection(loan_combo, list(loan_map.keys()))

    # STOCK_COMP sub-frame
    stock_comp_cell = tk.Frame(module_ref_cell, bg=_C_MOD)
    stock_comp_combo = ttk.Combobox(stock_comp_cell, width=52)
    stock_comp_combo.pack(side="left", padx=(0, 6))
    apply_entry_theme(stock_comp_combo)
    bind_tooltip(stock_comp_combo, tooltip_var, "Select a Computed Bank Entry from StockMan.")

    def _rebuild_stock_comp_combo():
        nonlocal stock_comp_map
        rows = get_stock_computed_bank_entries()
        stock_comp_map = {
            f"#{r[0]} | {r[1]} | {r[2]} ?{r[3]:.2f} | {r[4] or ''} {r[5] or ''}".strip(): r[0]
            for r in rows
        }
        stock_comp_combo["values"] = list(stock_comp_map.keys())
        progressive_selection(stock_comp_combo, list(stock_comp_map.keys()))

    # STOCK_ACTU sub-frame
    stock_actu_cell = tk.Frame(module_ref_cell, bg=_C_MOD)
    stock_actu_combo = ttk.Combobox(stock_actu_cell, width=44)
    stock_actu_combo.pack(side="left", padx=(0, 6))
    apply_entry_theme(stock_actu_combo)
    bind_tooltip(stock_actu_combo, tooltip_var, "Select an Actual Bank Entry from StockMan.")

    def _rebuild_stock_actu_combo():
        nonlocal stock_actu_map
        rows = get_stock_actual_bank_entries()
        stock_actu_map = {
            f"#{r[0]} | {r[1]} | {r[2]} ?{r[3]:.2f} | {r[4] or ''}".strip(): r[0]
            for r in rows
        }
        stock_actu_combo["values"] = list(stock_actu_map.keys())
        progressive_selection(stock_actu_combo, list(stock_actu_map.keys()))

    # MF sub-frame
    mf_cell = tk.Frame(module_ref_cell, bg=_C_MOD)
    mf_combo = ttk.Combobox(mf_cell, width=44)
    mf_combo.pack(side="left", padx=(0, 6))
    apply_entry_theme(mf_combo)
    bind_tooltip(mf_combo, tooltip_var, "Select an active Mutual Fund folio.")

    def _rebuild_mf_combo():
        nonlocal mf_map
        rows = get_active_mf_masters()
        mf_map = {
            f"{r[1]} | {r[4]} [Folio: {r[3]} - {r[2]}]": r[0]
            for r in rows
        }
        mf_combo["values"] = list(mf_map.keys())
        progressive_selection(mf_combo, list(mf_map.keys()))

    # INS sub-frame
    ins_cell = tk.Frame(module_ref_cell, bg=_C_MOD)
    ins_combo = ttk.Combobox(ins_cell, width=44)
    ins_combo.pack(side="left", padx=(0, 6))
    apply_entry_theme(ins_combo)
    bind_tooltip(ins_combo, tooltip_var, "Select an active Insurance policy.")

    def _rebuild_ins_combo():
        nonlocal ins_map
        rows = get_active_ins_masters()
        ins_map = {
            f"{r[1]} ({r[2]}) | Pol: {r[3]} | Assured: {r[6]}": r[0]
            for r in rows
        }
        ins_combo["values"] = list(ins_map.keys())
        progressive_selection(ins_combo, list(ins_map.keys()))

    def _on_module_type_change(*_):
        module_ref_entry.pack_forget()
        fd_cell.pack_forget()
        cc_cell.pack_forget()
        ppf_cell.pack_forget()
        loan_cell.pack_forget()
        stock_comp_cell.pack_forget()
        stock_actu_cell.pack_forget()
        mf_cell.pack_forget()
        ins_cell.pack_forget()

        mt = module_type_var.get()
        if mt == "FD":
            _rebuild_fd_combo()
            fd_cell.pack(side="left")
            if initial_fd_number and initial_fd_number in fd_combo["values"]:
                fd_combo.set(initial_fd_number)
            elif fd_combo["values"]:
                fd_combo.set(fd_combo["values"][0])
        elif mt == "CC":
            _rebuild_cc_combo()
            cc_cell.pack(side="left")
            if initial_cc_label and initial_cc_label in cc_combo["values"]:
                cc_combo.set(initial_cc_label)
            elif cc_combo["values"]:
                cc_combo.set(cc_combo["values"][0])
        elif mt == "PPF":
            _rebuild_ppf_combo()
            ppf_cell.pack(side="left")
            if initial_ppf_label and initial_ppf_label in ppf_combo["values"]:
                ppf_combo.set(initial_ppf_label)
            elif ppf_combo["values"]:
                ppf_combo.set(ppf_combo["values"][0])
        elif mt == "LOAN":
            _rebuild_loan_combo()
            loan_cell.pack(side="left")
            if initial_loan_label and initial_loan_label in loan_combo["values"]:
                loan_combo.set(initial_loan_label)
            elif loan_combo["values"]:
                loan_combo.set(loan_combo["values"][0])
        elif mt == "STOCK_COMP":
            _rebuild_stock_comp_combo()
            stock_comp_cell.pack(side="left")
            if initial_stock_comp_label and initial_stock_comp_label in stock_comp_combo["values"]:
                stock_comp_combo.set(initial_stock_comp_label)
            elif stock_comp_combo["values"]:
                stock_comp_combo.set(stock_comp_combo["values"][0])
        elif mt == "STOCK_ACTU":
            _rebuild_stock_actu_combo()
            stock_actu_cell.pack(side="left")
            if initial_stock_actu_label and initial_stock_actu_label in stock_actu_combo["values"]:
                stock_actu_combo.set(initial_stock_actu_label)
            elif stock_actu_combo["values"]:
                stock_actu_combo.set(stock_actu_combo["values"][0])
        elif mt == "MF":
            _rebuild_mf_combo()
            mf_cell.pack(side="left")
            if initial_mf_label and initial_mf_label in mf_combo["values"]:
                mf_combo.set(initial_mf_label)
            elif mf_combo["values"]:
                mf_combo.set(mf_combo["values"][0])
        elif mt == "INS":
            _rebuild_ins_combo()
            ins_cell.pack(side="left")
            if initial_ins_label and initial_ins_label in ins_combo["values"]:
                ins_combo.set(initial_ins_label)
            elif ins_combo["values"]:
                ins_combo.set(ins_combo["values"][0])
        else:
            module_ref_entry.pack(side="left")

    module_type_var.trace_add("write", _on_module_type_change)
    win.after(10, _on_module_type_change)

    # ── Warning label ─────────────────────────────────────────────────────
    warn_frame = tk.Frame(win, bg="#FEF3C7", relief="ridge", bd=1)
    warn_frame.pack(fill="x", padx=12, pady=(2, 2))

    tk.Label(
        warn_frame,
        text=(
            "ℹ  Cascading effects (downstream balances, pair links, and sub-ledger dates/amounts) are synced automatically.\n"
            "⚠  If you change Module Type, the old sub-ledger row is NOT touched — please fix it manually if needed."
        ),
        font=("Helvetica", 10, "bold"),
        bg="#FEF3C7",
        fg="#92400E",
        justify="left",
    ).pack(anchor="w", padx=10, pady=4)

    # ── Button bar ────────────────────────────────────────────────────────
    btn_frame = tk.Frame(win, bg=_THEME["main_bg"], relief="ridge", bd=2, pady=6)
    btn_frame.pack(fill="x", padx=12, pady=(4, 6))

    # ── Save handler ──────────────────────────────────────────────────────
    def on_save(_event=None) -> None:
        try:
            v_date = value_dt.get_date().strftime("%Y-%m-%d")
        except Exception:
            show_colorful_error(win, "Validation Error", "Value Date is invalid.")
            flash_error(value_dt)
            return

        try:
            t_date = trans_dt.get_date().strftime("%Y-%m-%d")
        except Exception:
            show_colorful_error(win, "Validation Error", "Transaction Date is invalid.")
            flash_error(trans_dt)
            return

        sn_raw = serial_no_entry.get().strip()
        serial_no_val = int(sn_raw) if sn_raw else None

        cheque_val = cheque_no_entry.get().strip() or None
        bank_remark_val = bank_remark_entry.get().strip() or None
        user_desc_val = user_desc_combo.get().strip() or None

        try:
            w_amt = float(withdrawal_entry.get().strip().replace(",", "") or "0")
            if w_amt < 0:
                raise ValueError
        except ValueError:
            show_colorful_error(win, "Validation Error", "Withdrawal must be a non-negative number.")
            flash_error(withdrawal_entry)
            return

        try:
            d_amt = float(deposit_entry.get().strip().replace(",", "") or "0")
            if d_amt < 0:
                raise ValueError
        except ValueError:
            show_colorful_error(win, "Validation Error", "Deposit must be a non-negative number.")
            flash_error(deposit_entry)
            return

        if w_amt == 0.0 and d_amt == 0.0:
            show_colorful_error(win, "Validation Error", "At least one of Withdrawal or Deposit must be non-zero.")
            flash_error(withdrawal_entry)
            return

        entry_type = entry_type_var.get()
        if entry_type == "INCOME" and (d_amt <= 0 or w_amt != 0.0):
            show_colorful_error(win, "Validation Error", "INCOME requires Deposit > 0 and Withdrawal = 0.")
            flash_error(deposit_entry)
            return
        elif entry_type == "EXPENSE" and (w_amt <= 0 or d_amt != 0.0):
            show_colorful_error(win, "Validation Error", "EXPENSE requires Withdrawal > 0 and Deposit = 0.")
            flash_error(withdrawal_entry)
            return

        try:
            bal = float(balance_entry.get().strip().replace(",", "") or "0")
            if bal < 0:
                raise ValueError
        except ValueError:
            show_colorful_error(win, "Validation Error", "Balance must be a non-negative number.")
            flash_error(balance_entry)
            return

        pair_raw = pair_id_var.get().strip()
        pair_id_val = int(pair_raw) if pair_raw else None

        bh_name = budget_head_combo.get().strip()
        bh_id_val = budget_map.get(bh_name)

        new_module_type = module_type_var.get()
        master_id = None

        # Resolve master_id based on module type
        if new_module_type == "FD":
            fd_num = fd_combo.get().strip()
            if not fd_num or fd_num not in fd_map:
                show_colorful_error(win, "Validation Error", "Please select a valid FD.")
                return
            master_id = fd_map[fd_num]
        elif new_module_type == "CC":
            cc_lbl = cc_combo.get().strip()
            if not cc_lbl or cc_lbl not in cc_map:
                show_colorful_error(win, "Validation Error", "Please select a valid Credit Card.")
                return
            master_id = cc_map[cc_lbl]
        elif new_module_type == "PPF":
            ppf_lbl = ppf_combo.get().strip()
            if not ppf_lbl or ppf_lbl not in ppf_map:
                show_colorful_error(win, "Validation Error", "Please select a valid PPF Account.")
                return
            master_id = ppf_map[ppf_lbl]
        elif new_module_type == "LOAN":
            loan_lbl = loan_combo.get().strip()
            if not loan_lbl or loan_lbl not in loan_map:
                show_colorful_error(win, "Validation Error", "Please select a valid Loan Account.")
                return
            master_id = loan_map[loan_lbl]
        elif new_module_type == "STOCK_COMP":
            stock_lbl = stock_comp_combo.get().strip()
            if not stock_lbl or stock_lbl not in stock_comp_map:
                show_colorful_error(win, "Validation Error", "Please select a Computed Bank entry.")
                return
            master_id = stock_comp_map[stock_lbl]
        elif new_module_type == "STOCK_ACTU":
            stock_lbl = stock_actu_combo.get().strip()
            if not stock_lbl or stock_lbl not in stock_actu_map:
                show_colorful_error(win, "Validation Error", "Please select an Actual Bank entry.")
                return
            master_id = stock_actu_map[stock_lbl]
        elif new_module_type == "MF":
            mf_lbl = mf_combo.get().strip()
            if not mf_lbl or mf_lbl not in mf_map:
                show_colorful_error(win, "Validation Error", "Please select a valid Mutual Fund.")
                return
            master_id = mf_map[mf_lbl]
        elif new_module_type == "INS":
            ins_lbl = ins_combo.get().strip()
            if not ins_lbl or ins_lbl not in ins_map:
                show_colorful_error(win, "Validation Error", "Please select a valid Insurance policy.")
                return
            master_id = ins_map[ins_lbl]
        elif new_module_type != "NONE":
            ref_raw = module_ref_entry.get().strip()
            if not ref_raw:
                show_colorful_error(win, "Validation Error", "Master ID is required for sub-ledgers.")
                return
            master_id = int(ref_raw)

        # Handle Sub-Ledger Creation if module_type changed
        module_ref_id_val = data["module_ref_id"]
        if new_module_type != data["module_type"]:
            try:
                with get_db_connection(BANK_DB_PATH) as conn:
                    module_ref_id_val = _create_subledger_row(
                        conn,
                        new_module_type,
                        master_id,
                        data["account_id"],
                        t_date,
                        w_amt,
                        d_amt,
                        bank_remark_val,
                    )
                    conn.commit()
            except sqlite3.Error as exc:
                show_colorful_error(win, "Database Error", f"Failed to create subledger row: {exc}")
                return

        # Perform cascades and save transaction
        try:
            cascades = db_update_bank_transaction(
                trans_id,
                serial_no=serial_no_val,
                value_date=v_date,
                trans_date=t_date,
                cheque_no=cheque_val,
                bank_desc=bank_remark_val,
                user_desc=user_desc_val,
                withdrawal_amount=w_amt,
                deposit_amount=d_amt,
                balance_after=bal,
                pair_id=pair_id_val,
                bh_id=bh_id_val,
                module_type=new_module_type,
                module_ref_id=module_ref_id_val,
                entry_type=entry_type,
                old_withdrawal=data["withdrawal_amount"] or 0.0,
                old_deposit=data["deposit_amount"] or 0.0,
                old_trans_date=data["trans_date"],
                old_pair_id=data["pair_id"],
                old_module_type=data["module_type"],
                old_module_ref_id=data["module_ref_id"],
                account_id=data["account_id"],
            )
        except sqlite3.Error as exc:
            show_colorful_error(win, "Database Error", f"Failed to save changes:\n{exc}")
            return

        # Build cascade messages
        lines = [f"Transaction #{trans_id} updated successfully."]
        n = cascades.get("balance_rows_adjusted", 0)
        if n:
            lines.append(f"  • {n} downstream balance row(s) recalculated.")
        if cascades.get("old_pair_unlinked"):
            lines.append(f"  • Old pair partner (#{data['pair_id']}) was unlinked.")
        if cascades.get("new_pair_linked"):
            lines.append(f"  • New pair partner (#{pair_id_val}) was linked back.")
        if cascades.get("subledger_updated"):
            mod = cascades.get("subledger_module", "")
            lines.append(f"  • {mod} sub-ledger row #{module_ref_id_val} date/amount synced.")
        if cascades.get("subledger_module_changed"):
            old_mod = data["module_type"] or "NONE"
            lines.append(
                f"  ⚠  Module type changed from {old_mod} — old sub-ledger row was NOT modified. Update it manually if needed."
            )

        # Check for TRANSFER auto-pairing
        if entry_type == "TRANSFER" and not pair_id_val and new_module_type == "NONE":
            do_auto_fill = show_colorful_yesno(
                win,
                "Transfer Saved",
                "Transaction updated successfully!\n\nWould you like to auto-fill the receiving side of this transfer?",
            )
            if do_auto_fill:
                cleanup_and_close()
                from .bank_transactions_add import add_bank_transaction_main
                parent.after(50, lambda: add_bank_transaction_main(
                    parent,
                    prefill_pair_id=trans_id,
                    prefill_withdrawal=d_amt,
                    prefill_deposit=w_amt,
                    prefill_val_date=v_date,
                    prefill_trans_date=t_date,
                    prefill_serial=serial_no_val,
                    prefill_cheque=cheque_val,
                    prefill_bank_desc=bank_remark_val,
                    prefill_user_desc=user_desc_val,
                    prefill_bh_id=bh_id_val,
                ))
                return

        show_colorful_info(win, "Saved", "\n".join(lines))
        cleanup_and_close()

    submit_button = tk.Button(
        btn_frame,
        text="💾  SAVE CHANGES  💾",
        command=on_save,
        font=("Comic Sans MS", 12, "bold"),
        bg=_THEME["submit_bg"],
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
        bg=_THEME["cancel_bg"],
        fg="white",
        activeforeground="white",
        relief="raised",
        bd=3,
        padx=8,
        pady=4,
        cursor="hand2",
    )
    cancel_btn.pack(side="right", padx=4)

    apply_button_animations(submit_button, _THEME["submit_bg"], _THEME["submit_hover_bg"])
    apply_button_animations(cancel_btn, _THEME["cancel_bg"], _THEME["cancel_hover_bg"])

    # ── Keyboard and traversal bindings ───────────────────────────────────
    win.bind("<F1>", lambda e: None if getattr(e, "state", 0) & 0x0004 else show_edit_help(win))
    win.bind("<Control-Return>", lambda e: submit_button.invoke())
    win.bind("<Escape>", cleanup_and_close)
    win.protocol("WM_DELETE_WINDOW", cleanup_and_close)

    serial_no_entry.bind("<Return>", lambda e: value_dt.focus_set())
    value_dt.bind("<Return>", lambda e: trans_dt.focus_set())
    trans_dt.bind("<Return>", lambda e: cheque_no_entry.focus_set())
    cheque_no_entry.bind("<Return>", lambda e: bank_remark_entry.focus_set())
    bank_remark_entry.bind("<Return>", lambda e: withdrawal_entry.focus_set())
    withdrawal_entry.bind("<Return>", lambda e: deposit_entry.focus_set())
    deposit_entry.bind("<Return>", lambda e: balance_entry.focus_set())
    balance_entry.bind("<Return>", lambda e: pair_id_display.focus_set())
    pair_id_display.bind("<Return>", lambda e: budget_head_combo.focus_set())
    budget_head_combo.bind("<Return>", lambda e: user_desc_combo.focus_set())
    user_desc_combo.bind("<Return>", lambda e: et_radios[0].focus_set())
    module_ref_entry.bind("<Return>", lambda e: submit_button.focus_set())
    fd_combo.bind("<Return>", lambda e: submit_button.focus_set())
    submit_button.bind("<Return>", lambda e: on_save())

    # Give focus to the first field.
    serial_no_entry.focus_set()

    parent.wait_window(win)

    # Restore grab so caller remains in focus
    try:
        if parent.winfo_exists():
            try:
                parent.grab_set()
            except Exception:
                pass
    except tk.TclError:
        pass



def show_edit_help(win: tk.Toplevel) -> None:
    guide_lines = [
        "This form allows you to edit a previously saved bank transaction.",
        "",
        "Fields:",
        "  Account      - Locked. You cannot change the account on edit.",
        "  Amounts      - Modifying Withdrawal or Deposit will auto-recalculate downstream balances.",
        "  Dates        - Modifying dates will correctly reorder your ledger.",
        "  Module Type  - You can change the sub-ledger product type. For instance, linking an existing standalone entry to an FD.",
        "",
        "Cascading effects are handled automatically. Sub-ledger balances are updated seamlessly."
    ]

    faq_data = [
        (
            "What exactly happens to downstream balances when I change an amount?",
            "The system automatically scans all transactions in this account with a 'Trans Dt' strictly greater than this one. It applies the difference in balance forward, so you don't need to manually fix subsequent rows."
        ),
        (
            "What happens if I change the Pair ID or unlink a transfer?",
            "If you clear the Pair ID, the opposite partner transaction is automatically unlinked and becomes a standalone entry. If you assign a new Pair ID, the new partner is bi-directionally linked to this transaction."
        ),
        (
            "What happens to the sub-ledger if I change the Module Type?",
            "If you completely change the Module Type (e.g., from FD to CC), the old sub-ledger row (FD) is left as an orphaned record and must be manually deleted or fixed. If you keep the same Module Type but change the amounts or dates, the existing sub-ledger row is seamlessly updated in place."
        )
    ]

    def inject_budget_heads_tab(notebook):
        try:
            bh_rows = _db_get_bh_with_parents()
        except Exception as exc:
            logger.warning("budget heads fetch failed: %s", exc)
            bh_rows = []
            
        tab_budget = tk.Frame(notebook, bg="#f0f9ff")
        notebook.add(tab_budget, text="Budget Heads Reference")

        search_frame = tk.Frame(tab_budget, bg="#e0f2fe", pady=5)
        search_frame.pack(fill="x", padx=10, pady=(6, 0))
        tk.Label(search_frame, text="Search:", font=("Helvetica", 11, "bold"), bg="#e0f2fe", fg="#0369a1").pack(side="left", padx=(6, 4))
        
        search_var = tk.StringVar()
        search_entry = tk.Entry(search_frame, textvariable=search_var, font=("Helvetica", 12), width=32, bg="#fff", fg="#0c4a6e", insertbackground="#0369a1", relief="solid", bd=1)
        search_entry.pack(side="left", padx=4)

        clear_btn = tk.Button(search_frame, text="✕", font=("Helvetica", 10, "bold"), bg="#bae6fd", fg="#0369a1", cursor="hand2", relief="flat", padx=8)
        clear_btn.pack(side="left", padx=4)

        bh_text = tk.Text(tab_budget, wrap="none", font=("Consolas", 11), bg="#f8fafc", bd=0, padx=6, pady=6)
        bh_text.pack(fill="both", expand=True, padx=10, pady=(4, 10))
        bh_text.tag_configure("highlight", background="#fef08a", foreground="#b45309", font=("Consolas", 11, "bold"))
        
        def _render_bh():
            bh_text.config(state="normal")
            bh_text.delete("1.0", "end")
            bh_text.insert("end", f"{'ID':<6} | {'Budget Head':<35} | {'Parent'}\n", "header")
            bh_text.insert("end", "-"*80 + "\n")
            for r in bh_rows:
                bh_text.insert("end", f"{r[0]:<6} | {r[1]:<35} | {r[3] or ''}\n")
            bh_text.config(state="disabled")
            
        _render_bh()

        def _do_search(*_):
            q = search_var.get().strip().lower()
            bh_text.tag_remove("highlight", "1.0", "end")
            if not q: return
            start_idx = "1.0"
            while True:
                pos = bh_text.search(q, start_idx, stopindex="end", nocase=True)
                if not pos: break
                end_pos = f"{pos}+{len(q)}c"
                bh_text.tag_add("highlight", pos, end_pos)
                start_idx = end_pos

        search_var.trace_add("write", _do_search)
        clear_btn.config(command=lambda: search_var.set(""))

    show_standard_help(
        parent=win,
        title="Edit Bank Transaction Help",
        guide_lines=guide_lines,
        faq_data=faq_data,
        extra_tabs_callback=inject_budget_heads_tab
    )
