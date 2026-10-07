# -*- coding: utf-8 -*-
# BankMan/cc_transactions_edit.py

"""
Module for editing Credit Card Transaction records (cc_transactions table).
"""

from typing import Union
import sqlite3
import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont
from tkcalendar import DateEntry
from datetime import datetime

from Shared.gui_utils import (
    apply_entry_theme,
    bind_tooltip,
    setup_footer_tooltip,
    flash_error,
    CC_TRANS_ADD_UI_THEME,
    apply_button_animations,
    bind_date_spin,
)
from Shared.dialog_utils import (
    show_colorful_info,
    show_colorful_error,
    show_colorful_yesno
)
from Shared.modal_utils import disable_parent
from Shared.window_manager import push_window, safe_close_modal
from Shared.globals import logger, get_db_connection, BANK_DB_PATH
from Shared.gui_progressive import progressive_selection
from .bank_db_utils import get_all_budget_heads
from .budget_head_add import add_account_type_main as _add_budget_head

_T = CC_TRANS_ADD_UI_THEME

_TRANS_TYPES = ["EXPENSE", "PAYMENT", "CASHBACK", "REVERSAL"]

def _make_band(container, bg, relief="ridge", padx=10, pady=6):
    band = tk.Frame(
        container,
        bg=bg,
        relief=relief,
        bd=2,
        padx=padx,
        pady=pady,
    )
    band.pack(fill="x", pady=6)
    label_row = tk.Frame(band, bg=bg)
    label_row.pack(fill="x", pady=(0, 2))
    entry_row = tk.Frame(band, bg=bg)
    entry_row.pack(fill="x", pady=(0, 2))
    return band, label_row, entry_row

def _band_label(parent, text, bg, font=("Helvetica", 14), padx=0):
    tk.Label(
        parent,
        text=text,
        font=font,
        bg=bg,
        fg=_T["label_fg"],
        anchor="w",
    ).pack(side="left", padx=(padx, 12))

def _fetch_transaction(cc_trans_id: int) -> dict | None:
    try:
        with get_db_connection(BANK_DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT c.cc_trans_id,
                       c.card_master_id,
                       c.account_id,
                       c.cc_trans_dt,
                       c.party,
                       c.expense,
                       c.cc_credit,
                       c.bh_id,
                       cm.card_name,
                       bh.bh_description as bh_name
                FROM cc_transactions c
                JOIN card_master cm ON c.card_master_id = cm.card_master_id
                LEFT JOIN budget_head bh ON c.bh_id = bh.bh_id
                WHERE c.cc_trans_id = ?
                """,
                (cc_trans_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            keys = [
                "cc_trans_id", "card_master_id", "account_id", "cc_trans_dt",
                "party", "expense", "cc_credit", "bh_id", "card_name", "bh_name"
            ]
            return dict(zip(keys, row))
    except sqlite3.Error as exc:
        logger.error("_fetch_transaction(%s): %s", cc_trans_id, exc)
        return None

def edit_cc_transaction(
    parent: Union[tk.Toplevel, tk.Tk],
    cc_trans_id: int,
    calling_button: tk.Widget | None = None,
) -> None:
    """Launch the Edit CC Transaction dialog."""

    data = _fetch_transaction(cc_trans_id)
    if data is None:
        show_colorful_error(
            parent,
            "Load Error",
            f"Could not load transaction #{cc_trans_id} from the database.",
        )
        return

    disable_parent(parent, calling_button=calling_button)

    win = tk.Toplevel(parent)
    win.title(f"✏️ Edit CC Transaction #{cc_trans_id} ✏️")
    win.geometry("900x560")
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

    win.bind("<Control-Return>", lambda e: _validate_and_save())
    win.bind("<Escape>", on_escape)
    win.protocol("WM_DELETE_WINDOW", on_escape)

    header_frame = tk.Frame(win, bg=_T["header_bg"], relief="raised", bd=3)
    header_frame.pack(fill="x", padx=5, pady=0)
    tk.Label(
        header_frame,
        text="Edit Credit Card Transaction",
        font=("Helvetica", 18, "bold"),
        bg=_T["header_bg"],
        fg=_T["header_fg"],
        pady=8,
    ).pack(fill="x")

    form_frame = tk.Frame(win, bg=_T["main_bg"])
    form_frame.pack(fill="both", expand=True, padx=20, pady=10)

    # 1. Card Info (Read-only)
    band_top, l_top, e_top = _make_band(form_frame, _T["band_master"])
    _band_label(l_top, "Credit Card:", _T["band_master"])
    _band_label(l_top, "Account ID:", _T["band_master"])

    card_label = tk.Label(
        e_top,
        text=data["card_name"],
        font=("Helvetica", 14),
        bg=_T["band_master"],
        fg=_T["label_fg"],
        anchor="w",
        width=30,
    )
    card_label.pack(side="left", padx=(0, 20))

    acct_label = tk.Label(
        e_top,
        text=str(data["account_id"]),
        font=("Helvetica", 14),
        bg=_T["band_master"],
        fg=_T["label_fg"],
        anchor="w",
        width=15,
    )
    acct_label.pack(side="left", padx=(0, 10))

    # 2. Date and Type
    band_mid1, l_mid1, e_mid1 = _make_band(form_frame, _T["band_details"])
    _band_label(l_mid1, "Trans Date (YYYY-MM-DD)*:", _T["band_details"])
    _band_label(l_mid1, "Trans Type:", _T["band_details"])

    trans_dt = DateEntry(
        e_mid1,
        width=16,
        font=("Helvetica", 14),
        background="darkblue",
        foreground="white",
        borderwidth=2,
        date_pattern="y-mm-dd",
    )
    trans_dt.pack(side="left", padx=(0, 20))
    bind_date_spin(trans_dt)
    
    try:
        dt = datetime.strptime(data["cc_trans_dt"], "%Y-%m-%d").date()
        trans_dt.set_date(dt)
    except Exception:
        pass

    trans_type_var = tk.StringVar()
    if data["expense"] > 0:
        trans_type_var.set("EXPENSE")
    elif data["cc_credit"] > 0:
        trans_type_var.set("PAYMENT")
    else:
        trans_type_var.set("EXPENSE")

    type_combo = ttk.Combobox(
        e_mid1,
        textvariable=trans_type_var,
        values=_TRANS_TYPES,
        state="readonly",
        font=("Helvetica", 14),
        width=18,
    )
    type_combo.pack(side="left", padx=(0, 10))
    apply_entry_theme(type_combo)

    # 3. Party and Amounts
    band_mid2, l_mid2, e_mid2 = _make_band(form_frame, _T["band_master"])
    _band_label(l_mid2, "Party / Merchant*:", _T["band_master"], padx=0)
    _band_label(l_mid2, "Expense:", _T["band_master"], padx=0)
    _band_label(l_mid2, "CC Credit:", _T["band_master"], padx=0)

    party_entry = tk.Entry(e_mid2, width=28, font=("Helvetica", 14))
    party_entry.pack(side="left", padx=(0, 20))
    party_entry.insert(0, data["party"])
    apply_entry_theme(party_entry)

    expense_entry = tk.Entry(e_mid2, width=12, font=("Helvetica", 14))
    expense_entry.pack(side="left", padx=(0, 20))
    expense_entry.insert(0, f"{data['expense']:.2f}")
    apply_entry_theme(expense_entry)

    cc_credit_entry = tk.Entry(e_mid2, width=12, font=("Helvetica", 14))
    cc_credit_entry.pack(side="left", padx=(0, 10))
    cc_credit_entry.insert(0, f"{data['cc_credit']:.2f}")
    apply_entry_theme(cc_credit_entry)

    # 4. Budget Head
    band_bot, l_bot, e_bot = _make_band(form_frame, _T["band_details"])
    _band_label(l_bot, "Budget Head (Optional):", _T["band_details"])

    bh_rows = []
    budget_map = {}
    bh_values = []

    budget_head_combo = ttk.Combobox(
        e_bot,
        font=("Helvetica", 14),
        width=30,
    )
    budget_head_combo.pack(side="left", padx=(0, 10))
    apply_entry_theme(budget_head_combo)

    def _refresh_budget_head_combo():
        nonlocal bh_rows, budget_map
        bh_rows = get_all_budget_heads()
        budget_map.clear()
        for r in bh_rows:
            budget_map[r[1]] = r[0]
        _update_bh_dropdown()

    def _update_bh_dropdown():
        current_type = trans_type_var.get()
        target_bh_type = "EXPENSE" if current_type == "EXPENSE" else "INCOME"
        filtered = ["(none)"] + [
            r[1] for r in bh_rows if r[2] == target_bh_type
        ]
        bh_values.clear()
        bh_values.extend(filtered)
        budget_head_combo["values"] = list(bh_values)
        current_sel = budget_head_combo.get()
        if current_sel not in bh_values:
            budget_head_combo.set("(none)")
        progressive_selection(budget_head_combo, list(bh_values))

    trans_type_var.trace_add("write", lambda *a: _update_bh_dropdown())

    def on_budget_head_focus_out(event):
        val = budget_head_combo.get().strip()
        if val and val != "(none)" and val not in budget_map:
            response = show_colorful_yesno(
                win,
                "New Budget Head?",
                f"'{val}' is not in the list.\nWould you like to add it?",
            )
            if response:
                _add_budget_head(win)
                _refresh_budget_head_combo()
                budget_head_combo.set(val)
                budget_head_combo.focus_set()
            else:
                budget_head_combo.set("(none)")

    budget_head_combo.bind("<FocusOut>", on_budget_head_focus_out, add="+")

    _refresh_budget_head_combo()
    if data["bh_name"]:
        budget_head_combo.set(data["bh_name"])
    else:
        budget_head_combo.set("(none)")

    btn_frame = tk.Frame(win, bg=_T["main_bg"])
    btn_frame.pack(pady=20)

    def _validate_and_save():
        try:
            cc_trans_dt = trans_dt.get_date().strftime("%Y-%m-%d")
        except Exception:
            flash_error(trans_dt)
            return

        party = party_entry.get().strip()
        if not party:
            flash_error(party_entry)
            return

        try:
            expense_str = expense_entry.get().replace(",", "")
            expense = float(expense_str or "0")
        except ValueError:
            flash_error(expense_entry)
            return

        try:
            credit_str = cc_credit_entry.get().replace(",", "")
            cc_credit = float(credit_str or "0")
        except ValueError:
            flash_error(cc_credit_entry)
            return

        ttype = trans_type_var.get()
        if ttype == "EXPENSE" and expense <= 0:
            flash_error(expense_entry)
            show_colorful_error(win, "Validation Error", "Expense must be > 0")
            return
        if ttype in ("PAYMENT", "CASHBACK", "REVERSAL") and cc_credit <= 0:
            flash_error(cc_credit_entry)
            show_colorful_error(win, "Validation Error", "CC Credit must be > 0")
            return
        if ttype != "EXPENSE" and expense != 0:
            show_colorful_error(win, "Validation Error", f"Expense must be 0 for {ttype}.")
            return
        if ttype == "EXPENSE" and cc_credit != 0:
            show_colorful_error(win, "Validation Error", "CC Credit must be 0 for EXPENSE.")
            return

        bh_desc = budget_head_combo.get().strip()
        bh_id = budget_map.get(bh_desc)

        try:
            with get_db_connection(BANK_DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT trans_id, withdrawal_amount, deposit_amount
                    FROM bank_transactions
                    WHERE module_type = 'CC' AND module_ref_id = ?
                    """,
                    (cc_trans_id,)
                )
                linked_bank_tx = cur.fetchone()

                cur.execute(
                    """
                    UPDATE cc_transactions
                    SET cc_trans_dt = ?,
                        party = ?,
                        expense = ?,
                        cc_credit = ?,
                        bh_id = ?
                    WHERE cc_trans_id = ?
                    """,
                    (cc_trans_dt, party, expense, cc_credit, bh_id, cc_trans_id)
                )

                if linked_bank_tx:
                    b_trans_id, old_w_amt, old_d_amt = linked_bank_tx
                    
                    new_w_amt = cc_credit if cc_credit > 0 else 0.0
                    new_d_amt = expense if expense > 0 else 0.0
                    
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
                        (cc_trans_dt, new_w_amt, new_d_amt, delta, b_trans_id)
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
                            (delta, data["account_id"], cc_trans_dt, cc_trans_dt, b_trans_id)
                        )

                conn.commit()
            
            cleanup_and_close()
        except Exception as exc:
            logger.error("Failed to update transaction: %s", exc)
            show_colorful_error(win, "DB Error", f"Update failed: {exc}")

    save_btn = tk.Button(
        btn_frame,
        text="Save Changes",
        font=("Helvetica", 14, "bold"),
        bg=_T.get("save_btn_bg", _T["button_bg"]),
        fg=_T.get("button_fg", "white"),
        activebackground=_T.get("button_active_bg", "#155e75"),
        activeforeground=_T.get("button_fg", "white"),
        cursor="hand2",
        command=_validate_and_save,
    )
    save_btn.pack(side="left", padx=10)

    cancel_btn = tk.Button(
        btn_frame,
        text="Cancel",
        font=("Helvetica", 14),
        bg=_T.get("cancel_btn_bg", "#64748b"),
        fg=_T.get("button_fg", "white"),
        activebackground="#475569",
        activeforeground=_T.get("button_fg", "white"),
        cursor="hand2",
        command=cleanup_and_close,
    )
    cancel_btn.pack(side="left", padx=10)

    apply_button_animations(save_btn, _T.get("save_btn_bg", _T["button_bg"]), _T.get("button_active_bg", "#155e75"))
    apply_button_animations(cancel_btn, _T.get("cancel_btn_bg", "#64748b"), "#475569")
