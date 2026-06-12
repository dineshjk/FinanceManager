# -*- coding: utf-8 -*-
# StockMan/trade_update.py

"""
trade_update.py
----------------

Modal window and helpers for updating existing trades in the StockMan application.

This module provides the interactive modal to select and update
trading contracts and associated transactions. The primary entry point is
the `update_trade(parent, calling_button)` function.

"""

from typing import Union
import tkinter as tk
from tkinter import ttk
import sqlite3
from datetime import datetime, timedelta
from tkcalendar import DateEntry

# Local imports using new package structure
from Shared.globals import (
    get_db_connection,
    get_etc,
    BROK,
    GST,
    SEBI,
    STT,
    logger,
)
from Shared.dialog_utils import (
    show_colorful_info,
    show_colorful_error,
    show_colorful_yesno,
)

from Shared.gui_utils import (
    apply_entry_theme,
    bind_tooltip,
    bind_entry_hover,
    apply_button_animations,
    setup_footer_tooltip,
    bind_date_spin,
)

from .date_utils import next_working_day
from Shared.modal_utils import disable_parent, enable_parent
from Shared.window_manager import push_window, pop_window, safe_close_modal
from Shared.gui_progressive import progressive_selection
from .trade_utils import (
    compute_avg_price,
    enforce_no_oversell_for_stock,
    select_trade_from_list,
)


def update_trade(
    parent: Union[tk.Toplevel, tk.Tk],
    calling_button: tk.Widget | None = None,
    id_trd: int | None = None,
) -> None:
    """
    Opens a modal window for trade data update, initializes form widgets,
    and manages parent window modality.

    If ``id_trd`` is provided, the trade-picker dialog is skipped and that
    trade is loaded directly.
    """

    if id_trd is not None:
        selected_id_trd = id_trd
    else:
        selected_id_trd = select_trade_from_list(
            parent, "Select Trade to Update", "#e0f7fa", "#00796b"
        )
    if not selected_id_trd:
        return

    # --------------------------------------------------------------------------
    # 2. MAIN UPDATE WINDOW SETUP (adapted from add_trade)
    # --------------------------------------------------------------------------

    # colors
    ratwinbg = "#f0f8ff"
    headbg = "#1e3a8a"
    titlefg = "#ffd700"
    ratframebg = "#75ebc3"  # Light teal/green for update
    btnfrbg = "#f8fafc"
    contfrbg = "#e0f2fe"
    compisinbg = "#fef3c7"
    qoqbg = "#dcfce7"
    rbnnbg = "#fce7f3"
    wbtbg = "#ede9fe"
    gssbg = "#f0fdf4"
    submitusualbg = "#22c55e"
    submitactivebg = "#16a34a"
    okactivebg = "#1e40af"
    cancelusualbg = "#ef4444"
    cancelactivebg = "#b91c1c"
    hintbg = "#f8fafc"

    modal_id = disable_parent(parent, calling_button=calling_button)

    data = {
        "lot_cont": 0.0,
        "stt_so_far": 0,
        "levies": 0.0,
        "comp_bt_amt": 0.0,
    }
    original_data = {}
    exchange_orders = []
    current_eo_index = 0
    # Holds trades recorded during this add_trade session
    current_session_trades = {}

    entries = {}
    widget_to_var = {}

    rat_win = tk.Toplevel(parent)
    rat_win.title("✨ Data Entry - Update Trade ✨")
    rat_win.geometry("1150x920")
    rat_win.resizable(False, False)
    rat_win.configure(bg=ratwinbg)
    rat_win.transient(parent)
    rat_win.grab_set()
    rat_win.focus_set()
    push_window(rat_win, parent)

    tooltip_var = setup_footer_tooltip(
        rat_win, bg_color=ratwinbg, fg_color=headbg
    )

    def on_ex_radio_key(
        event,
        radio_btn: tk.Radiobutton,
        value: str,
        exchange_var: tk.StringVar,
        nse_radio: tk.Radiobutton,
        bse_radio: tk.Radiobutton,
    ) -> None:
        if radio_btn.cget("state") == "disabled":
            return
        if event.keysym == "space":
            exchange_var.set(value)
            radio_btn.select()
        elif event.keysym in ("Right", "Left"):
            if radio_btn == nse_radio:
                bse_radio.focus_set()
                exchange_var.set("BSE")
                bse_radio.select()
            else:
                nse_radio.focus_set()
                exchange_var.set("NSE")
                nse_radio.select()

    # --- Bindings and Initial Load ---

    def _create_context_menu(widget):
        menu = tk.Menu(rat_win, tearoff=0)
        menu.add_command(
            label="Cut", command=lambda: widget.event_generate("<<Cut>>")
        )
        menu.add_command(
            label="Copy", command=lambda: widget.event_generate("<<Copy>>")
        )
        menu.add_command(
            label="Paste", command=lambda: widget.event_generate("<<Paste>>")
        )
        menu.add_separator()
        menu.add_command(
            label="Select All", command=lambda: widget.select_range(0, "end")
        )
        widget.bind(
            "<Button-3>",
            lambda e: (widget.focus_set(), menu.tk_popup(e.x_root, e.y_root)),
        )

    # --- Helper Functions (adapted for update) ---

    def cleanup_and_close(_event=None):
        enable_parent(modal_id)
        safe_close_modal(rat_win, parent)

    def on_escape(_event=None):
        # Revert to original data and close
        cleanup_and_close()

    # --- Focus color change for submit button ---
    def on_submit_focus_in(_event):
        submit_btn.config(bg="#2563eb")  # blue

    def on_submit_focus_out(_event):
        submit_btn.config(bg=submitusualbg)  # original green

    # --- Focus color change for ok button ---
    def on_ok_focus_in(_event):
        ok_btn.config(bg="#2563eb")  # blue

    def on_ok_focus_out(_event):
        ok_btn.config(bg=submitusualbg)  # original green

    def recalculate_from_wap_change(
        wap_var,
        qty_trd_var,
        exchange_var,
        buy_sell_var,
        brs_var,
        lp_var,
        lot_cont_var,
        tot_brok_var,
        etc_var,
        sebi_var,
        gst_var,
        stt_cont_var,
        stt_var,
        net_trade_var,
        lot_cont_entry,
        brs_entry,
        lp_entry,
        tot_brok_entry,
        etc_entry,
        sebi_entry,
        gst_entry,
        stt_entry,
        net_trade_entry,
        comp_bt_var,
        comp_bt_entry,
        stt_cont_entry,
        data,
        trd_date_entry,
        _event=None,
        callback=None,
    ):
        try:
            wap_value = wap_var.get()
            qty_trd_value = qty_trd_var.get()

            if wap_value <= 0 or qty_trd_value <= 0:
                return

            brs_value = round(wap_value * BROK, 4)
            brs_var.set(brs_value)

            lp_value = round(wap_value * qty_trd_value, 4)
            lp_var.set(lp_value)

            lot_cont_value = data["lot_cont_etf"] + data["lot_cont_non_etf"]
            lot_cont_var.set(round(lot_cont_value, 4))
            lot_cont_entry.update_idletasks()

            tot_brok_value = round(lp_value * BROK, 4)
            tot_brok_var.set(round(tot_brok_value, 4))
            data["levies"] = tot_brok_value

            trade_date = trd_date_entry.get_date()  # type: ignore
            etc_rate = get_etc(trade_date, exchange_var.get())
            etc_value = round(lp_value * etc_rate, 4)
            etc_var.set(etc_value)
            data["levies"] += etc_value

            sebi_value = round(lp_value * SEBI, 4)
            sebi_var.set(round(sebi_value, 4))
            data["levies"] += sebi_value

            gst_value = round(
                (tot_brok_value + etc_value + sebi_value) * GST, 4
            )
            gst_var.set(gst_value)
            data["levies"] += gst_value

            if data["lot_cont_non_etf"] != 0:
                stt_cont_value = int(round(data["lot_cont_non_etf"] * STT))
                stt_cont_value = max(stt_cont_value, 1)
                stt_cont_var.set(stt_cont_value)
            else:
                stt_cont_value = 0
                stt_cont_var.set(0)
            stt_cont_entry.update_idletasks()

            if data["is_etf"]:
                stt_value = 0.0
            else:
                stt_value = stt_cont_value - data["stt_so_far"]
            stt_var.set(stt_value)
            stt_entry.update_idletasks()
            data["levies"] += stt_value

            if buy_sell_var.get() == "BUY":
                net_trade_value = lp_value + data["levies"]
                comp_bt_value = data["comp_bt_amt"] + net_trade_value
            else:
                net_trade_value = lp_value - data["levies"]
                comp_bt_value = data["comp_bt_amt"] - net_trade_value

            net_trade_var.set(round(net_trade_value, 4))
            comp_bt_var.set(round(comp_bt_value, 2))

            for entry in [
                brs_entry,
                lp_entry,
                tot_brok_entry,
                etc_entry,
                sebi_entry,
                gst_entry,
                stt_entry,
                net_trade_entry,
                comp_bt_entry,
                stt_cont_entry,
            ]:
                entry.update_idletasks()

            if callback:
                callback()

        except (ValueError, tk.TclError, KeyError):
            pass

    def refresh_financial_formats():
        current_focus = rat_win.focus_get() if rat_win.focus_get() else None
        for e, v in [
            (wap_entry, wap_var),
            (brs_entry, brs_var),
            (lp_entry, lp_var),
            (tot_brok_entry, tot_brok_var),
            (etc_entry, etc_var),
            (sebi_entry, sebi_var),
            (gst_entry, gst_var),
            (stamp_duty_entry, stamp_duty_var),
            (sell_charge_entry, sell_charge_var),
            (igst_entry, igst_var),
            (net_trade_entry, net_trade_var),
            (lot_cont_entry, lot_cont_var),
            (etc_app_entry, etc_app_var),
            (gst_app_entry, gst_app_var),
            (stt_app_entry, stt_app_var),
            (net_trade_app_entry, net_trade_app_var),
            (diff_trd_entry, diff_trd_var),
        ]:
            if e != current_focus:
                try:
                    val = float(v.get())
                    state = str(e.cget("state"))
                    if state != "normal":
                        e.config(state="normal")
                    e.delete(0, "end")
                    e.insert(0, f"{val:.4f}")
                    if state != "normal":
                        e.config(state=state)
                except (ValueError, tk.TclError):
                    pass
        if comp_bt_entry != current_focus:
            try:
                val = float(comp_bt_var.get())
                state = str(comp_bt_entry.cget("state"))
                if state != "normal":
                    comp_bt_entry.config(state="normal")
                comp_bt_entry.delete(0, "end")
                comp_bt_entry.insert(0, f"{val:.2f}")
                if state != "normal":
                    comp_bt_entry.config(state=state)
            except (ValueError, tk.TclError):
                pass

    def calculate_applicable_fields(_event=None):
        try:
            lp_value = lp_var.get()
            if lp_value <= 0:
                return

            # Simple fallback for ETF status if not in update data dict
            is_etf = data.get("is_etf", False)

            etc_app_val = round(
                lp_value
                * get_etc(trd_date_entry.get_date(), exchange_var.get()),
                4,
            )
            etc_app_var.set(etc_app_val)

            brok_app_val = round(lp_value * BROK, 4)
            sebi_app_val = round(lp_value * SEBI, 4)
            gst_app_val = round(
                (brok_app_val + etc_app_val + sebi_app_val) * GST, 4
            )
            gst_app_var.set(gst_app_val)

            stt_cont_app_value = (
                max(int(round(lp_value * STT)), 1) if lp_value != 0 else 0
            )
            stt_app_val = (
                0.0
                if is_etf
                else float(stt_cont_app_value - data.get("stt_so_far", 0))
            )
            stt_app_var.set(stt_app_val)

            levies_app = (
                brok_app_val
                + etc_app_val
                + sebi_app_val
                + gst_app_val
                + stt_app_val
                + stamp_duty_var.get()
                + igst_var.get()
                + sell_charge_var.get()
            )
            net_app = (
                lp_value + levies_app
                if buy_sell_var.get() == "BUY"
                else lp_value - levies_app
            )
            net_trade_app_var.set(round(net_app, 4))
            diff_trd_var.set(round(net_trade_var.get() - net_app, 4))

            refresh_financial_formats()
        except (ValueError, tk.TclError, KeyError):
            pass

    def update_levies_and_net_trade(_event=None):
        """
        Update levies and net_trade_entry when any levy field value changes
        """
        try:
            # Recalculate levies with all components
            data["levies"] = (
                tot_brok_var.get()
                + etc_var.get()
                + sebi_var.get()
                + gst_var.get()
                + stamp_duty_var.get()
                + stt_var.get()
                + igst_var.get()
                + sell_charge_var.get()
            )

            # Recalculate net trade amount
            lp_value = lp_var.get()
            if buy_sell_var.get() == "BUY":
                net_trade_value = lp_value + data["levies"]
                comp_bt_value = data["comp_bt_amt"] + net_trade_value
            else:
                net_trade_value = lp_value - data["levies"]
                comp_bt_value = data["comp_bt_amt"] - net_trade_value

            net_trade_var.set(round(net_trade_value, 4))
            comp_bt_var.set(round(comp_bt_value, 2))

        except (ValueError, tk.TclError):
            pass

    # ... [Copy most of the UI creation and helper functions from add_trade.py] ...
    # ... [This includes show_help, on_radio_key, recalculate_from_wap_change, etc.] ...
    # ... [The following are the key modifications] ...

    # --- Integer Validation Settlement No ---
    def validate_int(P):
        return P.isdigit() or P == ""

    int_vcmd = (rat_win.register(validate_int), "%P")

    # Create the full window.
    header_frame = tk.Frame(rat_win, bg=headbg, relief="raised", bd=3)
    header_frame.pack(fill="x", padx=5, pady=0)

    # Main title with fancy styling
    title_label = tk.Label(
        header_frame,
        text="💼 DATA UPDATE SYSTEM 💼",
        font=("Comic Sans MS", 18, "bold"),
        bg=headbg,
        fg=titlefg,
        pady=8,
        relief="ridge",
        bd=2,
    )
    title_label.pack(fill="x")

    # Here goes the creation of all frames
    # This is the area reserved for the form to contain widgets
    rat_frame = tk.Frame(
        rat_win, bg=ratframebg, padx=15, pady=0, relief="raised", bd=2
    )
    rat_frame.pack(fill="both", expand=True, padx=10, pady=5)

    # Create a fancy horizontal frame for OK and Cancel buttons.
    btn_frame = tk.Frame(rat_win, pady=10, bg=btnfrbg, relief="ridge", bd=2)
    btn_frame.pack(fill="x", anchor="e", padx=10)

    # Create a two line frame to hold three fields with enhanced styling
    cont_frame = tk.Frame(
        rat_frame, bg=contfrbg, relief="ridge", bd=2, padx=10, pady=8
    )
    cont_frame.grid(
        row=0, column=0, rowspan=2, columnspan=5, sticky="ew", pady=10
    )

    # cont_frame starts
    # label frame
    cont_label_frame = tk.Frame(cont_frame, bg=contfrbg)
    cont_label_frame.pack(fill="x", pady=(0, 5))

    # entry frame
    cont_entry_frame = tk.Frame(cont_frame, bg=contfrbg)
    cont_entry_frame.pack(fill="x", pady=(0, 5))

    # note frame
    cont_note_frame = tk.Frame(cont_frame, bg=contfrbg)
    cont_note_frame.pack(fill="x", pady=(0, 5))

    # company_isin frame
    company_isin_frame = tk.Frame(
        rat_frame, bg=compisinbg, relief="groove", bd=2, padx=8, pady=6
    )
    company_isin_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=5)

    # qoq_frame
    qoq_frame = tk.Frame(
        rat_frame, bg=qoqbg, relief="ridge", bd=2, padx=8, pady=6
    )
    qoq_frame.grid(
        row=5, column=0, rowspan=2, columnspan=3, sticky="ew", pady=5
    )

    # qoq_label_frame
    qoq_label_frame = tk.Frame(qoq_frame, bg=qoqbg)
    qoq_label_frame.pack(fill="x", pady=(0, 2))
    # qoq_entry_frame
    qoq_entry_frame = tk.Frame(qoq_frame, bg=qoqbg)
    qoq_entry_frame.pack(fill="x", pady=(0, 2))

    # rbnn_frame
    rbnn_frame = tk.Frame(
        rat_frame, bg=rbnnbg, relief="ridge", bd=2, padx=8, pady=6
    )
    rbnn_frame.grid(
        row=7, column=0, rowspan=2, columnspan=4, sticky="ew", pady=5
    )

    # rbnn_label_frame
    rbnn_label_frame = tk.Frame(rbnn_frame, bg=rbnnbg)
    rbnn_label_frame.pack(fill="x", pady=(0, 2))

    # rbnn_entry_frame
    rbnn_entry_frame = tk.Frame(rbnn_frame, bg=rbnnbg)
    rbnn_entry_frame.pack(fill="x", pady=(0, 2))

    # wbt_frame
    wbt_frame = tk.Frame(
        rat_frame, bg=wbtbg, relief="groove", bd=2, padx=8, pady=6
    )
    wbt_frame.grid(
        row=9, column=0, rowspan=2, columnspan=4, sticky="ew", pady=5
    )

    # wbt_label_frame
    wbt_label_frame = tk.Frame(wbt_frame, bg=wbtbg)
    wbt_label_frame.pack(fill="x", pady=(0, 2))

    # wbt_entry_frame
    wbt_entry_frame = tk.Frame(wbt_frame, bg=wbtbg)
    wbt_entry_frame.pack(fill="x", pady=(0, 2))

    # gss_frame
    gss_frame = tk.Frame(
        rat_frame, bg=gssbg, relief="ridge", bd=2, padx=8, pady=6
    )
    gss_frame.grid(
        row=11, column=0, rowspan=2, columnspan=4, sticky="ew", pady=5
    )

    # gss_label_frame
    gss_label_frame = tk.Frame(gss_frame, bg=gssbg)
    gss_label_frame.pack(fill="x", pady=(0, 2))

    # gss_entry_frame
    gss_entry_frame = tk.Frame(gss_frame, bg=gssbg)
    gss_entry_frame.pack(fill="x", pady=(0, 2))

    # trd_note_frame
    trd_note_frame = tk.Frame(gss_frame, bg=gssbg)
    trd_note_frame.pack(fill="x", pady=(0, 2))

    # app_frame
    appbg = "#fef9c3"
    app_frame = tk.Frame(
        rat_frame, bg=appbg, relief="ridge", bd=2, padx=8, pady=6
    )
    app_frame.grid(
        row=13, column=0, rowspan=2, columnspan=4, sticky="ew", pady=5
    )
    app_label_frame = tk.Frame(app_frame, bg=appbg)
    app_label_frame.pack(fill="x", pady=(0, 2))
    app_entry_frame = tk.Frame(app_frame, bg=appbg)
    app_entry_frame.pack(fill="x", pady=(0, 2))
    # Frames end here

    # --- Variable Declaration ---
    cont_no_var = tk.StringVar()
    trd_dt_var = tk.StringVar()
    settle_no_var = tk.IntVar()
    settle_dt_var = tk.StringVar()
    no_of_trades_var = tk.IntVar()
    current_trade_no_var = tk.IntVar()
    note_cont_var = tk.StringVar()
    company_name_var = tk.StringVar()
    isin_var = tk.StringVar()
    buy_sell_var = tk.StringVar()
    qty_trd_var = tk.IntVar()
    ord_no_var = tk.StringVar()
    ord_dt_var = tk.StringVar()
    trd_no_var = tk.IntVar()
    qty_eo_var = tk.IntVar()
    rate_eo_var = tk.DoubleVar()
    brok_unit_eo_var = tk.DoubleVar()
    net_rate_eo_var = tk.DoubleVar()
    net_total_eo_var = tk.DoubleVar()
    exchange_var = tk.StringVar()
    wap_var = tk.DoubleVar()
    brs_var = tk.DoubleVar()
    lp_var = tk.DoubleVar()
    tot_brok_var = tk.DoubleVar()
    etc_var = tk.DoubleVar()
    sebi_var = tk.DoubleVar()
    sell_charge_var = tk.DoubleVar()
    gst_var = tk.DoubleVar()
    stamp_duty_var = tk.DoubleVar()
    stt_var = tk.IntVar()
    igst_var = tk.DoubleVar()
    net_trade_var = tk.DoubleVar()
    lot_cont_var = tk.DoubleVar()
    stt_cont_var = tk.IntVar()
    note_trd_var = tk.StringVar()
    comp_bt_var = tk.DoubleVar()
    etc_app_var = tk.DoubleVar()
    gst_app_var = tk.DoubleVar()
    stt_app_var = tk.DoubleVar()
    net_trade_app_var = tk.DoubleVar()
    diff_trd_var = tk.DoubleVar()

    # --- UI Widget Creation (similar to add_trade) ---
    # Contract No field
    tk.Label(
        cont_label_frame, bg=contfrbg, text="Cont No", font=("Helvetica", 14)
    ).pack(side="left", padx=(10, 0))
    cont_no_entry = tk.Entry(
        cont_entry_frame,
        textvariable=cont_no_var,
        width=25,
        font=("Helvetica", 14),
        state="readonly",
    )
    cont_no_entry.pack(side="left", padx=(10, 0))

    # Trade Date field
    tk.Label(
        cont_label_frame, bg=contfrbg, text="Trade Dt", font=("Helvetica", 14)
    ).pack(side="left", padx=(215, 0))
    trd_date_entry = DateEntry(
        cont_entry_frame,
        textvariable=trd_dt_var,
        date_pattern="dd-mm-yyyy",
        width=10,
        font=("Helvetica", 14),
    )
    trd_date_entry.pack(side="left", padx=15)
    bind_date_spin(trd_date_entry)

    # Settlement No field
    tk.Label(
        cont_label_frame, bg=contfrbg, text="Settle No", font=("Helvetica", 14)
    ).pack(side="left", padx=(80, 0))
    settle_no_entry = tk.Spinbox(
        cont_entry_frame,
        from_=0,
        to=9999999,
        width=7,
        textvariable=settle_no_var,
        validate="key",
        validatecommand=int_vcmd,
        font=("Helvetica", 14),
    )
    settle_no_entry.pack(side="left", padx=15)

    # Settlement Date field
    tk.Label(
        cont_label_frame, bg=contfrbg, text="Settle Dt", font=("Helvetica", 14)
    ).pack(side="left", padx=(50, 0))
    settle_date_entry = DateEntry(
        cont_entry_frame,
        textvariable=settle_dt_var,
        date_pattern="dd-mm-yyyy",
        width=10,
        font=("Helvetica", 14),
    )
    settle_date_entry.pack(side="left", padx=15)
    bind_date_spin(settle_date_entry)

    # No of Trades field
    tk.Label(
        cont_label_frame,
        bg=contfrbg,
        text="No of Trades",
        font=("Helvetica", 14),
    ).pack(side="left", padx=(80, 0))
    trades_spin = tk.Spinbox(
        cont_entry_frame,
        from_=1,
        to=10,
        width=6,
        textvariable=no_of_trades_var,
        validate="key",
        validatecommand=int_vcmd,
        font=("Helvetica", 14),
        state="readonly",
    )
    trades_spin.pack(side="left", padx=15)

    # Current Trade No field
    tk.Label(
        cont_label_frame,
        bg=contfrbg,
        text="Current Trade No",
        font=("Helvetica", 14),
    ).pack(side="left", padx=(15, 0))
    current_trade_no_entry = tk.Entry(
        cont_entry_frame,
        textvariable=current_trade_no_var,
        width=6,
        font=("Helvetica", 14),
        state="readonly",
    )
    current_trade_no_entry.pack(side="left", padx=40)

    # Contract Note field
    tk.Label(
        cont_note_frame,
        bg=contfrbg,
        text="Contract Note",
        font=("Helvetica", 14),
    ).pack(side="left", padx=(10, 0), pady=(10, 0))
    note_cont_entry = tk.Entry(
        cont_note_frame,
        textvariable=note_cont_var,
        width=75,
        font=("Helvetica", 14),
    )
    note_cont_entry.pack(side="left", padx=(10, 0), pady=(10, 0))

    # Company and ISIN fields
    tk.Label(
        company_isin_frame,
        bg="#fef3c7",
        text="Company",
        font=("Helvetica", 14),
    ).pack(side="left", padx=(5, 0))
    company_entry = ttk.Combobox(
        company_isin_frame,
        textvariable=company_name_var,
        width=38,
        font=("Helvetica", 14),
        state="readonly",
    )
    company_entry.pack(side="left", padx=15)

    tk.Label(
        company_isin_frame, bg="#fef3c7", text="ISIN", font=("Helvetica", 14)
    ).pack(side="left", padx=(3, 0))
    isin_entry = tk.Entry(
        company_isin_frame,
        textvariable=isin_var,
        width=14,
        font=("Helvetica", 14),
        state="readonly",
    )
    isin_entry.pack(side="left", padx=15)

    # Buy/Sell radio buttons
    tk.Label(
        company_isin_frame,
        bg=compisinbg,
        text="BUY/SELL",
        font=("Helvetica", 14),
    ).pack(side="left", padx=(10, 0), pady=2)
    buy_radio = tk.Radiobutton(
        company_isin_frame,
        bg=compisinbg,
        text="BUY",
        variable=buy_sell_var,
        value="BUY",
        font=("Helvetica", 14),
    )
    buy_radio.pack(side="left", padx=10)
    sell_radio = tk.Radiobutton(
        company_isin_frame,
        bg=compisinbg,
        text="SELL",
        variable=buy_sell_var,
        value="SELL",
        font=("Helvetica", 14),
    )
    sell_radio.pack(side="left")

    # Quantity Trade field
    tk.Label(
        qoq_label_frame, bg=qoqbg, text="Qty Trade", font=("Helvetica", 14)
    ).pack(side="left", padx=(0, 0), pady=4)
    qty_trd_entry = tk.Spinbox(
        qoq_entry_frame,
        from_=1,
        to=100000,
        width=4,
        textvariable=qty_trd_var,
        validate="key",
        validatecommand=int_vcmd,
        font=("Helvetica", 14),
    )
    qty_trd_entry.pack(side="left", padx=(0, 5), pady=4)

    # Order No field
    tk.Label(
        qoq_label_frame, bg=qoqbg, text="Order No", font=("Helvetica", 14)
    ).pack(side="left", padx=(7, 0))
    ord_no_entry = tk.Entry(
        qoq_entry_frame,
        textvariable=ord_no_var,
        validate="key",
        validatecommand=int_vcmd,
        width=21,
        font=("Helvetica", 14),
    )
    ord_no_entry.pack(side="left", padx=(30, 0))

    # Order Date field
    tk.Label(qoq_label_frame, text="Order Date", font=("Helvetica", 14)).pack(
        side="left", padx=(180, 0)
    )
    ord_dt_entry = DateEntry(
        qoq_entry_frame,
        textvariable=ord_dt_var,
        date_pattern="dd-mm-yyyy",
        width=10,
        font=("Helvetica", 14),
    )
    ord_dt_entry.pack(side="left", padx=(30, 0))
    bind_date_spin(ord_dt_entry)

    # Trade No field
    tk.Label(
        qoq_label_frame, bg=qoqbg, text="Trade No", font=("Helvetica", 14)
    ).pack(side="left", padx=(60, 0))
    trd_no_entry = tk.Entry(
        qoq_entry_frame,
        textvariable=trd_no_var,
        validate="key",
        validatecommand=int_vcmd,
        width=21,
        font=("Helvetica", 14),
    )
    trd_no_entry.pack(side="left", padx=(30, 0))

    # Qty EO field
    tk.Label(
        qoq_label_frame, bg=qoqbg, text="Qty EO", font=("Helvetica", 14)
    ).pack(side="left", padx=(185, 0))
    qty_eo_entry = tk.Spinbox(
        qoq_entry_frame,
        from_=1,
        to=100000,
        width=6,
        textvariable=qty_eo_var,
        validate="key",
        validatecommand=int_vcmd,
        font=("Helvetica", 14),
    )
    qty_eo_entry.pack(side="left", padx=(30, 0))

    # Rate EO field
    tk.Label(
        rbnn_label_frame, bg=rbnnbg, text="Rate EO", font=("Helvetica", 14)
    ).pack(side="left", padx=(0, 0))
    rate_eo_entry = tk.Entry(
        rbnn_entry_frame,
        textvariable=rate_eo_var,
        width=11,
        font=("Helvetica", 14),
    )
    rate_eo_entry.pack(side="left", padx=(0, 5))

    # Brok Unit EO field
    tk.Label(
        rbnn_label_frame,
        bg=rbnnbg,
        text="Brok Unit EO",
        font=("Helvetica", 14),
    ).pack(side="left", padx=(70, 0))
    brok_unit_eo_entry = tk.Entry(
        rbnn_entry_frame,
        textvariable=brok_unit_eo_var,
        width=11,
        font=("Helvetica", 14),
        state="readonly",
    )
    brok_unit_eo_entry.pack(side="left", padx=15)

    # Net Rate EO field
    tk.Label(
        rbnn_label_frame, bg=rbnnbg, text="Net Rate EO", font=("Helvetica", 14)
    ).pack(side="left", padx=(35, 0))
    net_rate_eo_entry = tk.Entry(
        rbnn_entry_frame,
        textvariable=net_rate_eo_var,
        width=11,
        font=("Helvetica", 14),
        state="readonly",
    )
    net_rate_eo_entry.pack(side="left", padx=15)

    # Net Total EO field
    tk.Label(
        rbnn_label_frame,
        bg=rbnnbg,
        text="Net Total EO",
        font=("Helvetica", 14),
    ).pack(side="left", padx=(40, 0))
    net_total_eo_entry = tk.Entry(
        rbnn_entry_frame,
        textvariable=net_total_eo_var,
        width=11,
        font=("Helvetica", 14),
        state="readonly",
    )
    net_total_eo_entry.pack(side="left", padx=15)

    # Exchange radio buttons
    tk.Label(
        rbnn_label_frame, bg=rbnnbg, text="Exchange", font=("Helvetica", 14)
    ).pack(side="left", padx=(70, 0), pady=2)
    nse_radio = tk.Radiobutton(
        rbnn_entry_frame,
        bg=rbnnbg,
        text="NSE",
        variable=exchange_var,
        value="NSE",
        font=("Helvetica", 14),
    )
    nse_radio.pack(side="left", padx=10)
    bse_radio = tk.Radiobutton(
        rbnn_entry_frame,
        bg=rbnnbg,
        text="BSE",
        variable=exchange_var,
        value="BSE",
        font=("Helvetica", 14),
    )
    bse_radio.pack(side="left")

    nse_radio.bind(
        "<KeyPress>",
        lambda e: on_ex_radio_key(
            e, nse_radio, "NSE", exchange_var, nse_radio, bse_radio
        ),
    )
    bse_radio.bind(
        "<KeyPress>",
        lambda e: on_ex_radio_key(
            e, bse_radio, "BSE", exchange_var, nse_radio, bse_radio
        ),
    )

    # Submit button
    submit_btn = tk.Button(
        rbnn_entry_frame,
        text="🚀 Submit 🚀",
        width=15,
        font=("Comic Sans MS", 14, "bold"),
        bg=submitusualbg,
        fg="white",
        activebackground=submitactivebg,
        activeforeground="white",
        relief="raised",
        bd=3,
        cursor="hand2",
    )
    submit_btn.pack(side="left", padx=30)
    apply_button_animations(submit_btn, submitusualbg, "#2563eb")

    # WAP field
    tk.Label(
        wbt_label_frame, bg=wbtbg, text="Wgt.Av.Price.", font=("Helvetica", 14)
    ).pack(side="left", padx=(0, 0), pady=2)
    wap_entry = tk.Entry(
        wbt_entry_frame, textvariable=wap_var, width=11, font=("Helvetica", 14)
    )
    wap_entry.pack(side="left", padx=0)

    # ... [rest of the widget creation from add_trade] ...
    # Brokerage per Share field starts here
    tk.Label(
        wbt_label_frame,
        bg=wbtbg,
        text="Brok/Share",
        font=("Helvetica", 14),
    ).pack(side="left", padx=(25, 0), pady=2)
    brs_entry = tk.Entry(
        wbt_entry_frame, textvariable=brs_var, width=11, font=("Helvetica", 14)
    )
    brs_entry.pack(side="left", padx=15)

    # Lot Price field starts here
    tk.Label(
        wbt_label_frame, bg=wbtbg, text="Lot Price", font=("Helvetica", 14)
    ).pack(side="left", padx=(50, 0), pady=2)
    lp_entry = tk.Entry(
        wbt_entry_frame, textvariable=lp_var, width=11, font=("Helvetica", 14)
    )
    lp_entry.pack(side="left", padx=15)

    # Lot Brok field starts here
    tk.Label(
        wbt_label_frame, bg=wbtbg, text="Lot Brok", font=("Helvetica", 14)
    ).pack(side="left", padx=(70, 0), pady=2)
    tot_brok_entry = tk.Entry(
        wbt_entry_frame,
        textvariable=tot_brok_var,
        width=11,
        font=("Helvetica", 14),
    )
    tot_brok_entry.pack(side="left", padx=15)

    # Exchange Charge field starts here
    tk.Label(
        wbt_label_frame, bg=wbtbg, text="ETC", font=("Helvetica", 14)
    ).pack(side="left", padx=(75, 0), pady=2)
    etc_entry = tk.Entry(
        wbt_entry_frame, textvariable=etc_var, width=11, font=("Helvetica", 14)
    )
    etc_entry.pack(side="left", padx=15)

    # SEBI Charge field starts here
    tk.Label(
        wbt_label_frame,
        bg=wbtbg,
        text="SEBI Charge",
        font=("Helvetica", 14),
    ).pack(side="left", padx=(110, 0), pady=2)
    sebi_entry = tk.Entry(
        wbt_entry_frame,
        textvariable=sebi_var,
        width=11,
        font=("Helvetica", 14),
    )
    sebi_entry.pack(side="left", padx=15)

    # Sell Charge field starts here
    tk.Label(
        wbt_label_frame,
        bg=wbtbg,
        text="Sell Charge",
        font=("Helvetica", 14),
    ).pack(side="left", padx=(40, 0), pady=2)
    sell_charge_entry = tk.Entry(
        wbt_entry_frame,
        textvariable=sell_charge_var,
        width=11,
        font=("Helvetica", 14),
    )
    sell_charge_entry.pack(side="left", padx=15)

    # GST field starts here
    tk.Label(
        gss_label_frame, bg=gssbg, text="GST", font=("Helvetica", 14)
    ).pack(side="left", padx=(0, 0), pady=2)
    gst_entry = tk.Entry(
        gss_entry_frame, textvariable=gst_var, width=11, font=("Helvetica", 14)
    )
    gst_entry.pack(side="left", padx=(0, 5))

    # Stamp Duty field starts here
    tk.Label(
        gss_label_frame,
        bg=gssbg,
        text="Stamp Duty",
        font=("Helvetica", 14),
    ).pack(side="left", padx=(100, 0), pady=2)
    stamp_duty_entry = tk.Entry(
        gss_entry_frame,
        textvariable=stamp_duty_var,
        width=11,
        font=("Helvetica", 14),
    )
    stamp_duty_entry.pack(side="left", padx=15)

    # STT field starts here
    tk.Label(
        gss_label_frame, bg=gssbg, text="STT", font=("Helvetica", 14)
    ).pack(side="left", padx=(50, 0), pady=2)
    stt_entry = tk.Entry(
        gss_entry_frame, textvariable=stt_var, width=11, font=("Helvetica", 14)
    )
    stt_entry.pack(side="left", padx=15)

    # IGST field starts here
    tk.Label(
        gss_label_frame, bg=gssbg, text="IGST", font=("Helvetica", 14)
    ).pack(side="left", padx=(110, 0), pady=2)
    igst_entry = tk.Entry(
        gss_entry_frame,
        textvariable=igst_var,
        width=11,
        font=("Helvetica", 14),
    )
    igst_entry.pack(side="left", padx=15)

    # Net Trade Amount field starts here
    tk.Label(
        gss_label_frame,
        bg=gssbg,
        text="Net Trade Amt.",
        font=("Helvetica", 14),
    ).pack(side="left", padx=(100, 0), pady=2)
    net_trade_entry = tk.Entry(
        gss_entry_frame,
        textvariable=net_trade_var,
        width=11,
        font=("Helvetica", 14),
    )
    net_trade_entry.pack(side="left", padx=15)

    # Contract Lot Price field starts here
    tk.Label(
        gss_label_frame,
        bg=gssbg,
        text="Cont Lot.",
        font=("Helvetica", 14),
    ).pack(side="left", padx=(24, 0), pady=2)
    lot_cont_entry = tk.Entry(
        gss_entry_frame,
        textvariable=lot_cont_var,
        width=11,
        font=("Helvetica", 14),
        state="readonly",
        takefocus=False,
    )
    lot_cont_entry.pack(side="left", padx=15)

    # STT Cont field starts here
    tk.Label(
        gss_label_frame,
        bg=gssbg,
        text="STT Cont.",
        font=("Helvetica", 14),
    ).pack(side="left", padx=(67, 0), pady=2)
    stt_cont_entry = tk.Entry(
        gss_entry_frame,
        textvariable=stt_cont_var,
        width=11,
        font=("Helvetica", 14),
        state="readonly",
        takefocus=False,
    )
    stt_cont_entry.pack(side="left", padx=15)

    # Trade Note field starts here
    tk.Label(
        trd_note_frame, bg=gssbg, text="Trade Note", font=("Helvetica", 14)
    ).pack(side="left", padx=(0, 0), pady=(15, 0))
    note_trd_entry = tk.Entry(
        trd_note_frame,
        textvariable=note_trd_var,
        width=60,
        font=("Helvetica", 14),
    )
    note_trd_entry.pack(side="left", padx=(10, 0), pady=(15, 0))

    # Computed Bank Transfer field starts here
    tk.Label(
        trd_note_frame, bg=gssbg, text="Bank Trans", font=("Helvetica", 14)
    ).pack(side="left", padx=(10, 0), pady=(15, 0))
    comp_bt_entry = tk.Entry(
        trd_note_frame,
        textvariable=comp_bt_var,
        width=11,
        font=("Helvetica", 14),
        state="readonly",
    )
    comp_bt_entry.pack(side="left", padx=(10, 0), pady=(15, 0))

    # --- Applicable (Theoretical) Frame Starts Here ---
    tk.Label(
        app_label_frame, bg=appbg, text="ETC (App)", font=("Helvetica", 14)
    ).pack(side="left", padx=(0, 0), pady=2)
    etc_app_entry = tk.Entry(
        app_entry_frame,
        textvariable=etc_app_var,
        width=11,
        font=("Helvetica", 14),
        state="readonly",
        takefocus=False,
    )
    etc_app_entry.pack(side="left", padx=(0, 5))

    tk.Label(
        app_label_frame, bg=appbg, text="GST (App)", font=("Helvetica", 14)
    ).pack(side="left", padx=(45, 0), pady=2)
    gst_app_entry = tk.Entry(
        app_entry_frame,
        textvariable=gst_app_var,
        width=11,
        font=("Helvetica", 14),
        state="readonly",
        takefocus=False,
    )
    gst_app_entry.pack(side="left", padx=15)

    tk.Label(
        app_label_frame, bg=appbg, text="STT (App)", font=("Helvetica", 14)
    ).pack(side="left", padx=(55, 0), pady=2)
    stt_app_entry = tk.Entry(
        app_entry_frame,
        textvariable=stt_app_var,
        width=11,
        font=("Helvetica", 14),
        state="readonly",
        takefocus=False,
    )
    stt_app_entry.pack(side="left", padx=15)

    tk.Label(
        app_label_frame, bg=appbg, text="Net (App)", font=("Helvetica", 14)
    ).pack(side="left", padx=(60, 0), pady=2)
    net_trade_app_entry = tk.Entry(
        app_entry_frame,
        textvariable=net_trade_app_var,
        width=11,
        font=("Helvetica", 14),
        state="readonly",
        takefocus=False,
    )
    net_trade_app_entry.pack(side="left", padx=15)

    tk.Label(
        app_label_frame, bg=appbg, text="Diff (Trd)", font=("Helvetica", 14)
    ).pack(side="left", padx=(65, 0), pady=2)
    diff_trd_entry = tk.Entry(
        app_entry_frame,
        textvariable=diff_trd_var,
        width=11,
        font=("Helvetica", 14),
        state="readonly",
        takefocus=False,
        fg="#b91c1c",
    )
    diff_trd_entry.pack(side="left", padx=15)

    # --- Apply Global Styles & Hovers ---
    theme_widgets = {
        "trd_date_entry": trd_date_entry,
        "settle_date_entry": settle_date_entry,
        "ord_dt_entry": ord_dt_entry,
        "cont_no_entry": cont_no_entry,
        "current_trade_no_entry": current_trade_no_entry,
        "note_cont_entry": note_cont_entry,
        "isin_entry": isin_entry,
        "ord_no_entry": ord_no_entry,
        "trd_no_entry": trd_no_entry,
        "rate_eo_entry": rate_eo_entry,
        "brok_unit_eo_entry": brok_unit_eo_entry,
        "net_rate_eo_entry": net_rate_eo_entry,
        "net_total_eo_entry": net_total_eo_entry,
        "wap_entry": wap_entry,
        "brs_entry": brs_entry,
        "lp_entry": lp_entry,
        "tot_brok_entry": tot_brok_entry,
        "etc_entry": etc_entry,
        "sebi_entry": sebi_entry,
        "sell_charge_entry": sell_charge_entry,
        "gst_entry": gst_entry,
        "stamp_duty_entry": stamp_duty_entry,
        "stt_entry": stt_entry,
        "igst_entry": igst_entry,
        "net_trade_entry": net_trade_entry,
        "lot_cont_entry": lot_cont_entry,
        "stt_cont_entry": stt_cont_entry,
        "note_trd_entry": note_trd_entry,
        "comp_bt_entry": comp_bt_entry,
        "etc_app_entry": etc_app_entry,
        "gst_app_entry": gst_app_entry,
        "stt_app_entry": stt_app_entry,
        "net_trade_app_entry": net_trade_app_entry,
        "diff_trd_entry": diff_trd_entry,
        "settle_no_entry": settle_no_entry,
        "trades_spin": trades_spin,
        "qty_trd_entry": qty_trd_entry,
        "qty_eo_entry": qty_eo_entry,
        "company_entry": company_entry,
    }

    for key, widget in theme_widgets.items():
        is_ro = str(widget.cget("state")) in ("readonly", "disabled")
        apply_entry_theme(widget, is_readonly=is_ro)
        bind_entry_hover(widget)
        _create_context_menu(widget)

    bind_tooltip(
        cont_no_entry,
        tooltip_var,
        "Enter the unique contract note number provided by your broker.",
    )
    bind_tooltip(
        trades_spin,
        tooltip_var,
        "Number of distinct trades expected within this contract.",
    )
    bind_tooltip(
        qty_trd_entry,
        tooltip_var,
        "The total quantity of shares for this specific trade.",
    )
    bind_tooltip(wap_entry, tooltip_var, "Weighted Average Price per unit.")
    bind_tooltip(company_entry, tooltip_var, "The company for this trade.")
    bind_tooltip(
        net_trade_entry, tooltip_var, "The net amount for this transaction."
    )

    # --- Buttons ---
    ok_btn = tk.Button(
        btn_frame,
        text="✅ OK ✅",
        font=("Helvetica", 14, "bold"),
        bg="#10b981",
        fg="white",
        activebackground="#059669",
        activeforeground="white",
        width=12,
        bd=3,
        relief="raised",
        cursor="hand2",
    )
    ok_btn.pack(side="right", padx=5)
    apply_button_animations(ok_btn, "#10b981", "#059669")

    cancel_btn = tk.Button(
        btn_frame,
        text="❌ Cancel ❌",
        font=("Helvetica", 14, "bold"),
        bg="#ef4444",
        fg="white",
        activebackground="#dc2626",
        activeforeground="white",
        width=12,
        bd=3,
        relief="raised",
        cursor="hand2",
        command=cleanup_and_close,
    )
    cancel_btn.pack(side="right", padx=5)
    apply_button_animations(cancel_btn, "#ef4444", "#dc2626")

    hint_label = tk.Label(
        btn_frame,
        text="Press F1 for help, and Esc to Rollback.",
        font=("Helvetica", 16),
        bg=hintbg,
    )
    hint_label.pack(side="left", padx=8)

    # --------------------------------------------------------------------------
    # 3. DATA LOADING AND EVENT HANDLING
    # --------------------------------------------------------------------------

    def load_trade_data(id_trd):
        nonlocal data, original_data, exchange_orders, current_eo_index
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                # Fetch transaction and stock info
                cursor.execute(
                    """
                    SELECT t.*, s.isin
                    FROM transactions t
                    JOIN stocks s ON t.id_stk = s.id_stk
                    WHERE t.id_trd = ?
                    """,
                    (id_trd,),
                )
                trans_row = cursor.fetchone()
                if not trans_row:
                    show_colorful_error(
                        rat_win, "Error", f"Trade with ID {id_trd} not found."
                    )
                    cleanup_and_close()
                    return
                trans_cols = [desc[0] for desc in cursor.description]
                data.update(dict(zip(trans_cols, trans_row)))

                # Fetch contract
                cursor.execute(
                    "SELECT * FROM contracts WHERE cont_no = ?",
                    (data["cont_no"],),
                )
                cont_row = cursor.fetchone()
                cont_cols = [desc[0] for desc in cursor.description]
                data.update(dict(zip(cont_cols, cont_row)))

                # Get all trade IDs for the contract to determine current trade number
                cursor.execute(
                    "SELECT id_trd FROM transactions WHERE cont_no = ? ORDER BY id_trd ASC",
                    (data["cont_no"],),
                )
                all_ids_in_contract = [r[0] for r in cursor.fetchall()]
                try:
                    # Store 1-based index
                    data["current_trade_no"] = (
                        all_ids_in_contract.index(id_trd) + 1
                    )
                except ValueError:
                    data["current_trade_no"] = 0  # Fallback

                # Fetch other trades in the same contract to calculate base values
                cursor.execute(
                    "SELECT price_lot_trd, stt_trd FROM transactions WHERE cont_no = ? AND id_trd != ? AND net_amt_trd IS NOT NULL",
                    (data["cont_no"], id_trd),
                )
                other_trades = cursor.fetchall()
                data["lot_cont"] = sum(
                    r[0] for r in other_trades if r[0] is not None
                )
                data["stt_so_far"] = sum(
                    r[1] for r in other_trades if r[1] is not None
                )

                # Fetch exchange orders
                cursor.execute(
                    "SELECT * FROM exchange_orders WHERE id_trd = ? ORDER BY id_eo",
                    (id_trd,),
                )
                eo_cols = [desc[0] for desc in cursor.description]
                exchange_orders = [
                    dict(zip(eo_cols, row)) for row in cursor.fetchall()
                ]

                # Fetch total computed bank amount for OTHER transactions in the contract
                cursor.execute(
                    """
                    SELECT SUM(CASE
                        WHEN trade_type_trd = 'BUY' THEN net_amt_trd
                        WHEN trade_type_trd = 'SELL' THEN -net_amt_trd
                        ELSE 0
                    END)
                    FROM transactions
                    WHERE cont_no = ? AND id_trd != ? AND net_amt_trd IS NOT NULL
                    """,
                    (data["cont_no"], id_trd),
                )
                comp_bt_row = cursor.fetchone()
                comp_bt_amt_so_far = (
                    comp_bt_row[0]
                    if comp_bt_row and comp_bt_row[0] is not None
                    else 0.0
                )
                data["comp_bt_amt"] = comp_bt_amt_so_far
            original_data = data.copy()
            original_data["exchange_orders"] = [
                eo.copy() for eo in exchange_orders
            ]
            current_eo_index = 0
            populate_form()

        except sqlite3.Error as e:
            show_colorful_error(
                rat_win, "Database Error", f"Failed to load trade: {e}"
            )
            cleanup_and_close()

    def populate_form():
        # Populate contract fields
        cont_no_var.set(data.get("cont_no", ""))
        trd_dt_str = data.get("trd_dt", "")
        if trd_dt_str:
            trd_date_entry.set_date(
                datetime.strptime(trd_dt_str, "%Y-%m-%d").date()
            )
        settle_no_var.set(data.get("settle_no", 0))
        settle_dt_str = data.get("settle_dt", "")
        if settle_dt_str:
            settle_date_entry.set_date(
                datetime.strptime(settle_dt_str, "%Y-%m-%d").date()
            )
        no_of_trades_var.set(data.get("no_of_trades", 1))
        current_trade_no_var.set(data.get("current_trade_no", 0))
        note_cont_var.set(data.get("note_cont", ""))

        # Populate transaction fields
        company_name_var.set(data.get("company_name", ""))
        isin_var.set(data.get("isin", ""))
        buy_sell_var.set(data.get("trade_type_trd", "BUY"))
        qty_trd_var.set(data.get("qty_trd", 0))
        exchange_var.set(data.get("exchange", "NSE"))
        note_trd_var.set(data.get("note_trd", ""))

        # Populate calculated fields
        wap_var.set(data.get("wap_unit_trd", 0.0))
        brs_var.set(data.get("brok_unit_trd", 0.0))
        lp_var.set(data.get("price_lot_trd", 0.0))
        tot_brok_var.set(data.get("brok_lot_trd", 0.0))
        etc_var.set(data.get("etc_trd", 0.0))
        sebi_var.set(data.get("sebi_trd", 0.0))
        gst_var.set(data.get("gst_trd", 0.0))
        stamp_duty_var.set(data.get("stamp_trd", 0.0))
        stt_var.set(data.get("stt_trd", 0))
        igst_var.set(data.get("igst_trd", 0.0))
        sell_charge_var.set(data.get("sell_chrg_trd", 0.0))
        net_trade_var.set(data.get("net_amt_trd", 0.0))

        # Calculate the total comp_bt including the current trade being edited
        base_comp_bt = data.get(
            "comp_bt_amt", 0.0
        )  # This is from OTHER trades
        current_net_amt = data.get("net_amt_trd", 0.0)
        current_trade_type = data.get("trade_type_trd", "BUY")

        if current_trade_type == "BUY":
            total_comp_bt = base_comp_bt + current_net_amt
        else:  # SELL
            total_comp_bt = base_comp_bt - current_net_amt

        comp_bt_var.set(round(total_comp_bt, 2))

        # Load current EO
        load_current_eo()

    def load_current_eo():
        if exchange_orders and 0 <= current_eo_index < len(exchange_orders):
            eo = exchange_orders[current_eo_index]
            ord_no_var.set(eo.get("ord_no", "0"))
            ord_dt_str = eo.get("ord_dt", "")
            if ord_dt_str:
                ord_dt_entry.set_date(
                    datetime.strptime(ord_dt_str, "%Y-%m-%d").date()
                )
            trd_no_var.set(eo.get("trd_no", 0))
            qty_eo_var.set(eo.get("qty_eo", 0))
            rate_eo_var.set(eo.get("rate_eo", 0.0))
            brok_unit_eo_var.set(eo.get("brok_unit_eo", 0.0))
            net_rate_eo_var.set(eo.get("net_rate_eo", 0.0))
            net_total_eo_var.set(eo.get("net_total_eo", 0.0))
            submit_btn.config(state="normal")
            ok_btn.config(state="disabled")
        else:
            # No more EOs
            submit_btn.config(state="disabled")
            ok_btn.config(state="normal")

    def rate_eo_entry_key_release(
        _event,
        rate_eo_var: tk.DoubleVar,
        brok_unit_eo_var: tk.DoubleVar,
        buy_sell_var: tk.StringVar,
        net_rate_eo_var: tk.DoubleVar,
        qty_eo_var: tk.IntVar,
        net_total_eo_var: tk.DoubleVar,
    ) -> None:
        """
        Update brokerage and net values when the Rate EO entry is changed.
        """
        try:
            rate_eo_value = float(rate_eo_var.get())
            brok_unit_eo_value = round(BROK * rate_eo_value, 4)
            brok_unit_eo_var.set(brok_unit_eo_value)

            if buy_sell_var.get() == "BUY":
                net_rate_eo_value = round(
                    rate_eo_value + brok_unit_eo_value, 4
                )
            else:
                net_rate_eo_value = round(
                    rate_eo_value - brok_unit_eo_value, 4
                )
            net_rate_eo_var.set(net_rate_eo_value)

            net_total_eo_value = round(qty_eo_var.get() * net_rate_eo_value, 4)
            net_total_eo_var.set(net_total_eo_value)

        except (ValueError, tk.TclError):
            pass

    def rate_eo_entry_focus_out(
        _event,
        rate_eo_var: tk.DoubleVar,
    ) -> None:
        """
        Format the rate_eo value on focus out.
        """
        try:
            rate_eo_value = float(rate_eo_var.get())
            rate_eo_var.set(round(rate_eo_value, 4))
        except (ValueError, tk.TclError):
            pass

    def on_submit_eo():
        nonlocal current_eo_index
        # Save current EO data from form back to the `exchange_orders` list
        if exchange_orders and 0 <= current_eo_index < len(exchange_orders):
            exchange_orders[current_eo_index].update(
                {
                    "ord_no": ord_no_var.get(),
                    "ord_dt": ord_dt_entry.get_date().strftime("%Y-%m-%d"),
                    "trd_no": trd_no_var.get(),
                    "qty_eo": qty_eo_var.get(),
                    "rate_eo": rate_eo_var.get(),
                    "brok_unit_eo": brok_unit_eo_var.get(),
                    "net_rate_eo": net_rate_eo_var.get(),
                    "net_total_eo": net_total_eo_var.get(),
                }
            )

        current_eo_index += 1
        if current_eo_index < len(exchange_orders):
            load_current_eo()
            show_colorful_info(
                rat_win,
                "Next Order",
                f"Loaded Exchange Order {current_eo_index + 1}/{len(exchange_orders)}",
            )
        else:
            show_colorful_info(
                rat_win,
                "Last Order",
                "All exchange orders processed. Click 'Update Trade' to save.",
            )
            load_current_eo()  # This will disable submit and enable OK

    def show_help(_event=None):
        help_text = (
            "Update Trade Help:\n\n"
            "• Use this window to modify existing trade details.\n"
            "• Applicable (App) fields show theoretical values based on broker rates.\n"
            "• Hover over any field to see its specific hint at the bottom.\n"
            "• Press 'OK' to save changes to the database.\n"
            "• Press 'Esc' to cancel and close this window."
        )
        show_colorful_info(rat_win, "Help - Update Trade", help_text)

    def validate_positive_financial_input_and_format(_event=None):
        if _event is not None and hasattr(_event, "widget"):
            widget = _event.widget
            try:
                val = float(widget.get())
                if val < 0:
                    raise ValueError("Negative value")
                widget.config(bg="black")
            except ValueError:

                def blink(w, colors, delay=100, count=0):
                    try:
                        if count < len(colors):
                            w.config(bg=colors[count])
                            w.after(delay, blink, w, colors, delay, count + 1)
                        else:
                            w.config(bg="#ffcccc")
                    except tk.TclError:
                        pass

                blink_colors = ["#ffcccc", "black"] * 5
                blink(widget, blink_colors)
                return

        try:
            if _event is not None and hasattr(_event, "widget"):
                widget = _event.widget
                current_value = float(widget.get() or 0)
                formatted_value = (
                    0.0000 if current_value == 0 else round(current_value, 4)
                )
                widget.delete(0, "end")
                widget.insert(0, f"{formatted_value:.4f}")
        except (ValueError, tk.TclError, AttributeError):
            pass

    def on_update_trade():
        total_qty = sum(eo.get("qty_eo", 0) for eo in exchange_orders)
        qty_trd_var.set(total_qty)
        total_price = sum(
            eo.get("qty_eo", 0) * eo.get("rate_eo", 0.0)
            for eo in exchange_orders
        )
        wap_var.set(total_price / total_qty if total_qty else 0)

        # Call the updated function with all required variables
        recalculate_from_wap_change(
            wap_var,
            qty_trd_var,
            exchange_var,
            buy_sell_var,
            brs_var,
            lp_var,
            lot_cont_var,
            tot_brok_var,
            etc_var,
            sebi_var,
            gst_var,
            stt_cont_var,
            stt_var,
            net_trade_var,
            lot_cont_entry,
            brs_entry,
            lp_entry,
            tot_brok_entry,
            etc_entry,
            sebi_entry,
            gst_entry,
            stt_entry,
            net_trade_entry,
            comp_bt_var,
            comp_bt_entry,
            stt_cont_entry,
            data,
            trd_date_entry,
        )

        calculate_applicable_fields()

        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()

                cursor.execute(
                    "UPDATE contracts SET trd_dt=?, settle_no=?, settle_dt=?, note_cont=? WHERE cont_no = ?",
                    (
                        trd_date_entry.get_date().strftime("%Y-%m-%d"),
                        settle_no_var.get(),
                        settle_date_entry.get_date().strftime("%Y-%m-%d"),
                        note_cont_var.get(),
                        data["cont_no"],
                    ),
                )

                cursor.execute(
                    """
                    UPDATE transactions SET
                        trd_dt=?, trade_type_trd=?, exchange=?, qty_trd=?, wap_unit_trd=?, brok_unit_trd=?, price_lot_trd=?,
                        brok_lot_trd=?, etc_trd=?, sebi_trd=?, sell_chrg_trd=?, gst_trd=?, stamp_trd=?, stt_trd=?, igst_trd=?,
                        net_amt_trd=?, etc_trd_applicable=?, gst_trd_applicable=?, stt_trd_applicable=?, net_amt_trd_applicable=?, note_trd=?
                    WHERE id_trd = ?
                    """,
                    (
                        trd_date_entry.get_date().strftime("%Y-%m-%d"),
                        buy_sell_var.get(),
                        exchange_var.get(),
                        qty_trd_var.get(),
                        wap_var.get(),
                        brs_var.get(),
                        lp_var.get(),
                        tot_brok_var.get(),
                        etc_var.get(),
                        sebi_var.get(),
                        sell_charge_var.get(),
                        gst_var.get(),
                        stamp_duty_var.get(),
                        stt_var.get(),
                        igst_var.get(),
                        net_trade_var.get(),
                        etc_app_var.get(),
                        gst_app_var.get(),
                        stt_app_var.get(),
                        net_trade_app_var.get(),
                        note_trd_var.get(),
                        data["id_trd"],
                    ),
                )

                for eo in exchange_orders:
                    cursor.execute(
                        "UPDATE exchange_orders SET ord_no=?, ord_dt=?, trd_no=?, qty_eo=?, rate_eo=?, brok_unit_eo=?, net_rate_eo=?, net_total_eo=? WHERE id_eo = ?",
                        (
                            eo["ord_no"],
                            eo["ord_dt"],
                            eo["trd_no"],
                            eo["qty_eo"],
                            eo["rate_eo"],
                            eo["brok_unit_eo"],
                            eo["net_rate_eo"],
                            eo["net_total_eo"],
                            eo["id_eo"],
                        ),
                    )

                cursor.execute(
                    """
                    UPDATE contracts SET
                        brok_cont = (SELECT SUM(brok_lot_trd) FROM transactions WHERE cont_no = ?),
                        etc_cont = (SELECT SUM(etc_trd) FROM transactions WHERE cont_no = ?),
                        sebi_cont = (SELECT SUM(sebi_trd) FROM transactions WHERE cont_no = ?),
                        gst_cont = (SELECT SUM(gst_trd) FROM transactions WHERE cont_no = ?),
                        stamp_cont = (SELECT SUM(stamp_trd) FROM transactions WHERE cont_no = ?),
                        stt_cont = (SELECT SUM(stt_trd) FROM transactions WHERE cont_no = ?),
                        igst_cont = (SELECT SUM(igst_trd) FROM transactions WHERE cont_no = ?),
                        net_amt_cont = (SELECT SUM(net_amt_trd) FROM transactions WHERE cont_no = ?),
                        sell_chrg_cont = (SELECT SUM(sell_chrg_trd) FROM transactions WHERE cont_no = ?),
                        etc_cont_applicable = (SELECT SUM(etc_trd_applicable) FROM transactions WHERE cont_no = ?),
                        gst_cont_applicable = (SELECT SUM(gst_trd_applicable) FROM transactions WHERE cont_no = ?),
                        stt_cont_applicable = (SELECT SUM(stt_trd_applicable) FROM transactions WHERE cont_no = ?),
                        net_amt_cont_applicable = (SELECT SUM(net_amt_trd_applicable) FROM transactions WHERE cont_no = ?),
                        no_of_trades = ?
                    WHERE cont_no = ?
                    """,
                    (
                        data["cont_no"],
                        data["cont_no"],
                        data["cont_no"],
                        data["cont_no"],
                        data["cont_no"],
                        data["cont_no"],
                        data["cont_no"],
                        data["cont_no"],
                        data["cont_no"],
                        data["cont_no"],
                        data["cont_no"],
                        data["cont_no"],
                        data["cont_no"],
                        no_of_trades_var.get(),
                        data["cont_no"],
                    ),
                )

                cursor.execute(
                    "DELETE FROM computed_bank WHERE cont_no = ?",
                    (data["cont_no"],),
                )
                cursor.execute(
                    "SELECT SUM(CASE WHEN trade_type_trd = 'BUY' THEN net_amt_trd WHEN trade_type_trd = 'SELL' THEN -net_amt_trd ELSE 0 END), SUM(CASE WHEN trade_type_trd = 'BUY' THEN net_amt_trd_applicable WHEN trade_type_trd = 'SELL' THEN -net_amt_trd_applicable ELSE 0 END) FROM transactions WHERE cont_no = ? AND net_amt_trd IS NOT NULL",
                    (data["cont_no"],),
                )
                comp_bt_row = cursor.fetchone()

                if comp_bt_row and comp_bt_row[0] != 0:
                    cursor.execute(
                        "INSERT INTO computed_bank (cont_no, comp_bt_dt, comp_bt_type, comp_bt_amt, comp_bt_amt_applicable, comp_bt_desc) VALUES (?, ?, ?, ?, ?, ?)",
                        (
                            data["cont_no"],
                            settle_date_entry.get_date().strftime("%Y-%m-%d"),
                            "DEBIT" if comp_bt_row[0] > 0 else "CREDIT",
                            round(abs(comp_bt_row[0]), 2),
                            round(abs(comp_bt_row[1] or 0.0), 2),
                            "Buying" if comp_bt_row[0] > 0 else "Selling",
                        ),
                    )
                enforce_no_oversell_for_stock(cursor, data["id_stk"])

                conn.commit()

                compute_avg_price(data["id_stk"], buy_sell_var.get())

                show_colorful_info(
                    rat_win, "Success", "Trade updated successfully!"
                )

                # --- Prompt for another trade update ---
                if show_colorful_yesno(
                    rat_win,
                    "🔄 Update Another Trade?",
                    "Do you want to update another trade?",
                ):
                    new_id = select_trade_from_list(
                        rat_win, "Select Trade to Update", "#e0f7fa", "#00796b"
                    )
                    if new_id:
                        load_trade_data(new_id)
                        trd_date_entry.focus_set()
                    else:
                        cleanup_and_close()
                else:
                    cleanup_and_close()

        except (sqlite3.Error, ValueError) as e:
            show_colorful_error(
                rat_win, "Database Error", f"Failed to update trade: {e}"
            )

    def on_enter(_event=None) -> None:
        focused_widget = rat_win.focus_get()
        if focused_widget in (submit_btn, cancel_btn, ok_btn):
            inv = getattr(focused_widget, "invoke", None)
            try:
                if inv is not None:
                    inv()
            except TypeError:
                pass
        elif isinstance(
            focused_widget,
            (tk.Entry, tk.Spinbox, tk.Text, tk.Radiobutton, ttk.Combobox),
        ):
            next_widget = focused_widget.tk_focusNext()
            if next_widget is not None:
                next_widget.focus_set()
        else:
            inv = getattr(ok_btn, "invoke", None)
            try:
                if inv is not None:
                    inv()
            except TypeError:
                pass

    # --- Bindings and Initial Load ---
    rat_win.bind("<Return>", on_enter)
    submit_btn.config(command=on_submit_eo)
    ok_btn.config(command=on_update_trade)
    rat_win.bind("<Escape>", on_escape)
    rat_win.bind("<F1>", show_help)

    def _trigger_wap_calc(event=None):
        recalculate_from_wap_change(
            wap_var,
            qty_trd_var,
            exchange_var,
            buy_sell_var,
            brs_var,
            lp_var,
            lot_cont_var,
            tot_brok_var,
            etc_var,
            sebi_var,
            gst_var,
            stt_cont_var,
            stt_var,
            net_trade_var,
            lot_cont_entry,
            brs_entry,
            lp_entry,
            tot_brok_entry,
            etc_entry,
            sebi_entry,
            gst_entry,
            stt_entry,
            net_trade_entry,
            comp_bt_var,
            comp_bt_entry,
            stt_cont_entry,
            data,
            trd_date_entry,
        )

    wap_entry.bind("<KeyRelease>", _trigger_wap_calc)
    wap_entry.bind("<FocusOut>", _trigger_wap_calc, add="+")

    rate_eo_entry.bind(
        "<KeyRelease>",
        lambda event: rate_eo_entry_key_release(
            event,
            rate_eo_var,
            brok_unit_eo_var,
            buy_sell_var,
            net_rate_eo_var,
            qty_eo_var,
            net_total_eo_var,
        ),
    )
    rate_eo_entry.bind(
        "<FocusOut>",
        lambda event: rate_eo_entry_focus_out(event, rate_eo_var),
        add="+",
    )

    for entry in [
        rate_eo_entry,
        brok_unit_eo_entry,
        net_rate_eo_entry,
        net_total_eo_entry,
        brs_entry,
        lp_entry,
        tot_brok_entry,
        etc_entry,
        sebi_entry,
        sell_charge_entry,
        gst_entry,
        stamp_duty_entry,
        stt_entry,
        igst_entry,
        net_trade_entry,
    ]:
        entry.bind(
            "<FocusOut>", validate_positive_financial_input_and_format, add="+"
        )
    submit_btn.bind("<FocusIn>", on_submit_focus_in)
    submit_btn.bind("<FocusOut>", on_submit_focus_out)
    ok_btn.bind("<FocusIn>", on_ok_focus_in)
    ok_btn.bind("<FocusOut>", on_ok_focus_out)

    for entry in [
        etc_entry,
        gst_entry,
        igst_entry,
        sebi_entry,
        sell_charge_entry,
        stamp_duty_entry,
        stt_entry,
        tot_brok_entry,
    ]:
        entry.bind("<KeyRelease>", update_levies_and_net_trade)
        entry.bind("<FocusOut>", update_levies_and_net_trade)

    # Initial data load
    load_trade_data(selected_id_trd)
    trd_date_entry.focus_set()

    parent.wait_window(rat_win)
    try:
        if parent.winfo_exists():
            parent.grab_set()
    except tk.TclError:
        logger.debug("parent.grab_set skipped: parent destroyed.")
