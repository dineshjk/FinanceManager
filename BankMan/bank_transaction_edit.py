# -*- coding: utf-8 -*-
# BankMan/bank_transaction_edit.py

"""
Edit-form for a single ``bank_transactions`` row.

Opened from the Bank Transactions Manager when the user clicks
"✏️ Edit Selected".  The form is pre-populated with the selected row's
current values; every editable column is exposed as a widget.

Columns intentionally excluded from editing
-------------------------------------------
* ``trans_id``   — primary key, immutable.
* ``account_id`` — changing would corrupt balance chains in two accounts.

Balance recalculation
---------------------
If withdrawal_amount or deposit_amount is changed the net effect on the
running balance changes.  ``db_update_bank_transaction`` automatically
adjusts every subsequent row in the same account so the balance chain
remains consistent.

Cascading effects applied automatically
---------------------------------------
* Downstream ``balance_after`` values for the same account are
  recalculated when withdrawal / deposit amounts change.
* The paired transfer row (``pair_id``) is re-linked when the pair
  assignment is modified.
* The linked sub-ledger row (FD / CC / Loan / PPF) has its date and
  primary amount columns updated to stay in sync when ``module_type``
  is unchanged.  CC sub-ledger ``bh_id`` is always synced.
* If ``module_type`` itself changes, the *old* sub-ledger row is left
  untouched — the user is warned to fix it manually.

Theme
-----
``BANK_TRANSACTION_EDIT_UI_THEME`` — deep indigo / lavender — is visually
opposite to the warm amber/peach of ``BANK_TRANSACTION_ADD_UI_THEME``,
making edit windows immediately distinguishable from add windows.
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
    BANK_TRANSACTION_EDIT_UI_THEME as _THEME,
    bind_tooltip,
    flash_error,
    setup_footer_tooltip,
    bind_date_spin,
)
from Shared.dialog_utils import show_colorful_error, show_colorful_info
from Shared.modal_utils import disable_parent
from Shared.window_manager import push_window, safe_close_modal
from Shared.globals import get_db_connection, BANK_DB_PATH, logger
from Shared.gui_progressive import progressive_selection
from .bank_db_utils import (
    db_update_bank_transaction,
    get_all_budget_heads,
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


def _band_label(parent, text, bg, font=("Helvetica", 13), padx=0, fg="#1e293b"):
    tk.Label(parent, text=text, font=font, bg=bg, fg="#1e293b", anchor="w").pack(
        side="left", padx=(padx, 12)
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def edit_bank_transaction(
    parent: Union[tk.Toplevel, tk.Tk],
    trans_id: int,
    calling_button: tk.Widget | None = None,
) -> None:
    """Open a modal edit form pre-populated with the selected transaction.

    Parameters
    ----------
    parent:
        Owning window (the Bank Transactions Manager).
    trans_id:
        Primary key of the ``bank_transactions`` row to edit.
    calling_button:
        The button that opened this modal (disabled while open).
    """

    # ── Fetch current data ────────────────────────────────────────────────
    data = _fetch_transaction(trans_id)
    if data is None:
        show_colorful_error(
            parent,
            "Load Error",
            f"Could not load transaction #{trans_id} from the database.",
        )
        return

    # ── Budget head lookup ────────────────────────────────────────────────
    bh_rows = sorted(get_all_budget_heads(), key=lambda r: r[1])
    bh_id_to_name = {r[0]: r[1] for r in bh_rows}
    bh_name_to_id = {r[1]: r[0] for r in bh_rows}
    bh_values = ["(none)"] + [r[1] for r in bh_rows]

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

    # Footer tooltip — must be packed FIRST (anchors to absolute bottom).
    tooltip_var = setup_footer_tooltip(win)

    def cleanup_and_close(_event=None):
        return safe_close_modal(win, parent, calling_button)

    # ── Header ────────────────────────────────────────────────────────────
    hdr = tk.Frame(win, bg=_THEME["header_bg"], relief="raised", bd=3)
    hdr.pack(fill="x", padx=5, pady=5)

    tk.Label(
        hdr,
        text=f"✏️   Edit Bank Transaction   #{trans_id}   ✏️",
        font=_FH,
        bg=_THEME["header_bg"],
        fg=_THEME["header_fg"],
        relief="ridge",
        bd=2,
    ).pack(fill="x", pady=8)

    # ── Main form ─────────────────────────────────────────────────────────
    form_body = tk.Frame(win, bg=_THEME["main_bg"])
    form_body.pack(fill="x", padx=12, pady=4)

    _C_BAND = _THEME["main_bg"]
    _L_FG = "#1e293b"

    # ── Band 1: Reference & Dates ─────────────────────────────────────────
    band1, lrow1, erow1 = _make_band(form_body, _C_BAND)
    band1.pack(fill="x", pady=(0, 4))

    _band_label(lrow1, "Account", _C_BAND, _F, fg=_L_FG)
    _band_label(lrow1, "Sr No.", _C_BAND, _F, padx=230, fg=_L_FG)
    _band_label(lrow1, "Cheque No", _C_BAND, _F, padx=20, fg=_L_FG)
    _band_label(lrow1, "Value Dt", _C_BAND, _F, padx=20, fg=_L_FG)
    _band_label(lrow1, "Trans Dt", _C_BAND, _F, padx=90, fg=_L_FG)

    acct_var = tk.StringVar(value=data["account_label"])
    acct_entry = tk.Entry(erow1, textvariable=acct_var, width=25, font=_F, state="readonly")
    acct_entry.pack(side="left", padx=(0, 20))
    apply_entry_theme(acct_entry, is_readonly=True)
    bind_tooltip(
        acct_entry,
        tooltip_var,
        "The bank account for this transaction (read-only).",
    )

    serial_var = tk.StringVar(value=str(data["serial_no"]) if data["serial_no"] else "")
    serial_entry = tk.Entry(erow1, textvariable=serial_var, width=5, font=_F)
    serial_entry.pack(side="left", padx=(0, 20))
    apply_entry_theme(serial_entry)
    bind_tooltip(
        serial_entry,
        tooltip_var,
        "Optional bank serial / reference number. Leave blank for NULL.",
    )

    cheque_var = tk.StringVar(value=data["cheque_no"] or "")
    cheque_entry = tk.Entry(erow1, textvariable=cheque_var, width=10, font=_F)
    cheque_entry.pack(side="left", padx=(0, 20))
    apply_entry_theme(cheque_entry)
    bind_tooltip(
        cheque_entry, tooltip_var, "Cheque number for cheque-based transactions."
    )

    value_dt = DateEntry(erow1, date_pattern="dd-mm-yyyy", width=14, font=_F)
    value_dt.set_date(
        datetime.strptime(
            data["value_date"] or datetime.today().strftime("%Y-%m-%d"), "%Y-%m-%d"
        )
    )
    value_dt.pack(side="left", padx=(0, 20))
    apply_entry_theme(value_dt)
    bind_tooltip(
        value_dt,
        tooltip_var,
        "Value date — bank effective date for interest calculation.",
    )

    trans_dt = DateEntry(erow1, date_pattern="dd-mm-yyyy", width=14, font=_F)
    trans_dt.set_date(
        datetime.strptime(
            data["trans_date"] or datetime.today().strftime("%Y-%m-%d"), "%Y-%m-%d"
        )
    )
    trans_dt.pack(side="left")
    apply_entry_theme(trans_dt)
    bind_tooltip(
        trans_dt,
        tooltip_var,
        "Transaction date — calendar date the event was initiated.",
    )

    bind_date_spin(value_dt)
    bind_date_spin(trans_dt)

    # ── Band 2: Remarks ───────────────────────────────────────────────────
    band2, lrow2, erow2 = _make_band(form_body, _C_BAND)
    band2.pack(fill="x", pady=(0, 4))

    _band_label(lrow2, "Bank Remark", _C_BAND, _F, fg=_L_FG)

    bank_remark_var = tk.StringVar(value=data["bank_desc"] or "")
    bank_remark_entry = tk.Entry(erow2, textvariable=bank_remark_var, width=60, font=_F)
    bank_remark_entry.pack(side="left")
    apply_entry_theme(bank_remark_entry)
    bind_tooltip(
        bank_remark_entry, tooltip_var, "Narration as printed on the bank statement."
    )

    # ── Band 3: Amounts ───────────────────────────────────────────────────
    band3, lrow3, erow3 = _make_band(form_body, _C_BAND)
    band3.pack(fill="x", pady=(0, 4))

    _band_label(lrow3, "Withdrawal", _C_BAND, _F, fg=_L_FG)
    _band_label(lrow3, "Deposit", _C_BAND, _F, padx=45, fg=_L_FG)
    _band_label(lrow3, "Balance", _C_BAND, _F, padx=70, fg=_L_FG)
    _band_label(lrow3, "Pair ID", _C_BAND, _F, padx=80, fg=_L_FG)
    _band_label(lrow3, "Budget Head", _C_BAND, _F, padx=190, fg=_L_FG)

    def _fmt(v) -> str:
        try:
            return f"{float(v):.2f}"
        except (TypeError, ValueError):
            return "0.00"

    withdrawal_var = tk.StringVar(value=_fmt(data["withdrawal_amount"]))
    withdrawal_entry = tk.Entry(erow3, textvariable=withdrawal_var, width=11, font=_FB)
    withdrawal_entry.pack(side="left", padx=(0, 30))
    apply_entry_theme(withdrawal_entry)
    bind_tooltip(
        withdrawal_entry,
        tooltip_var,
        "Amount leaving the account (debit). Use 0.00 if N/A.",
    )

    deposit_var = tk.StringVar(value=_fmt(data["deposit_amount"]))
    deposit_entry = tk.Entry(erow3, textvariable=deposit_var, width=11, font=_FB)
    deposit_entry.pack(side="left", padx=(0, 30))
    apply_entry_theme(deposit_entry)
    bind_tooltip(
        deposit_entry,
        tooltip_var,
        "Amount entering the account (credit). Use 0.00 if N/A.",
    )

    balance_var = tk.StringVar(value=_fmt(data["balance_after"]))
    balance_entry = tk.Entry(erow3, textvariable=balance_var, width=11, font=_FB)
    balance_entry.pack(side="left", padx=(0, 30))
    apply_entry_theme(balance_entry)
    bind_tooltip(
        balance_entry,
        tooltip_var,
        "Running account balance immediately after this transaction.",
    )

    pair_var = tk.StringVar(value=str(data["pair_id"]) if data["pair_id"] else "")
    pair_entry = tk.Entry(erow3, textvariable=pair_var, width=14, font=_F)
    pair_entry.pack(side="left", padx=(0, 84))
    apply_entry_theme(pair_entry)
    bind_tooltip(
        pair_entry,
        tooltip_var,
        "Pair ID linking this row to its transfer counterpart (leave blank for none).",
    )

    bh_combo = ttk.Combobox(erow3, width=15, values=bh_values, font=_F)
    current_bh_name = bh_id_to_name.get(data["bh_id"], "(none)")
    bh_combo.set(current_bh_name)
    bh_combo.pack(side="left")
    apply_entry_theme(bh_combo)
    progressive_selection(bh_combo, bh_values)
    bind_tooltip(
        bh_combo, tooltip_var, "Budget category for expense / income analysis reports."
    )

    # ── Band 4: Module Linkage ────────────────────────────────────────────
    mod_band = tk.Frame(form_body, bg=_C_BAND, relief="ridge", bd=2, padx=10, pady=6)
    mod_band.pack(fill="x", pady=(0, 4))

    entry_type_lrow = tk.Frame(mod_band, bg=_C_BAND)
    entry_type_lrow.pack(fill="x", pady=(0, 2))
    entry_type_erow = tk.Frame(mod_band, bg=_C_BAND)
    entry_type_erow.pack(fill="x", pady=(0, 6))

    _band_label(entry_type_lrow, "Entry Type", _C_BAND, _F, fg=_L_FG)
    _band_label(entry_type_lrow, "User Desc", _C_BAND, _F, padx=250, fg=_L_FG)

    entry_type_var = tk.StringVar(value=data["entry_type"] or "TRANSFER")
    for et in _ENTRY_TYPES:
        tk.Radiobutton(
            entry_type_erow,
            text=et,
            variable=entry_type_var,
            value=et,
            font=("Helvetica", 11),
            bg=_C_BAND,
            activebackground=_THEME["hover_bg"],
            selectcolor=_THEME["focus_bg"],
            fg=_L_FG,
        ).pack(side="left", padx=8)

    user_desc_var = tk.StringVar(value=data["user_desc"] or "")
    user_desc_entry = tk.Entry(entry_type_erow, textvariable=user_desc_var, width=60, font=_F)
    user_desc_entry.pack(side="left", padx=(20, 0))
    apply_entry_theme(user_desc_entry)
    bind_tooltip(
        user_desc_entry,
        tooltip_var,
        "Your own note or personal description for this transaction.",
    )

    mod_type_lrow = tk.Frame(mod_band, bg=_C_BAND)
    mod_type_lrow.pack(fill="x", pady=(0, 2))
    mod_type_erow = tk.Frame(mod_band, bg=_C_BAND)
    mod_type_erow.pack(fill="x", pady=(0, 6))

    _band_label(mod_type_lrow, "Module Type", _C_BAND, _F, fg=_L_FG)

    current_mt = data["module_type"] or "NONE"
    module_type_var = tk.StringVar(value=current_mt)
    for mt in _MODULE_TYPES[:4]:
        tk.Radiobutton(
            mod_type_erow,
            text=mt,
            variable=module_type_var,
            value=mt,
            font=("Helvetica", 10),
            bg=_C_BAND,
            activebackground=_THEME["hover_bg"],
            selectcolor=_THEME["focus_bg"],
            fg=_L_FG,
        ).pack(side="left", padx=4)

    tk.Frame(mod_type_erow, bg=_C_BAND, width=20).pack(side="left")
    for mt in _MODULE_TYPES[4:]:
        tk.Radiobutton(
            mod_type_erow,
            text=mt,
            variable=module_type_var,
            value=mt,
            font=("Helvetica", 10),
            bg=_C_BAND,
            activebackground=_THEME["hover_bg"],
            selectcolor=_THEME["focus_bg"],
            fg=_L_FG,
        ).pack(side="left", padx=4)

    mod_ref_lrow = tk.Frame(mod_band, bg=_C_BAND)
    mod_ref_lrow.pack(fill="x", pady=(0, 2))
    mod_ref_erow = tk.Frame(mod_band, bg=_C_BAND)
    mod_ref_erow.pack(fill="x", pady=(0, 2))

    _band_label(mod_ref_lrow, "Module Ref / Master ID", _C_BAND, _F, fg=_L_FG)

    mod_ref_var = tk.StringVar(
        value=str(data["module_ref_id"]) if data["module_ref_id"] else ""
    )
    mod_ref_entry = tk.Entry(mod_ref_erow, textvariable=mod_ref_var, width=50, font=_F)
    mod_ref_entry.pack(side="left")
    apply_entry_theme(mod_ref_entry)
    bind_tooltip(
        mod_ref_entry,
        tooltip_var,
        "Integer product ID for the linked sub-ledger row (FD, CC, Loan, PPF etc.). Leave blank for NONE.",
    )

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
        # — Dates —
        try:
            v_date = value_dt.get_date().strftime("%Y-%m-%d")
        except Exception:
            show_colorful_error(win, "Validation", "Value Date is invalid.")
            flash_error(value_dt)
            return
        try:
            t_date = trans_dt.get_date().strftime("%Y-%m-%d")
        except Exception:
            show_colorful_error(win, "Validation", "Trans Date is invalid.")
            flash_error(trans_dt)
            return

        # — Serial No —
        sn_raw = serial_var.get().strip()
        if sn_raw:
            if not sn_raw.isdigit():
                show_colorful_error(
                    win, "Validation", "Serial No must be a whole number."
                )
                flash_error(serial_entry)
                return
            serial_no_val: int | None = int(sn_raw)
        else:
            serial_no_val = None

        # — Amounts —
        def _parse_amount(entry: tk.Entry, label: str) -> float | None:
            try:
                return float(entry.get().strip().replace(",", "") or "0")
            except ValueError:
                show_colorful_error(win, "Validation", f"{label} must be a number.")
                flash_error(entry)
                return None

        w_amt = _parse_amount(withdrawal_entry, "Withdrawal")
        if w_amt is None:
            return
        d_amt = _parse_amount(deposit_entry, "Deposit")
        if d_amt is None:
            return
        bal = _parse_amount(balance_entry, "Balance After")
        if bal is None:
            return

        # — Pair ID —
        pair_raw = pair_var.get().strip()
        if pair_raw:
            if not pair_raw.isdigit():
                show_colorful_error(
                    win, "Validation", "Pair ID must be a whole number."
                )
                flash_error(pair_entry)
                return
            pair_id_val: int | None = int(pair_raw)
        else:
            pair_id_val = None

        # — Budget Head —
        bh_name = bh_combo.get().strip()
        bh_id_val: int | None = bh_name_to_id.get(bh_name)

        # — Module Ref —
        mr_raw = mod_ref_var.get().strip()
        if mr_raw:
            if not mr_raw.isdigit():
                show_colorful_error(
                    win, "Validation", "Module Ref ID must be a whole number."
                )
                flash_error(mod_ref_entry)
                return
            mod_ref_val: int | None = int(mr_raw)
        else:
            mod_ref_val = None

        # — Module Type —
        mt_val = module_type_var.get()
        mt_db: str | None = None if mt_val == "NONE" else mt_val

        # — Entry Type —
        et_val = entry_type_var.get()

        # — Persist —
        try:
            cascades = db_update_bank_transaction(
                trans_id,
                serial_no=serial_no_val,
                value_date=v_date,
                trans_date=t_date,
                cheque_no=cheque_var.get().strip() or None,
                bank_desc=bank_remark_var.get().strip() or None,
                user_desc=user_desc_var.get().strip() or None,
                withdrawal_amount=w_amt,
                deposit_amount=d_amt,
                balance_after=bal,
                pair_id=pair_id_val,
                bh_id=bh_id_val,
                module_type=mt_db,
                module_ref_id=mod_ref_val,
                entry_type=et_val,
                old_withdrawal=data["withdrawal_amount"] or 0.0,
                old_deposit=data["deposit_amount"] or 0.0,
                old_trans_date=data["trans_date"],
                old_pair_id=data["pair_id"],
                old_module_type=data["module_type"],
                old_module_ref_id=data["module_ref_id"],
                account_id=data["account_id"],
            )
        except sqlite3.Error as exc:
            show_colorful_error(
                win, "Database Error", f"Failed to save changes:\n{exc}"
            )
            logger.exception("edit_bank_transaction: UPDATE failed for %s", trans_id)
            return

        # Build a human-readable cascade summary.
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
            lines.append(f"  • {mod} sub-ledger row #{mod_ref_val} date/amount synced.")
        if cascades.get("subledger_module_changed"):
            old_mod = data["module_type"] or "NONE"
            lines.append(
                f"  ⚠  Module type changed from {old_mod} — old sub-ledger row "
                "was NOT modified.  Fix it manually if needed."
            )

        show_colorful_info(win, "Saved", "\n".join(lines))
        cleanup_and_close()

    save_btn = tk.Button(
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
    save_btn.pack(side="right", padx=8)

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

    apply_button_animations(save_btn, _THEME["submit_bg"], _THEME["submit_hover_bg"])
    apply_button_animations(cancel_btn, _THEME["cancel_bg"], _THEME["cancel_hover_bg"])

    # ── Keyboard bindings ────────────────────────────────────────────────
    win.bind("<Escape>", cleanup_and_close)
    win.protocol("WM_DELETE_WINDOW", cleanup_and_close)

    # Tab order for plain Entry widgets
    serial_entry.bind("<Return>", lambda _e: cheque_entry.focus_set())
    cheque_entry.bind("<Return>", lambda _e: value_dt.focus_set())
    value_dt.bind("<Return>", lambda _e: trans_dt.focus_set())
    trans_dt.bind("<Return>", lambda _e: bank_remark_entry.focus_set())
    bank_remark_entry.bind("<Return>", lambda _e: withdrawal_entry.focus_set())
    withdrawal_entry.bind("<Return>", lambda _e: deposit_entry.focus_set())
    deposit_entry.bind("<Return>", lambda _e: balance_entry.focus_set())
    balance_entry.bind("<Return>", lambda _e: pair_entry.focus_set())
    pair_entry.bind("<Return>", lambda _e: bh_combo.focus_set())
    bh_combo.bind("<Return>", lambda _e: user_desc_entry.focus_set())
    user_desc_entry.bind("<Return>", lambda _e: mod_ref_entry.focus_set())
    mod_ref_entry.bind("<Return>", lambda _e: save_btn.focus_set())

    # Give focus to the first field.
    serial_entry.focus_set()

    parent.wait_window(win)

    # Restore grab so the caller stays in focus.
    try:
        if parent.winfo_exists():
            parent.grab_set()
    except tk.TclError:
        pass
