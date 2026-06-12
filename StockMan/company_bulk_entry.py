# -*- coding: utf-8 -*-
# File:
# C:\Data\Personal\Finance_and_Investment\finprog\FinanceManager\StockMan\company_bulk_entry.py

"""
Bulk entry of company data into the stocks table with progress UI and
modal management.

This module provides a GUI for bulk inserting company records, using
centralized modal window management (disable_parent/enable_parent).
"""

# import re
import sqlite3
import threading
import time
import tkinter as tk
from typing import Union

# from typing import Optional, Tuple


from Shared.globals import get_db_connection, logger
from Shared.dialog_utils import show_colorful_info

# Import using new package structure
# Import centralized modal management
from Shared.modal_utils import (
    disable_parent,
)
from Shared.window_manager import (
    push_window,
    pop_window,
    activate_previous_window,
)

# =====================================================
# CENTRALIZED MODAL WINDOW MANAGEMENT SYSTEM
# =====================================================


# --- GUI Bulk Entry Company ---


# --- GUI Bulk Entry Company ---
def bulk_entry_company(parent: Union[tk.Tk, tk.Toplevel]) -> None:
    """GUI version: Bulk insert company data into the stocks table
    with progress UI."""
    disable_parent(parent)
    # Tuple: stock_code, company_name, short_name, isin, ticker, face_value,
    # sector, is_active, is_etf, tick
    company_data = [
        (
            "ABFRL",
            "Aditya Birla Fashion & Retail Ltd",
            "Adi Birla Fashion",
            "INE647O01011",
            "ABFRL.NS",
            10.0,
            "Consumer Durables",
            1,
            0,
            0.01,
        ),
        (
            "ADILIF",
            "Aditya Birla Lifestyle Brands Limited",
            "Adi Birla Lifestyle",
            "INE14LE01019",
            "ADL.NS",
            10.0,
            "Retail",
            1,
            0,
            0.01,
        ),
        (
            "ADANIPORTS",
            "Adani Ports and Special Economic Zone Limited",
            "Adani Ports",
            "INE742F01042",
            "ADANIPORTS.NS",
            2.0,
            "Port & Port services",
            1,
            0,
            0.1,
        ),
        (
            "DMART",
            "Avenue Supermarts Limited DMART",
            "Dmart",
            "INE192R01011",
            "DMART.NS",
            10.0,
            "Consumer Durables",
            1,
            0,
            0.1,
        ),
        (
            "BAJFINANCE",
            "Bajaj Finance Limited",
            "Bajaj Fin",
            "INE296A01024",
            "BAJFINANCE.NS",
            2.0,
            "Non Banking Financial Company (NBFC)",
            1,
            0,
            0.5,
        ),
        (
            "BANKBARODA",
            "Bank of Baroda",
            "BoB",
            "INE028A01039",
            "BANKBARODA.NS",
            2.0,
            "Banking",
            1,
            0,
            0.01,
        ),
        (
            "BHEL",
            "Bharat Heavy Electricals Limited",
            "BHEL",
            "INE257A01026",
            "BHEL.NS",
            2.0,
            "Heavy Electrical Equipment",
            1,
            0,
            0.01,
        ),
        (
            "COALINDIA",
            "Coal India Limited",
            "Coal India",
            "INE522F01014",
            "COALINDIA.NS",
            10.0,
            "Coal",
            1,
            0,
            0.05,
        ),
        (
            "DEEPAKNTR",
            "Deepak Nitrite Limited",
            "Deepak Nitrite",
            "INE288B01029",
            "DEEPAKNTR.NS",
            2.0,
            "Chemicals",
            1,
            0,
            0.1,
        ),
        (
            "DIXTEC",
            "Dixon Technologies (India) Limited",
            "Dixon Tech",
            "INE935N01020",
            "DIXON.NS",
            2.0,
            "Consumer Durables",
            1,
            0,
            1,
        ),
        (
            "ETERNAL(ZOMATO)",
            "Eternal Limited",
            "Zomato",
            "INE758T01015",
            "ZOMATO.NS",
            1.0,
            "E-Commerce/App based Aggregator",
            1,
            0,
            0.01,
        ),
        (
            "GRWRHITECH",
            "Garware Hi-Tech Films Limited",
            "Garware Hi-Tech Films",
            "INE291A01017",
            "GRWRHITECH.NS",
            10.0,
            "Plastics",
            1,
            0,
            0.1,
        ),
        (
            "HCLTECH",
            "HCL Technologies Limited",
            "HCL Tech",
            "INE860A01027",
            "HCLTECH.NS",
            2.0,
            "Software and Consultancy",
            1,
            0,
            0.1,
        ),
        (
            "HAL",
            "Hindustan Aeronautics Limited",
            "HAL",
            "INE066F01020",
            "HAL.NS",
            5.0,
            "Aerospace",
            1,
            0,
            0.1,
        ),
        (
            "HDFC",
            "HDFC Bank Limited",
            "HDFC Bank",
            "INE040A01034",
            "HDFCBANK.NS",
            1.0,
            "Banking",
            1,
            0,
            0.1,
        ),
        (
            "HYUNDAI",
            "Hyundai Motor India Limited",
            "Hyundai Motor India",
            "INE0V6F01027",
            "HYUNDAI.NS",
            10.0,
            "Automobile",
            1,
            0,
            0.1,
        ),
        (
            "ICIBAN",
            "ICICI Bank Limited",
            "ICICI Bank",
            "INE090A01021",
            "ICICIBANK.NS",
            2.0,
            "Banking",
            1,
            0,
            0.1,
        ),
        (
            "BSE500IETF",
            "ICICI Prudential BSE 500 ETF",
            "IPru BSE 500 ETF",
            "INF109KC1V59",
            "BSE500IETF.NS",
            1.0,
            "Finance ETF",
            1,
            1,
            0.01,
        ),
        (
            "GOLDIETF",
            "ICICI Prudential Gold ETF",
            "IPru Gold ETF",
            "INF109KC1NT3",
            "SETFGOLD.NS",
            1.0,
            "Gold ETF",
            1,
            1,
            0.01,
        ),
        (
            "ISEC",
            "ICICI Securities Limited",
            "ISecure",
            "INE763G01038",
            "ISEC.NS",
            5.0,
            "Finance",
            1,
            0,
            0.1,
        ),
        (
            "IOC",
            "Indian Oil Corporation Limited",
            "IOC",
            "INE242A01010",
            "IOC.NS",
            10.0,
            "Refineries/Oil-Gas",
            1,
            0,
            0.01,
        ),
        (
            "IREDA",
            "Indian Renewable Energy Development Agency Ltd",
            "IREDA",
            "INE202E01016",
            "IREDA.NS",
            10.0,
            "Finance",
            1,
            0,
            0.01,
        ),
        (
            "INFY",
            "Infosys Ltd",
            "Infosys",
            "INE009A01021",
            "INFY.NS",
            5.0,
            "IT",
            1,
            0,
            0.1,
        ),
        (
            "IRB",
            "IRB Infrastructure Developers Limited",
            "IRB",
            "INE821I01022",
            "IRB.NS",
            1.0,
            "Infrastructure",
            1,
            0,
            0.01,
        ),
        (
            "ITC",
            "ITC Limited",
            "ITC",
            "INE154A01025",
            "ITC.NS",
            1.0,
            "FMCG",
            1,
            0,
            0.05,
        ),
        (
            "JUSTDIAL",
            "Just Dial Limited",
            "Just Dial",
            "INE599M01018",
            "JUSTDIAL.NS",
            10.0,
            "E-Commerce/App based Aggregator",
            1,
            0,
            0.05,
        ),
        (
            "KOTAKBANK",
            "Kotak Mahindra Bank Ltd",
            "Kotak Mahindra Bank",
            "INE237A01028",
            "KOTAKBANK.NS",
            5.0,
            "Banking",
            1,
            0,
            0.1,
        ),
        (
            "KPIGREEN",
            "KPI Green Energy Limited",
            "KPI Green Energy",
            "INE542W01017",
            "KPIGREEN.NS",
            5.0,
            "Power",
            1,
            0,
            0.05,
        ),
        (
            "KPEL",
            "K.P. Energy Limited",
            "K.P. Energy",
            "INE127T01021",
            "KPEL.BO",
            5.0,
            "Power",
            1,
            0,
            0.05,
        ),
        (
            "KSOLVES",
            "Ksolves India Limited",
            "Ksolves India",
            "INE0D6I01023",
            "KSOLVES.NS",
            5.0,
            "IT",
            1,
            0,
            0.1,
        ),
        (
            "LT",
            "Larsen & Toubro Limited",
            "L & T",
            "INE018A01030",
            "LT.NS",
            2.0,
            "Infrastructure",
            1,
            0,
            0.1,
        ),
        (
            "NDTV",
            "New Delhi Television Limited",
            "NDTV",
            "INE155G01029",
            "NDTV.NS",
            4.0,
            "Media",
            1,
            0,
            0.01,
        ),
        (
            "NIFTYBEES",
            "Nippon ETF Nifty 50 Bees",
            "Nippon ETF Nif50 Bees",
            "INF204KB14I2",
            "NIFTYBEES.NS",
            1.0,
            "ETF",
            1,
            1,
            0.01,
        ),
        (
            "ONGC",
            "Oil And Natural Gas Corporation",
            "ONGC",
            "INE213A01029",
            "ONGC.NS",
            5.0,
            "Refineries/Oil-Gas",
            1,
            0,
            0.01,
        ),
        (
            "SOUTHBANK",
            "The South Indian Bank Limited",
            "South Indian Bank",
            "INE683A01023",
            "SOUTHBANK.NS",
            1.0,
            "Banking",
            1,
            0,
            0.01,
        ),
        (
            "TATACAP",
            "Tata Capital Limited",
            "Tata Capital",
            "INE976I01016",
            "",
            10.0,
            "Financial Services",
            1,
            0,
            0.01,
        ),
        (
            "TATAMTRDVR",
            "Tata Motors Passenger Vehicles Ltd",
            "Tata Motors",
            "IN9155A01020",
            "TATAMTRDVR.NS",
            2.0,
            "Automobile",
            1,
            0,
            0.01,
        ),
        (
            "TATAPOWER",
            "Tata Power Company Limited",
            "Tata Power",
            "INE245A01021",
            "TATAPOWER.NS",
            1.0,
            "Power/Generation/Distribution",
            1,
            0,
            0.05,
        ),
        (
            "TATASTEEL",
            "Tata Steel Limited",
            "Tata Steel",
            "INE081A01020",
            "TATASTEEL.NS",
            1.0,
            "Steel",
            1,
            0,
            0.01,
        ),
        (
            "TECHM",
            "Tech Mahindra Limited",
            "Tech Mahindra",
            "INE669C01036",
            "TECHM.NS",
            5.0,
            "IT",
            1,
            0,
            0.1,
        ),
        (
            "UNIONBANK",
            "Union Bank Of India",
            "Union Bank",
            "INE692A01016",
            "UNIONBANK.NS",
            10.0,
            "Banking",
            1,
            0,
            0.01,
        ),
        (
            "WAAREE",
            "Waaree Energies Limited",
            "Waaree Energies",
            "INE377N01017",
            "WAAREEENER.NS",
            10.0,
            "Capital Goods",
            1,
            0,
            0.1,
        ),
        (
            "WIPRO",
            "Wipro Ltd",
            "Wipro",
            "INE075A01022",
            "WIPRO.NS",
            2.0,
            "IT",
            1,
            0,
            0.01,
        ),
    ]

    win = tk.Toplevel(parent)
    win.title("Bulk Entry Company")
    win.geometry("500x200")
    win.resizable(False, False)
    win.transient(parent)
    win.grab_set()
    push_window(win, parent)

    status_label = tk.Label(
        win, text="Starting bulk entry...", font=("Helvetica", 12)
    )
    status_label.pack(pady=20)
    progress = tk.DoubleVar(value=0)
    progress_bar = tk.Scale(
        win,
        variable=progress,
        from_=0,
        to=len(company_data),
        orient="horizontal",
        length=400,
        showvalue=False,
        state="disabled",
    )
    progress_bar.pack(pady=10)

    def do_bulk_entry():
        added_count = 0
        skipped_count = 0
        updated_count = 0  # <-- NEW VARIABLE
        logger.info(
            "Starting bulk entry of companies. Total: %d", len(company_data)
        )
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                msg = ""
                for idx, (
                    code,
                    name,
                    short,
                    isin,
                    ticker,  # <-- NEW FIELD
                    fv,
                    sector,
                    active,
                    isetf,
                    tick,
                ) in enumerate(company_data, 1):
                    logger.debug(
                        "Processing company #%d: %s (%s)", idx, name, code
                    )
                    cur.execute(
                        "SELECT 1 FROM stocks WHERE stk_code = ? "
                        "OR isin = ?",
                        (code, isin),
                    )
                    if cur.fetchone():
                        # If the company exists, update its ticker!
                        try:
                            cur.execute(
                                "UPDATE stocks SET ticker = ? WHERE stk_code = ?",
                                (ticker, code),
                            )
                            updated_count += 1
                            msg = f"🔄 Updated {name} with ticker."
                            logger.info(
                                "Updated company ticker: %s (%s) -> %s",
                                name,
                                code,
                                ticker,
                            )
                        except sqlite3.Error as ue:
                            skipped_count += 1
                            msg = f"⚠️ Error updating {name}."
                            logger.error(
                                "Error updating ticker for %s: %s", name, ue
                            )
                    else:
                        try:
                            cur.execute(
                                """
                                INSERT INTO stocks (stk_code, company_name,
                                                  short_name, isin, ticker, face_value,
                                                  sector, is_active, is_etf,
                                                  tick)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                                (
                                    code,
                                    name,
                                    short,
                                    isin,
                                    ticker,  # <-- NEW FIELD
                                    fv,
                                    sector,
                                    active,
                                    isetf,
                                    tick,
                                ),
                            )
                            added_count += 1
                            msg = f"✅ Added {name}."
                            logger.info("Added company: %s (%s)", name, code)
                        except sqlite3.IntegrityError as ie:
                            # Skip duplicates or constraint failures but log
                            skipped_count += 1
                            msg = f"⚠️ Skipping {name}: integrity error."
                            logger.info(
                                "Skipping company due to integrity error "
                                "for %s (%s): %s",
                                name,
                                code,
                                ie,
                            )
                    status_text = (
                        f"{msg}\n{added_count} added, "
                        f"{skipped_count} skipped."
                    )
                    win.after(0, status_label.config, {"text": status_text})
                    win.after(0, progress.set, idx)
                    time.sleep(0.05)
                conn.commit()
                logger.info(
                    "Bulk entry complete. Added: %d, Skipped: %d",
                    added_count,
                    skipped_count,
                )
        except sqlite3.Error as e:
            logger.error(
                "Database error during bulk entry: %s", e, exc_info=True
            )
            win.after(0, status_label.config, {"text": f"❌ Error: {e}"})
        msg = f"Added: {added_count}\nUpdated: {updated_count}\nSkipped: {skipped_count}"

        # Show the summary info dialog before destroying this bulk-entry
        # window. When the info dialog is closed, perform cleanup (pop
        # stack, release grab, destroy the bulk-entry window) and then
        # activate the previous window.
        # activate_previous_window is imported at module level

        def _cleanup_after_info():
            try:
                pop_window()
            except (RuntimeError, AttributeError):
                pass
            try:
                win.grab_release()
            except (RuntimeError, tk.TclError, AttributeError):
                pass
            try:
                win.destroy()
            except (RuntimeError, tk.TclError, AttributeError):
                pass
            try:
                activate_previous_window()
            except (RuntimeError, AttributeError):
                pass

            # Try to align keyboard focus with the visually focused button
            # on parent.
            try:
                btns = getattr(parent, "_menu_buttons", None)
                cb_idx = getattr(parent, "_come_back_index", None)

                def _choose_target_button():
                    # Prefer a button that already shows focus/active state
                    if btns:
                        for b in btns:
                            try:
                                states = tuple(b.state())
                            except (RuntimeError, tk.TclError, AttributeError):
                                states = ()
                            if "focus" in states or "active" in states:
                                return b
                    # Defensive: clamp cb_idx (come_back_index) if out of range
                    safe_idx = None
                    try:
                        total = len(btns) if btns is not None else 0
                    except (TypeError, AttributeError):
                        total = 0
                    if isinstance(cb_idx, int) and total > 0:
                        if 0 <= cb_idx < total:
                            safe_idx = cb_idx
                        else:
                            try:
                                logger.warning(
                                    "company_bulk_entry: _come_back_index "
                                    "range (%s)",
                                    cb_idx,
                                )
                            except (RuntimeError, AttributeError):
                                # Best-effort: ignore logging failures
                                pass
                            safe_idx = 0
                    # Fallback to safe_idx
                    if btns is not None and safe_idx is not None:
                        try:
                            return btns[safe_idx]
                        except (IndexError, TypeError):
                            pass
                    # Last resort: first button
                    if btns:
                        return btns[0]
                    return None

                def _focus_parent_button(attempts=4):
                    try:
                        target = _choose_target_button()
                        if target is not None:
                            parent.lift()
                            parent.focus_force()
                            target.focus_force()
                            target.focus_set()
                            try:
                                target.state(["focus", "active"])
                            except (RuntimeError, tk.TclError, AttributeError):
                                pass
                            parent.update_idletasks()
                            if target != parent.focus_get() and attempts > 0:
                                # Retry focus using after with args
                                parent.after(
                                    120,
                                    _focus_parent_button,
                                    attempts - 1,
                                )
                    except (RuntimeError, tk.TclError, AttributeError):
                        pass

                parent.after(80, _focus_parent_button)
            except (RuntimeError, tk.TclError, AttributeError):
                pass

        # Schedule info dialog shortly to allow UI to update; cleanup will run
        # when the user closes the info dialog.
        def _show_info():
            try:
                win.grab_release()  # Prevent nested grab conflicts
            except (RuntimeError, tk.TclError, AttributeError):
                pass
            show_colorful_info(
                parent=parent,
                title="Bulk Entry Complete",
                message=msg,
                on_close=_cleanup_after_info,
            )

        parent.after(100, _show_info)

    threading.Thread(target=do_bulk_entry, daemon=True).start()
    # Do not enable the parent here: the bulk window remains active until the
    # background thread finishes and the info dialog's on_close runs the
    # cleanup which pops the stack and destroys the bulk window. Enabling the
    # parent prematurely causes modality/state mismatches and focus bugs.


# File:
# C:\Data\Personal\Finance_and_Investment\finprog\FinanceManager\StockMan\company_bulk_entry.py ends here
