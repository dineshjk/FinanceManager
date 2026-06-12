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
from tkinter import font as tkfont
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
from Shared.globals import get_db_connection, BANK_DB_PATH, logger
from Shared.gui_progressive import progressive_selection
from .bank_db_utils import (
    db_update_bank_transaction,
    get_all_budget_heads,
    get_all_accounts,
    get_all_user_descriptions,
    get_active_fd_masters,
    _db_get_all_card_masters,
    _db_get_ppf_master_id,
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
    bh_type_map = {r[1]: r[2] for r in bh_rows}
    bh_id_to_name = {r[0]: r[1] for r in bh_rows}
    bh_values = ["(none)"] + [r[1] for r in bh_rows]

    fd_map: dict = {}  # fd_number → fd_master_id
    cc_map: dict = {}  # display_label → card_master_id

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

    # General entry
    module_ref_entry = tk.Entry(module_ref_cell, width=50, font=_F)
    module_ref_entry.insert(0, str(data["module_ref_id"]) if data["module_ref_id"] else "")
    module_ref_entry.pack(side="left")
    apply_entry_theme(module_ref_entry)
    bind_tooltip(module_ref_entry, tooltip_var, "Integer product ID. Leave blank if not required.")

    # FD cell
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

    # CC cell
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

    def _on_module_type_change(*_):
        if module_type_var.get() == "FD":
            module_ref_entry.pack_forget()
            cc_cell.pack_forget()
            _rebuild_fd_combo()
            fd_cell.pack(side="left")
            if initial_fd_number and initial_fd_number in fd_combo["values"]:
                fd_combo.set(initial_fd_number)
            elif fd_combo["values"]:
                fd_combo.set(fd_combo["values"][0])
        elif module_type_var.get() == "CC":
            module_ref_entry.pack_forget()
            fd_cell.pack_forget()
            _rebuild_cc_combo()
            cc_cell.pack(side="left")
            if initial_cc_label and initial_cc_label in cc_combo["values"]:
                cc_combo.set(initial_cc_label)
            elif cc_combo["values"]:
                cc_combo.set(cc_combo["values"][0])
        else:
            fd_cell.pack_forget()
            cc_cell.pack_forget()
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
            master_id = _db_get_ppf_master_id()
            if master_id is None:
                show_colorful_error(win, "Validation Error", "No active PPF master found.")
                return
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
            parent.grab_set()
    except tk.TclError:
        pass
