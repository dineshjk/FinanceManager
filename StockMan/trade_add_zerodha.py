# -*- coding: utf-8 -*-
# StockMan/trade_add_zerodha.py

"""
trade_add_zerodha.py
--------------------
Dedicated Data Entry window and controller for Zerodha Contract Notes.

Handles:
- Consolidated Zerodha contract note format (CNT-...)
- Multiple ISIN trade rows with WAP and turnover
- Consolidated contract-level levies footer (STT, Stamp duty, ETC, GST, SEBI, etc.)
- Automatic proportionate levies bifurcation engine
- Atomic persistence into contracts, transactions, exchange_orders, and computed_bank
"""

from typing import Union, Callable, Optional
import tkinter as tk
from tkinter import ttk
import sqlite3
from datetime import datetime, date
from tkcalendar import DateEntry

from Shared.globals import (
    get_db_connection,
    logger,
    BROK,
    GST,
    SEBI,
    STT,
    get_etc,
)
from Shared.dialog_utils import (
    show_colorful_info,
    show_colorful_error,
    show_colorful_yesno,
)
from Shared.gui_utils import (
    bind_tooltip,
    apply_entry_theme,
    bind_date_spin,
    setup_footer_tooltip,
    universal_tree_sort,
    apply_button_animations,
)
from Shared.modal_utils import disable_parent, enable_parent
from Shared.window_manager import push_window, safe_close_modal
from Shared.gui_progressive import progressive_selection
from .date_utils import next_working_day
from .company_add import add_company
from .trade_utils import (
    compute_avg_price,
    enforce_no_oversell_for_stock,
    bifurcate_zerodha_levies,
)


def get_current_fy_prefix(d: Union[date, datetime]) -> str:
    """Return 'CNT-y1/y2-' for the Indian Financial Year (Apr-Mar) of the given date.

    In Indian Financial Year YYYY-(YYYY+1), y1 is the last two digits of YYYY
    and y2 is the last two digits of YYYY+1.
    For example, for dates in FY 2026-2027, returns 'CNT-26/27-'.
    """
    if hasattr(d, "date") and callable(getattr(d, "date")):
        d = d.date()
    if d.month >= 4:
        y1 = d.year % 100
        y2 = (d.year + 1) % 100
    else:
        y1 = (d.year - 1) % 100
        y2 = d.year % 100
    return f"CNT-{y1:02d}/{y2:02d}-"


def add_trade_zerodha(
    parent: Union[tk.Toplevel, tk.Tk],
    calling_button: Optional[tk.Widget] = None,
    on_switch_to_icici: Optional[Callable[[], None]] = None,
) -> None:
    """Launch the Zerodha Contract Note Data Entry modal window."""

    # Colors
    bg_win = "#f0f8ff"
    bg_header = "#0f172a"
    fg_title = "#38bdf8"
    bg_section = "#e0f2fe"
    bg_sub_sec = "#f8fafc"
    bg_table = "#ffffff"
    fg_label = "#1e293b"

    modal_id = disable_parent(parent, calling_button=calling_button)

    win = tk.Toplevel(parent)
    win.title("✨ Data Entry - Trade (Zerodha Contract) ✨")
    win.geometry("1180x880")
    win.minsize(1080, 720)
    win.resizable(True, True)
    win.configure(bg=bg_win)
    win.transient(parent)
    win.grab_set()
    win.focus_set()

    try:
        push_window(win, parent)
    except (RuntimeError, tk.TclError) as exc:
        logger.debug("push_window failed: %s", exc)

    tooltip_var = setup_footer_tooltip(win)

    def cleanup_and_close(_event=None):
        return safe_close_modal(win, parent, calling_button)

    # ── State ─────────────────────────────────────────────────────────────
    # List of trades currently added to this contract: each is a dict
    trades_list: list[dict] = []
    editing_trade_idx = [-1]  # -1 means adding a new trade, >= 0 means editing
    obligation_var = tk.StringVar(value="0.00")
    gross_obligation_display_var = tk.StringVar(value="₹ 0.00")

    # ── 1. Header Frame ───────────────────────────────────────────────────
    header_frame = tk.Frame(win, bg=bg_header, relief="raised", bd=3)
    header_frame.pack(fill="x", padx=6, pady=(6, 2))

    tk.Label(
        header_frame,
        text="✨ Data Entry - Trade (Zerodha Contract Note) ✨",
        font=("Helvetica", 16, "bold"),
        bg=bg_header,
        fg=fg_title,
    ).pack(side="left", padx=15, pady=8)

    # Broker Mode Switcher
    broker_switch_frame = tk.Frame(header_frame, bg=bg_header)
    broker_switch_frame.pack(side="right", padx=15)

    tk.Label(
        broker_switch_frame,
        text="Broker:",
        font=("Helvetica", 12, "bold"),
        bg=bg_header,
        fg="white",
    ).pack(side="left", padx=(0, 5))

    def _on_switch_icici():
        if trades_list:
            if not show_colorful_yesno(
                win,
                "Discard Changes?",
                "You have entered trades in this Zerodha contract.\nSwitching to ICICI mode will discard them.\n\nContinue?",
            ):
                return
        cleanup_and_close()
        if on_switch_to_icici:
            on_switch_to_icici()

    switch_icici_btn = tk.Button(
        broker_switch_frame,
        text="Switch to ICICI Securities ➡️",
        font=("Helvetica", 10, "bold"),
        bg="#1e3a8a",
        fg="white",
        activebackground="#2563eb",
        command=_on_switch_icici,
        cursor="hand2",
        padx=8,
        pady=2,
    )
    switch_icici_btn.pack(side="left", padx=5)

    # ── Main Content Body ─────────────────────────────────────────────────
    main_frame = tk.Frame(win, bg=bg_win)
    main_frame.pack(fill="both", expand=True, padx=6, pady=2)

    # ── 1. Contract Header Section ────────────────────────────────────────
    cont_box = tk.LabelFrame(
        main_frame,
        text="  Contract Note Header  ",
        font=("Helvetica", 12, "bold"),
        bg=bg_section,
        fg=bg_header,
        relief="groove",
        bd=2,
        padx=12,
        pady=6,
    )
    cont_box.pack(fill="x", padx=10, pady=4)

    hdr_grid = tk.Frame(cont_box, bg=bg_section)
    hdr_grid.pack(fill="x", pady=2)
    hdr_grid.grid_columnconfigure(0, weight=0)
    hdr_grid.grid_columnconfigure(1, weight=1)
    hdr_grid.grid_columnconfigure(2, weight=0)
    hdr_grid.grid_columnconfigure(3, weight=1)

    # Row 0: Contract No & Trade Date
    tk.Label(hdr_grid, text="Contract No:", font=("Helvetica", 11, "bold"), bg=bg_section, fg=fg_label).grid(
        row=0, column=0, sticky="w", padx=(4, 6), pady=3
    )
    initial_cont_prefix = get_current_fy_prefix(datetime.now().date())
    cont_no_var = tk.StringVar(value=initial_cont_prefix)
    cont_no_entry = tk.Entry(hdr_grid, textvariable=cont_no_var, font=("Helvetica", 11, "bold"))
    cont_no_entry.grid(row=0, column=1, sticky="ew", padx=(0, 25), pady=3)
    cont_no_entry.icursor(tk.END)
    bind_tooltip(cont_no_entry, tooltip_var, f"Zerodha Contract Note Number, e.g. '{initial_cont_prefix}96502367'")

    def _check_auto_icici_switch(_event=None):
        val = cont_no_var.get().strip().upper()
        if val.startswith("ISEC"):
            win.after(100, _on_switch_icici)
    cont_no_entry.bind("<KeyRelease>", _check_auto_icici_switch, add="+")

    tk.Label(hdr_grid, text="Trade Date:", font=("Helvetica", 11, "bold"), bg=bg_section, fg=fg_label).grid(
        row=0, column=2, sticky="w", padx=(10, 6), pady=3
    )
    trd_dt_entry = DateEntry(hdr_grid, date_pattern="dd-mm-yyyy", font=("Helvetica", 11))
    trd_dt_entry.grid(row=0, column=3, sticky="ew", padx=(0, 10), pady=3)
    bind_date_spin(trd_dt_entry)
    bind_tooltip(trd_dt_entry, tooltip_var, "Date on which trades took place.")

    # Row 1: Settlement No & Settlement Date
    tk.Label(hdr_grid, text="Settlement No:", font=("Helvetica", 11, "bold"), bg=bg_section, fg=fg_label).grid(
        row=1, column=0, sticky="w", padx=(4, 6), pady=3
    )
    settle_no_var = tk.StringVar(value="0")
    settle_no_entry = tk.Entry(hdr_grid, textvariable=settle_no_var, font=("Helvetica", 11, "bold"))
    settle_no_entry.grid(row=1, column=1, sticky="ew", padx=(0, 25), pady=3)
    bind_tooltip(settle_no_entry, tooltip_var, "Settlement Number from Zerodha Contract Note.")

    tk.Label(hdr_grid, text="Settlement Date:", font=("Helvetica", 11, "bold"), bg=bg_section, fg=fg_label).grid(
        row=1, column=2, sticky="w", padx=(10, 6), pady=3
    )
    settle_dt_entry = DateEntry(hdr_grid, date_pattern="dd-mm-yyyy", font=("Helvetica", 11))
    settle_dt_entry.grid(row=1, column=3, sticky="ew", padx=(0, 10), pady=3)
    bind_date_spin(settle_dt_entry)
    bind_tooltip(settle_dt_entry, tooltip_var, "Settlement Date for pay-in/pay-out.")

    # Auto-adjust settle date and prefix when trade date changes
    def _on_trd_dt_change(_event=None):
        try:
            t_dt = trd_dt_entry.get_date()
            s_dt = next_working_day(t_dt)
            settle_dt_entry.set_date(s_dt)

            cur_cont = cont_no_var.get().strip()
            new_prefix = get_current_fy_prefix(t_dt)
            if not cur_cont or cur_cont.startswith("CNT-"):
                parts = cur_cont.split("-")
                if len(parts) <= 2 or (len(parts) == 3 and not parts[2]):
                    cont_no_var.set(new_prefix)
                elif len(parts) == 3 and parts[2]:
                    cont_no_var.set(f"{new_prefix}{parts[2]}")

            if "_recalculate_default_levies" in globals() or "_recalculate_default_levies" in locals():
                _recalculate_default_levies()
        except Exception:
            pass
    trd_dt_entry.bind("<<DateEntrySelected>>", _on_trd_dt_change)

    # Row 2: Contract Note / Remark
    tk.Label(hdr_grid, text="Contract Note / Remark:", font=("Helvetica", 10), bg=bg_section, fg=fg_label).grid(
        row=2, column=0, sticky="w", padx=(4, 6), pady=(4, 2)
    )
    note_cont_var = tk.StringVar()
    note_cont_entry = tk.Entry(hdr_grid, textvariable=note_cont_var, font=("Helvetica", 10))
    note_cont_entry.grid(row=2, column=1, columnspan=3, sticky="ew", padx=(0, 10), pady=(4, 2))

    # ── 2. Trades Entry Section (ISIN / Security Row) ─────────────────────
    trades_box = tk.LabelFrame(
        main_frame,
        text="  Trades in this Contract (One row per ISIN)  ",
        font=("Helvetica", 12, "bold"),
        bg="#fef3c7",
        fg=bg_header,
        relief="groove",
        bd=2,
        padx=10,
        pady=6,
    )
    trades_box.pack(fill="x", padx=10, pady=4)

    # Lookup data from stocks
    company_names = []
    company_to_id = {}
    company_to_isin = {}
    company_to_etf = {}

    def _reload_stock_lookups():
        nonlocal company_names, company_to_id, company_to_isin, company_to_etf
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id_stk, company_name, isin, is_etf FROM stocks ORDER BY company_name ASC")
                rows = cursor.fetchall()
                company_names = [r[1] for r in rows]
                company_to_id = {r[1]: r[0] for r in rows}
                company_to_isin = {r[1]: (r[2] or "") for r in rows}
                company_to_etf = {r[1]: bool(r[3]) for r in rows}
        except sqlite3.Error as e:
            logger.error("Failed to load stocks for Zerodha trade entry: %s", e)

    _reload_stock_lookups()

    tr_input_frame = tk.Frame(trades_box, bg="#fef3c7")
    tr_input_frame.pack(fill="x", pady=2)

    # Company selection
    tk.Label(tr_input_frame, text="Company / Symbol:", font=("Helvetica", 11, "bold"), bg="#fef3c7").grid(row=0, column=0, sticky="w", padx=4, pady=2)
    company_var = tk.StringVar()
    company_combo = ttk.Combobox(tr_input_frame, textvariable=company_var, values=company_names, width=36, font=("Helvetica", 11, "bold"))
    company_combo.grid(row=0, column=1, sticky="w", padx=4, pady=2)
    progressive_selection(company_combo, company_names)

    # ISIN
    tk.Label(tr_input_frame, text="ISIN:", font=("Helvetica", 11), bg="#fef3c7").grid(row=0, column=2, sticky="w", padx=4, pady=2)
    isin_var = tk.StringVar()
    isin_entry = tk.Entry(tr_input_frame, textvariable=isin_var, width=15, font=("Helvetica", 11), state="readonly")
    isin_entry.grid(row=0, column=3, sticky="w", padx=4, pady=2)

    def _on_company_select(_event=None):
        name = company_var.get().strip()
        if name in company_to_isin:
            isin_var.set(company_to_isin[name])
        else:
            isin_var.set("")
    company_combo.bind("<<ComboboxSelected>>", _on_company_select)
    company_combo.bind("<FocusOut>", _on_company_select)

    # Type: BUY / SELL
    tk.Label(tr_input_frame, text="Type:", font=("Helvetica", 11, "bold"), bg="#fef3c7").grid(row=0, column=4, sticky="w", padx=4, pady=2)
    type_var = tk.StringVar(value="BUY")
    type_combo = ttk.Combobox(tr_input_frame, textvariable=type_var, values=["BUY", "SELL"], width=6, state="readonly", font=("Helvetica", 11, "bold"))
    type_combo.grid(row=0, column=5, sticky="w", padx=4, pady=2)

    # Exchange: NSE / BSE
    tk.Label(tr_input_frame, text="Exchange:", font=("Helvetica", 11), bg="#fef3c7").grid(row=0, column=6, sticky="w", padx=4, pady=2)
    exchange_var = tk.StringVar(value="NSE")
    exchange_combo = ttk.Combobox(tr_input_frame, textvariable=exchange_var, values=["NSE", "BSE"], width=6, state="readonly", font=("Helvetica", 11))
    exchange_combo.grid(row=0, column=7, sticky="w", padx=4, pady=2)

    # Row 1 of Trade Input: Qty, WAP, Lot Price, Brok/u, Sell Chrg
    tr_input_r1 = tk.Frame(trades_box, bg="#fef3c7")
    tr_input_r1.pack(fill="x", pady=4)

    tk.Label(tr_input_r1, text="Quantity:", font=("Helvetica", 11, "bold"), bg="#fef3c7").pack(side="left", padx=(4, 2))
    qty_var = tk.StringVar(value="1")
    qty_entry = tk.Entry(tr_input_r1, textvariable=qty_var, width=8, font=("Helvetica", 11, "bold"))
    qty_entry.pack(side="left", padx=(0, 15))

    tk.Label(tr_input_r1, text="WAP (₹):", font=("Helvetica", 11, "bold"), bg="#fef3c7").pack(side="left", padx=(4, 2))
    wap_var = tk.StringVar(value="0.00")
    wap_entry = tk.Entry(tr_input_r1, textvariable=wap_var, width=11, font=("Helvetica", 11, "bold"))
    wap_entry.pack(side="left", padx=(0, 15))

    # Auto lot price label
    tk.Label(tr_input_r1, text="Turnover (₹):", font=("Helvetica", 11), bg="#fef3c7").pack(side="left", padx=(4, 2))
    lot_price_lbl_var = tk.StringVar(value="0.00")
    lot_price_lbl = tk.Label(tr_input_r1, textvariable=lot_price_lbl_var, font=("Helvetica", 11, "bold"), bg="#fef3c7", fg="#1e40af")
    lot_price_lbl.pack(side="left", padx=(0, 15))

    def _update_lot_price(*_args):
        try:
            q = int(qty_var.get().strip() or "0")
            w = float(wap_var.get().strip() or "0.0")
            lot_price_lbl_var.set(f"{q * w:,.2f}")
        except ValueError:
            lot_price_lbl_var.set("0.00")
    qty_var.trace_add("write", _update_lot_price)
    wap_var.trace_add("write", _update_lot_price)

    tk.Label(tr_input_r1, text="Brok/sh (₹):", font=("Helvetica", 10), bg="#fef3c7").pack(side="left", padx=(4, 2))
    brok_unit_var = tk.StringVar(value="0.00")
    brok_unit_entry = tk.Entry(tr_input_r1, textvariable=brok_unit_var, width=7, font=("Helvetica", 10))
    brok_unit_entry.pack(side="left", padx=(0, 15))
    bind_tooltip(brok_unit_entry, tooltip_var, "Brokerage per share (₹0 on Zerodha equity delivery).")

    tk.Label(tr_input_r1, text="Sell/DP Chrg (₹):", font=("Helvetica", 10), bg="#fef3c7").pack(side="left", padx=(4, 2))
    sell_chrg_var = tk.StringVar(value="0.00")
    sell_chrg_entry = tk.Entry(tr_input_r1, textvariable=sell_chrg_var, width=8, font=("Helvetica", 10))
    sell_chrg_entry.pack(side="left", padx=(0, 10))
    bind_tooltip(sell_chrg_entry, tooltip_var, "Specific DP / Sell charge for this scrip (e.g. ₹15.93).")

    # Trade Buttons
    tr_btn_bar = tk.Frame(trades_box, bg="#fef3c7")
    tr_btn_bar.pack(fill="x", pady=(4, 6))

    def _clear_trade_inputs():
        editing_trade_idx[0] = -1
        company_var.set("")
        isin_var.set("")
        type_var.set("BUY")
        exchange_var.set("NSE")
        qty_var.set("1")
        wap_var.set("0.00")
        brok_unit_var.set("0.00")
        sell_chrg_var.set("0.00")
        add_tr_btn.config(text="➕ Add Trade to Contract", bg="#22c55e")
        company_combo.focus_set()

    def _render_trades_tree():
        for item in tr_tree.get_children():
            tr_tree.delete(item)

        b_tot = 0.0
        s_tot = 0.0
        for i, t in enumerate(trades_list):
            turnover = t["qty"] * t["wap"]
            if t["trade_type"] == "BUY":
                b_tot += turnover
            else:
                s_tot += turnover
            tr_tree.insert(
                "",
                "end",
                iid=str(i),
                values=(
                    i + 1,
                    t["company_name"],
                    t["isin"],
                    t["trade_type"],
                    t["exchange"],
                    t["qty"],
                    f"{t['wap']:.4f}",
                    f"{turnover:,.2f}",
                    f"{t['brok_unit']:.4f}",
                    f"{t['sell_chrg']:.2f}",
                ),
            )

        # Update Summary line
        net_ob = b_tot - s_tot
        ob_type = "Pay-in (Outflow)" if net_ob >= 0 else "Pay-out (Inflow)"
        summary_lbl_var.set(
            f"Total Trades: {len(trades_list)}  |  "
            f"Buy Turnover: ₹ {b_tot:,.2f}  |  "
            f"Sell Turnover: ₹ {s_tot:,.2f}  |  "
            f"Gross Obligation: ₹ {abs(net_ob):,.2f} {ob_type}"
        )
        obligation_var.set(f"{net_ob:.2f}")
        gross_obligation_display_var.set(f"₹ {abs(net_ob):,.2f} ({ob_type})")
        _recalculate_default_levies()

    def _on_add_or_update_trade():
        c_name = company_var.get().strip()
        if not c_name:
            show_colorful_error(win, "Validation Error", "Please select or enter a Company / Symbol.")
            company_combo.focus_set()
            return

        # Check if company exists in stocks table
        if c_name not in company_to_id:
            prompt = show_colorful_yesno(
                win,
                "Company Not Found",
                f"The company '{c_name}' does not exist in the database.\n\nWould you like to add it now?",
            )
            if prompt:
                add_company(win, initial_company_name=c_name)
                _reload_stock_lookups()
                company_combo["values"] = company_names
                progressive_selection(company_combo, company_names)
                if c_name not in company_to_id:
                    show_colorful_error(win, "Company Required", f"Company '{c_name}' was not created.")
                    return
            else:
                return

        id_stk = company_to_id[c_name]
        isin = company_to_isin.get(c_name, "")
        is_etf = company_to_etf.get(c_name, False)

        try:
            qty = int(qty_var.get().strip())
            if qty <= 0:
                raise ValueError()
        except ValueError:
            show_colorful_error(win, "Validation Error", "Quantity must be a positive integer.")
            qty_entry.focus_set()
            return

        try:
            wap = float(wap_var.get().strip())
            if wap <= 0:
                raise ValueError()
        except ValueError:
            show_colorful_error(win, "Validation Error", "WAP must be a positive number.")
            wap_entry.focus_set()
            return

        try:
            b_unit = float(brok_unit_var.get().strip() or "0.0")
        except ValueError:
            b_unit = 0.0

        try:
            s_chrg = float(sell_chrg_var.get().strip() or "0.0")
        except ValueError:
            s_chrg = 0.0

        trade_dict = {
            "id_stk": id_stk,
            "company_name": c_name,
            "isin": isin,
            "is_etf": is_etf,
            "trade_type": type_var.get(),
            "exchange": exchange_var.get(),
            "qty": qty,
            "wap": wap,
            "brok_unit": b_unit,
            "sell_chrg": s_chrg,
            "note_trd": "",
        }

        if editing_trade_idx[0] >= 0:
            trades_list[editing_trade_idx[0]] = trade_dict
        else:
            trades_list.append(trade_dict)

        _render_trades_tree()
        _clear_trade_inputs()

    add_tr_btn = tk.Button(
        tr_btn_bar,
        text="➕ Add Trade to Contract",
        command=_on_add_or_update_trade,
        font=("Helvetica", 11, "bold"),
        bg="#22c55e",
        fg="white",
        activebackground="#16a34a",
        cursor="hand2",
        padx=12,
        pady=3,
    )
    add_tr_btn.pack(side="left", padx=5)

    def _on_delete_trade():
        sel = tr_tree.selection()
        if not sel:
            show_colorful_error(win, "Selection Error", "Please select a trade from the table to remove.")
            return
        idx = int(sel[0])
        del trades_list[idx]
        _render_trades_tree()
        _clear_trade_inputs()

    del_tr_btn = tk.Button(
        tr_btn_bar,
        text="🗑️ Remove Selected Trade",
        command=_on_delete_trade,
        font=("Helvetica", 10, "bold"),
        bg="#ef4444",
        fg="white",
        activebackground="#dc2626",
        cursor="hand2",
        padx=8,
        pady=3,
    )
    del_tr_btn.pack(side="left", padx=5)

    clear_tr_btn = tk.Button(
        tr_btn_bar,
        text="🧹 Clear Fields",
        command=_clear_trade_inputs,
        font=("Helvetica", 10),
        bg="#e2e8f0",
        cursor="hand2",
        padx=8,
        pady=3,
    )
    clear_tr_btn.pack(side="left", padx=5)

    # Treeview for Trades in this Contract
    tree_frame = tk.Frame(trades_box, bg=bg_table, bd=1, relief="ridge")
    tree_frame.pack(fill="both", expand=True, pady=4)

    tr_scroll = ttk.Scrollbar(tree_frame, orient="vertical")
    tr_scroll.pack(side="right", fill="y")

    tr_cols = ("#", "Company", "ISIN", "Type", "Exch", "Qty", "WAP", "Turnover (₹)", "Brok/sh (₹)", "Sell Chrg (₹)")
    tr_tree = ttk.Treeview(
        tree_frame,
        columns=tr_cols,
        show="headings",
        height=5,
        yscrollcommand=tr_scroll.set,
    )
    tr_scroll.config(command=tr_tree.yview)

    tr_col_widths = {
        "#": (40, "center", False),
        "Company": (260, "w", True),
        "ISIN": (130, "center", False),
        "Type": (75, "center", False),
        "Exch": (65, "center", False),
        "Qty": (75, "e", False),
        "WAP": (95, "e", False),
        "Turnover (₹)": (140, "e", True),
        "Brok/sh (₹)": (90, "e", False),
        "Sell Chrg (₹)": (100, "e", False),
    }
    for col, (w, anch, st) in tr_col_widths.items():
        tr_tree.heading(col, text=col, command=lambda c=col: universal_tree_sort(tr_tree, c, False))
        tr_tree.column(col, width=w, anchor=anch, stretch=st)

    tr_tree.pack(fill="both", expand=True)

    def _on_tree_select(_event=None):
        sel = tr_tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        if idx < len(trades_list):
            t = trades_list[idx]
            editing_trade_idx[0] = idx
            company_var.set(t["company_name"])
            isin_var.set(t["isin"])
            type_var.set(t["trade_type"])
            exchange_var.set(t["exchange"])
            qty_var.set(str(t["qty"]))
            wap_var.set(str(t["wap"]))
            brok_unit_var.set(str(t["brok_unit"]))
            sell_chrg_var.set(str(t["sell_chrg"]))
            add_tr_btn.config(text=f"✏️ Update Trade #{idx + 1}", bg="#3b82f6")

    tr_tree.bind("<<TreeviewSelect>>", _on_tree_select)

    # Summary Line
    summary_lbl_var = tk.StringVar(value="Total Trades: 0  |  Buy Turnover: ₹ 0.00  |  Sell Turnover: ₹ 0.00  |  Gross Obligation: ₹ 0.00")
    summary_lbl = tk.Label(
        trades_box,
        textvariable=summary_lbl_var,
        font=("Helvetica", 11, "bold"),
        bg="#fef3c7",
        fg="#0f766e",
    )
    summary_lbl.pack(anchor="w", pady=(2, 0))

    # ── 3. Statutory Levies & Charges (Contract Note Footer) ─────────────
    levies_box = tk.LabelFrame(
        main_frame,
        text="  Statutory Levies & Charges (Contract Note Footer)  ",
        font=("Helvetica", 12, "bold"),
        bg="#ede9fe",
        fg=bg_header,
        relief="groove",
        bd=2,
        padx=12,
        pady=6,
    )
    levies_box.pack(fill="x", padx=10, pady=6)

    # Grid of levies inputs: 5 rows x 2 fields per row (4 columns total: Label 1, Entry 1, Label 2, Entry 2)
    lg_frame = tk.Frame(levies_box, bg="#ede9fe")
    lg_frame.pack(fill="x", pady=4)

    lg_frame.grid_columnconfigure(0, weight=0)
    lg_frame.grid_columnconfigure(1, weight=1)
    lg_frame.grid_columnconfigure(2, weight=0)
    lg_frame.grid_columnconfigure(3, weight=1)

    def _make_levy_field(parent_f, r, c_pair, label_text, var, tooltip="", is_bold=False):
        c_lbl = c_pair * 2
        c_ent = c_pair * 2 + 1
        lbl = tk.Label(
            parent_f,
            text=label_text,
            font=("Helvetica", 11, "bold" if is_bold else "normal"),
            bg="#ede9fe",
            fg=fg_label,
        )
        lbl.grid(row=r, column=c_lbl, sticky="w", padx=(10, 6), pady=4)
        ent = tk.Entry(
            parent_f,
            textvariable=var,
            font=("Helvetica", 11, "bold"),
            justify="right",
        )
        ent.grid(row=r, column=c_ent, sticky="ew", padx=(0, 20 if c_pair == 0 else 10), pady=4)
        if tooltip:
            bind_tooltip(ent, tooltip_var, tooltip)
        return ent

    # Variables for Levies & Obligations (Fields a through j)
    payin_payout_var = tk.StringVar(value="0.00")         # a. Pay in Pay Out
    taxable_val_var = tk.StringVar(value="0.00")          # b. Taxable Value (sum of brok + 0.01)
    etc_cont_var = tk.StringVar(value="0.00")             # c. ETC (formula as in trade_add)
    clearing_var = tk.StringVar(value="0.00")             # d. Clearing Charges (0.00)
    gst_var = tk.StringVar(value="0.00")                  # e. GST (18% default)
    igst_var = tk.StringVar(value="0.00")                 # f. IGST (0.00)
    stt_var = tk.StringVar(value="0")                     # g. STT (default value as in ICICI trade_add)
    sebi_var = tk.StringVar(value="0.00")                 # h. SEBI (default value as in ICICI trade_add)
    stamp_var = tk.StringVar(value="0.00")                # i. Stamp Duty (0.00)
    net_client_amt_var = tk.StringVar(value="0.00")       # j. Net Amount Receivable/Payable by client

    total_levies_display_var = tk.StringVar(value="₹ 0.00")
    net_settlement_status_var = tk.StringVar(value="₹ 0.00  [Payable by Client (DEBIT / Outflow)]")

    # Row 0:
    # a. Pay in Pay Out
    payin_payout_entry = _make_levy_field(
        lg_frame, 0, 0, "Pay in / Pay Out (₹):", payin_payout_var,
        "Net Obligation from all ISIN trades: Total Buy Turnover - Total Sell Turnover.",
        is_bold=True,
    )
    # b. Taxable Value
    taxable_val_entry = _make_levy_field(
        lg_frame, 0, 1, "Taxable Value (₹):", taxable_val_var,
        "Taxable value of supply / brokerage (Default: sum of brokerage + 0.01).",
    )

    # Row 1:
    # c. ETC
    etc_cont_entry = _make_levy_field(
        lg_frame, 1, 0, "Exchange Trans. Charges (₹):", etc_cont_var,
        "Exchange Transaction Charges (Computed using applicable exchange rate).",
    )
    # d. Clearing Charges
    clearing_entry = _make_levy_field(
        lg_frame, 1, 1, "Clearing Charges (₹):", clearing_var,
        "Clearing Charges (Default: 0.00).",
    )

    # Row 2:
    # e. GST
    gst_entry = _make_levy_field(
        lg_frame, 2, 0, "GST (18%) (₹):", gst_var,
        "Consolidated Goods & Services Tax (Default: 18% of Taxable Value + ETC + SEBI).",
    )
    # f. IGST
    igst_entry = _make_levy_field(
        lg_frame, 2, 1, "IGST (₹):", igst_var,
        "Integrated GST if interstate (Default: 0.00).",
    )

    # Row 3:
    # g. STT
    stt_entry = _make_levy_field(
        lg_frame, 3, 0, "Securities Trans. Tax (₹):", stt_var,
        "Securities Transaction Tax (Default: 0.1% of non-ETF turnover, integer).",
    )
    # h. SEBI
    sebi_entry = _make_levy_field(
        lg_frame, 3, 1, "SEBI Turnover Fees (₹):", sebi_var,
        "SEBI Turnover Charges (Default: turnover * 0.000001).",
    )

    # Row 4:
    # i. Stamp Duty
    stamp_entry = _make_levy_field(
        lg_frame, 4, 0, "Stamp Duty (₹):", stamp_var,
        "State Stamp Duty (Default: 0.00).",
    )
    # j. Net Amount Receivable/Payable by client
    net_client_amt_entry = _make_levy_field(
        lg_frame, 4, 1, "Net Amt Rec/Pay by Client (₹):", net_client_amt_var,
        "Net Amount Receivable or Payable by client (Computed as per ICICI trade_add UI).",
        is_bold=True,
    )

    # Bottom summary of levies
    levies_summary_bar = tk.Frame(levies_box, bg="#ddd6fe", bd=1, relief="ridge", padx=10, pady=6)
    levies_summary_bar.pack(fill="x", pady=(8, 4))

    tk.Label(levies_summary_bar, text="Pay in / Pay Out Obligation:", font=("Helvetica", 11, "bold"), bg="#ddd6fe", fg="#1e3a8a").pack(side="left", padx=(6, 4))
    tk.Label(levies_summary_bar, textvariable=gross_obligation_display_var, font=("Helvetica", 11, "bold"), bg="#ddd6fe", fg="#1e3a8a").pack(side="left", padx=(0, 20))

    tk.Label(levies_summary_bar, text="Total Taxes & Charges:", font=("Helvetica", 11, "bold"), bg="#ddd6fe", fg="#5b21b6").pack(side="left", padx=(6, 4))
    tk.Label(levies_summary_bar, textvariable=total_levies_display_var, font=("Helvetica", 11, "bold"), bg="#ddd6fe", fg="#5b21b6").pack(side="left", padx=(0, 20))

    tk.Label(levies_summary_bar, text="Net Settlement:", font=("Helvetica", 11, "bold"), bg="#ddd6fe", fg="#b91c1c").pack(side="left", padx=(6, 4))
    tk.Label(levies_summary_bar, textvariable=net_settlement_status_var, font=("Helvetica", 11, "bold"), bg="#ddd6fe", fg="#b91c1c").pack(side="left", padx=(0, 6))

    def _recalculate_net_contract_amount(*_args):
        try:
            ob = float(payin_payout_var.get().strip() or "0.0")
            taxable = float(taxable_val_var.get().strip() or "0.0")
            etc = float(etc_cont_var.get().strip() or "0.0")
            clearing = float(clearing_var.get().strip() or "0.0")
            gst = float(gst_var.get().strip() or "0.0")
            igst = float(igst_var.get().strip() or "0.0")
            stt = float(stt_var.get().strip() or "0.0")
            sebi = float(sebi_var.get().strip() or "0.0")
            stamp = float(stamp_var.get().strip() or "0.0")

            tot_lev = round(taxable + etc + clearing + gst + igst + stt + sebi + stamp, 2)
            total_levies_display_var.set(f"₹ {tot_lev:,.2f}")

            # For net amount receivable / payable by client:
            # As per ICICI trade_add logic:
            # For BUY: net_trade_value = lp_value + levies (client pays)
            # For SELL: net_trade_value = lp_value - levies (client receives)
            # Overall net bank settlement:
            # If ob >= 0 (Pay-in, Buy >= Sell): client pays ob + tot_lev
            # If ob < 0 (Pay-out, Sell > Buy): client receives abs(ob) - tot_lev
            if ob >= 0:
                net_amt = round(ob + tot_lev, 2)
                status = "Payable by Client (DEBIT / Outflow)"
            else:
                net_val = round(abs(ob) - tot_lev, 2)
                if net_val >= 0:
                    net_amt = net_val
                    status = "Receivable by Client (CREDIT / Inflow)"
                else:
                    net_amt = abs(net_val)
                    status = "Payable by Client (DEBIT / Outflow)"

            # Avoid cursor jumping if entry is currently focused
            try:
                if win.focus_get() != net_client_amt_entry:
                    net_client_amt_var.set(f"{net_amt:.2f}")
            except Exception:
                net_client_amt_var.set(f"{net_amt:.2f}")

            net_settlement_status_var.set(f"₹ {net_amt:,.2f}  [{status}]")
        except ValueError:
            total_levies_display_var.set("₹ 0.00")
            net_settlement_status_var.set("₹ 0.00")

    def _recalculate_default_levies():
        """Calculate and set default values for fields a through j based on current trades."""
        if not trades_list:
            payin_payout_var.set("0.00")
            taxable_val_var.set("0.00")
            etc_cont_var.set("0.00")
            clearing_var.set("0.00")
            gst_var.set("0.00")
            igst_var.set("0.00")
            stt_var.set("0")
            sebi_var.set("0.00")
            stamp_var.set("0.00")
            net_client_amt_var.set("0.00")
            _recalculate_net_contract_amount()
            return

        b_tot = sum(t["qty"] * t["wap"] for t in trades_list if t["trade_type"] == "BUY")
        s_tot = sum(t["qty"] * t["wap"] for t in trades_list if t["trade_type"] == "SELL")
        total_turnover = b_tot + s_tot

        # a. Pay in Pay Out: Net Obligation for ISIN (Their total)
        net_ob = round(b_tot - s_tot, 2)
        payin_payout_var.set(f"{net_ob:.2f}")

        # b. Taxable Value: sum of brokerage + 0.01
        sum_brok = sum(t["qty"] * t.get("brok_unit", 0.0) for t in trades_list)
        taxable_val = round(sum_brok + 0.01, 2)
        taxable_val_var.set(f"{taxable_val:.2f}")

        # c. ETC: As applicable formula as in trade_add (sum of turnover * get_etc(trd_dt, exch))
        try:
            t_dt = trd_dt_entry.get_date()
        except Exception:
            t_dt = datetime.now().date()
        etc_sum = 0.0
        for t in trades_list:
            rate = get_etc(t_dt, t.get("exchange", "NSE"))
            etc_sum += (t["qty"] * t["wap"]) * rate
        etc_val = round(etc_sum, 2)
        etc_cont_var.set(f"{etc_val:.2f}")

        # d. Clearing Charges: Keep 0.00
        clearing_val = 0.0
        clearing_var.set("0.00")

        # h. SEBI: Default value as in add_trade (ICICI) (total_turnover * SEBI)
        sebi_val = round(total_turnover * SEBI, 2)
        sebi_var.set(f"{sebi_val:.2f}")

        # e. GST: Default should be 18% (Taxable Value + ETC + SEBI + Clearing)
        gst_base = taxable_val + etc_val + sebi_val + clearing_val
        gst_val = round(gst_base * GST, 2)
        gst_var.set(f"{gst_val:.2f}")

        # f. IGST: Default 0.00
        igst_var.set("0.00")

        # g. STT: Default value as in add_trade (ICICI) (non-ETF turnover * STT, integer)
        non_etf_turnover = sum(t["qty"] * t["wap"] for t in trades_list if not t.get("is_etf", False))
        stt_val = int(round(non_etf_turnover * STT)) if non_etf_turnover > 0 else 0
        stt_var.set(str(stt_val))

        # i. Stamp Duty: Keep 0.00
        stamp_var.set("0.00")

        # j. Net Amount Receivable/Payable: Recalculated by _recalculate_net_contract_amount
        _recalculate_net_contract_amount()

    for v in (payin_payout_var, taxable_val_var, etc_cont_var, clearing_var, gst_var, igst_var, stt_var, sebi_var, stamp_var):
        v.trace_add("write", _recalculate_net_contract_amount)

    _recalculate_default_levies()

    # ── 4. Main Action Buttons ─────────────────────────────────────────────
    btn_box = tk.Frame(win, bg=bg_win, relief="ridge", bd=2, pady=6)
    btn_box.pack(side="bottom", fill="x", padx=10, pady=(2, 6))

    def _on_save_contract():
        # Validations
        cont_no = cont_no_var.get().strip().upper()
        prefix = get_current_fy_prefix(trd_dt_entry.get_date())
        if not cont_no or cont_no in ("CNT-", prefix):
            show_colorful_error(win, "Validation Error", f"Please enter a valid Zerodha Contract Note Number (e.g. {prefix}96502367).")
            cont_no_entry.focus_set()
            return

        if not trades_list:
            show_colorful_error(win, "No Trades", "Please add at least one trade to the contract table before saving.")
            company_combo.focus_set()
            return

        try:
            settle_no = int(settle_no_var.get().strip() or "0")
        except ValueError:
            settle_no = 0

        trd_dt_str = trd_dt_entry.get_date().strftime("%Y-%m-%d")
        settle_dt_str = settle_dt_entry.get_date().strftime("%Y-%m-%d")

        # Prepare contract levies dictionary
        try:
            c_levies = {
                "brok": float(taxable_val_var.get().strip() or "0.0"),
                "taxable_value": float(taxable_val_var.get().strip() or "0.0"),
                "etc": float(etc_cont_var.get().strip() or "0.0"),
                "clearing": float(clearing_var.get().strip() or "0.0"),
                "gst": float(gst_var.get().strip() or "0.0"),
                "igst": float(igst_var.get().strip() or "0.0"),
                "stt": int(round(float(stt_var.get().strip() or "0"))),
                "sebi": float(sebi_var.get().strip() or "0.0"),
                "stamp": float(stamp_var.get().strip() or "0.0"),
                "sell_chrg": sum(t.get("sell_chrg", 0.0) for t in trades_list),
            }
        except ValueError as e:
            show_colorful_error(win, "Input Error", f"One or more levy values are invalid numbers: {e}")
            return

        # Run Bifurcation
        try:
            bifurcated_result = bifurcate_zerodha_levies(
                trades=trades_list,
                contract_levies=c_levies,
                trd_dt=trd_dt_str,
            )
        except Exception as e:
            logger.error("Bifurcation failed: %s", e, exc_info=True)
            show_colorful_error(win, "Bifurcation Failed", f"Failed to bifurcate levies: {e}")
            return

        b_trades = bifurcated_result["bifurcated_trades"]
        c_totals = bifurcated_result["contract_totals"]

        # Confirm with User
        confirm_msg = (
            f"Ready to persist Zerodha Contract:\n\n"
            f"Contract No: {cont_no}\n"
            f"Trade Date: {trd_dt_str} | Settlement: {settle_dt_str}\n"
            f"Total Trades: {len(b_trades)}\n"
            f"Total Turnover: ₹ {c_totals['total_turnover']:,.2f}\n"
            f"Total Levies: ₹ {c_totals['tax_cont'] + c_totals['chrg_cont']:,.2f}\n"
            f"Net Bank Settlement: ₹ {abs(c_totals['net_bank_settlement']):,.2f} "
            f"({'DEBIT / Outflow' if c_totals['net_bank_settlement'] >= 0 else 'CREDIT / Inflow'})\n\n"
            f"Proceed with database save?"
        )
        if not show_colorful_yesno(win, "Confirm Contract Save", confirm_msg):
            return

        # Atomic SQLite Persistence
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute("PRAGMA foreign_keys = ON;")

                # Check if contract already exists
                cur.execute("SELECT id_cont FROM contracts WHERE cont_no = ?", (cont_no,))
                exists_cont = cur.fetchone()
                if exists_cont:
                    show_colorful_error(
                        win,
                        "Duplicate Contract",
                        f"Contract No '{cont_no}' already exists in the database.\n"
                        f"Please check contract number or use Trade Manager to edit.",
                    )
                    return

                # Check oversell for any SELL trades
                for t in b_trades:
                    if t["trade_type_trd"] == "SELL":
                        cur.execute(
                            "SELECT buy_qty, sell_qty FROM stocks WHERE id_stk = ?",
                            (t["id_stk"],),
                        )
                        stk_row = cur.fetchone()
                        if stk_row:
                            available_qty = stk_row[0] - stk_row[1]
                            if t["qty_trd"] > available_qty:
                                show_colorful_error(
                                    win,
                                    "Oversell Blocked",
                                    f"Cannot sell {t['qty_trd']} shares of '{t['company_name']}'.\n"
                                    f"Available quantity in portfolio: {available_qty}.",
                                )
                                return

                # 1. Insert into contracts
                cur.execute(
                    """
                    INSERT INTO contracts (
                        cont_no, trd_dt, settle_no, settle_dt, no_of_trades,
                        brok_cont, etc_cont, sebi_cont, gst_cont, stamp_cont,
                        stt_cont, igst_cont, sell_chrg_cont, net_amt_cont,
                        etc_cont_applicable, gst_cont_applicable, stt_cont_applicable, net_amt_cont_applicable,
                        note_cont
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        cont_no,
                        trd_dt_str,
                        settle_no,
                        settle_dt_str,
                        len(b_trades),
                        c_totals["brok_cont"],
                        c_totals["etc_cont"],
                        c_totals["sebi_cont"],
                        c_totals["gst_cont"],
                        c_totals["stamp_cont"],
                        c_totals["stt_cont"],
                        c_totals["igst_cont"],
                        c_totals["sell_chrg_cont"],
                        c_totals["net_amt_cont"],
                        c_totals["etc_cont_applicable"],
                        c_totals["gst_cont_applicable"],
                        c_totals["stt_cont_applicable"],
                        c_totals["net_amt_cont_applicable"],
                        note_cont_var.get().strip(),
                    ),
                )

                # 2. Insert into transactions & exchange_orders
                inserted_tx_ids = []
                for t in b_trades:
                    cur.execute(
                        """
                        INSERT INTO transactions (
                            cont_no, trd_dt, company_name, trade_type_trd, id_stk,
                            exchange, qty_trd, wap_unit_trd, brok_unit_trd, price_lot_trd,
                            brok_lot_trd, etc_trd, sebi_trd, sell_chrg_trd, gst_trd,
                            stamp_trd, stt_trd, igst_trd, net_amt_trd,
                            etc_trd_applicable, gst_trd_applicable, stt_trd_applicable, net_amt_trd_applicable,
                            note_trd
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            cont_no,
                            trd_dt_str,
                            t["company_name"],
                            t["trade_type_trd"],
                            t["id_stk"],
                            t["exchange"],
                            t["qty_trd"],
                            t["wap_unit_trd"],
                            t["brok_unit_trd"],
                            t["price_lot_trd"],
                            t["brok_lot_trd"],
                            t["etc_trd"],
                            t["sebi_trd"],
                            t["sell_chrg_trd"],
                            t["gst_trd"],
                            t["stamp_trd"],
                            t["stt_trd"],
                            t["igst_trd"],
                            t["net_amt_trd"],
                            t["etc_trd_applicable"],
                            t["gst_trd_applicable"],
                            t["stt_trd_applicable"],
                            t["net_amt_trd_applicable"],
                            t["note_trd"],
                        ),
                    )
                    tx_id = cur.lastrowid
                    inserted_tx_ids.append(tx_id)

                    # Insert consolidated summary exchange_order row
                    cur.execute(
                        """
                        INSERT INTO exchange_orders (
                            id_trd, exchange_eo, ord_no, ord_dt, trd_no,
                            qty_eo, rate_eo, brok_unit_eo, net_rate_eo, net_total_eo
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            tx_id,
                            t["exchange"],
                            0,
                            trd_dt_str,
                            0,
                            t["qty_trd"],
                            t["wap_unit_trd"],
                            t["brok_unit_trd"],
                            t["wap_unit_trd"] + t["brok_unit_trd"],
                            t["price_lot_trd"],
                        ),
                    )

                # 3. Insert into computed_bank
                net_bank = c_totals["net_bank_settlement"]
                if net_bank != 0:
                    bt_type = "DEBIT" if net_bank > 0 else "CREDIT"
                    desc = f"Zerodha Contract {cont_no} ({len(b_trades)} trades)"
                    cur.execute(
                        """
                        INSERT INTO computed_bank (
                            cont_no, comp_bt_dt, comp_bt_type, comp_bt_amt,
                            comp_bt_amt_applicable, comp_bt_desc
                        ) VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            cont_no,
                            settle_dt_str,
                            bt_type,
                            round(abs(net_bank), 2),
                            round(abs(c_totals["net_amt_cont_applicable"]), 2),
                            desc,
                        ),
                    )

                # Enforce no oversell check
                for t in b_trades:
                    if t["trade_type_trd"] == "SELL":
                        enforce_no_oversell_for_stock(cur, t["id_stk"])

                conn.commit()

            # 4. Recompute stock averages after commit
            for t in b_trades:
                compute_avg_price(t["id_stk"], t["trade_type_trd"])

            show_colorful_info(
                win,
                "🎉 Contract Saved Successfully",
                f"Zerodha Contract '{cont_no}' with {len(b_trades)} trades has been saved successfully!\n\n"
                f"Net Bank Settlement: ₹ {abs(net_bank):,.2f} ({'DEBIT' if net_bank >= 0 else 'CREDIT'}).",
            )

            if show_colorful_yesno(win, "Add Another Contract?", "Would you like to enter another Zerodha contract note?"):
                # Reset form
                trades_list.clear()
                _render_trades_tree()
                cont_no_var.set(get_current_fy_prefix(datetime.now().date()))
                settle_no_var.set("0")
                note_cont_var.set("")
                _recalculate_default_levies()
                cont_no_entry.focus_set()
            else:
                cleanup_and_close()

        except sqlite3.IntegrityError as e:
            show_colorful_error(win, "Database Integrity Error", f"Could not save contract:\n{e}")
        except Exception as e:
            logger.error("Failed to save Zerodha contract: %s", e, exc_info=True)
            show_colorful_error(win, "Save Error", f"An unexpected error occurred: {e}")

    save_btn = tk.Button(
        btn_box,
        text="💾  EXECUTE & SAVE ZERODHA CONTRACT  💾",
        command=_on_save_contract,
        font=("Comic Sans MS", 12, "bold"),
        bg="#22c55e",
        fg="white",
        activebackground="#16a34a",
        activeforeground="white",
        relief="raised",
        bd=3,
        padx=15,
        pady=5,
        cursor="hand2",
    )
    save_btn.pack(side="right", padx=10)

    cancel_btn = tk.Button(
        btn_box,
        text="❌  Cancel / Close  ❌",
        command=cleanup_and_close,
        font=("Comic Sans MS", 12, "bold"),
        bg="#ef4444",
        fg="white",
        activebackground="#b91c1c",
        activeforeground="white",
        relief="raised",
        bd=3,
        padx=10,
        pady=5,
        cursor="hand2",
    )
    cancel_btn.pack(side="right", padx=5)

    apply_button_animations(save_btn, "#22c55e", "#16a34a")
    apply_button_animations(cancel_btn, "#ef4444", "#b91c1c")

    win.bind("<Control-Return>", lambda e: save_btn.invoke())
    win.bind("<Escape>", cleanup_and_close)
    win.protocol("WM_DELETE_WINDOW", cleanup_and_close)

    parent.wait_window(win)
