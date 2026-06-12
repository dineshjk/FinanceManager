# -*- coding: utf-8 -*-
# File: C:\Data\Personal\Finance_and_Investment\finprog\FinanceManager\StockMan\merger_entry.py

"""
This module handles the management of Corporate Mergers,
including target extinguishing, new share allotment,
and fractional cash settlements.
"""

from typing import Union
import tkinter as tk
from tkinter import ttk
import sqlite3
from tkcalendar import DateEntry
from datetime import datetime
import math

from Shared.globals import get_db_connection, logger
from Shared.dialog_utils import (
    show_colorful_info,
    show_colorful_error,
    show_colorful_yesno,
)
from .company_add import add_company
from .company_ex_import import export_company
from Shared.modal_utils import disable_parent, enable_parent
from Shared.window_manager import push_window, pop_window, safe_close_modal
from Shared.gui_progressive import progressive_selection
from Shared.gui_utils import (
    bind_tooltip,
    bind_entry_hover,
    on_enter_focus_next,
    apply_button_animations,
    apply_entry_theme,
    setup_footer_tooltip,
    bind_date_spin,
)
from Shared.validation_utils import validate_positive_numeric
from .trade_utils import compute_avg_price, manage_sell


def fetch_target_financials(
    id_stk: int, target_date_str: str
) -> tuple[int, float]:
    """Calculates holding quantity and net invested amount on or before a date."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    SUM(CASE WHEN trade_type_trd = 'BUY' THEN qty_trd ELSE -qty_trd END),
                    SUM(CASE WHEN trade_type_trd = 'BUY' THEN net_amt_trd ELSE -net_amt_trd END)
                FROM transactions
                WHERE id_stk = ? AND trd_dt < ?
                """,
                (id_stk, target_date_str),
            )
            result = cursor.fetchone()
            qty = int(result[0]) if result and result[0] else 0
            inv_amt = float(result[1]) if result and result[1] else 0.0
            return qty, inv_amt
    except sqlite3.Error as e:
        logger.error("Failed to fetch target financials: %s", e)
        return 0, 0.0


def add_merger(
    parent: Union[tk.Toplevel, tk.Tk], calling_button: tk.Widget | None = None
) -> None:
    # --- Purple/Corporate Theme for Mergers ---
    winbg = "#faf5ff"  # Purple 50
    headbg = "#4c1d95"  # Purple 900
    titlefg = "#e9d5ff"  # Purple 200
    mainfrbg = "#d8b4fe"  # Purple 300
    compfrbg = "#f3e8ff"  # Purple 100
    datefrbg = "#e0e7ff"  # Indigo 100
    ratiofrbg = "#e9d5ff"  # Purple 200
    notefrbg = "#f8fafc"  # Slate 50
    btnfrbg = "#faf5ff"  # Purple 50
    submitusualbg = "#7c3aed"  # Purple 600
    submitactivebg = "#6d28d9"  # Purple 700
    cancelusualbg = "#475569"  # Slate 600
    cancelactivebg = "#334155"  # Slate 700

    modal_id = disable_parent(parent, calling_button=calling_button)
    merg_win = tk.Toplevel(parent)
    merg_win.title("🤝 Corporate Merger Entry 🤝")
    merg_win.geometry("980x800")
    merg_win.resizable(False, False)
    merg_win.configure(bg=winbg)
    merg_win.transient(parent)
    merg_win.grab_set()
    push_window(merg_win, parent)

    tooltip_var = setup_footer_tooltip(
        merg_win, bg_color=winbg, fg_color=headbg
    )

    companies = []
    company_to_data = {}

    def _refresh_company_data():
        companies.clear()
        company_to_data.clear()
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT company_name, id_stk FROM stocks WHERE is_active = 1 ORDER BY company_name"
                )
                for row in cursor.fetchall():
                    companies.append(row[0])
                    company_to_data[row[0]] = {"id_stk": row[1]}
        except sqlite3.Error as e:
            logger.error("Failed to fetch companies for Merger: %s", e)

    def _invoke_add_company():
        add_company(merg_win)
        _refresh_company_data()
        target_combo["values"] = companies
        acquirer_combo["values"] = companies
        progressive_selection(target_combo, companies)
        progressive_selection(acquirer_combo, companies)

    _refresh_company_data()

    # --- UI Variables ---
    merger_name_var = tk.StringVar()
    target_name_var = tk.StringVar()
    acquirer_name_var = tk.StringVar()
    exchange_var = tk.StringVar(value="NSE")

    old_ratio_var = tk.IntVar(value=100)
    new_ratio_var = tk.IntVar(value=67)

    held_qty_var = tk.IntVar(value=0)
    target_invested_var = tk.DoubleVar(value=0.0)
    newly_allotted_qty_var = tk.IntVar(value=0)
    refund_amt_var = tk.DoubleVar(value=0.0)

    note_var = tk.StringVar()

    def _calculate_allotment(*_args):
        try:
            t_ratio = int(old_ratio_var.get())
            a_ratio = int(new_ratio_var.get())
            held = int(held_qty_var.get())

            if t_ratio > 0 and a_ratio > 0 and held > 0:
                # Calculate theoretical shares and floor it for actual allotment
                theoretical_shares = held * (a_ratio / t_ratio)
                allotted_qty = math.floor(theoretical_shares)
                newly_allotted_qty_var.set(allotted_qty)
            else:
                newly_allotted_qty_var.set(0)
        except (ValueError, tk.TclError):
            newly_allotted_qty_var.set(0)

    def _update_holdings(*_args):
        target_company = target_name_var.get().strip()
        if target_company in company_to_data:
            id_stk = company_to_data[target_company]["id_stk"]
            try:
                dt_str = allotment_dt_entry.get_date().strftime("%Y-%m-%d")
                qty, inv_amt = fetch_target_financials(id_stk, dt_str)
                held_qty_var.set(qty)
                target_invested_var.set(inv_amt)
                _calculate_allotment()
            except Exception:
                pass

    def _on_submit(_event=None):
        target_comp = target_name_var.get().strip()
        acquirer_comp = acquirer_name_var.get().strip()

        if (
            target_comp not in company_to_data
            or acquirer_comp not in company_to_data
        ):
            show_colorful_error(
                merg_win, "Validation Error", "Please select valid companies."
            )
            return
        if target_comp == acquirer_comp:
            show_colorful_error(
                merg_win,
                "Validation Error",
                "Target and Acquirer cannot be the same company.",
            )
            return

        id_target = company_to_data[target_comp]["id_stk"]
        id_acquirer = company_to_data[acquirer_comp]["id_stk"]

        try:
            h_qty = int(held_qty_var.get())
            a_qty = int(newly_allotted_qty_var.get())
            t_inv = float(target_invested_var.get())
            refund = float(refund_amt_var.get())

            if h_qty <= 0:
                show_colorful_error(
                    merg_win,
                    "Holding Error",
                    "You do not hold any shares of the Target company.",
                )
                return

            allot_dt = allotment_dt_entry.get_date().strftime("%Y-%m-%d")

            refund_dt = refund_dt_entry.get_date().strftime("%Y-%m-%d")

        except ValueError:
            show_colorful_error(
                merg_win, "Data Error", "Please ensure all numbers are valid."
            )
            return

        # Calculate the transferred cost basis (cannot be less than 0)
        transferred_cost = max(0.0, t_inv - refund)

        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA foreign_keys = ON;")

                # 1. Insert Corporate Action to get id_act
                details_text = f"Merger: Extinguished {h_qty} shares into {a_qty} shares of {acquirer_comp}."
                cursor.execute(
                    """
                    INSERT INTO corp_acts (id_stk, act_dt, type_act, details_act, ratio_old, ratio_new, note_act)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        id_target,
                        allot_dt,
                        "MERGER",
                        details_text,
                        int(old_ratio_var.get()),
                        int(new_ratio_var.get()),
                        note_var.get().strip(),
                    ),
                )
                id_act = cursor.lastrowid

                # --- NEW LOGIC: Generate single contract based on id_act ---
                sys_cont_no = f"MRG_{id_act}"
                settle_no = int(f"555{id_act}")

                # 2. Create the Single Master Contract
                cursor.execute(
                    "INSERT INTO contracts (cont_no, trd_dt, settle_no, settle_dt, no_of_trades, net_amt_cont, net_amt_cont_applicable) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        sys_cont_no,
                        allot_dt,
                        settle_no,
                        allot_dt,
                        2,
                        t_inv + transferred_cost,
                        t_inv + transferred_cost,
                    ),
                )

                # 3. Transaction 1: Extinguish Target (SELL)
                cursor.execute(
                    """
                    INSERT INTO transactions (
                        id_stk, cont_no, trd_dt, company_name, trade_type_trd, exchange,
                        qty_trd, wap_unit_trd, price_lot_trd, net_amt_trd, net_amt_trd_applicable, note_trd
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        id_target,
                        sys_cont_no,
                        allot_dt,
                        target_comp,
                        "SELL",
                        exchange_var.get(),
                        h_qty,
                        t_inv / h_qty if h_qty else 0.0,
                        t_inv,
                        t_inv,
                        t_inv,
                        "Merger Extinguishment",
                    ),
                )
                extinguish_trd_id = cursor.lastrowid

                # 4. Transaction 2: Allot Acquirer (BUY)
                id_trd = None
                if a_qty > 0:
                    cursor.execute(
                        """
                        INSERT INTO transactions (
                            id_stk, cont_no, trd_dt, company_name, trade_type_trd, exchange,
                            qty_trd, wap_unit_trd, price_lot_trd, net_amt_trd, net_amt_trd_applicable, note_trd
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            id_acquirer,
                            sys_cont_no,
                            allot_dt,
                            acquirer_comp,
                            "BUY",
                            exchange_var.get(),
                            a_qty,
                            transferred_cost / a_qty if a_qty else 0.0,
                            transferred_cost,
                            transferred_cost,
                            transferred_cost,
                            "Merger Allotment",
                        ),
                    )
                    id_trd = cursor.lastrowid

                # 5. Computed Bank Entry (Only if there is a fractional cash refund)
                tx_id = None
                if refund > 0:
                    cursor.execute(
                        """
                        INSERT INTO computed_bank (cont_no, comp_bt_dt, comp_bt_type, comp_bt_amt, comp_bt_amt_applicable, comp_bt_desc)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            sys_cont_no,
                            refund_dt,
                            "CREDIT",
                            refund,
                            refund,
                            f"Fractional share refund from {target_comp} merger",
                        ),
                    )
                    tx_id = cursor.lastrowid

                # 6. Insert into Merger Table (Linking to sys_cont_no)
                cursor.execute(
                    """
                    INSERT INTO merger (
                        id_act, id_stk_existing, id_stk_new, name, ratio_old, ratio_new,
                        held_qty, newly_allotted_qty, allotment_dt, invested_amt,
                        refund_amt, cont_no, id_trd, id_extinguish_trd,
                        id_allotment_trd, id_comp_bt, note_allot
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        id_act,
                        id_target,
                        id_acquirer,
                        merger_name_var.get().strip(),
                        int(old_ratio_var.get()),
                        int(new_ratio_var.get()),
                        h_qty,
                        a_qty,
                        allot_dt,
                        t_inv,
                        refund,
                        sys_cont_no,
                        id_trd,
                        extinguish_trd_id,
                        id_trd,
                        tx_id,
                        note_var.get().strip(),  # <--- Directly grab the note here
                    ),
                )

                # 7. Mark Target as Inactive
                cursor.execute(
                    "UPDATE stocks SET is_active = 0 WHERE id_stk = ?",
                    (id_target,),
                )

                conn.commit()

            # --- ADD THIS AFTER THE COMMIT ---
            # Execute the FIFO allocation silently (poke=False so it doesn't pop up UI alerts)
            manage_sell(extinguish_trd_id, poke=False)

            compute_avg_price(id_target)
            compute_avg_price(id_acquirer)

            # Prompt for another entry
            response = show_colorful_yesno(
                merg_win,
                "Success",
                f"Merger recorded!\n{target_comp} shares extinguished.\n{acquirer_comp} shares allotted.\n\nDo you want to add another merger?",
            )

            if response:
                merger_name_var.set("")
                target_name_var.set("")
                acquirer_name_var.set("")
                old_ratio_var.set(100)
                new_ratio_var.set(67)
                held_qty_var.set(0)
                target_invested_var.set(0.0)
                newly_allotted_qty_var.set(0)
                refund_amt_var.set(0.0)
                note_var.set("")
                _refresh_company_data()  # Refresh to drop the now inactive target
                target_combo["values"] = companies
                acquirer_combo["values"] = companies
                merger_name_entry.focus_set()
            else:
                close_merger()

        except sqlite3.Error as e:
            logger.error("Database error saving Merger: %s", e)
            show_colorful_error(
                merg_win, "Database Error", f"Failed to save record: {e}"
            )

    def close_merger(_event=None):
        enable_parent(modal_id)
        safe_close_modal(merg_win, parent)

    # --- UI LAYOUT ---
    header_frame = tk.Frame(merg_win, bg=headbg, relief="raised", bd=3)
    header_frame.pack(fill="x", padx=5, pady=0)
    tk.Label(
        header_frame,
        text="🤝 CORPORATE MERGER ENTRY 🤝",
        font=("Comic Sans MS", 18, "bold"),
        bg=headbg,
        fg=titlefg,
        pady=8,
    ).pack(fill="x")

    main_frame = tk.Frame(
        merg_win, bg=mainfrbg, padx=15, pady=10, relief="raised", bd=2
    )
    main_frame.pack(fill="both", expand=True, padx=10, pady=10)

    # 1. Companies Frame
    comp_frame = tk.Frame(
        main_frame, bg=compfrbg, relief="groove", bd=2, padx=10, pady=15
    )
    comp_frame.pack(fill="x", pady=(0, 10))

    tk.Label(
        comp_frame,
        text="Merger Name",
        bg=compfrbg,
        font=("Helvetica", 13, "bold"),
        fg=headbg,
    ).grid(row=0, column=0, sticky="w", pady=5)
    merger_name_entry = tk.Entry(
        comp_frame,
        textvariable=merger_name_var,
        width=35,
        font=("Helvetica", 13),
    )
    merger_name_entry.grid(row=0, column=1, padx=15, pady=5)

    tk.Label(
        comp_frame,
        text="Acquired Co. (Old)",
        bg=compfrbg,
        font=("Helvetica", 13, "bold"),
        fg=headbg,
    ).grid(row=1, column=0, sticky="w", pady=5)
    target_combo = ttk.Combobox(
        comp_frame,
        textvariable=target_name_var,
        values=companies,
        width=33,
        font=("Helvetica", 13),
    )
    target_combo.grid(row=1, column=1, padx=15, pady=5)
    progressive_selection(target_combo, companies)
    target_name_var.trace_add("write", _update_holdings)

    tk.Label(
        comp_frame,
        text="Acquiring Co. (New)",
        bg=compfrbg,
        font=("Helvetica", 13, "bold"),
        fg=headbg,
    ).grid(row=2, column=0, sticky="w", pady=5)

    acq_frame = tk.Frame(comp_frame, bg=compfrbg)
    acq_frame.grid(row=2, column=1, padx=15, pady=5, sticky="w")

    acquirer_combo = ttk.Combobox(
        acq_frame,
        textvariable=acquirer_name_var,
        values=companies,
        width=25,
        font=("Helvetica", 13),
    )
    acquirer_combo.pack(side="left")
    progressive_selection(acquirer_combo, companies)

    add_co_btn = tk.Button(
        acq_frame,
        text="➕ New",
        font=("Helvetica", 10, "bold"),
        bg=submitusualbg,
        fg="white",
        cursor="hand2",
        command=_invoke_add_company,
    )
    add_co_btn.pack(side="left", padx=(5, 0))

    tk.Label(
        comp_frame,
        text="Exchange",
        bg=compfrbg,
        font=("Helvetica", 13, "bold"),
        fg=headbg,
    ).grid(row=0, column=2, padx=(20, 5), rowspan=3)
    tk.Radiobutton(
        comp_frame,
        text="NSE",
        variable=exchange_var,
        value="NSE",
        bg=compfrbg,
        font=("Helvetica", 12),
    ).grid(row=1, column=3)
    tk.Radiobutton(
        comp_frame,
        text="BSE",
        variable=exchange_var,
        value="BSE",
        bg=compfrbg,
        font=("Helvetica", 12),
    ).grid(row=2, column=3)

    # 2. Dates Frame
    date_frame = tk.Frame(
        main_frame, bg=datefrbg, relief="ridge", bd=2, padx=10, pady=15
    )
    date_frame.pack(fill="x", pady=(0, 10))
    tk.Label(
        date_frame,
        text="Allotment / Ex-Date",
        bg=datefrbg,
        font=("Helvetica", 13, "bold"),
        fg=headbg,
    ).pack(side="left", padx=5)
    allotment_dt_entry = DateEntry(
        date_frame, date_pattern="dd-mm-yyyy", font=("Helvetica", 13), width=12
    )
    allotment_dt_entry.pack(side="left", padx=15)
    allotment_dt_entry.bind("<<DateEntrySelected>>", _update_holdings)
    allotment_dt_entry.bind("<FocusOut>", _update_holdings, add="+")

    # 3. Swap Ratio Frame
    calc_frame = tk.Frame(
        main_frame, bg=ratiofrbg, relief="ridge", bd=2, padx=10, pady=15
    )
    calc_frame.pack(fill="x", pady=(0, 10))

    tk.Label(
        calc_frame,
        text="Swap Ratio Details:",
        bg=ratiofrbg,
        font=("Helvetica", 13, "bold", "underline"),
        fg=headbg,
    ).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 10))

    tk.Label(
        calc_frame,
        text="Old Shares Required",
        bg=ratiofrbg,
        font=("Helvetica", 12, "bold"),
        fg="#1e3a8a",
    ).grid(row=1, column=0, sticky="w", pady=5)
    t_ratio_entry = tk.Entry(
        calc_frame,
        textvariable=old_ratio_var,
        width=10,
        font=("Helvetica", 13),
    )
    t_ratio_entry.grid(row=1, column=1, padx=15, pady=5)

    tk.Label(
        calc_frame,
        text="New Shares Given",
        bg=ratiofrbg,
        font=("Helvetica", 12, "bold"),
        fg="#1e3a8a",
    ).grid(row=1, column=2, sticky="w", padx=(20, 5), pady=5)
    a_ratio_entry = tk.Entry(
        calc_frame,
        textvariable=new_ratio_var,
        width=10,
        font=("Helvetica", 13),
    )
    a_ratio_entry.grid(row=1, column=3, pady=5)

    tk.Label(
        calc_frame,
        text="Old Held Qty",
        bg=ratiofrbg,
        font=("Helvetica", 12, "bold"),
        fg="#b91c1c",
    ).grid(row=2, column=0, sticky="w", pady=(15, 5))
    held_qty_entry = tk.Entry(
        calc_frame,
        textvariable=held_qty_var,
        width=12,
        font=("Helvetica", 13),
        state="readonly",
    )
    held_qty_entry.grid(row=2, column=1, padx=15, pady=(15, 5))

    tk.Label(
        calc_frame,
        text="New Allotted Qty",
        bg=ratiofrbg,
        font=("Helvetica", 12, "bold"),
        fg="#047857",
    ).grid(row=2, column=2, sticky="w", padx=(20, 5), pady=(15, 5))
    allotted_qty_entry = tk.Entry(
        calc_frame,
        textvariable=newly_allotted_qty_var,
        width=12,
        font=("Helvetica", 13),
    )
    allotted_qty_entry.grid(row=2, column=3, pady=(15, 5))

    tk.Label(
        calc_frame,
        text="Fractional Cash Refund (₹)",
        bg=ratiofrbg,
        font=("Helvetica", 12, "bold"),
        fg="#b45309",
    ).grid(row=3, column=0, sticky="w", pady=5)
    refund_entry = tk.Entry(
        calc_frame,
        textvariable=refund_amt_var,
        width=15,
        font=("Helvetica", 13),
    )
    refund_entry.grid(row=3, column=1, padx=15, pady=5)

    # --- ADD THESE LINES RIGHT HERE ---
    tk.Label(
        calc_frame,
        text="Refund Date (Bank)",
        bg=ratiofrbg,
        font=("Helvetica", 12, "bold"),
        fg="#b45309",
    ).grid(row=3, column=2, sticky="w", padx=(20, 5), pady=5)
    refund_dt_entry = DateEntry(
        calc_frame, date_pattern="dd-mm-yyyy", font=("Helvetica", 13), width=12
    )
    refund_dt_entry.grid(row=3, column=3, pady=5)

    bind_date_spin(allotment_dt_entry, callback=_update_holdings)
    bind_date_spin(refund_dt_entry)

    t_ratio_entry.bind("<KeyRelease>", _calculate_allotment)
    a_ratio_entry.bind("<KeyRelease>", _calculate_allotment)

    # 4. Notes Frame
    note_frame = tk.Frame(
        main_frame, bg=notefrbg, relief="ridge", bd=2, padx=10, pady=15
    )
    note_frame.pack(fill="x", pady=(0, 10))

    tk.Label(
        note_frame,
        text="Notes / Remarks",
        bg=notefrbg,
        font=("Helvetica", 13, "bold"),
        fg="#334155",
    ).grid(row=1, column=0, sticky="w", padx=5, pady=5)
    note_entry = tk.Entry(
        note_frame, textvariable=note_var, width=68, font=("Helvetica", 13)
    )
    note_entry.grid(row=1, column=1, sticky="w", padx=10, pady=5)

    # --- Central Engine Setup (Theme & Tooltips) ---

    theme_widgets = {
        "merger_name_entry": merger_name_entry,
        "target_combo": target_combo,
        "acquirer_combo": acquirer_combo,
        "allotment_dt_entry": allotment_dt_entry,
        "t_ratio_entry": t_ratio_entry,
        "a_ratio_entry": a_ratio_entry,
        "held_qty_entry": held_qty_entry,
        "allotted_qty_entry": allotted_qty_entry,
        "refund_entry": refund_entry,
        "refund_dt_entry": refund_dt_entry,
        "note_entry": note_entry,
    }

    for key, widget in theme_widgets.items():
        is_ro = key == "held_qty_entry"
        apply_entry_theme(widget, is_readonly=is_ro)

    bind_tooltip(
        merger_name_entry,
        tooltip_var,
        "Optional: Enter a descriptive name for this merger event (e.g., HDFC Bank Merger).",
    )
    bind_tooltip(
        target_combo,
        tooltip_var,
        "Select the old company (Target) whose shares will be extinguished.",
    )
    bind_tooltip(
        acquirer_combo,
        tooltip_var,
        "Select the new company that will issue new shares.",
    )
    bind_tooltip(
        refund_dt_entry,
        tooltip_var,
        "The exact date the fractional cash refund was credited to your bank account.",
    )
    bind_tooltip(
        allotment_dt_entry,
        tooltip_var,
        "The date when the old shares are extinguished and new shares are allotted.",
    )
    bind_tooltip(
        t_ratio_entry,
        tooltip_var,
        "The number of old shares required for the swap.",
    )
    bind_tooltip(
        a_ratio_entry,
        tooltip_var,
        "The number of new shares given for the required old shares.",
    )
    bind_tooltip(
        held_qty_entry,
        tooltip_var,
        "Your current holding of the old company (auto-calculated).",
    )
    bind_tooltip(
        allotted_qty_entry,
        tooltip_var,
        "The number of new shares you will receive (auto-calculated, can be edited).",
    )
    bind_tooltip(
        refund_entry,
        tooltip_var,
        "Any cash settlement received in lieu of fractional shares.",
    )
    # bind_tooltip(
    #     cont_no_entry,
    #     tooltip_var,
    #     "Optional: Enter the associated Contract Note or Reference Number.",
    # )
    bind_tooltip(
        note_entry,
        tooltip_var,
        "Any extra remarks or details about this merger.",
    )

    # --- Buttons Frame ---
    btn_frame = tk.Frame(merg_win, pady=10, bg=btnfrbg, relief="ridge", bd=2)
    btn_frame.pack(fill="x", anchor="e", padx=10, pady=(0, 10))

    save_btn = tk.Button(
        btn_frame,
        text="🚀 Execute Merger 🚀",
        command=_on_submit,
        font=("Comic Sans MS", 12, "bold"),
        bg="#22c55e",
        activebackground="#16a34a",
        activeforeground="white",
        fg="white",
        width=20,
        cursor="hand2",
    )
    save_btn.pack(side="right", padx=10)

    cancel_btn = tk.Button(
        btn_frame,
        text="❌ Cancel ❌",
        command=close_merger,
        font=("Comic Sans MS", 12, "bold"),
        bg=cancelusualbg,
        activebackground=cancelactivebg,
        activeforeground="white",
        fg="white",
        width=12,
        cursor="hand2",
    )
    cancel_btn.pack(side="right", padx=5)

    # Button Animations
    apply_button_animations(save_btn, "#22c55e", "#2563eb")
    apply_button_animations(cancel_btn, cancelusualbg, cancelactivebg)

    merg_win.bind(
        "<Return>",
        lambda e: on_enter_focus_next(e, merg_win, save_btn, cancel_btn),
    )
    merg_win.bind("<Escape>", close_merger)
    merg_win.protocol("WM_DELETE_WINDOW", close_merger)
    merger_name_entry.focus_set()

    parent.wait_window(merg_win)
    try:
        if parent.winfo_exists():
            parent.grab_set()
    except tk.TclError:
        pass


# File: C:\Data\Personal\Finance_and_Investment\finprog\FinanceManager\StockMan\merger_entry.py ends here
