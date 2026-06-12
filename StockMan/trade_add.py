# -*- coding: utf-8 -*-
# StockMan/trade_add.py

"""
trade_add.py
----------------

Modal window and helpers for adding trades to the StockMan application.

This module implements the interactive modal used to create and update
trading contracts and associated transactions in the application's
SQLite database. The primary entry point is the `add_trade(parent,
calling_button)` function which builds a Toplevel dialog that guides the
user through contract-level and trade-level fields, performs validation,
and persists data to the `contracts`, `transactions` and related
exchange tables.
"""

# Core imports
from typing import Union
import tkinter as tk
from tkinter import ttk
import sqlite3
from datetime import datetime
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
    bind_tooltip,
    apply_entry_theme,
    bind_date_spin,
)

from .date_utils import next_working_day
from Shared.modal_utils import disable_parent, enable_parent
from Shared.window_manager import push_window, pop_window, safe_close_modal
from Shared.gui_progressive import progressive_selection
from .company_add import add_company
from .company_ex_import import export_company
from .trade_utils import compute_avg_price, enforce_no_oversell_for_stock
from .validation_utils import (
    ValidationError,
    show_validation_error,
    validate_exchange_order_payload,
    validate_order_quantity_progress,
    validate_trade_core_payload,
    validate_required_mapping,
)


def validate_required_fields(data_dict, required_fields, parent_window=None):
    try:
        validate_required_mapping(data_dict, required_fields)
    except ValidationError as exc:
        show_validation_error(parent_window, exc, title="Missing Data")
        return False
    return True


def fetch_and_populate_contract(
    cont_no_entry,
    data,
    trd_date_entry,
    settle_no_entry,
    settle_no_var,
    settle_date_entry,
    trades_spin,
    no_of_trades_var,
    comp_bt_var,
    comp_bt_entry,
    current_trade_no,
    current_trade_no_var,
    current_session_trades,
):
    cont_no = cont_no_entry.get().strip()
    if not cont_no:
        return False

    data["cont_no"] = cont_no

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT trd_dt, settle_no, settle_dt, no_of_trades "
                "FROM contracts WHERE cont_no = ?",
                (cont_no,),
            )
            row = cursor.fetchone()

            if row:
                cursor.execute(
                    "SELECT COUNT(*) FROM transactions WHERE cont_no = ?",
                    (cont_no,),
                )
                existing_trades_count = cursor.fetchone()[0] or 0
                new_current_trade_no = existing_trades_count + 1

                cursor.execute(
                    """
                    SELECT SUM(CASE
                        WHEN trade_type_trd = 'BUY' THEN net_amt_trd
                        WHEN trade_type_trd = 'SELL' THEN -net_amt_trd
                        ELSE 0
                    END)
                    FROM transactions
                    WHERE cont_no = ? AND net_amt_trd IS NOT NULL
                    """,
                    (cont_no,),
                )
                comp_bt_row = cursor.fetchone()
                comp_bt_amt = (
                    comp_bt_row[0]
                    if comp_bt_row and comp_bt_row[0] is not None
                    else 0.0
                )
            else:
                if not current_session_trades:
                    try:
                        cursor.execute(
                            "SELECT trd_dt FROM transactions "
                            "ORDER BY id_trd DESC LIMIT 1"
                        )
                        last_trade_row = cursor.fetchone()
                        if last_trade_row:
                            last_dt_str = last_trade_row[0]
                            last_dt = datetime.strptime(
                                last_dt_str, "%Y-%m-%d"
                            ).date()
                            next_day = next_working_day(last_dt)
                            trd_date_entry.set_date(next_day)
                    except (sqlite3.Error, ValueError) as e:
                        logger.error("Error fetching last trade date: %s", e)
                return True

        if row:
            (
                data["trd_dt"],
                data["settle_no"],
                data["settle_dt"],
                data["no_of_trades"],
            ) = row

            if data["trd_dt"]:
                date_obj = datetime.strptime(data["trd_dt"], "%Y-%m-%d").date()
                trd_date_entry.set_date(date_obj)

            if data["settle_no"] is not None:
                settle_no_entry.delete(0, "end")
                settle_no_entry.insert(0, str(data["settle_no"]))
                settle_no_var.set(int(data["settle_no"]))

            if data["settle_dt"]:
                date_obj = datetime.strptime(
                    data["settle_dt"], "%Y-%m-%d"
                ).date()
                settle_date_entry.set_date(date_obj)

            if data["no_of_trades"] is not None:
                no_of_trades = int(data["no_of_trades"])
                no_of_trades_var.set(no_of_trades)  # <--- ADD THIS LINE
                trades_spin.delete(0, "end")
                trades_spin.insert(0, str(no_of_trades))
                current_trade_no[0] = new_current_trade_no
                current_trade_no_var.set(new_current_trade_no)

                data["comp_bt_amt"] = comp_bt_amt
                comp_bt_var.set(comp_bt_amt)
                comp_bt_entry.delete(0, "end")
                comp_bt_entry.insert(0, f"{comp_bt_amt:.2f}")
        return True
    except (ValueError, tk.TclError) as exc:
        logger.debug("fetch_and_populate_contract error: %s", exc)
        return False


def update_and_calculate_settle_no(
    cont_no_entry, settle_no_entry, settle_no_var
) -> int:
    try:
        cont_no = cont_no_entry.get().strip()
        if not cont_no:
            return 0

        parts = cont_no.split("/")
        if len(parts) > 1:
            settle_no_str = parts[1]
            if settle_no_str.isdigit():
                settle_no = int(settle_no_str)
                settle_no_var.set(settle_no)
                settle_no_entry.delete(0, "end")
                settle_no_entry.insert(0, str(settle_no))
                return settle_no

        logger.debug("Could not extract settle_no from cont_no: %s", cont_no)
        settle_no_var.set(0)
        settle_no_entry.delete(0, "end")
        settle_no_entry.insert(0, "0")
        return 0

    except (ValueError, tk.TclError) as exc:
        logger.debug("update_and_calculate_settle_no error: %s", exc)
        settle_no_var.set(0)
        settle_no_entry.delete(0, "end")
        settle_no_entry.insert(0, "0")
        return 0


def update_settle_date_on_focus(
    trd_date_entry: DateEntry,
    settle_date_entry: DateEntry,
    _event=None,
) -> None:
    try:
        trade_date = trd_date_entry.get_date()
        settle_date_entry.set_date(next_working_day(trade_date))
    except (ValueError, tk.TclError) as _exc:
        logger.debug(
            "update_settle_date_on_focus primary path failed: %s", _exc
        )
        try:
            settle_date_entry.set_date(trd_date_entry.get_date())
        except (ValueError, tk.TclError) as _exc2:
            logger.debug("fallback set_date failed: %s", _exc2)


def ord_no_focus_in(
    _event,
    qty_trd_entry: tk.Spinbox,
    qty_trd_var: tk.IntVar,
    data: dict,
    qty_eo_entry: tk.Spinbox,
    qty_eo_var: tk.IntVar,
) -> None:
    qty_trd_entry.config(state="disabled")
    qty_trd_value = qty_trd_var.get()
    remaining_qty = qty_trd_var.get() - data["check_qty"]
    if qty_trd_value > 0:
        qty_eo_entry.config(to=remaining_qty)
        qty_eo_var.set(remaining_qty)


def update_ord_dt_on_focus(
    _event,
    trd_date_entry: DateEntry,
    ord_dt_entry: DateEntry,
) -> None:
    try:
        trade_date = trd_date_entry.get_date()
        ord_dt_entry.set_date(trade_date)
    except (ValueError, tk.TclError) as _exc:
        logger.debug("update_ord_dt_on_focus failed: %s", _exc)


def qty_eo_on_focus_in(
    _event,
    qty_trd_var: tk.IntVar,
    data: dict,
    qty_eo_var: tk.IntVar,
    submit_btn: tk.Button,
) -> None:
    remaining_qty = qty_trd_var.get() - data["check_qty"]
    qty_eo_var.set(remaining_qty)
    submit_btn.config(state="normal")


def update_check_qty_on_focus_out_of_qty_eo(
    _event,
    qty_eo_var: tk.IntVar,
    data: dict,
) -> None:
    try:
        qty_eo_value = qty_eo_var.get()
        data["check_qty"] += qty_eo_value
    except (ValueError, tk.TclError, NameError):
        pass


def rate_eo_entry_key_release(
    _event,
    rate_eo_var: tk.DoubleVar,
    brok_unit_eo_var: tk.DoubleVar,
    brok_unit_eo_entry: tk.Entry,
    buy_sell_var: tk.StringVar,
    net_rate_eo_var: tk.DoubleVar,
    net_rate_eo_entry: tk.Entry,
    qty_eo_var: tk.IntVar,
    net_total_eo_var: tk.DoubleVar,
    net_total_eo_entry: tk.Entry,
) -> None:
    try:
        rate_eo_value = float(rate_eo_var.get())
        brok_unit_eo_value = round(BROK * rate_eo_value, 4)
        brok_unit_eo_var.set(brok_unit_eo_value)
        brok_unit_eo_entry.delete(0, "end")
        brok_unit_eo_entry.insert(0, f"{brok_unit_eo_value:.4f}")
        qty_eo_value = qty_eo_var.get()
        if buy_sell_var.get() == "BUY":
            net_rate_eo_value = round(rate_eo_value + brok_unit_eo_value, 4)
        else:
            net_rate_eo_value = round(rate_eo_value - brok_unit_eo_value, 4)
        net_total_eo_value = round(qty_eo_value * net_rate_eo_value, 4)
        net_rate_eo_var.set(net_rate_eo_value)
        net_rate_eo_entry.delete(0, "end")
        net_rate_eo_entry.insert(0, f"{net_rate_eo_value:.4f}")
        net_total_eo_var.set(net_total_eo_value)
        net_total_eo_entry.delete(0, "end")
        net_total_eo_entry.insert(0, f"{net_total_eo_value:.4f}")
    except (ValueError, tk.TclError):
        pass


def rate_eo_entry_focus_out(
    _event,
    rate_eo_var: tk.DoubleVar,
    rate_eo_entry: tk.Entry,
) -> None:
    try:
        rate_eo_value = float(rate_eo_var.get())
        rate_eo_value = round(rate_eo_value, 4)
        rate_eo_entry.delete(0, "end")
        rate_eo_entry.insert(0, f"{rate_eo_value:.4f}")
    except (ValueError, tk.TclError):
        pass


def on_radio_key(
    event,
    radio_btn: tk.Radiobutton,
    value: str,
    buy_sell_var: tk.StringVar,
    buy_radio: tk.Radiobutton,
    sell_radio: tk.Radiobutton,
) -> None:
    if radio_btn.cget("state") == "disabled":
        return
    if event.keysym == "space":
        buy_sell_var.set(value)
        radio_btn.select()
    elif event.keysym in ("Right", "Left"):
        if radio_btn == buy_radio:
            sell_radio.focus_set()
            buy_sell_var.set("SELL")
            sell_radio.select()
        else:
            buy_radio.focus_set()
            buy_sell_var.set("BUY")
            buy_radio.select()


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


def on_radio_click(radio_btn, var, value):
    if radio_btn.cget("state") != "disabled":
        var.set(value)
        radio_btn.select()
        radio_btn.focus_set()


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

        # Brok/Share = SUM(qty_eo * brok_unit_eo) / qty_trd from actual exchange orders
        _eos_w = data.get("exchange_orders", [])
        if _eos_w and qty_trd_value > 0:
            _total_brok_w = sum(
                eo["qty_eo"] * eo["brok_unit_eo"] for eo in _eos_w
            )
            brs_value = round(_total_brok_w / qty_trd_value, 4)
        else:
            _total_brok_w = round(wap_value * qty_trd_value * BROK, 4)
            brs_value = round(wap_value * BROK, 4)
        brs_var.set(brs_value)

        lp_value = round(wap_value * qty_trd_value, 4)
        lp_var.set(lp_value)

        lot_cont_value = data["lot_cont_etf"] + data["lot_cont_non_etf"]
        lot_cont_var.set(round(lot_cont_value, 4))
        lot_cont_entry.update_idletasks()

        tot_brok_value = round(_total_brok_w, 4)
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

        gst_value = round((tot_brok_value + etc_value + sebi_value) * GST, 4)
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


def on_submit(
    _event=None,
    *,
    data,
    rat_win,
    submit_btn,
    nse_radio,
    bse_radio,
    qty_trd_var,
    exchange_var,
    ord_no_var,
    ord_dt_entry,
    trd_no_var,
    qty_eo_var,
    rate_eo_var,
    brok_unit_eo_var,
    net_rate_eo_var,
    net_total_eo_var,
    qty_eo_entry,
    ord_no_entry,
    trd_no_entry,
    rate_eo_entry,
    brok_unit_eo_entry,
    net_rate_eo_entry,
    net_total_eo_entry,
    wap_var,
    brs_var,
    lp_var,
    tot_brok_var,
    etc_var,
    sebi_var,
    gst_var,
    lot_cont_var,
    stt_cont_var,
    stt_var,
    stamp_duty_var,
    igst_var,
    sell_charge_var,
    net_trade_var,
    lot_cont_entry,
    wap_entry,
    brs_entry,
    lp_entry,
    tot_brok_entry,
    etc_entry,
    sebi_entry,
    gst_entry,
    stt_entry,
    stt_cont_entry,
    stamp_duty_entry,
    igst_entry,
    sell_charge_entry,
    net_trade_entry,
    buy_sell_var,
    etc_app_var,
    gst_app_var,
    stt_app_var,
    net_trade_app_var,
    diff_trd_var,
    cleanup_and_close,
    validate_required_fields_fn,
    calculate_applicable_fields_fn=None,
    refresh_financial_formats_fn=None,
):
    submit_btn.config(state="disabled")

    required_fields = ["cont_no", "company_name"]
    if not validate_required_fields_fn(data, required_fields, rat_win):
        return

    try:
        data["qty_trd"] = qty_trd_var.get()
        data["exchange"] = exchange_var.get()
        data["ord_no"] = ord_no_var.get()
        data["ord_dt"] = ord_dt_entry.get_date().strftime("%Y-%m-%d")
        data["trd_no"] = trd_no_var.get()
        data["qty_eo"] = qty_eo_var.get()
        data["rate_eo"] = rate_eo_var.get()
        data["brok_unit_eo"] = brok_unit_eo_var.get()
        data["net_rate_eo"] = net_rate_eo_var.get()
        data["net_total_eo"] = net_total_eo_var.get()
        data["total_order_price"] += data["qty_eo"] * data["rate_eo"]

        normalized_trade = validate_trade_core_payload(
            data,
            require_id_stk=True,
        )
        data.update(normalized_trade)
        validate_order_quantity_progress(data["check_qty"], data["qty_trd"])
        order_payload = validate_exchange_order_payload(
            {
                "exchange_eo": data["exchange"],
                "ord_no": data["ord_no"],
                "ord_dt": data["ord_dt"],
                "trd_no": data["trd_no"],
                "qty_eo": data["qty_eo"],
                "rate_eo": data["rate_eo"],
                "brok_unit_eo": data["brok_unit_eo"],
                "net_rate_eo": data["net_rate_eo"],
                "net_total_eo": data["net_total_eo"],
            },
            order_index=len(data.get("exchange_orders", [])) + 1,
        )

        missing_fields = [
            f for f in required_fields if f not in data or data[f] is None
        ]
        if missing_fields:
            return

        # --- 1. IN-MEMORY SAVING LOGIC FIRST ---
        if "exchange_orders" not in data:
            data["exchange_orders"] = []

        data["exchange_orders"].append(order_payload)

        # --- 2. ALL UI AND LOCAL DATA LOGIC SECOND ---
        if data["check_qty"] < data["qty_trd"]:
            trd_no_var.set(trd_no_var.get() + 1)
            brok_unit_eo_var.set(0.0)
            net_rate_eo_var.set(0.0)
            net_total_eo_var.set(0.0)

            if data["check_qty"] < 1:
                data["check_qty"] = 1

            qty_eo_entry.config(
                from_=1, to=data["qty_trd"] - data["check_qty"]
            )
            qty_eo_entry.update_idletasks()

            # Format the newly reset 0.0 values to 0.0000
            if refresh_financial_formats_fn:
                refresh_financial_formats_fn()

            ord_no_entry.focus_set()
            ord_no_entry.select_range(0, "end")

        else:
            data["average_rate"] = data["total_order_price"] / data["qty_trd"]
            data["levies"] = 0.0

            wap_value = data["average_rate"]
            wap_var.set(round(wap_value, 4))
            wap_entry.update_idletasks()

            # Brok/Share = SUM(qty_eo * brok_unit_eo) / qty_trd
            _eos = data.get("exchange_orders", [])
            _qty_trd = data["qty_trd"]
            _total_brok_amount = sum(
                eo["qty_eo"] * eo["brok_unit_eo"] for eo in _eos
            )
            brs_value = (
                round(_total_brok_amount / _qty_trd, 4) if _qty_trd else 0.0
            )
            brs_var.set(brs_value)
            brs_entry.update_idletasks()

            lp_value = data["total_order_price"]
            lp_var.set(round(lp_value, 4))
            lp_entry.update_idletasks()

            tot_brok_value = round(_total_brok_amount, 4)
            tot_brok_var.set(round(tot_brok_value, 4))
            tot_brok_entry.update_idletasks()
            data["levies"] += tot_brok_value

            trade_date = datetime.strptime(data["trd_dt"], "%Y-%m-%d").date()
            etc_rate = get_etc(trade_date, data["exchange"])
            etc_value = round(lp_value * etc_rate, 4)
            etc_var.set(round(etc_value, 4))
            etc_entry.update_idletasks()
            data["levies"] += etc_value

            sebi_value = lp_value * SEBI
            sebi_var.set(round(sebi_value, 4))
            sebi_entry.update_idletasks()
            data["levies"] += sebi_value

            gst_value = (tot_brok_value + etc_value + sebi_value) * GST
            gst_var.set(round(gst_value, 4))
            gst_entry.update_idletasks()
            data["levies"] += gst_value

            if data["is_etf"]:
                data["lot_cont_etf"] += lp_value
            else:
                data["lot_cont_non_etf"] += lp_value
            lot_cont_value = data["lot_cont_etf"] + data["lot_cont_non_etf"]
            lot_cont_var.set(round(lot_cont_value, 4))
            lot_cont_entry.update_idletasks()

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

            stamp_duty_value = 0.0
            stamp_duty_var.set(round(stamp_duty_value, 4))
            stamp_duty_entry.update_idletasks()
            data["levies"] += stamp_duty_value

            igst_value = 0.0
            igst_var.set(round(igst_value, 4))
            igst_entry.update_idletasks()
            data["levies"] += igst_value

            sell_charge_value = 0.0
            sell_charge_var.set(round(sell_charge_value, 4))
            sell_charge_entry.update_idletasks()
            data["levies"] += sell_charge_value

            if buy_sell_var.get() == "BUY":
                net_trade_value = lp_value + data["levies"]
            else:
                net_trade_value = lp_value - data["levies"]
            net_trade_var.set(round(net_trade_value, 4))
            net_trade_entry.update_idletasks()

            if calculate_applicable_fields_fn:
                calculate_applicable_fields_fn()

            wap_entry.focus_set()
            wap_entry.select_range(0, "end")

            # Disable EO fields now that all are entered
            ord_no_entry.config(state="disabled")
            ord_dt_entry.config(state="disabled")
            trd_no_entry.config(state="disabled")
            qty_eo_entry.config(state="disabled")
            rate_eo_entry.config(state="disabled")
            brok_unit_eo_entry.config(state="disabled")
            net_rate_eo_entry.config(state="disabled")
            net_total_eo_entry.config(state="disabled")
            nse_radio.config(state="disabled")
            bse_radio.config(state="disabled")

    except ValidationError as exc:
        title = (
            "⚠️ Quantity Error"
            if "Ordered quantity" in str(exc)
            else "Validation Error"
        )
        show_validation_error(rat_win, exc, title=title)
        if "Ordered quantity" in str(exc):
            data.get("exchange_orders", []).clear()
            cleanup_and_close()
        return
    except sqlite3.Error as e:
        logger.error("Database error occurred: %s", str(e))
        logger.error("Data at time of error: %s", data)


def add_trade(
    parent: Union[tk.Toplevel, tk.Tk], calling_button: tk.Widget | None = None
) -> None:
    # colors
    ratwinbg = "#f0f8ff"
    headbg = "#1e3a8a"
    titlefg = "#ffd700"
    ratframebg = "#a475eb"
    btnfrbg = "#f8fafc"
    contfrbg = "#e0f2fe"
    compisinbg = "#fef3c7"
    qoqbg = "#dcfce7"
    rbnnbg = "#fce7f3"
    wbtbg = "#ede9fe"
    gssbg = "#f0fdf4"
    appbg = "#fef9c3"
    submitusualbg = "#22c55e"
    submitactivebg = "#16a34a"
    okactivebg = "#1e40af"
    cancelusualbg = "#ef4444"
    cancelactivebg = "#b91c1c"
    hintbg = "#f8fafc"

    modal_id = disable_parent(parent, calling_button=calling_button)

    # Data Initialization
    data = {
        "company_name": "",
        "isin": "",
        "brok_cont": 0.0,
        "etc_cont": 0.0,
        "sebi_cont": 0.0,
        "gst_cont": 0.0,
        "stamp_cont": 0.0,
        "stt_cont": 0.0,
        "igst_cont": 0.0,
        "sell_chrg_cont": 0.0,
        "net_amt_cont": 0.0,
        "check_qty": 0,
        "total_order_price": 0.0,
        "average_rate": 0.0,
        "levies": 0.0,
        "cont_no": "",
        "trd_dt": "",
        "settle_no": 0,
        "settle_dt": "",
        "no_of_trades": 1,
        "trade_type_trd": "BUY",
        "id_stk": None,
        "id_trd": None,
        "qty_trd": 0,
        "exchange": "NSE",
        "ord_no": 0,
        "ord_dt": "",
        "trd_no": 0,
        "qty_eo": 0,
        "rate_eo": 0.0,
        "brok_unit_eo": 0.0,
        "net_rate_eo": 0.0,
        "net_total_eo": 0.0,
        "note_cont": "",
        "note_trd": "",
        "note_eo": "",
        "lot_cont": 0.0,
        "lot_cont_etf": 0.0,
        "lot_cont_non_etf": 0.0,
        "stt_so_far": 0,
        "stt_so_far_app": 0.0,
        "comp_bt_amt": 0.0,
        "is_etf": False,
        "etc_trd_applicable": 0.0,
        "gst_trd_applicable": 0.0,
        "stt_trd_applicable": 0.0,
        "net_amt_trd_applicable": 0.0,
        "difference_trd": 0.0,
    }

    entries = {}
    widget_to_var = {}
    current_trade_no = [1]
    current_session_trades = {}

    # --- Toplevel Creation ---
    rat_win = tk.Toplevel(parent)
    rat_win.title("✨ Data Entry - Trade ✨")
    rat_win.geometry("1150x920")
    rat_win.resizable(False, False)
    rat_win.configure(bg=ratwinbg)
    rat_win.transient(parent)
    rat_win.grab_set()
    rat_win.focus_set()
    try:
        push_window(rat_win, parent)
    except (RuntimeError, tk.TclError) as _exc:
        logger.debug("push_window failed: %s", _exc)

    # --- Tooltip Variable ---
    tooltip_var = tk.StringVar(
        value="💡 Hover over fields to view helpful tips here."
    )

    def on_qty_trd_focus(_event):
        try:
            cont_no = cont_no_var.get().strip()
            company_name = company_name_var.get().strip()

            if not cont_no or not company_name:
                return

            data["cont_no"] = cont_no
            data["trd_dt"] = trd_date_entry.get_date().strftime("%Y-%m-%d")
            data["settle_no"] = settle_no_var.get()
            data["settle_dt"] = settle_date_entry.get_date().strftime(
                "%Y-%m-%d"
            )
            data["no_of_trades"] = no_of_trades_var.get()
            data["company_name"] = company_name
            data["trade_type_trd"] = buy_sell_var.get()

            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id_stk FROM stocks WHERE company_name = ?",
                    (data["company_name"],),
                )
                stock_result = cursor.fetchone()
                if not stock_result:
                    return

                data["id_stk"] = stock_result[0]

            cont_no_entry.config(state="readonly", takefocus=False)
            trd_date_entry.config(state="disabled")
            settle_date_entry.config(state="disabled")
            settle_no_entry.config(state="disabled")
            trades_spin.config(state="disabled")
            company_entry.config(state="disabled")
            buy_radio.config(state="disabled")
            sell_radio.config(state="disabled")

            ord_no_entry.config(state="normal")
            ord_dt_entry.config(state="normal")
            trd_no_entry.config(state="normal")
            qty_eo_entry.config(state="normal")
            rate_eo_entry.config(state="normal")
            brok_unit_eo_entry.config(state="normal")
            net_rate_eo_entry.config(state="normal")
            net_total_eo_entry.config(state="normal")
            nse_radio.config(state="normal")
            bse_radio.config(state="normal")
            submit_btn.config(state="disabled")

        except (sqlite3.Error, tk.TclError) as _exc:
            logger.exception(
                "Unexpected error completing transaction: %s", _exc
            )

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

        def show_menu(event):
            widget.focus_set()
            menu.tk_popup(event.x_root, event.y_root)

        widget.bind("<Button-3>", show_menu)

    def refresh_financial_formats():
        try:
            current_focus = rat_win.focus_get()
        except KeyError:
            current_focus = None

        # 4 decimal fields (Non-Integral)
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
            (rate_eo_entry, rate_eo_var),
            (brok_unit_eo_entry, brok_unit_eo_var),
            (net_rate_eo_entry, net_rate_eo_var),
            (net_total_eo_entry, net_total_eo_var),
        ]:
            # Do not reformat the field currently being typed in to prevent cursor jumping
            if e == current_focus:
                continue
            try:
                val = float(v.get())

                # SAVE STATE AND UNLOCK
                current_state = str(e.cget("state"))
                if current_state != "normal":
                    e.config(state="normal")

                e.delete(0, "end")
                e.insert(0, f"{val:.4f}")

                # RESTORE PREVIOUS STATE
                if current_state != "normal":
                    e.config(state=current_state)
            except (ValueError, tk.TclError):
                pass

        # 2 decimal field
        if comp_bt_entry != current_focus:
            try:
                val = float(comp_bt_var.get())

                current_state = str(comp_bt_entry.cget("state"))
                if current_state != "normal":
                    comp_bt_entry.config(state="normal")

                comp_bt_entry.delete(0, "end")
                comp_bt_entry.insert(0, f"{val:.2f}")

                if current_state != "normal":
                    comp_bt_entry.config(state=current_state)
            except (ValueError, tk.TclError):
                pass

    def calculate_applicable_fields(_event=None):
        try:
            lp_value = lp_var.get()
            if lp_value <= 0:
                return

            etc_app_val = 0.0
            eos = data.get("exchange_orders", [])
            if eos:
                try:
                    t_date = datetime.strptime(
                        data.get("trd_dt", ""), "%Y-%m-%d"
                    ).date()
                except ValueError:
                    t_date = datetime.now().date()
                for eo in eos:
                    qty = eo.get("qty_eo", 0)
                    rate = eo.get("rate_eo", 0.0)
                    ex = eo.get("exchange_eo") or data.get("exchange", "NSE")
                    eo_val = qty * rate
                    etc_app_val += round(eo_val * get_etc(t_date, ex), 4)

            if etc_app_val == 0.0 and lp_value > 0:
                try:
                    t_date = datetime.strptime(
                        data.get("trd_dt", ""), "%Y-%m-%d"
                    ).date()
                except ValueError:
                    t_date = datetime.now().date()
                etc_app_val = round(
                    lp_value * get_etc(t_date, exchange_var.get()), 4
                )

            etc_app_var.set(round(etc_app_val, 4))

            brok_app_val = round(lp_value * BROK, 4)
            sebi_app_val = round(lp_value * SEBI, 4)

            gst_app_val = round(
                (brok_app_val + etc_app_val + sebi_app_val) * GST, 4
            )
            gst_app_var.set(gst_app_val)

            if data.get("lot_cont_non_etf", 0) != 0:
                stt_cont_app_value = int(round(data["lot_cont_non_etf"] * STT))
                stt_cont_app_value = max(stt_cont_app_value, 1)
            else:
                stt_cont_app_value = 0

            if data.get("is_etf", False):
                stt_app_val = 0.0
            else:
                stt_app_val = stt_cont_app_value - data.get(
                    "stt_so_far_app", 0.0
                )

            stt_app_var.set(stt_app_val)

            stamp_val = stamp_duty_var.get()
            igst_val = igst_var.get()
            sell_chrg_val = sell_charge_var.get()

            levies_app = (
                brok_app_val
                + etc_app_val
                + sebi_app_val
                + gst_app_val
                + stt_app_val
                + stamp_val
                + igst_val
                + sell_chrg_val
            )

            if buy_sell_var.get() == "BUY":
                net_app = lp_value + levies_app
            else:
                net_app = lp_value - levies_app

            net_trade_app_var.set(round(net_app, 4))

            diff_val = net_trade_var.get() - net_app
            diff_trd_var.set(round(diff_val, 4))

            for w in [
                etc_app_entry,
                gst_app_entry,
                stt_app_entry,
                net_trade_app_entry,
                diff_trd_entry,
            ]:
                w.update_idletasks()
            refresh_financial_formats()

        except (ValueError, tk.TclError, KeyError):
            pass

    def on_net_trade_change(_event=None):
        try:
            calculate_applicable_fields()

            if buy_sell_var.get() == "BUY":
                comp_bt_value = data["comp_bt_amt"] + net_trade_var.get()
            else:
                comp_bt_value = data["comp_bt_amt"] - net_trade_var.get()
            comp_bt_var.set(round(comp_bt_value, 2))
            comp_bt_entry.update_idletasks()
        except (ValueError, tk.TclError):
            pass

    def update_levies_and_net_trade(_event=None):
        try:
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

            lp_value = lp_var.get()
            if buy_sell_var.get() == "BUY":
                net_trade_value = lp_value + data["levies"]
                comp_bt_value = data["comp_bt_amt"] + net_trade_value
            else:
                net_trade_value = lp_value - data["levies"]
                comp_bt_value = data["comp_bt_amt"] - net_trade_value

            net_trade_var.set(round(net_trade_value, 4))
            net_trade_entry.update_idletasks()
            comp_bt_var.set(round(comp_bt_value, 2))
            comp_bt_entry.update_idletasks()

            calculate_applicable_fields()
        except (ValueError, tk.TclError):
            pass

    def sebi_on_focus_out(_event=None):
        try:
            gst_value = round(
                (tot_brok_var.get() + etc_var.get() + sebi_var.get()) * GST, 4
            )
            gst_var.set(gst_value)
            update_levies_and_net_trade()
        except (tk.TclError, ValueError):
            pass

    def validate_int(P):
        return P.isdigit() or P == ""

    int_vcmd = (rat_win.register(validate_int), "%P")

    def show_help(_event=None):
        rat_win.unbind("<Escape>")
        help_win = tk.Toplevel(rat_win)
        try:
            help_win.transient(rat_win)
        except (tk.TclError, AttributeError) as _exc:
            logger.debug("help_win.transient failed: %s", _exc)
        help_win.title("Help — Trade Entry")
        help_win.configure(bg="#fffaf0")
        help_win.geometry("640x620")
        help_win.resizable(False, False)
        help_win.grab_set()
        push_window(help_win, rat_win)
        try:
            help_win.focus_set()
        except tk.TclError:
            pass

        header = tk.Label(
            help_win,
            text="Trade Entry Help",
            font=("Helvetica", 16, "bold"),
            bg="#ff7f50",
            fg="white",
            pady=8,
        )
        header.pack(fill="x")

        body = tk.Frame(help_win, bg="#fffaf0", padx=12, pady=12)
        body.pack(fill="both", expand=True)

        text = tk.Text(
            body,
            wrap="word",
            bg="#fffaf0",
            bd=0,
            padx=6,
            pady=6,
            font=("Helvetica", 11),
            height=12,
        )
        text.pack(fill="both", expand=True)

        help_lines = [
            "• This is a data entry form for new trade.",
            "• In one contract, there may be more than one trade and in one",
            "  trade, there may be more than one exchange order.",
            "",
            "Please pay attention while entering the data into the following fields:",
            "  - Number of Trades: Trades within one contract.",
            "  - Company (Press first letter to filter or type initial chars)",
            "  - Buy/Sell Buttons: In SELL trade, do select SELL.",
            "  - Qty Trade (After moving from this field many fields will be locked)",
            "  - Rate EO : Please enter positive value.",
            "",
            "The following fields are read only:",
            "  > Current Trade No.",
            "  > ISIN",
            "  > Sell Charge (if trade is a 'BUY' Trade)",
            "  > Applicable Framework (Mathematical checks against broker charges)",
            "",
            "Hotkeys:",
            "  F1: This screen (Help)",
            "  F2: Session Trades",
            "  Escape: Rollback the trade",
            "  Enter/Space: Execute button or Advance field",
        ]

        full_text = "\n".join(help_lines)
        text.insert("1.0", full_text)

        highlights = {
            "Number of Trades": "#d2691e",
            "Company": "#2e8b57",
            "Buy/Sell": "#4682b4",
            "Qty Trade": "#b22222",
            "Rate EO": "#8b008b",
            "Applicable Framework": "#8b0000",
        }
        for word, color in highlights.items():
            start = "1.0"
            while True:
                pos = text.search(word, start, stopindex="end")
                if not pos:
                    break
                end_pos = f"{pos}+{len(word)}c"
                tag_name = f"tag_{word.replace(' ', '_')}"
                text.tag_add(tag_name, pos, end_pos)
                text.tag_config(
                    tag_name, foreground=color, font=("Helvetica", 11, "bold")
                )
                start = end_pos

        text.config(state="disabled")

        def close_help(e=None):
            safe_close_modal(help_win, rat_win)
            rat_win.bind("<Escape>", on_escape)
            return "break"

        help_win.bind("<Escape>", close_help)
        help_win.protocol("WM_DELETE_WINDOW", close_help)

        btn = tk.Button(
            help_win,
            text="Close",
            command=close_help,
            font=("Helvetica", 11, "bold"),
            bg="#4682b4",
            fg="white",
            padx=12,
            pady=6,
            cursor="hand2",
        )
        btn.pack(side="bottom", pady=10)
        try:
            btn.focus_set()
        except tk.TclError:
            pass

    def show_session_trades(_event=None):
        if not current_session_trades:
            try:
                show_colorful_info(
                    rat_win,
                    "No Trades",
                    "No trades have been recorded in this session yet.",
                )
            except (tk.TclError,):
                pass
            return

        rat_win.unbind("<Escape>")

        session_entries = list(current_session_trades.items())
        idx = {"i": 0}

        viewer = tk.Toplevel(rat_win)
        viewer.title("Session Trades Viewer")
        viewer.transient(rat_win)
        viewer.grab_set()
        viewer.resizable(False, False)
        viewer.geometry("520x260")

        push_window(viewer, rat_win)
        try:
            viewer.focus_set()
        except tk.TclError:
            pass

        content = tk.Frame(viewer)
        content.pack(fill="both", expand=True, padx=10, pady=10)

        left_btn = tk.Button(content, text="◀", width=3)
        left_btn.pack(side="left", padx=(10, 5), pady=6)
        right_btn = tk.Button(content, text="▶", width=3)
        right_btn.pack(side="right", padx=(5, 10), pady=6)

        info_text = tk.Text(
            content, wrap="word", height=8, bg="#f8fafc", bd=0, relief="flat"
        )
        info_text.pack(fill="both", expand=True, padx=10, pady=6)

        info_text.tag_configure(
            "label", font=("Helvetica", 11, "bold"), foreground="#0b63a7"
        )
        info_text.tag_configure(
            "value", font=("Helvetica", 11), foreground="#0b3d2e"
        )
        info_text.tag_configure(
            "net", font=("Helvetica", 11, "bold"), foreground="#b91c1c"
        )
        info_text.config(state="disabled")

        status_label = tk.Label(
            content, text="", font=("Helvetica", 10, "bold"), bg="#f8fafc"
        )
        status_label.pack(side="bottom", pady=(0, 6))

        def update_view():
            i = idx["i"]
            sr, t = session_entries[i]
            info_text.config(state="normal")
            info_text.delete("1.0", "end")
            info_text.insert("end", "Sr. No: ", "label")
            info_text.insert("end", f"{sr}\n", "value")
            info_text.insert("end", "Contract: ", "label")
            info_text.insert("end", f"{t.get('Cont')}\n", "value")
            info_text.insert("end", "Trade Dt: ", "label")
            info_text.insert("end", f"{t.get('Trade Dt')}\n", "value")
            info_text.insert("end", "Company: ", "label")
            info_text.insert("end", f"{t.get('Company')}\n", "value")
            info_text.insert("end", "B/S: ", "label")
            info_text.insert("end", f"{t.get('B/S')}\n", "value")
            info_text.insert("end", "Qty: ", "label")
            info_text.insert("end", f"{t.get('Qty')}\n", "value")
            info_text.insert("end", "Average: ", "label")
            info_text.insert("end", f"{t.get('Average'):.4f}\n", "value")
            info_text.insert("end", "Net: ", "label")
            info_text.insert("end", f"{t.get('Net'):.4f}\n", "net")
            info_text.config(state="disabled")

            left_btn.config(state="disabled" if i == 0 else "normal")
            if i >= len(session_entries) - 1:
                right_btn.config(state="disabled")
                status_label.config(
                    text="Last Trade",
                    fg="#b91c1c",
                    font=("Helvetica", 10, "bold"),
                )
            else:
                right_btn.config(state="normal")
                status_label.config(text="", fg="#064e3b")

        def go_prev(_event=None):
            if idx["i"] > 0:
                idx["i"] -= 1
                update_view()

        def go_next(_event=None):
            if idx["i"] < len(session_entries) - 1:
                idx["i"] += 1
                update_view()

        left_btn.config(command=go_prev)
        right_btn.config(command=go_next)
        viewer.bind("<Left>", lambda e: go_prev())
        viewer.bind("<Right>", lambda e: go_next())

        def close_viewer(_event=None):
            safe_close_modal(viewer, rat_win)
            rat_win.bind("<Escape>", on_escape)
            return "break"

        viewer.bind("<Escape>", close_viewer)
        viewer.protocol("WM_DELETE_WINDOW", close_viewer)
        viewer.bind("<Return>", close_viewer)
        ok_btn_viewer = tk.Button(
            content, text="OK", width=10, command=close_viewer
        )
        ok_btn_viewer.pack(side="bottom", pady=(0, 8))
        try:
            ok_btn_viewer.focus_set()
        except tk.TclError:
            pass
        update_view()

    def cleanup_and_close(_event=None):
        return safe_close_modal(rat_win, parent, calling_button)

    def update_sell_charge_state(*_args):
        if buy_sell_var.get().upper() == "BUY":
            sell_charge_entry.config(state="disabled")
        else:
            sell_charge_entry.config(state="normal")

    def update_comp_bt_state():
        try:
            if current_trade_no[0] < no_of_trades_var.get():
                comp_bt_entry.config(state="disabled", takefocus=False)
            else:
                comp_bt_entry.config(state="normal", takefocus=True)
        except (NameError, tk.TclError):
            pass

    def _discard_partial_entries_and_close():
        try:
            cont_no = data.get("cont_no")
            if not cont_no:
                return

            with get_db_connection() as conn:
                cur = conn.cursor()
                # If they escape before ANY trade is saved, clean up the empty contract
                cur.execute(
                    "SELECT COUNT(*) FROM transactions WHERE cont_no = ?",
                    (cont_no,),
                )
                if cur.fetchone()[0] == 0:
                    cur.execute(
                        "DELETE FROM contracts WHERE cont_no = ?", (cont_no,)
                    )

                conn.commit()
        except (sqlite3.Error, ValueError, tk.TclError) as _exc:
            logger.error("Error during partial entry rollback: %s", _exc)
        finally:
            cleanup_and_close()

    def on_escape(_event=None) -> None:
        if _event and hasattr(_event, "widget") and _event.widget:
            try:
                if _event.widget.winfo_toplevel() != rat_win:
                    return
            except tk.TclError:
                pass
        _discard_partial_entries_and_close()

    def on_ok() -> None:
        required_fields = ["cont_no", "company_name"]
        if not validate_required_fields(data, required_fields, parent):
            return

        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()

                # 1. Handle Contract
                cursor.execute(
                    "SELECT COUNT(*) FROM contracts WHERE cont_no = ?",
                    (data["cont_no"],),
                )
                if cursor.fetchone()[0] > 0:
                    cursor.execute(
                        """
                        UPDATE contracts
                        SET trd_dt = ?, settle_no = ?, settle_dt = ?,
                            no_of_trades = ?, note_cont = ?
                        WHERE cont_no = ?
                        """,
                        (
                            data["trd_dt"],
                            data["settle_no"],
                            data["settle_dt"],
                            data["no_of_trades"],
                            note_cont_var.get(),
                            data["cont_no"],
                        ),
                    )
                else:
                    cursor.execute(
                        """
                        INSERT INTO contracts
                        (cont_no, trd_dt, settle_no, settle_dt, no_of_trades, note_cont)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            data["cont_no"],
                            data["trd_dt"],
                            data["settle_no"],
                            data["settle_dt"],
                            data["no_of_trades"],
                            note_cont_var.get(),
                        ),
                    )

                # 2. Insert Transaction
                cursor.execute(
                    """
                    INSERT INTO transactions
                    (cont_no, trd_dt, company_name, trade_type_trd, id_stk,
                     exchange, qty_trd, wap_unit_trd, brok_unit_trd, price_lot_trd,
                     brok_lot_trd, etc_trd, sebi_trd, sell_chrg_trd, gst_trd,
                     stamp_trd, stt_trd, igst_trd, net_amt_trd,
                     etc_trd_applicable, gst_trd_applicable, stt_trd_applicable, net_amt_trd_applicable,
                     note_trd)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        data["cont_no"],
                        data["trd_dt"],
                        data["company_name"],
                        data["trade_type_trd"],
                        data["id_stk"],
                        data.get("exchange", "NSE"),
                        data.get("qty_trd", 0),
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
                    ),
                )
                data["id_trd"] = cursor.lastrowid

                # 3. Insert Exchange Orders
                for eo in data.get("exchange_orders", []):
                    cursor.execute(
                        """
                        INSERT INTO exchange_orders
                        (id_trd, exchange_eo, ord_no, ord_dt, trd_no, qty_eo, rate_eo,
                         brok_unit_eo, net_rate_eo, net_total_eo)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            data["id_trd"],
                            eo["exchange_eo"],
                            eo["ord_no"],
                            eo["ord_dt"],
                            eo["trd_no"],
                            eo["qty_eo"],
                            eo["rate_eo"],
                            eo["brok_unit_eo"],
                            eo["net_rate_eo"],
                            eo["net_total_eo"],
                        ),
                    )

                cursor.execute(
                    """
                    UPDATE contracts
                    SET
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

                if data["trade_type_trd"] == "SELL":
                    enforce_no_oversell_for_stock(cursor, data["id_stk"])

                conn.commit()

                try:
                    sr_no = len(current_session_trades) + 1
                    net_val = float(net_trade_var.get())
                    qty_val = int(data.get("qty_trd") or qty_trd_var.get())
                    avg_val = (net_val / qty_val) if qty_val else 0.0
                    current_session_trades[sr_no] = {
                        "Cont": data.get("cont_no"),
                        "Trade Dt": data.get("trd_dt"),
                        "Company": data.get("company_name"),
                        "B/S": data.get("trade_type_trd"),
                        "Qty": qty_val,
                        "Average": avg_val,
                        "Net": net_val,
                    }
                except (ValueError, KeyError, TypeError) as _exc:
                    logger.debug("Failed to record session trade: %s", _exc)

            compute_avg_price(data["id_stk"], data.get("trade_type_trd"))

        except (sqlite3.Error, ValueError) as e:
            logger.error("Error saving trade: %s", str(e))
            show_colorful_error(
                parent,
                "Database Error",
                f"Failed to save trade: {str(e)}",
            )
            return  # HALT EXECUTION: Prevent the UI from advancing if the DB fails!

        # UI updates and next-trade logic safely proceed only if no error occurred
        if current_trade_no[0] < no_of_trades_var.get():
            current_trade_no[0] += 1
            current_trade_no_var.set(current_trade_no[0])

            data["check_qty"] = 0
            data["total_order_price"] = 0.0
            data["average_rate"] = 0.0
            data["exchange_orders"] = []
            data["levies"] = 0.0
            data["comp_bt_amt"] = comp_bt_var.get()
            data["lot_cont"] += lp_var.get()

            qty_trd_var.set(1)
            ord_no_var.set("0")
            trd_no_var.set(0)
            qty_eo_var.set(1)
            rate_eo_var.set(0.0)
            brok_unit_eo_var.set(0.0)
            net_rate_eo_var.set(0.0)
            net_total_eo_var.set(0.0)

            wap_var.set(0.0)
            brs_var.set(0.0)
            lp_var.set(0.0)
            tot_brok_var.set(0.0)
            etc_var.set(0.0)
            sebi_var.set(0.0)
            gst_var.set(0.0)
            stamp_duty_var.set(0.0)
            note_trd_var.set("")
            igst_var.set(0.0)
            sell_charge_var.set(0.0)
            net_trade_var.set(0.0)

            data["stt_so_far"] += stt_var.get()
            data["stt_so_far_app"] += stt_app_var.get()
            stt_var.set(0)

            etc_app_var.set(0.0)
            gst_app_var.set(0.0)
            stt_app_var.set(0.0)
            net_trade_app_var.set(0.0)
            diff_trd_var.set(0.0)

            # Format the newly reset values to 0.0000 before the user types
            refresh_financial_formats()

            company_entry.config(state="normal")
            buy_radio.config(state="normal")
            sell_radio.config(state="normal")
            qty_trd_entry.config(state="normal")

            submit_btn.config(state="disabled")
            nse_radio.config(state="disabled")
            bse_radio.config(state="disabled")
            ord_no_entry.config(state="disabled")
            ord_dt_entry.config(state="disabled")
            trd_no_entry.config(state="disabled")
            qty_eo_entry.config(state="disabled")
            rate_eo_entry.config(state="disabled")
            brok_unit_eo_entry.config(state="disabled")
            net_rate_eo_entry.config(state="disabled")
            net_total_eo_entry.config(state="disabled")

            company_name_var.set("")
            isin_var.set("")
            buy_sell_var.set("BUY")
            update_comp_bt_state()
            company_entry.focus_set()

            show_colorful_info(
                rat_win,
                "✅ Trade Complete",
                f"Trade {current_trade_no[0] - 1} completed successfully.\nPlease enter details for Trade {current_trade_no[0]}.",
            )
        else:
            with get_db_connection() as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT SUM(CASE
                        WHEN trade_type_trd = 'BUY' THEN net_amt_trd_applicable
                        WHEN trade_type_trd = 'SELL' THEN -net_amt_trd_applicable
                        ELSE 0 END)
                    FROM transactions WHERE cont_no = ?
                    """,
                    (data["cont_no"],),
                )
                comp_bt_app_row = cursor.fetchone()
                comp_bt_app_value = (
                    comp_bt_app_row[0]
                    if comp_bt_app_row and comp_bt_app_row[0]
                    else 0.0
                )

                comp_bt_value = comp_bt_var.get()
                if comp_bt_value != 0:
                    if comp_bt_value > 0:
                        cursor.execute(
                            """
                            INSERT INTO computed_bank
                            (cont_no, comp_bt_dt, comp_bt_type, comp_bt_amt, comp_bt_amt_applicable, comp_bt_desc)
                            VALUES (?, ?, ?, ?, ?, ?)
                            """,
                            (
                                data["cont_no"],
                                data["settle_dt"],
                                "DEBIT",
                                round(comp_bt_value, 2),
                                round(comp_bt_app_value, 2),
                                "Buying",
                            ),
                        )
                    else:
                        cursor.execute(
                            """
                            INSERT INTO computed_bank
                            (cont_no, comp_bt_dt, comp_bt_type, comp_bt_amt, comp_bt_amt_applicable, comp_bt_desc)
                            VALUES (?, ?, ?, ?, ?, ?)
                            """,
                            (
                                data["cont_no"],
                                data["settle_dt"],
                                "CREDIT",
                                round(-comp_bt_value, 2),
                                round(abs(comp_bt_app_value), 2),
                                "Selling",
                            ),
                        )
                conn.commit()

            trade_word = (
                "trade has" if no_of_trades_var.get() == 1 else "trades have"
            )
            show_colorful_info(
                rat_win,
                "🎉 Contract Complete",
                f"{no_of_trades_var.get()} {trade_word} been completed successfully.\nContract No: {data['cont_no']} has been completed successfully.",
            )
            response = show_colorful_yesno(
                rat_win,
                "🔄 Add Another Trade?",
                "Do you want to add another trade?",
            )
            if response:
                reset_form_for_new_contract()
            else:
                cleanup_and_close()

    def reset_form_for_new_contract():
        current_trade_no[0] = 1
        current_trade_no_var.set(current_trade_no[0])
        data.clear()

        new_trade_date = datetime.now().date()
        if current_session_trades:
            try:
                last_trade_sr = max(current_session_trades.keys())
                last_trade_date_str = current_session_trades[
                    last_trade_sr
                ].get("Trade Dt")
                if last_trade_date_str:
                    last_trade_date = datetime.strptime(
                        last_trade_date_str, "%Y-%m-%d"
                    ).date()
                    new_trade_date = next_working_day(last_trade_date)
            except (ValueError, TypeError, KeyError):
                new_trade_date = datetime.now().date()

        new_settle_date = next_working_day(new_trade_date)
        new_trade_date_db_str = new_trade_date.strftime("%Y-%m-%d")
        new_settle_date_db_str = new_settle_date.strftime("%Y-%m-%d")
        new_trade_date_display_str = new_trade_date.strftime("%d-%m-%Y")
        new_settle_date_display_str = new_settle_date.strftime("%d-%m-%Y")

        data.update(
            {
                "company_name": "",
                "isin": "",
                "brok_cont": 0.0,
                "etc_cont": 0.0,
                "sebi_cont": 0.0,
                "gst_cont": 0.0,
                "stamp_cont": 0.0,
                "stt_cont": 0,
                "igst_cont": 0.0,
                "sell_chrg_cont": 0.0,
                "net_amt_cont": 0.0,
                "check_qty": 0,
                "total_order_price": 0.0,
                "average_rate": 0.0,
                "levies": 0.0,
                "trd_dt": new_trade_date_db_str,
                "settle_dt": new_settle_date_db_str,
                "note_trd": "",
                "lot_cont": 0.0,
                "lot_cont_etf": 0.0,
                "lot_cont_non_etf": 0.0,
                "stt_so_far": 0,
                "stt_so_far_app": 0.0,
                "comp_bt_amt": 0.0,
                "etc_trd_applicable": 0.0,
                "gst_trd_applicable": 0.0,
                "stt_trd_applicable": 0.0,
                "net_amt_trd_applicable": 0.0,
                "difference_trd": 0.0,
            }
        )

        cont_no_var.set("")
        trd_dt_var.set(new_trade_date_display_str)
        settle_no_var.set(0)
        settle_dt_var.set(new_settle_date_display_str)
        no_of_trades_var.set(1)

        company_name_var.set("")
        isin_var.set("")
        buy_sell_var.set("BUY")

        qty_trd_var.set(1)
        ord_no_var.set("0")
        trd_no_var.set(0)
        qty_eo_var.set(1)
        rate_eo_var.set(0.0)
        brok_unit_eo_var.set(0.0)
        net_rate_eo_var.set(0.0)
        net_total_eo_var.set(0.0)
        exchange_var.set("NSE")
        comp_bt_var.set(0.0)

        wap_var.set(0.0)
        brs_var.set(0.0)
        lp_var.set(0.0)
        tot_brok_var.set(0.0)
        etc_var.set(0.0)
        sebi_var.set(0.0)
        gst_var.set(0.0)
        stt_var.set(0)
        stamp_duty_var.set(0.0)
        note_trd_var.set("")
        igst_var.set(0.0)
        sell_charge_var.set(0.0)
        net_trade_var.set(0.0)
        lot_cont_var.set(0.0)
        stt_cont_var.set(0)
        comp_bt_var.set(0.0)
        is_etf_var.set(False)

        etc_app_var.set(0.0)
        gst_app_var.set(0.0)
        stt_app_var.set(0.0)
        net_trade_app_var.set(0.0)
        diff_trd_var.set(0.0)

        refresh_financial_formats()

        cont_no_entry.config(state="normal")
        trd_date_entry.config(state="normal")
        settle_no_entry.config(state="normal")
        settle_date_entry.config(state="normal")
        trades_spin.config(state="normal")
        qty_trd_entry.config(state="normal")

        company_entry.config(state="normal")
        buy_radio.config(state="normal")
        sell_radio.config(state="normal")

        submit_btn.config(state="disabled")
        nse_radio.config(state="disabled")
        bse_radio.config(state="disabled")
        ord_no_entry.config(state="disabled")
        ord_dt_entry.config(state="disabled")
        trd_no_entry.config(state="disabled")
        qty_eo_entry.config(state="disabled")
        rate_eo_entry.config(state="disabled")
        brok_unit_eo_entry.config(state="disabled")
        net_rate_eo_entry.config(state="disabled")
        net_total_eo_entry.config(state="disabled")

        cont_no_entry.focus_set()
        cont_no_entry.select_range(0, "end")

    def format_wap_on_focus_out(_event=None):
        try:
            current_value = wap_var.get()
            formatted_value = round(current_value, 4)
            wap_var.set(formatted_value)
            wap_entry.delete(0, "end")
            wap_entry.insert(0, f"{formatted_value:.4f}")
        except (ValueError, tk.TclError):
            pass

    def validate_positive_financial_input_and_format(_event=None):
        """Validates input and triggers a 5-cycle blinking animation if invalid."""
        if _event is not None and hasattr(_event, "widget"):
            widget = _event.widget
            try:
                val = float(widget.get())
                if val < 0:
                    raise ValueError("Negative value")
                widget.config(bg="black")  # Changed from "white" to "black"
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

                # 5 flashes of red and black (changed "white" to "black")
                blink_colors = ["#ffcccc", "black"] * 5
                blink(widget, blink_colors)
                return

        try:
            if _event is not None and hasattr(_event, "widget"):
                widget = _event.widget
                field_var = widget_to_var.get(widget)
                if field_var is None:
                    return
                current_value = float(widget.get() or 0)
                formatted_value = (
                    0.0000 if current_value == 0 else round(current_value, 4)
                )
                field_var.set(formatted_value)
                widget.delete(0, "end")
                widget.insert(0, f"{formatted_value:.4f}")
        except (ValueError, tk.TclError, AttributeError):
            pass

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

    # Create the full window.
    header_frame = tk.Frame(rat_win, bg=headbg, relief="raised", bd=3)
    header_frame.pack(fill="x", padx=5, pady=0)

    title_label = tk.Label(
        header_frame,
        text="💼 DATA ENTRY SYSTEM 💼",
        font=("Comic Sans MS", 18, "bold"),
        bg=headbg,
        fg=titlefg,
        pady=8,
        relief="ridge",
        bd=2,
    )
    title_label.pack(fill="x")

    rat_frame = tk.Frame(
        rat_win, bg=ratframebg, padx=15, pady=0, relief="raised", bd=2
    )
    rat_frame.pack(fill="both", expand=True, padx=10, pady=5)

    btn_frame = tk.Frame(rat_win, pady=10, bg=btnfrbg, relief="ridge", bd=2)
    btn_frame.pack(fill="x", anchor="e", padx=10)

    cont_frame = tk.Frame(
        rat_frame, bg=contfrbg, relief="ridge", bd=2, padx=10, pady=8
    )
    cont_frame.grid(
        row=0, column=0, rowspan=2, columnspan=5, sticky="ew", pady=10
    )

    cont_label_frame = tk.Frame(cont_frame, bg=contfrbg)
    cont_label_frame.pack(fill="x", pady=(0, 5))
    cont_entry_frame = tk.Frame(cont_frame, bg=contfrbg)
    cont_entry_frame.pack(fill="x", pady=(0, 5))
    cont_note_frame = tk.Frame(cont_frame, bg=contfrbg)
    cont_note_frame.pack(fill="x", pady=(0, 5))

    company_isin_frame = tk.Frame(
        rat_frame, bg=compisinbg, relief="groove", bd=2, padx=8, pady=6
    )
    company_isin_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=5)

    qoq_frame = tk.Frame(
        rat_frame, bg=qoqbg, relief="ridge", bd=2, padx=8, pady=6
    )
    qoq_frame.grid(
        row=5, column=0, rowspan=2, columnspan=3, sticky="ew", pady=5
    )
    qoq_label_frame = tk.Frame(qoq_frame, bg=qoqbg)
    qoq_label_frame.pack(fill="x", pady=(0, 2))
    qoq_entry_frame = tk.Frame(qoq_frame, bg=qoqbg)
    qoq_entry_frame.pack(fill="x", pady=(0, 2))

    rbnn_frame = tk.Frame(
        rat_frame, bg=rbnnbg, relief="ridge", bd=2, padx=8, pady=6
    )
    rbnn_frame.grid(
        row=7, column=0, rowspan=2, columnspan=4, sticky="ew", pady=5
    )
    rbnn_label_frame = tk.Frame(rbnn_frame, bg=rbnnbg)
    rbnn_label_frame.pack(fill="x", pady=(0, 2))
    rbnn_entry_frame = tk.Frame(rbnn_frame, bg=rbnnbg)
    rbnn_entry_frame.pack(fill="x", pady=(0, 2))

    wbt_frame = tk.Frame(
        rat_frame, bg=wbtbg, relief="groove", bd=2, padx=8, pady=6
    )
    wbt_frame.grid(
        row=9, column=0, rowspan=2, columnspan=4, sticky="ew", pady=5
    )
    wbt_label_frame = tk.Frame(wbt_frame, bg=wbtbg)
    wbt_label_frame.pack(fill="x", pady=(0, 2))
    wbt_entry_frame = tk.Frame(wbt_frame, bg=wbtbg)
    wbt_entry_frame.pack(fill="x", pady=(0, 2))

    gss_frame = tk.Frame(
        rat_frame, bg=gssbg, relief="ridge", bd=2, padx=8, pady=6
    )
    gss_frame.grid(
        row=11, column=0, rowspan=2, columnspan=4, sticky="ew", pady=5
    )
    gss_label_frame = tk.Frame(gss_frame, bg=gssbg)
    gss_label_frame.pack(fill="x", pady=(0, 2))
    gss_entry_frame = tk.Frame(gss_frame, bg=gssbg)
    gss_entry_frame.pack(fill="x", pady=(0, 2))
    trd_note_frame = tk.Frame(gss_frame, bg=gssbg)
    trd_note_frame.pack(fill="x", pady=(0, 2))

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

    # --- Contract No field ---
    tk.Label(
        cont_label_frame, bg=contfrbg, text="Cont No", font=("Helvetica", 14)
    ).pack(side="left", padx=(10, 0))
    cont_no_var = tk.StringVar()
    cont_no_entry = tk.Entry(
        cont_entry_frame,
        textvariable=cont_no_var,
        width=25,
        font=("Helvetica", 14, "bold"),
    )
    cont_no_entry.pack(side="left", padx=(10, 0))
    widget_to_var[cont_no_entry] = cont_no_var
    cont_no_entry.focus_set()
    entries["cont_no"] = cont_no_entry

    # --- Trade Date field ---
    tk.Label(
        cont_label_frame, bg=contfrbg, text="Trade Dt", font=("Helvetica", 14)
    ).pack(side="left", padx=(215, 0))
    trd_dt_var = tk.StringVar()
    trd_date_entry = DateEntry(
        cont_entry_frame,
        textvariable=trd_dt_var,
        date_pattern="dd-mm-yyyy",
        width=10,
        font=("Helvetica", 14),
    )
    trd_date_entry.pack(side="left", padx=15)
    bind_date_spin(trd_date_entry)
    entries["trd_dt"] = trd_date_entry
    widget_to_var[trd_date_entry] = trd_dt_var

    # --- Settlement No field ---
    tk.Label(
        cont_label_frame, bg=contfrbg, text="Settle No", font=("Helvetica", 14)
    ).pack(side="left", padx=(80, 0))
    settle_no_var = tk.IntVar()
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
    widget_to_var[settle_no_entry] = settle_no_var
    entries["settle_no"] = settle_no_entry

    # --- Settlement Date field ---
    tk.Label(
        cont_label_frame, bg=contfrbg, text="Settle Dt", font=("Helvetica", 14)
    ).pack(side="left", padx=(50, 0))
    settle_dt_var = tk.StringVar()
    settle_date_entry = DateEntry(
        cont_entry_frame,
        textvariable=settle_dt_var,
        date_pattern="dd-mm-yyyy",
        width=10,
        font=("Helvetica", 14),
    )
    settle_date_entry.pack(side="left", padx=15)
    bind_date_spin(settle_date_entry)
    widget_to_var[settle_date_entry] = settle_dt_var
    entries["settle_dt"] = settle_date_entry

    # --- No of Trades field ---
    tk.Label(
        cont_label_frame,
        bg=contfrbg,
        text="No of Trades",
        font=("Helvetica", 14),
    ).pack(side="left", padx=(80, 0))
    no_of_trades_var = tk.IntVar()
    trades_spin = tk.Spinbox(
        cont_entry_frame,
        from_=1,
        to=10,
        width=6,
        textvariable=no_of_trades_var,
        validate="key",
        validatecommand=int_vcmd,
        font=("Helvetica", 14),
    )
    trades_spin.pack(side="left", padx=15)
    widget_to_var[trades_spin] = trades_spin
    entries["no_of_trades"] = trades_spin

    # --- Current Trade No field ---
    tk.Label(
        cont_label_frame,
        bg=contfrbg,
        text="Current Trade No",
        font=("Helvetica", 14),
    ).pack(side="left", padx=(15, 0))
    current_trade_no_var = tk.IntVar(value=current_trade_no[0])
    current_trade_no_entry = tk.Entry(
        cont_entry_frame,
        textvariable=current_trade_no_var,
        width=6,
        font=("Helvetica", 14),
        state="readonly",
        takefocus=False,
    )
    current_trade_no_entry.pack(side="left", padx=40)
    widget_to_var[current_trade_no_entry] = current_trade_no_var
    entries["current_trade_no"] = current_trade_no_entry

    # --- Contract Note field ---
    tk.Label(
        cont_note_frame,
        bg=contfrbg,
        text="Contract Note",
        font=("Helvetica", 14),
    ).pack(side="left", padx=(10, 0), pady=(10, 0))
    note_cont_var = tk.StringVar()
    note_cont_entry = tk.Entry(
        cont_note_frame,
        textvariable=note_cont_var,
        width=75,
        font=("Helvetica", 14),
    )
    note_cont_entry.pack(side="left", padx=(10, 0), pady=(10, 0))
    widget_to_var[note_cont_entry] = note_cont_var
    entries["note_cont"] = note_cont_entry

    # --- Company and ISIN fields ---
    tk.Label(
        company_isin_frame,
        bg="#fef3c7",
        text="Company",
        font=("Helvetica", 14),
    ).pack(side="left", padx=(5, 0))

    company_name_var = tk.StringVar()
    is_etf_var = tk.BooleanVar()
    isin_var = tk.StringVar()
    companies = []
    company_to_isin = {}
    company_to_etf = {}

    company_entry = ttk.Combobox(
        company_isin_frame,
        values=companies,
        textvariable=company_name_var,
        width=38,
        font=("Helvetica", 14),
    )

    def _refresh_company_data():
        nonlocal companies, company_to_isin, company_to_etf
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT company_name, isin, is_etf FROM stocks ORDER BY company_name ASC"
            )
            rows = cursor.fetchall()
            companies = [row[0] for row in rows]
            company_to_isin = {row[0]: (row[1] or "") for row in rows}
            company_to_etf = {row[0]: row[2] for row in rows}
            cursor.close()
        company_entry["values"] = companies
        progressive_selection(company_entry, companies)

    _refresh_company_data()
    company_entry.pack(side="left", padx=15)
    progressive_selection(company_entry, companies)

    def _maybe_fill_isin(*_args):
        try:
            name = company_name_var.get().strip()
            if not name:
                isin_var.set("")
                return

            isin_val = company_to_isin.get(name)
            etf_val = company_to_etf.get(name)

            if etf_val is not None:
                is_etf_var.set(etf_val)
                data["is_etf"] = bool(etf_val)
            else:
                is_etf_var.set(False)
                data["is_etf"] = False

            if isin_val is not None:
                isin_var.set(isin_val)
            else:
                isin_var.set("")
        except (AttributeError, KeyError, tk.TclError) as _exc:
            pass

    company_entry.bind(
        "<<ComboboxSelected>>", lambda e: _maybe_fill_isin(), add="+"
    )
    company_entry.bind("<FocusOut>", lambda e: _maybe_fill_isin(), add="+")

    def on_company_focus_out(_event=None):
        try:
            if not rat_win.winfo_exists():
                return
        except (tk.TclError, NameError):
            return
        name = company_name_var.get().strip()
        if not name:
            return
        if not isin_var.get().strip():
            response = show_colorful_yesno(
                rat_win,
                "Company Not Found",
                f"The company '{name}' was not found. Would you like to add it now?",
            )
            if response:
                add_company(rat_win)
                export_company(rat_win)
                _refresh_company_data()
                company_entry.focus_set()
            else:
                show_colorful_error(
                    rat_win,
                    "Invalid Company",
                    "You cannot change company here. Please select a company from the Company menu.",
                )
                company_entry.focus_set()
                company_entry.select_range(0, "end")

    company_entry.bind("<FocusOut>", on_company_focus_out, add="+")
    try:
        company_name_var.trace_add("write", lambda *a: _maybe_fill_isin())
    except AttributeError:
        pass
    widget_to_var[company_entry] = company_name_var
    entries["company"] = company_entry

    tk.Label(
        company_isin_frame, bg="#fef3c7", text="ISIN", font=("Helvetica", 14)
    ).pack(side="left", padx=(3, 0))
    isin_entry = tk.Entry(
        company_isin_frame,
        textvariable=isin_var,
        width=14,
        font=("Helvetica", 14),
        state="readonly",
        takefocus=False,
    )
    isin_entry.pack(side="left", padx=15)
    widget_to_var[isin_entry] = isin_var
    entries["isin"] = isin_entry

    # --- Buy/Sell radio buttons ---
    tk.Label(
        company_isin_frame,
        bg=compisinbg,
        text="BUY/SELL",
        font=("Helvetica", 14),
    ).pack(side="left", padx=(10, 0), pady=2)
    buy_sell_var = tk.StringVar(value="BUY")
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
    widget_to_var[buy_radio] = buy_sell_var
    widget_to_var[sell_radio] = buy_sell_var
    entries["trade_type_trd"] = buy_sell_var

    # --- Quantity Trade field ---
    tk.Label(
        qoq_label_frame, bg=qoqbg, text="Qty Trade", font=("Helvetica", 14)
    ).pack(side="left", padx=(0, 0), pady=4)
    qty_trd_var = tk.IntVar()
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
    widget_to_var[qty_trd_entry] = qty_trd_var
    entries["qty_trd"] = qty_trd_entry

    # --- Order No field ---
    tk.Label(
        qoq_label_frame, bg=qoqbg, text="Order No", font=("Helvetica", 14)
    ).pack(side="left", padx=(7, 0))
    ord_no_var = tk.StringVar()
    ord_no_entry = tk.Entry(
        qoq_entry_frame,
        textvariable=ord_no_var,
        validate="key",
        validatecommand=int_vcmd,
        width=21,
        font=("Helvetica", 14),
        state="disabled",
    )
    ord_no_entry.pack(side="left", padx=(30, 0))
    widget_to_var[ord_no_entry] = ord_no_var
    entries["ord_no"] = ord_no_entry

    # --- Order Date field ---
    tk.Label(
        qoq_label_frame, text="Order Date", font=("Helvetica", 14), bg=qoqbg
    ).pack(side="left", padx=(180, 0))
    ord_dt_var = tk.StringVar()
    ord_dt_entry = DateEntry(
        qoq_entry_frame,
        textvariable=ord_dt_var,
        date_pattern="dd-mm-yyyy",
        width=10,
        font=("Helvetica", 14),
        state="disabled",
    )
    ord_dt_entry.pack(side="left", padx=(30, 0))
    bind_date_spin(ord_dt_entry)
    widget_to_var[ord_dt_entry] = ord_dt_var
    entries["ord_dt"] = ord_dt_entry

    # --- Trade No field ---
    tk.Label(
        qoq_label_frame, bg=qoqbg, text="Trade No", font=("Helvetica", 14)
    ).pack(side="left", padx=(60, 0))
    trd_no_var = tk.IntVar()
    trd_no_entry = tk.Entry(
        qoq_entry_frame,
        textvariable=trd_no_var,
        validate="key",
        validatecommand=int_vcmd,
        width=21,
        font=("Helvetica", 14),
        state="disabled",
    )
    trd_no_entry.pack(side="left", padx=(30, 0))
    widget_to_var[trd_no_entry] = trd_no_var
    entries["trd_no"] = trd_no_entry

    # --- Qty EO field ---
    tk.Label(
        qoq_label_frame, bg=qoqbg, text="Qty EO", font=("Helvetica", 14)
    ).pack(side="left", padx=(185, 0))
    qty_eo_var = tk.IntVar()
    qty_eo_entry = tk.Spinbox(
        qoq_entry_frame,
        from_=1,
        to=100000,
        width=6,
        textvariable=qty_eo_var,
        validate="key",
        validatecommand=int_vcmd,
        font=("Helvetica", 14),
        state="disabled",
    )
    qty_eo_entry.pack(side="left", padx=(30, 0))
    widget_to_var[qty_eo_entry] = qty_eo_var
    entries["qty_eo"] = qty_eo_entry

    # --- Rate EO field ---
    tk.Label(
        rbnn_label_frame, bg=rbnnbg, text="Rate EO", font=("Helvetica", 14)
    ).pack(side="left", padx=(0, 0))
    rate_eo_var = tk.DoubleVar()
    rate_eo_entry = tk.Entry(
        rbnn_entry_frame,
        textvariable=rate_eo_var,
        width=11,
        font=("Helvetica", 14),
        state="disabled",
    )
    widget_to_var[rate_eo_entry] = rate_eo_var
    rate_eo_entry.pack(side="left", padx=(0, 5))
    entries["rate_eo"] = rate_eo_entry

    # --- Brok Unit EO field ---
    tk.Label(
        rbnn_label_frame,
        bg=rbnnbg,
        text="Brok Unit EO",
        font=("Helvetica", 14),
    ).pack(side="left", padx=(70, 0))
    brok_unit_eo_var = tk.DoubleVar()
    brok_unit_eo_entry = tk.Entry(
        rbnn_entry_frame,
        textvariable=brok_unit_eo_var,
        width=11,
        font=("Helvetica", 14),
        state="disabled",
    )
    brok_unit_eo_entry.pack(side="left", padx=15)
    widget_to_var[brok_unit_eo_entry] = brok_unit_eo_var
    entries["brok_unit_eo"] = brok_unit_eo_entry

    # --- Net Rate EO field ---
    tk.Label(
        rbnn_label_frame, bg=rbnnbg, text="Net Rate EO", font=("Helvetica", 14)
    ).pack(side="left", padx=(35, 0))
    net_rate_eo_var = tk.DoubleVar()
    net_rate_eo_entry = tk.Entry(
        rbnn_entry_frame,
        textvariable=net_rate_eo_var,
        width=11,
        font=("Helvetica", 14),
        state="disabled",
    )
    net_rate_eo_entry.pack(side="left", padx=15)
    widget_to_var[net_rate_eo_entry] = net_rate_eo_var
    entries["net_rate_eo"] = net_rate_eo_entry

    # --- Net Total EO field ---
    tk.Label(
        rbnn_label_frame,
        bg=rbnnbg,
        text="Net Total EO",
        font=("Helvetica", 14),
    ).pack(side="left", padx=(40, 0))
    net_total_eo_var = tk.DoubleVar()
    net_total_eo_entry = tk.Entry(
        rbnn_entry_frame,
        textvariable=net_total_eo_var,
        width=11,
        font=("Helvetica", 14),
        state="disabled",
    )
    net_total_eo_entry.pack(side="left", padx=15)
    widget_to_var[net_total_eo_entry] = net_total_eo_var
    entries["net_total_eo"] = net_total_eo_entry

    # --- Exchange radio buttons field ---
    tk.Label(
        rbnn_label_frame, bg=rbnnbg, text="Exchange", font=("Helvetica", 14)
    ).pack(side="left", padx=(70, 0), pady=2)
    exchange_var = tk.StringVar(value="NSE")
    nse_radio = tk.Radiobutton(
        rbnn_entry_frame,
        bg=rbnnbg,
        text="NSE",
        variable=exchange_var,
        value="NSE",
        font=("Helvetica", 14),
        state="disabled",
    )
    nse_radio.pack(side="left", padx=10)
    bse_radio = tk.Radiobutton(
        rbnn_entry_frame,
        bg=rbnnbg,
        text="BSE",
        variable=exchange_var,
        value="BSE",
        font=("Helvetica", 14),
        state="disabled",
    )
    bse_radio.pack(side="left")
    widget_to_var[nse_radio] = exchange_var
    widget_to_var[bse_radio] = exchange_var
    entries["exchange"] = exchange_var

    # --- Submit button field ---
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
        command=lambda: None,
        state="disabled",
    )
    submit_btn.pack(side="left", padx=30)

    # --- Weighted Average Price field ---
    tk.Label(
        wbt_label_frame, bg=wbtbg, text="Wgt.Av.Price.", font=("Helvetica", 14)
    ).pack(side="left", padx=(0, 0), pady=2)
    wap_var = tk.DoubleVar()
    wap_entry = tk.Entry(
        wbt_entry_frame, textvariable=wap_var, width=11, font=("Helvetica", 14)
    )
    wap_entry.pack(side="left", padx=0)
    widget_to_var[wap_entry] = wap_var
    entries["wap_unit_trd"] = wap_entry

    # --- Brokerage per Share field ---
    tk.Label(
        wbt_label_frame, bg=wbtbg, text="Brok/Share", font=("Helvetica", 14)
    ).pack(side="left", padx=(25, 0), pady=2)
    brs_var = tk.DoubleVar()
    brs_entry = tk.Entry(
        wbt_entry_frame, textvariable=brs_var, width=11, font=("Helvetica", 14)
    )
    brs_entry.pack(side="left", padx=15)
    widget_to_var[brs_entry] = brs_var
    entries["brok_unit_trd"] = brs_entry

    # --- Lot Price field ---
    tk.Label(
        wbt_label_frame, bg=wbtbg, text="Lot Price", font=("Helvetica", 14)
    ).pack(side="left", padx=(50, 0), pady=2)
    lp_var = tk.DoubleVar()
    lp_entry = tk.Entry(
        wbt_entry_frame, textvariable=lp_var, width=11, font=("Helvetica", 14)
    )
    lp_entry.pack(side="left", padx=15)
    widget_to_var[lp_entry] = lp_var
    entries["price_lot_trd"] = lp_entry

    # --- Lot Brok field ---
    tk.Label(
        wbt_label_frame, bg=wbtbg, text="Lot Brok", font=("Helvetica", 14)
    ).pack(side="left", padx=(70, 0), pady=2)
    tot_brok_var = tk.DoubleVar()
    tot_brok_entry = tk.Entry(
        wbt_entry_frame,
        textvariable=tot_brok_var,
        width=11,
        font=("Helvetica", 14),
    )
    tot_brok_entry.pack(side="left", padx=15)
    widget_to_var[tot_brok_entry] = tot_brok_var
    entries["brok_lot_trd"] = tot_brok_entry

    # --- Exchange Charge field ---
    tk.Label(
        wbt_label_frame, bg=wbtbg, text="ETC", font=("Helvetica", 14)
    ).pack(side="left", padx=(75, 0), pady=2)
    etc_var = tk.DoubleVar()
    etc_entry = tk.Entry(
        wbt_entry_frame, textvariable=etc_var, width=11, font=("Helvetica", 14)
    )
    etc_entry.pack(side="left", padx=15)
    widget_to_var[etc_entry] = etc_var
    entries["etc"] = etc_entry

    # --- SEBI Charge field ---
    tk.Label(
        wbt_label_frame, bg=wbtbg, text="SEBI Charge", font=("Helvetica", 14)
    ).pack(side="left", padx=(110, 0), pady=2)
    sebi_var = tk.DoubleVar()
    sebi_entry = tk.Entry(
        wbt_entry_frame,
        textvariable=sebi_var,
        width=11,
        font=("Helvetica", 14),
    )
    sebi_entry.pack(side="left", padx=15)
    widget_to_var[sebi_entry] = sebi_var
    entries["sebi"] = sebi_entry

    # --- Sell Charge field ---
    tk.Label(
        wbt_label_frame, bg=wbtbg, text="Sell Charge", font=("Helvetica", 14)
    ).pack(side="left", padx=(40, 0), pady=2)
    sell_charge_var = tk.DoubleVar()
    sell_charge_entry = tk.Entry(
        wbt_entry_frame,
        textvariable=sell_charge_var,
        width=11,
        font=("Helvetica", 14),
        state="readonly" if buy_sell_var.get().upper() == "BUY" else "normal",
    )
    sell_charge_entry.pack(side="left", padx=15)
    widget_to_var[sell_charge_entry] = sell_charge_var
    entries["sell_charge"] = sell_charge_entry
    buy_sell_var.trace_add("write", lambda *a: update_sell_charge_state())
    update_sell_charge_state()

    # --- GST field ---
    tk.Label(
        gss_label_frame, bg=gssbg, text="GST", font=("Helvetica", 14)
    ).pack(side="left", padx=(0, 0), pady=2)
    gst_var = tk.DoubleVar()
    gst_entry = tk.Entry(
        gss_entry_frame, textvariable=gst_var, width=11, font=("Helvetica", 14)
    )
    gst_entry.pack(side="left", padx=(0, 5))
    widget_to_var[gst_entry] = gst_var
    entries["gst"] = gst_entry

    # --- Stamp Duty field ---
    tk.Label(
        gss_label_frame, bg=gssbg, text="Stamp Duty", font=("Helvetica", 14)
    ).pack(side="left", padx=(100, 0), pady=2)
    stamp_duty_var = tk.DoubleVar()
    stamp_duty_entry = tk.Entry(
        gss_entry_frame,
        textvariable=stamp_duty_var,
        width=11,
        font=("Helvetica", 14),
    )
    stamp_duty_entry.pack(side="left", padx=15)
    widget_to_var[stamp_duty_entry] = stamp_duty_var
    entries["stamp_duty"] = stamp_duty_entry

    # --- STT field ---
    tk.Label(
        gss_label_frame, bg=gssbg, text="STT", font=("Helvetica", 14)
    ).pack(side="left", padx=(50, 0), pady=2)
    stt_var = tk.IntVar()
    stt_entry = tk.Entry(
        gss_entry_frame, textvariable=stt_var, width=11, font=("Helvetica", 14)
    )
    stt_entry.pack(side="left", padx=15)
    widget_to_var[stt_entry] = stt_var
    entries["stt"] = stt_entry

    # --- IGST field ---
    tk.Label(
        gss_label_frame, bg=gssbg, text="IGST", font=("Helvetica", 14)
    ).pack(side="left", padx=(110, 0), pady=2)
    igst_var = tk.DoubleVar()
    igst_entry = tk.Entry(
        gss_entry_frame,
        textvariable=igst_var,
        width=11,
        font=("Helvetica", 14),
    )
    igst_entry.pack(side="left", padx=15)
    widget_to_var[igst_entry] = igst_var
    entries["igst"] = igst_entry

    # --- Net Trade Amount field ---
    tk.Label(
        gss_label_frame,
        bg=gssbg,
        text="Net Trade Amt.",
        font=("Helvetica", 14),
    ).pack(side="left", padx=(100, 0), pady=2)
    net_trade_var = tk.DoubleVar()
    net_trade_entry = tk.Entry(
        gss_entry_frame,
        textvariable=net_trade_var,
        width=11,
        font=("Helvetica", 14),
    )
    net_trade_entry.pack(side="left", padx=15)
    widget_to_var[net_trade_entry] = net_trade_var
    entries["net_trade"] = net_trade_entry

    # --- Contract Lot Price field ---
    tk.Label(
        gss_label_frame, bg=gssbg, text="Cont Lot.", font=("Helvetica", 14)
    ).pack(side="left", padx=(24, 0), pady=2)
    lot_cont_var = tk.DoubleVar()
    lot_cont_entry = tk.Entry(
        gss_entry_frame,
        textvariable=lot_cont_var,
        width=11,
        font=("Helvetica", 14),
        state="readonly",
        takefocus=False,
    )
    lot_cont_entry.pack(side="left", padx=15)
    widget_to_var[lot_cont_entry] = lot_cont_var
    entries["lot_cont"] = lot_cont_entry

    # --- STT Cont field ---
    tk.Label(
        gss_label_frame, bg=gssbg, text="STT Cont.", font=("Helvetica", 14)
    ).pack(side="left", padx=(67, 0), pady=2)
    stt_cont_var = tk.IntVar()
    stt_cont_entry = tk.Entry(
        gss_entry_frame,
        textvariable=stt_cont_var,
        width=11,
        font=("Helvetica", 14),
        state="readonly",
        takefocus=False,
    )
    stt_cont_entry.pack(side="left", padx=15)
    widget_to_var[stt_cont_entry] = stt_cont_var
    entries["stt_cont"] = stt_cont_entry

    # --- Trade Note field ---
    tk.Label(
        trd_note_frame, bg=gssbg, text="Trade Note", font=("Helvetica", 14)
    ).pack(side="left", padx=(0, 0), pady=(15, 0))
    note_trd_var = tk.StringVar()
    note_trd_entry = tk.Entry(
        trd_note_frame,
        textvariable=note_trd_var,
        width=60,
        font=("Helvetica", 14),
    )
    note_trd_entry.pack(side="left", padx=(10, 0), pady=(15, 0))
    widget_to_var[note_trd_entry] = note_trd_var
    entries["note_trd"] = note_trd_entry

    # --- Computed Bank Transfer field ---
    tk.Label(
        trd_note_frame, bg=gssbg, text="Bank Trans", font=("Helvetica", 14)
    ).pack(side="left", padx=(10, 0), pady=(15, 0))
    comp_bt_var = tk.DoubleVar()
    comp_bt_entry = tk.Entry(
        trd_note_frame,
        textvariable=comp_bt_var,
        width=11,
        font=("Helvetica", 14),
    )
    comp_bt_entry.pack(side="left", padx=(10, 0), pady=(15, 0))
    widget_to_var[comp_bt_entry] = comp_bt_var
    entries["comp_bt_amt"] = comp_bt_entry

    if current_trade_no[0] < no_of_trades_var.get():
        comp_bt_entry.config(state="disabled", takefocus=False)
    else:
        comp_bt_entry.config(state="normal", takefocus=True)

    # --- Applicable (Theoretical) Frame Starts Here ---
    tk.Label(
        app_label_frame, bg=appbg, text="ETC (App)", font=("Helvetica", 14)
    ).pack(side="left", padx=(0, 0), pady=2)
    etc_app_var = tk.DoubleVar()
    etc_app_entry = tk.Entry(
        app_entry_frame,
        textvariable=etc_app_var,
        width=11,
        font=("Helvetica", 14),
        state="readonly",
        takefocus=False,
    )
    etc_app_entry.pack(side="left", padx=(0, 5))
    widget_to_var[etc_app_entry] = etc_app_var
    entries["etc_trd_applicable"] = etc_app_entry

    tk.Label(
        app_label_frame, bg=appbg, text="GST (App)", font=("Helvetica", 14)
    ).pack(side="left", padx=(45, 0), pady=2)
    gst_app_var = tk.DoubleVar()
    gst_app_entry = tk.Entry(
        app_entry_frame,
        textvariable=gst_app_var,
        width=11,
        font=("Helvetica", 14),
        state="readonly",
        takefocus=False,
    )
    gst_app_entry.pack(side="left", padx=15)
    widget_to_var[gst_app_entry] = gst_app_var
    entries["gst_trd_applicable"] = gst_app_entry

    tk.Label(
        app_label_frame, bg=appbg, text="STT (App)", font=("Helvetica", 14)
    ).pack(side="left", padx=(55, 0), pady=2)
    stt_app_var = tk.DoubleVar()
    stt_app_entry = tk.Entry(
        app_entry_frame,
        textvariable=stt_app_var,
        width=11,
        font=("Helvetica", 14),
        state="readonly",
        takefocus=False,
    )
    stt_app_entry.pack(side="left", padx=15)
    widget_to_var[stt_app_entry] = stt_app_var
    entries["stt_trd_applicable"] = stt_app_entry

    tk.Label(
        app_label_frame, bg=appbg, text="Net (App)", font=("Helvetica", 14)
    ).pack(side="left", padx=(60, 0), pady=2)
    net_trade_app_var = tk.DoubleVar()
    net_trade_app_entry = tk.Entry(
        app_entry_frame,
        textvariable=net_trade_app_var,
        width=11,
        font=("Helvetica", 14),
        state="readonly",
        takefocus=False,
    )
    net_trade_app_entry.pack(side="left", padx=15)
    widget_to_var[net_trade_app_entry] = net_trade_app_var
    entries["net_amt_trd_applicable"] = net_trade_app_entry

    tk.Label(
        app_label_frame, bg=appbg, text="Diff (Trd)", font=("Helvetica", 14)
    ).pack(side="left", padx=(65, 0), pady=2)
    diff_trd_var = tk.DoubleVar()
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
    widget_to_var[diff_trd_entry] = diff_trd_var
    entries["difference_trd"] = diff_trd_entry

    # --- Apply Global Styles, Entry Hovers & Tooltips ---
    for key, widget in entries.items():
        # Safety check: Skip Tkinter variables (StringVar, etc.) stored in the dict
        if not isinstance(widget, tk.Widget):
            continue

        is_ro = False
        try:
            if str(widget.cget("state")) in ("readonly", "disabled"):
                is_ro = True
        except (tk.TclError, AttributeError):
            pass
        apply_entry_theme(widget, is_readonly=is_ro)

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
    bind_tooltip(
        etc_entry,
        tooltip_var,
        "Exchange Transaction Charges levied by NSE/BSE.",
    )
    bind_tooltip(sebi_entry, tooltip_var, "SEBI turnover fees.")
    bind_tooltip(
        stt_entry,
        tooltip_var,
        "Securities Transaction Tax applied to this transaction.",
    )
    bind_tooltip(
        net_trade_entry,
        tooltip_var,
        "The final net amount after all levies are applied.",
    )

    # --- Tooltip Label ---
    info_label = tk.Label(
        rat_win,
        textvariable=tooltip_var,
        bg=ratwinbg,
        fg="#5122df",
        font=("Helvetica", 14, "italic", "bold"),
        anchor="center",
        pady=5,
    )
    info_label.pack(fill="x", side="bottom")

    # --- OK and Cancel Buttons ---
    ok_btn = tk.Button(
        btn_frame,
        text="✅ OK ✅",
        width=12,
        font=("Comic Sans MS", 12, "bold"),
        bg=submitusualbg,
        fg="white",
        activebackground=okactivebg,
        activeforeground="white",
        relief="raised",
        bd=3,
        cursor="hand2",
        command=on_ok,
    )
    ok_btn.pack(side="right", padx=5)
    cancel_btn = tk.Button(
        btn_frame,
        text="❌ Cancel ❌",
        width=12,
        font=("Comic Sans MS", 12, "bold"),
        bg=cancelusualbg,
        fg="white",
        activebackground=cancelactivebg,
        activeforeground="white",
        relief="raised",
        bd=3,
        cursor="hand2",
        command=cleanup_and_close,
    )
    cancel_btn.pack(side="right", padx=5)

    hint_label = tk.Label(
        btn_frame,
        text="Press F1 for help, F2 to see trades of this session and Esc to Rollback.",
        font=("Helvetica", 16),
        bg=hintbg,
    )
    hint_label.pack(side="left", padx=8)

    # Hover animations for Submit, OK, Cancel buttons
    submit_btn.bind("<Enter>", lambda e: submit_btn.config(bg="#2563eb"))
    submit_btn.bind("<Leave>", lambda e: submit_btn.config(bg=submitusualbg))
    submit_btn.bind("<FocusIn>", lambda e: submit_btn.config(bg="#2563eb"))
    submit_btn.bind(
        "<FocusOut>", lambda e: submit_btn.config(bg=submitusualbg)
    )

    ok_btn.bind("<Enter>", lambda e: ok_btn.config(bg="#1e40af"))
    ok_btn.bind("<Leave>", lambda e: ok_btn.config(bg=submitusualbg))
    ok_btn.bind("<FocusIn>", lambda e: ok_btn.config(bg="#1e40af"))
    ok_btn.bind("<FocusOut>", lambda e: ok_btn.config(bg=submitusualbg))

    cancel_btn.bind("<Enter>", lambda e: cancel_btn.config(bg="#991b1b"))
    cancel_btn.bind("<Leave>", lambda e: cancel_btn.config(bg=cancelusualbg))
    cancel_btn.bind("<FocusIn>", lambda e: cancel_btn.config(bg="#991b1b"))
    cancel_btn.bind(
        "<FocusOut>", lambda e: cancel_btn.config(bg=cancelusualbg)
    )

    rat_win.protocol("WM_DELETE_WINDOW", cleanup_and_close)

    # ======================================================================
    # EVENT BINDINGS
    # ======================================================================
    cont_no_entry.bind(
        "<FocusOut>",
        lambda event: fetch_and_populate_contract(
            cont_no_entry,
            data,
            trd_date_entry,
            settle_no_entry,
            settle_no_var,
            settle_date_entry,
            trades_spin,
            no_of_trades_var,
            comp_bt_var,
            comp_bt_entry,
            current_trade_no,
            current_trade_no_var,
            current_session_trades,
        ),
        add="+",
    )
    settle_no_entry.bind(
        "<FocusIn>",
        lambda event: update_and_calculate_settle_no(
            cont_no_entry, settle_no_entry, settle_no_var
        ),
        add="+",
    )
    settle_date_entry.bind(
        "<FocusIn>",
        lambda event: update_settle_date_on_focus(
            trd_date_entry, settle_date_entry, event
        ),
        add="+",
    )
    qty_trd_entry.bind("<FocusIn>", on_qty_trd_focus, add="+")
    ord_no_entry.bind(
        "<FocusIn>",
        lambda event: ord_no_focus_in(
            event, qty_trd_entry, qty_trd_var, data, qty_eo_entry, qty_eo_var
        ),
        add="+",
    )
    ord_dt_entry.bind(
        "<FocusIn>",
        lambda event: update_ord_dt_on_focus(
            event, trd_date_entry, ord_dt_entry
        ),
        add="+",
    )
    qty_eo_entry.bind(
        "<FocusIn>",
        lambda event: qty_eo_on_focus_in(
            event, qty_trd_var, data, qty_eo_var, submit_btn
        ),
        add="+",
    )
    qty_eo_entry.bind(
        "<FocusOut>",
        lambda event: update_check_qty_on_focus_out_of_qty_eo(
            event, qty_eo_var, data
        ),
        add="+",
    )

    rate_eo_entry.bind(
        "<KeyRelease>",
        lambda event: rate_eo_entry_key_release(
            event,
            rate_eo_var,
            brok_unit_eo_var,
            brok_unit_eo_entry,
            buy_sell_var,
            net_rate_eo_var,
            net_rate_eo_entry,
            qty_eo_var,
            net_total_eo_var,
            net_total_eo_entry,
        ),
    )
    rate_eo_entry.bind(
        "<FocusOut>",
        lambda event: rate_eo_entry_focus_out(
            event, rate_eo_var, rate_eo_entry
        ),
        add="+",
    )

    def _compute_net_eo_on_focus(_event=None):
        """Recompute Net Rate EO and Net Total EO from current Rate/Brok/Qty."""
        try:
            rate = rate_eo_var.get()
            brok = brok_unit_eo_var.get()
            qty = qty_eo_var.get()
            if buy_sell_var.get() == "BUY":
                net_rate = round(rate + brok, 4)
            else:
                net_rate = round(rate - brok, 4)
            net_total = round(qty * net_rate, 4)
            net_rate_eo_var.set(net_rate)
            net_total_eo_var.set(net_total)
        except (ValueError, tk.TclError):
            pass

    net_rate_eo_entry.bind("<FocusIn>", _compute_net_eo_on_focus, add="+")
    net_total_eo_entry.bind("<FocusIn>", _compute_net_eo_on_focus, add="+")

    for radio_btn, value in [(buy_radio, "BUY"), (sell_radio, "SELL")]:
        radio_btn.bind(
            "<Key>",
            lambda e, btn=radio_btn, val=value: on_radio_key(
                e, btn, val, buy_sell_var, buy_radio, sell_radio
            ),
        )
    for radio_btn, value in [(nse_radio, "NSE"), (bse_radio, "BSE")]:
        radio_btn.bind(
            "<Key>",
            lambda e, btn=radio_btn, val=value: on_ex_radio_key(
                e, btn, val, exchange_var, nse_radio, bse_radio
            ),
        )

    buy_radio.bind(
        "<Button-1>", lambda e: on_radio_click(buy_radio, buy_sell_var, "BUY")
    )
    sell_radio.bind(
        "<Button-1>",
        lambda e: on_radio_click(sell_radio, buy_sell_var, "SELL"),
    )
    nse_radio.bind(
        "<Button-1>", lambda e: on_radio_click(nse_radio, exchange_var, "NSE")
    )
    bse_radio.bind(
        "<Button-1>", lambda e: on_radio_click(bse_radio, exchange_var, "BSE")
    )

    def wap_on_focus_out(e):
        format_wap_on_focus_out(e)
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
            e,
            callback=calculate_applicable_fields,
        )

    wap_entry.bind(
        "<KeyRelease>",
        lambda e: recalculate_from_wap_change(
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
            e,
            callback=calculate_applicable_fields,
        ),
    )
    wap_entry.bind("<FocusOut>", wap_on_focus_out, add="+")
    sebi_entry.bind("<FocusOut>", lambda e: sebi_on_focus_out(e), add="+")

    def _handle_submit():
        on_submit(
            data=data,
            rat_win=rat_win,
            submit_btn=submit_btn,
            nse_radio=nse_radio,
            bse_radio=bse_radio,
            qty_trd_var=qty_trd_var,
            exchange_var=exchange_var,
            ord_no_var=ord_no_var,
            ord_dt_entry=ord_dt_entry,
            trd_no_var=trd_no_var,
            qty_eo_var=qty_eo_var,
            rate_eo_var=rate_eo_var,
            brok_unit_eo_var=brok_unit_eo_var,
            net_rate_eo_var=net_rate_eo_var,
            net_total_eo_var=net_total_eo_var,
            qty_eo_entry=qty_eo_entry,
            ord_no_entry=ord_no_entry,
            trd_no_entry=trd_no_entry,
            rate_eo_entry=rate_eo_entry,
            brok_unit_eo_entry=brok_unit_eo_entry,
            net_rate_eo_entry=net_rate_eo_entry,
            net_total_eo_entry=net_total_eo_entry,
            wap_var=wap_var,
            brs_var=brs_var,
            lp_var=lp_var,
            tot_brok_var=tot_brok_var,
            etc_var=etc_var,
            sebi_var=sebi_var,
            gst_var=gst_var,
            lot_cont_var=lot_cont_var,
            stt_cont_var=stt_cont_var,
            stt_var=stt_var,
            stamp_duty_var=stamp_duty_var,
            igst_var=igst_var,
            sell_charge_var=sell_charge_var,
            net_trade_var=net_trade_var,
            lot_cont_entry=lot_cont_entry,
            wap_entry=wap_entry,
            brs_entry=brs_entry,
            lp_entry=lp_entry,
            tot_brok_entry=tot_brok_entry,
            etc_entry=etc_entry,
            sebi_entry=sebi_entry,
            gst_entry=gst_entry,
            stt_entry=stt_entry,
            stt_cont_entry=stt_cont_entry,
            stamp_duty_entry=stamp_duty_entry,
            igst_entry=igst_entry,
            sell_charge_entry=sell_charge_entry,
            net_trade_entry=net_trade_entry,
            buy_sell_var=buy_sell_var,
            etc_app_var=etc_app_var,
            gst_app_var=gst_app_var,
            stt_app_var=stt_app_var,
            net_trade_app_var=net_trade_app_var,
            diff_trd_var=diff_trd_var,
            cleanup_and_close=cleanup_and_close,
            validate_required_fields_fn=validate_required_fields,
            calculate_applicable_fields_fn=calculate_applicable_fields,
            refresh_financial_formats_fn=refresh_financial_formats,
        )

    submit_btn.config(command=_handle_submit)

    # Check every financial entry is positive.
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

    lp_entry.bind("<FocusOut>", calculate_applicable_fields, add="+")
    net_trade_entry.bind("<KeyRelease>", on_net_trade_change)

    for entry in [
        etc_entry,
        gst_entry,
        igst_entry,
        sell_charge_entry,
        stamp_duty_entry,
        stt_entry,
        tot_brok_entry,
    ]:
        entry.bind("<KeyRelease>", update_levies_and_net_trade, add="+")
        entry.bind("<FocusOut>", update_levies_and_net_trade, add="+")

    def _select_all_on_focus(event):
        try:
            widget = event.widget
            widget.select_range(0, "end")
            widget.icursor("end")
        except (tk.TclError, AttributeError):
            pass

    _selectable_widgets = [
        cont_no_entry,
        trd_date_entry,
        settle_no_entry,
        settle_date_entry,
        trades_spin,
        note_cont_entry,
        company_entry,
        qty_trd_entry,
        ord_no_entry,
        ord_dt_entry,
        trd_no_entry,
        qty_eo_entry,
        rate_eo_entry,
        brok_unit_eo_entry,
        net_rate_eo_entry,
        net_total_eo_entry,
        wap_entry,
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
        note_trd_entry,
        comp_bt_entry,
    ]
    for _w in _selectable_widgets:
        _w.bind("<FocusIn>", _select_all_on_focus, add="+")

    rat_win.bind("<Return>", on_enter)
    rat_win.bind("<Escape>", on_escape)
    rat_win.bind("<F1>", show_help)
    rat_win.bind("<F2>", show_session_trades)

    for widget in entries.values():
        if isinstance(widget, tk.Entry):
            _create_context_menu(widget)

    # Use .after() to guarantee Tkinter's background sync doesn't overwrite our formatting on load
    rat_win.after(100, refresh_financial_formats)

    parent.wait_window(rat_win)
    try:
        if parent.winfo_exists():
            parent.grab_set()
    except tk.TclError:
        pass
