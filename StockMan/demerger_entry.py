# -*- coding: utf-8 -*-
# StockMan/demerger_entry.py

"""
This module handles Corporate Demergers.
It allows for dynamic allocation of the parent company's invested
capital to one or more newly spun-off child companies based on the
official Cost of Acquisition (CoA) percentages.
"""

from typing import Union
import tkinter as tk
from tkinter import ttk
import sqlite3
from tkcalendar import DateEntry
import math

from Shared.globals import get_db_connection, logger
from Shared.dialog_utils import (
    show_colorful_info,
    show_colorful_error,
    show_colorful_yesno,
)
from .company_add import add_company
from .trade_utils import compute_avg_price
from Shared.modal_utils import disable_parent, enable_parent
from Shared.window_manager import push_window, pop_window, safe_close_modal
from Shared.gui_progressive import progressive_selection
from Shared.gui_utils import (
    apply_entry_theme,
    bind_tooltip,
    setup_footer_tooltip,
    bind_date_spin,
    apply_button_animations,
)


def fetch_parent_financials(
    id_stk: int, target_date_str: str
) -> tuple[int, float]:
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
    except sqlite3.Error:
        return 0, 0.0


def add_demerger(
    parent: Union[tk.Toplevel, tk.Tk], calling_button: tk.Widget | None = None
) -> None:
    # --- Amber/Slate Theme ---
    winbg = "#fffbeb"  # Amber 50
    headbg = "#b45309"  # Amber 700
    titlefg = "#fef3c7"  # Amber 100
    mainfrbg = "#fcd34d"  # Amber 300
    compfrbg = "#fef3c7"  # Amber 100
    childfrbg = "#f8fafc"  # Slate 50
    btnfrbg = "#fffbeb"  # Amber 50
    submitusualbg = "#d97706"  # Amber 600
    submitactivebg = "#b45309"  # Amber 700
    cancelusualbg = "#475569"  # Slate 600
    cancelactivebg = "#334155"  # Slate 700

    modal_id = disable_parent(parent, calling_button=calling_button)
    dem_win = tk.Toplevel(parent)
    dem_win.title("✂️ Corporate Demerger Entry ✂️")
    tooltip_var = setup_footer_tooltip(
        dem_win, bg_color="#fffbeb"
    )  # #fffbeb is the Amber winbg
    dem_win.geometry("1250x800")
    dem_win.resizable(False, True)
    dem_win.configure(bg=winbg)
    dem_win.transient(parent)
    dem_win.grab_set()
    dem_win.focus_set()
    push_window(dem_win, parent)

    companies = []
    company_to_data = {}
    child_rows = []  # Will store dicts of Tkinter variables for each child row

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
        except sqlite3.Error:
            pass

    def _invoke_add_company():
        add_company(dem_win)
        _refresh_company_data()
        parent_combo["values"] = companies
        progressive_selection(parent_combo, companies)
        for row in child_rows:
            row["combo"]["values"] = companies
            progressive_selection(row["combo"], companies)

    _refresh_company_data()

    # --- Parent Variables ---
    parent_name_var = tk.StringVar()
    held_qty_var = tk.IntVar(value=0)
    parent_invested_var = tk.DoubleVar(value=0.0)
    exchange_var = tk.StringVar(value="NSE")
    note_var = tk.StringVar()

    def _update_parent_holdings(*_args):
        p_comp = parent_name_var.get().strip()
        if p_comp in company_to_data:
            id_stk = company_to_data[p_comp]["id_stk"]
            dt_str = ex_dt_entry.get_date().strftime("%Y-%m-%d")
            qty, inv_amt = fetch_parent_financials(id_stk, dt_str)
            held_qty_var.set(qty)
            parent_invested_var.set(inv_amt)
            _calculate_all_children()

    def _calculate_all_children(*_args):
        try:
            p_qty = int(held_qty_var.get())
            p_inv = float(parent_invested_var.get())

            for row in child_rows:
                p_ratio = int(row["p_ratio_var"].get())
                c_ratio = int(row["c_ratio_var"].get())
                coa_pct = float(row["coa_var"].get())

                if p_ratio > 0 and c_ratio > 0 and p_qty > 0:
                    theo_shares = p_qty * (c_ratio / p_ratio)
                    row["a_qty_var"].set(math.floor(theo_shares))
                else:
                    row["a_qty_var"].set(0)

                if coa_pct > 0 and p_inv > 0:
                    row["t_cost_var"].set(round(p_inv * (coa_pct / 100), 2))
                else:
                    row["t_cost_var"].set(0.0)
        except (ValueError, tk.TclError):
            pass

    def _add_child_row():
        if len(child_rows) >= 5:
            show_colorful_error(
                dem_win,
                "Limit Reached",
                "Maximum of 5 child companies allowed per transaction.",
            )
            return

        # Start at row 1, 2, 3... because Row 0 is now strictly reserved for our Headers
        row_idx = len(child_rows) + 1

        row_vars = {
            "name_var": tk.StringVar(),
            "p_ratio_var": tk.IntVar(value=1),
            "c_ratio_var": tk.IntVar(value=1),
            "coa_var": tk.DoubleVar(value=0.0),
            "a_qty_var": tk.IntVar(value=0),
            "t_cost_var": tk.DoubleVar(value=0.0),
            "refund_var": tk.DoubleVar(value=0.0),
        }

        # Company Select
        combo = ttk.Combobox(
            children_container,
            textvariable=row_vars["name_var"],
            values=companies,
            width=20,
            font=("Helvetica", 11),
        )
        combo.grid(row=row_idx, column=0, padx=5, pady=5)
        progressive_selection(combo, companies)
        row_vars["combo"] = combo
        apply_entry_theme(combo)

        # Ratios
        p_ratio_entry = tk.Entry(
            children_container,
            textvariable=row_vars["p_ratio_var"],
            width=5,
            font=("Helvetica", 11),
        )
        p_ratio_entry.grid(row=row_idx, column=1, padx=2, pady=5)
        apply_entry_theme(p_ratio_entry)

        tk.Label(
            children_container,
            text=":",
            bg=childfrbg,
            font=("Helvetica", 11, "bold"),
        ).grid(row=row_idx, column=2, pady=5)

        c_ratio_entry = tk.Entry(
            children_container,
            textvariable=row_vars["c_ratio_var"],
            width=5,
            font=("Helvetica", 11),
        )
        c_ratio_entry.grid(row=row_idx, column=3, padx=2, pady=5)
        apply_entry_theme(c_ratio_entry)

        # CoA %
        coa_entry = tk.Entry(
            children_container,
            textvariable=row_vars["coa_var"],
            width=8,
            font=("Helvetica", 11),
        )
        coa_entry.grid(row=row_idx, column=4, padx=15, pady=5)
        apply_entry_theme(coa_entry)

        # Computed Allotment & Cost (Readonly)
        a_qty_entry = tk.Entry(
            children_container,
            textvariable=row_vars["a_qty_var"],
            width=8,
            font=("Helvetica", 11, "bold"),
            state="readonly",
        )
        a_qty_entry.grid(row=row_idx, column=5, padx=10, pady=5)
        apply_entry_theme(a_qty_entry, is_readonly=True)

        t_cost_entry = tk.Entry(
            children_container,
            textvariable=row_vars["t_cost_var"],
            width=12,
            font=("Helvetica", 11),
            state="readonly",
        )
        t_cost_entry.grid(row=row_idx, column=6, padx=10, pady=5)
        apply_entry_theme(t_cost_entry, is_readonly=True)

        # Refund
        refund_entry = tk.Entry(
            children_container,
            textvariable=row_vars["refund_var"],
            width=10,
            font=("Helvetica", 11),
        )
        refund_entry.grid(row=row_idx, column=7, padx=5, pady=5)
        apply_entry_theme(refund_entry)

        # Refund Date
        refund_dt_entry = DateEntry(
            children_container,
            date_pattern="dd-mm-yyyy",
            font=("Helvetica", 11),
            width=10,
        )
        refund_dt_entry.grid(row=row_idx, column=8, padx=5, pady=5)
        bind_date_spin(refund_dt_entry)
        row_vars["refund_dt_entry"] = refund_dt_entry

        # Bindings
        row_vars["p_ratio_var"].trace_add("write", _calculate_all_children)
        row_vars["c_ratio_var"].trace_add("write", _calculate_all_children)
        row_vars["coa_var"].trace_add("write", _calculate_all_children)

        bind_tooltip(combo, tooltip_var, "Select the spun-off child company.")
        bind_tooltip(
            p_ratio_entry, tooltip_var, "Ratio component: Parent shares held."
        )
        bind_tooltip(
            c_ratio_entry,
            tooltip_var,
            "Ratio component: Child shares received.",
        )
        bind_tooltip(
            coa_entry,
            tooltip_var,
            "Cost of Acquisition percentage for this child.",
        )
        bind_tooltip(
            refund_entry,
            tooltip_var,
            "Enter any cash refund received for fractional shares.",
        )

        child_rows.append(row_vars)

    def _on_submit(_event=None):
        p_comp = parent_name_var.get().strip()
        if p_comp not in company_to_data:
            show_colorful_error(
                dem_win, "Error", "Please select a valid Parent company."
            )
            return

        id_parent = company_to_data[p_comp]["id_stk"]
        ex_dt = ex_dt_entry.get_date().strftime("%Y-%m-%d")
        rec_dt = rec_dt_entry.get_date().strftime("%Y-%m-%d")
        p_qty = int(held_qty_var.get())
        p_inv = float(parent_invested_var.get())

        if p_qty <= 0:
            show_colorful_error(
                dem_win,
                "Holding Error",
                "You do not hold any shares of the Parent company.",
            )
            return

        if not child_rows:
            show_colorful_error(
                dem_win, "Error", "Please add at least one Child company."
            )
            return

        total_coa = 0.0
        total_deduction = 0.0
        allotment_data = []

        for row in child_rows:
            c_comp = row["name_var"].get().strip()
            if not c_comp or c_comp not in company_to_data:
                show_colorful_error(
                    dem_win, "Error", "Ensure all Child companies are valid."
                )
                return
            if c_comp == p_comp:
                show_colorful_error(
                    dem_win,
                    "Error",
                    "Child company cannot be the same as the Parent.",
                )
                return

            coa = float(row["coa_var"].get())
            total_coa += coa

            t_cost = float(row["t_cost_var"].get())
            total_deduction += t_cost

            allotment_data.append(
                {
                    "id_child": company_to_data[c_comp]["id_stk"],
                    "c_comp_name": c_comp,
                    "p_ratio": int(row["p_ratio_var"].get()),
                    "c_ratio": int(row["c_ratio_var"].get()),
                    "coa_pct": coa,
                    "a_qty": int(row["a_qty_var"].get()),
                    "t_cost": t_cost,
                    "refund": float(row["refund_var"].get()),
                    "refund_dt": row["refund_dt_entry"]
                    .get_date()
                    .strftime("%Y-%m-%d"),
                }
            )

        if total_coa > 100.0:
            show_colorful_error(
                dem_win,
                "CoA Error",
                f"Total Cost of Acquisition cannot exceed 100%. Currently at {total_coa}%.",
            )
            return

        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA foreign_keys = ON;")

                # 1. Update Corporate Actions Master Ledger first to get id_act
                cursor.execute(
                    """INSERT INTO corp_acts (id_stk, act_dt, type_act, details_act, note_act)
                       VALUES (?, ?, ?, ?, ?)""",
                    (
                        id_parent,
                        ex_dt,
                        "DEMERGER",
                        f"Demerger: Spun-off {len(allotment_data)} child companies.",
                        note_var.get().strip(),
                    ),
                )
                id_act = cursor.lastrowid

                # 2. Insert Event into demerger_events using the new id_act
                cursor.execute(
                    """INSERT INTO demerger_events (id_act, id_stk_parent, ex_dt, record_dt, total_held_qty, total_invested_amt, note_demerger)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        id_act,
                        id_parent,
                        ex_dt,
                        rec_dt,
                        p_qty,
                        p_inv,
                        note_var.get().strip(),
                    ),
                )
                id_dem = cursor.lastrowid
                settle_base = int(f"666{id_dem}")
                parent_adjustment_trd_id = None

                # 3. True Lot Bifurcation (Parent Deduction)
                if total_deduction > 0:
                    retention_multiplier = 1.0 - (total_coa / 100.0)

                    # Fetch all open BUY lots for the parent
                    cursor.execute(
                        """
                        SELECT id_trd, cont_no, trd_dt, company_name, exchange, qty_trd,
                               wap_unit_trd, price_lot_trd, net_amt_trd, net_amt_trd_applicable,
                               sold_qty, note_trd
                        FROM transactions
                        WHERE id_stk = ? AND trade_type_trd = 'BUY' AND qty_trd > sold_qty
                        """,
                        (id_parent,),
                    )
                    open_lots = cursor.fetchall()

                    for lot in open_lots:
                        (
                            l_id_trd,
                            l_cont_no,
                            l_trd_dt,
                            l_comp,
                            l_exch,
                            l_qty_trd,
                            l_wap,
                            l_price_lot,
                            l_net,
                            l_net_app,
                            l_sold,
                            l_note,
                        ) = lot
                        open_qty = l_qty_trd - l_sold

                        if l_sold > 0:
                            # Partially sold lot: Lock the history for the sold portion
                            locked_net = (l_net / l_qty_trd) * l_sold
                            locked_net_app = (l_net_app / l_qty_trd) * l_sold
                            locked_price_lot = (
                                (l_price_lot / l_qty_trd) * l_sold
                                if l_price_lot
                                else 0.0
                            )

                            cursor.execute(
                                """
                                UPDATE transactions
                                SET qty_trd = ?, net_amt_trd = ?, net_amt_trd_applicable = ?, price_lot_trd = ?
                                WHERE id_trd = ?
                                """,
                                (
                                    l_sold,
                                    locked_net,
                                    locked_net_app,
                                    locked_price_lot,
                                    l_id_trd,
                                ),
                            )

                            # Insert the new bifurcated open lot with reduced cost basis
                            new_net = (
                                (l_net / l_qty_trd)
                                * open_qty
                                * retention_multiplier
                            )
                            new_net_app = (
                                (l_net_app / l_qty_trd)
                                * open_qty
                                * retention_multiplier
                            )
                            new_price_lot = (
                                (l_price_lot / l_qty_trd)
                                * open_qty
                                * retention_multiplier
                                if l_price_lot
                                else 0.0
                            )
                            new_wap = l_wap * retention_multiplier

                            cursor.execute(
                                """INSERT INTO transactions (id_stk, cont_no, trd_dt, company_name, trade_type_trd, exchange, qty_trd, wap_unit_trd, price_lot_trd, net_amt_trd, net_amt_trd_applicable, note_trd)
                                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                                (
                                    id_parent,
                                    l_cont_no,
                                    l_trd_dt,
                                    l_comp,
                                    "BUY",
                                    l_exch,
                                    open_qty,
                                    new_wap,
                                    new_price_lot,
                                    new_net,
                                    new_net_app,
                                    l_note + " [Demerger Adj]",
                                ),
                            )
                        else:
                            # Completely unsold lot: Just apply the multiplier to lower the cost basis
                            cursor.execute(
                                """UPDATE transactions
                                   SET net_amt_trd = net_amt_trd * ?, net_amt_trd_applicable = net_amt_trd_applicable * ?, price_lot_trd = price_lot_trd * ?, wap_unit_trd = wap_unit_trd * ?
                                   WHERE id_trd = ?""",
                                (
                                    retention_multiplier,
                                    retention_multiplier,
                                    retention_multiplier,
                                    retention_multiplier,
                                    l_id_trd,
                                ),
                            )

                    # Dummy audit trail for the deducted capital
                    cont_p = f"DEM_DED_{id_dem}"
                    cursor.execute(
                        "INSERT INTO contracts (cont_no, trd_dt, settle_no, settle_dt, no_of_trades, net_amt_cont, net_amt_cont_applicable) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (
                            cont_p,
                            rec_dt,
                            settle_base,
                            rec_dt,
                            1,
                            total_deduction,
                            total_deduction,
                        ),
                    )
                    cursor.execute(
                        """INSERT INTO transactions (id_stk, cont_no, trd_dt, company_name, trade_type_trd, exchange, qty_trd, wap_unit_trd, price_lot_trd, net_amt_trd, net_amt_trd_applicable, note_trd)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            id_parent,
                            cont_p,
                            rec_dt,
                            p_comp,
                            "SELL",
                            exchange_var.get(),
                            0,
                            0.0,
                            total_deduction,
                            total_deduction,
                            total_deduction,
                            "Demerger CoA Deduction Audit",
                        ),
                    )
                    parent_adjustment_trd_id = cursor.lastrowid
                    cursor.execute(
                        """
                        UPDATE demerger_events
                        SET parent_adjustment_trd_id = ?
                        WHERE id_demerger = ?
                        """,
                        (parent_adjustment_trd_id, id_dem),
                    )

                # 4. Child Allotments (Reordered to grab tx_id and id_trd first)
                for i, data in enumerate(allotment_data):
                    cont_c = f"DEM_ALT_{id_dem}_{i}"
                    tx_id = None
                    id_trd = None

                    # 4a. Computed Bank Entry for Fractional Refund (Get tx_id) using dynamic Refund Date
                    if data["refund"] > 0:
                        cursor.execute(
                            """INSERT INTO computed_bank (cont_no, comp_bt_dt, comp_bt_type, comp_bt_amt, comp_bt_amt_applicable, comp_bt_desc)
                               VALUES (?, ?, ?, ?, ?, ?)""",
                            (
                                cont_c,
                                data["refund_dt"],
                                "CREDIT",
                                data["refund"],
                                data["refund"],
                                f"Fractional share refund from {data['c_comp_name']} demerger allotment",
                            ),
                        )
                        tx_id = cursor.lastrowid

                    # 4b. Allotment Transactions (Get id_trd) preventing negative cost basis
                    net_transferred = max(0.0, data["t_cost"] - data["refund"])
                    if data["a_qty"] > 0 or net_transferred > 0:
                        cursor.execute(
                            "INSERT INTO contracts (cont_no, trd_dt, settle_no, settle_dt, no_of_trades, net_amt_cont, net_amt_cont_applicable) VALUES (?, ?, ?, ?, ?, ?, ?)",
                            (
                                cont_c,
                                rec_dt,
                                settle_base + i + 1,
                                rec_dt,
                                1,
                                net_transferred,
                                net_transferred,
                            ),
                        )
                        wap = (
                            (net_transferred / data["a_qty"])
                            if data["a_qty"] > 0
                            else 0.0
                        )
                        cursor.execute(
                            """INSERT INTO transactions (id_stk, cont_no, trd_dt, company_name, trade_type_trd, exchange, qty_trd, wap_unit_trd, price_lot_trd, net_amt_trd, net_amt_trd_applicable, note_trd)
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                            (
                                data["id_child"],
                                cont_c,
                                rec_dt,
                                data["c_comp_name"],
                                "BUY",
                                exchange_var.get(),
                                data["a_qty"],
                                wap,
                                net_transferred,
                                net_transferred,
                                net_transferred,
                                "Demerger Allotment",
                            ),
                        )
                        id_trd = cursor.lastrowid

                    # 4c. Insert Allotment Record WITH the new foreign keys
                    cursor.execute(
                        """INSERT INTO demerger_allotments (id_demerger, id_stk_child, id_trd, id_comp_bt, ratio_parent, ratio_child, coa_percent, allotted_qty, transferred_cost, refund_amt)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            id_dem,
                            data["id_child"],
                            id_trd,
                            tx_id,
                            data["p_ratio"],
                            data["c_ratio"],
                            data["coa_pct"],
                            data["a_qty"],
                            data["t_cost"],
                            data["refund"],
                        ),
                    )

                conn.commit()

            # Recalculate Averages
            compute_avg_price(id_parent)
            for data in allotment_data:
                compute_avg_price(data["id_child"])

            resp = show_colorful_yesno(
                dem_win,
                "Success",
                f"Demerger recorded for {p_comp}.\n\nDo you want to add another?",
            )
            if resp:
                _close_demerger()  # For complexity, easiest reset is reopening
                add_demerger(parent)
            else:
                _close_demerger()

        except sqlite3.Error as e:
            logger.error("DB Error in Demerger: %s", e)
            show_colorful_error(
                dem_win, "Database Error", f"Failed to save: {e}"
            )

    def _close_demerger(_event=None):
        if _event and hasattr(_event, "widget") and _event.widget:
            try:
                if _event.widget.winfo_toplevel() != dem_win:
                    return
            except tk.TclError:
                pass
        return safe_close_modal(dem_win, parent, calling_button)

    # --- UI LAYOUT ---
    tk.Label(
        dem_win,
        text="✂️ CORPORATE DEMERGER ENTRY ✂️",
        font=("Comic Sans MS", 18, "bold"),
        bg=headbg,
        fg=titlefg,
        pady=8,
    ).pack(fill="x")
    main_frame = tk.Frame(
        dem_win, bg=mainfrbg, padx=15, pady=10, relief="raised", bd=2
    )
    main_frame.pack(fill="both", expand=True, padx=10, pady=10)

    # 1. Parent Identification Frame
    p_frame = tk.Frame(
        main_frame, bg=compfrbg, relief="groove", bd=2, padx=10, pady=10
    )
    p_frame.pack(fill="x", pady=(0, 10))
    tk.Label(
        p_frame,
        text="Parent Company",
        bg=compfrbg,
        font=("Helvetica", 13, "bold"),
        fg=headbg,
    ).grid(row=0, column=0, sticky="w", pady=5)

    parent_combo = ttk.Combobox(
        p_frame,
        textvariable=parent_name_var,
        values=companies,
        width=30,
        font=("Helvetica", 13),
    )
    parent_combo.grid(row=0, column=1, padx=15, pady=5)
    progressive_selection(parent_combo, companies)
    parent_name_var.trace_add("write", _update_parent_holdings)
    apply_entry_theme(parent_combo)

    tk.Button(
        p_frame,
        text="➕ New Co.",
        font=("Helvetica", 10, "bold"),
        bg=submitusualbg,
        fg="white",
        cursor="hand2",
        command=_invoke_add_company,
    ).grid(row=0, column=2, padx=5)

    tk.Label(
        p_frame, text="Exchange:", bg=compfrbg, font=("Helvetica", 12, "bold")
    ).grid(row=0, column=3, padx=(20, 5), rowspan=2)
    tk.Radiobutton(
        p_frame, text="NSE", variable=exchange_var, value="NSE", bg=compfrbg
    ).grid(row=0, column=4, sticky="w")
    tk.Radiobutton(
        p_frame, text="BSE", variable=exchange_var, value="BSE", bg=compfrbg
    ).grid(row=1, column=4, sticky="w")

    # 2. Dates Frame (Moved UP)
    d_frame = tk.Frame(
        main_frame, bg=compfrbg, relief="ridge", bd=2, padx=10, pady=10
    )
    d_frame.pack(fill="x", pady=(0, 10))
    tk.Label(
        d_frame,
        text="Record Date",
        bg=compfrbg,
        font=("Helvetica", 12, "bold"),
    ).pack(side="left")
    rec_dt_entry = DateEntry(
        d_frame, date_pattern="dd-mm-yyyy", font=("Helvetica", 12), width=12
    )
    rec_dt_entry.pack(side="left", padx=10)
    # rec_dt_entry.bind("<<DateEntrySelected>>", _update_parent_holdings)
    # rec_dt_entry.bind("<FocusOut>", _update_parent_holdings, add="+")
    apply_entry_theme(rec_dt_entry)

    tk.Label(
        d_frame,
        text="Ex-Date / Allotment",
        bg=compfrbg,
        font=("Helvetica", 12, "bold"),
    ).pack(side="left", padx=(20, 0))
    ex_dt_entry = DateEntry(
        d_frame, date_pattern="dd-mm-yyyy", font=("Helvetica", 12), width=12
    )
    ex_dt_entry.pack(side="left", padx=10)
    ex_dt_entry.bind("<<DateEntrySelected>>", _update_parent_holdings)
    ex_dt_entry.bind("<FocusOut>", _update_parent_holdings, add="+")

    apply_entry_theme(ex_dt_entry)

    bind_date_spin(rec_dt_entry)
    bind_date_spin(ex_dt_entry, callback=_update_parent_holdings)

    # 3. Financial Snapshot Frame (Moved DOWN)
    snap_frame = tk.Frame(
        main_frame, bg=compfrbg, relief="groove", bd=2, padx=10, pady=10
    )
    snap_frame.pack(fill="x", pady=(0, 10))

    tk.Label(
        snap_frame,
        text="Held Qty:",
        bg=compfrbg,
        font=("Helvetica", 12, "bold"),
        fg="#b91c1c",
    ).pack(side="left", pady=5)
    held_qty_entry = tk.Entry(
        snap_frame,
        textvariable=held_qty_var,
        width=12,
        font=("Helvetica", 12),
        state="readonly",
    )
    held_qty_entry.pack(side="left", padx=(5, 30))
    apply_entry_theme(held_qty_entry, is_readonly=True)

    tk.Label(
        snap_frame,
        text="Total Invested (₹):",
        bg=compfrbg,
        font=("Helvetica", 12, "bold"),
        fg="#b91c1c",
    ).pack(side="left")
    parent_inv_entry = tk.Entry(
        snap_frame,
        textvariable=parent_invested_var,
        width=15,
        font=("Helvetica", 12),
        state="readonly",
    )
    parent_inv_entry.pack(side="left", padx=5)
    apply_entry_theme(parent_inv_entry, is_readonly=True)

    # 3. Children Container
    c_wrapper = tk.Frame(
        main_frame, bg=childfrbg, relief="ridge", bd=2, padx=5, pady=5
    )
    c_wrapper.pack(fill="both", expand=True, pady=(0, 10))

    header = tk.Frame(c_wrapper, bg=childfrbg)
    header.pack(fill="x", pady=5)
    tk.Label(
        header,
        text="Spun-off Child Companies",
        font=("Helvetica", 13, "bold", "underline"),
        bg=childfrbg,
        fg=headbg,
    ).pack(side="left", padx=5)
    tk.Button(
        header,
        text="➕ Add Child Row",
        command=_add_child_row,
        bg="#059669",
        fg="white",
        font=("Helvetica", 10, "bold"),
    ).pack(side="right", padx=5)

    children_container = tk.Frame(c_wrapper, bg=childfrbg)
    children_container.pack(fill="both", expand=True)

    # Column Headers (Anchored strictly to Row 0 of children_container)
    tk.Label(
        children_container,
        text="Company",
        bg=childfrbg,
        font=("Helvetica", 10, "bold"),
    ).grid(row=0, column=0, padx=5, pady=5)
    tk.Label(
        children_container,
        text="Ratio (P:C)",
        bg=childfrbg,
        font=("Helvetica", 10, "bold"),
    ).grid(row=0, column=1, columnspan=3, padx=2, pady=5)
    tk.Label(
        children_container,
        text="CoA %",
        bg=childfrbg,
        font=("Helvetica", 10, "bold"),
    ).grid(row=0, column=4, padx=15, pady=5)
    tk.Label(
        children_container,
        text="Allotted Qty",
        bg=childfrbg,
        font=("Helvetica", 10, "bold"),
    ).grid(row=0, column=5, padx=10, pady=5)
    tk.Label(
        children_container,
        text="Transferred Cost",
        bg=childfrbg,
        font=("Helvetica", 10, "bold"),
    ).grid(row=0, column=6, padx=10, pady=5)
    tk.Label(
        children_container,
        text="Refund (₹)",
        bg=childfrbg,
        font=("Helvetica", 10, "bold"),
    ).grid(row=0, column=7, padx=5, pady=5)
    tk.Label(
        children_container,
        text="Refund Date",
        bg=childfrbg,
        font=("Helvetica", 10, "bold"),
    ).grid(row=0, column=8, padx=5, pady=5)

    # --- Tooltip Setup ---
    # MUST be defined before _add_child_row is called

    # Start with one row
    _add_child_row()

    bind_tooltip(
        parent_combo,
        tooltip_var,
        "Select the parent company undergoing the demerger.",
    )
    bind_tooltip(
        rec_dt_entry,
        tooltip_var,
        "The record date set to determine eligible shareholders.",
    )
    bind_tooltip(
        ex_dt_entry,
        tooltip_var,
        "The ex-date or allotment date for the spin-off.",
    )

    # Buttons
    btn_frame = tk.Frame(dem_win, pady=10, bg=btnfrbg, relief="ridge", bd=2)
    btn_frame.pack(fill="x", anchor="e", padx=10, pady=(0, 10))

    save_btn = tk.Button(
        btn_frame,
        text="🚀 Execute Demerger 🚀",
        command=_on_submit,
        font=("Comic Sans MS", 12, "bold"),
        bg="#22c55e",
        activebackground="#16a34a",
        activeforeground="white",
        fg="white",
        width=22,
    )
    save_btn.pack(side="right", padx=10)
    apply_button_animations(save_btn, "#22c55e", "#2563eb")
    cancel_btn = tk.Button(
        btn_frame,
        text="❌ Cancel ❌",
        command=_close_demerger,
        font=("Comic Sans MS", 12, "bold"),
        bg=cancelusualbg,
        activebackground=cancelactivebg,
        fg="white",
        width=12,
    )
    cancel_btn.pack(side="right", padx=5)

    def _focus_next(e):
        if e.widget.winfo_class() not in ("Button", "TCombobox"):
            e.widget.tk_focusNext().focus()
            return "break"

    dem_win.bind("<Return>", _focus_next)
    dem_win.bind("<Escape>", _close_demerger)
    dem_win.protocol("WM_DELETE_WINDOW", _close_demerger)
    parent_combo.focus_set()
    parent.wait_window(dem_win)
