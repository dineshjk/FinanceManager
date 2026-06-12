# -*- coding: utf-8 -*-
# StockMan/ipo.py

"""
This module handles the management of IPOs within the stock portfolio.
"""

from typing import Union
import tkinter as tk
from tkinter import ttk
import sqlite3
from tkcalendar import DateEntry
from datetime import date, timedelta

# Local project imports
from Shared.globals import get_db_connection, logger
from Shared.dialog_utils import (
    show_colorful_info,
    show_colorful_error,
    show_colorful_yesno,
)

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

from .company_add import add_company
from .company_ex_import import export_company
from .trade_utils import compute_avg_price, process_allotment
from Shared.modal_utils import disable_parent, enable_parent
from Shared.window_manager import push_window, pop_window, safe_close_modal
from Shared.gui_progressive import progressive_selection


def ipo(
    parent: Union[tk.Toplevel, tk.Tk], calling_button: tk.Widget | None = None
) -> None:
    """
    Opens a modal window for IPO/FPO data entry and saves it to the database.
    """

    # --- Color Theme Variables ---
    winbg = "#f0f8ff"
    headbg = "#1e3a8a"
    titlefg = "#ffd700"
    mainfrbg = "#a475eb"
    compfrbg = "#fef3c7"
    datefrbg = "#e0f2fe"
    appfrbg = "#dcfce7"
    allotfrbg = "#fce7f3"
    notefrbg = "#f0fdf4"
    btnfrbg = "#f8fafc"
    submitusualbg = "#22c55e"
    submitactivebg = "#16a34a"
    cancelusualbg = "#ef4444"
    cancelactivebg = "#b91c1c"

    modal_id = disable_parent(parent, calling_button=calling_button)
    ipo_win = tk.Toplevel(parent)
    ipo_win.title("✨ IPO / FPO Entry ✨")

    # Adjusted window height and width to accommodate stacked frames
    ipo_win.geometry("960x680")
    ipo_win.resizable(False, False)
    ipo_win.configure(bg=winbg)
    ipo_win.transient(parent)
    ipo_win.grab_set()
    push_window(ipo_win, parent)

    tooltip_var = setup_footer_tooltip(
        ipo_win, bg_color=mainfrbg, fg_color="#5122df"
    )

    # --- Fetch Companies & Initialize Session ---
    companies = []
    company_to_id = {}
    current_session_ipos = {}

    def _refresh_company_data(combo_widget=None):
        companies.clear()
        company_to_id.clear()
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT company_name, id_stk FROM stocks ORDER BY company_name"
                )
                for row in cursor.fetchall():
                    companies.append(row[0])
                    company_to_id[row[0]] = row[1]
        except sqlite3.Error as e:
            logger.error("Failed to fetch companies for IPO: %s", e)

        if combo_widget:
            combo_widget["values"] = companies
            progressive_selection(combo_widget, companies)

    _refresh_company_data()

    # --- UI Variables ---
    company_name_var = tk.StringVar()
    exchange_var = tk.StringVar(value="NSE")
    offer_name_var = tk.StringVar()
    issue_type_var = tk.StringVar(value="IPO")
    issue_price_var = tk.DoubleVar()

    applied_qty_var = tk.IntVar()
    allotted_qty_var = tk.IntVar()
    allotted_amt_var = tk.DoubleVar()
    status_var = tk.StringVar(value="APPLIED")
    note_allot_var = tk.StringVar()

    # --- Dynamic Helpers & Animations ---
    def _calculate_allotted_amount(*_args):
        try:
            qty = allotted_qty_var.get()
            price = issue_price_var.get()
            allotted_amt_var.set(round(qty * price, 2))
        except (ValueError, tk.TclError):
            allotted_amt_var.set(0.0)

    def _update_subsequent_dates(event=None):
        try:
            open_date = open_dt_entry.get_date()
            close_dt_entry.set_date(open_date + timedelta(days=2))
            allotment_dt_entry.set_date(open_date + timedelta(days=3))
            listing_dt_entry.set_date(open_date + timedelta(days=6))
        except Exception:
            pass

    # (Local tooltip and validation functions removed to use central engine)

    def on_company_focus_out(_event=None):
        name = company_name_var.get().strip()
        if not name:
            return
        if name not in company_to_id:
            response = show_colorful_yesno(
                ipo_win,
                "Company Not Found",
                f"The company '{name}' was not found. Would you like to add it now?",
            )
            if response:
                add_company(ipo_win)
                export_company(ipo_win)
                _refresh_company_data(company_combo)
                company_combo.focus_set()
            else:
                show_colorful_error(
                    ipo_win,
                    "Invalid Company",
                    "You cannot change the company here. Please select a valid company from the list.",
                )
                company_combo.focus_set()
                company_combo.select_range(0, "end")

    def reset_form_for_new_ipo():
        """Resets variables and focuses company combo for the next entry."""
        company_name_var.set("")
        offer_name_var.set("")
        issue_type_var.set("IPO")
        issue_price_var.set(0.0)
        applied_qty_var.set(0)
        allotted_qty_var.set(0)
        allotted_amt_var.set(0.0)
        status_var.set("APPLIED")
        exchange_var.set("NSE")
        note_allot_var.set("")
        company_combo.focus_set()

    def show_session_ipos(_event=None):
        if not current_session_ipos:
            try:
                show_colorful_info(
                    ipo_win,
                    "No Entries",
                    "No IPOs have been recorded in this session yet.",
                )
            except tk.TclError:
                pass
            return

        ipo_win.unbind("<Escape>")

        session_entries = list(current_session_ipos.items())
        idx = {"i": 0}

        viewer = tk.Toplevel(ipo_win)
        viewer.title("Session IPO Viewer")
        viewer.transient(ipo_win)
        viewer.grab_set()
        viewer.resizable(False, False)
        viewer.geometry("520x280")

        push_window(viewer, ipo_win)
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
            content, wrap="word", height=9, bg="#f8fafc", bd=0, relief="flat"
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
            info_text.insert("end", "Company: ", "label")
            info_text.insert("end", f"{t.get('Company')}\n", "value")
            info_text.insert("end", "Offer Name: ", "label")
            info_text.insert("end", f"{t.get('Offer')}\n", "value")
            info_text.insert("end", "Issue Price: ", "label")
            info_text.insert("end", f"{t.get('Price'):.2f}\n", "value")
            info_text.insert("end", "Applied Qty: ", "label")
            info_text.insert("end", f"{t.get('Applied')}\n", "value")
            info_text.insert("end", "Allotted Qty: ", "label")
            info_text.insert("end", f"{t.get('Allotted')}\n", "value")
            info_text.insert("end", "Allotted Amt: ", "label")
            info_text.insert("end", f"{t.get('Amount'):.2f}\n", "net")
            info_text.config(state="disabled")

            left_btn.config(state="disabled" if i == 0 else "normal")
            if i >= len(session_entries) - 1:
                right_btn.config(state="disabled")
                status_label.config(
                    text="Last Entry",
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
            safe_close_modal(viewer, ipo_win)
            ipo_win.bind("<Escape>", _close_ipo)
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

    def show_help(_event=None):
        help_win = tk.Toplevel(ipo_win)
        help_win.transient(ipo_win)
        help_win.grab_set()
        help_win.title("Help - IPO Entry")
        help_win.configure(bg="#fffaf0")
        help_win.geometry("600x550")
        help_win.resizable(False, False)
        push_window(help_win, ipo_win)

        header = tk.Label(
            help_win,
            text="IPO Entry Help",
            font=("Helvetica", 16, "bold"),
            bg="#0284c7",
            fg="white",
            pady=8,
        )
        header.pack(fill="x")

        body = tk.Frame(help_win, bg="#fffaf0", padx=15, pady=15)
        body.pack(fill="both", expand=True)

        text = tk.Text(
            body, wrap="word", bg="#fffaf0", bd=0, font=("Helvetica", 11)
        )
        text.pack(fill="both", expand=True)

        help_lines = [
            "This form tracks your primary market applications (IPO/FPO).\n",
            "• Company Name: Choose the company from the dropdown.",
            "• Offer Name: E.g., 'Hyundai IPO 2024'.",
            "• Issue Price: The final per-share price of the issue.",
            "• Dates: Entering an Open Date automatically estimates the Close, Allotment, and Listing dates.",
            "• Applied Qty: The number of shares you bid for.",
            "• Status: Whether the application was APPLIED, ALLOTTED, or REJECTED.",
            "• Allotted Qty: The exact number of shares credited to you.",
            "• Allotted Amount: Automatically calculated based on Issue Price.\n",
            "Hotkeys:",
            "  F1: Show this help window.",
            "  F2: Show session entries.",
            "  Esc: Close help or close the main entry window.",
            "  Enter: Advance cursor or execute focused button.",
            "  Tab: Advance cursor.",
        ]

        text.insert("1.0", "\n".join(help_lines))
        highlights = {
            "Company Name:": "#d2691e",
            "Offer Name:": "#2e8b57",
            "Issue Price:": "#4682b4",
            "Dates:": "#b22222",
            "Applied Qty:": "#8b008b",
            "Status:": "#2f4f4f",
            "Allotted Qty:": "#b22222",
            "Allotted Amount:": "#2f4f4f",
            "Hotkeys:": "#000000",
        }
        for word, color in highlights.items():
            start = "1.0"
            while True:
                pos = text.search(word, start, stopindex="end")
                if not pos:
                    break
                end_pos = f"{pos}+{len(word)}c"
                text.tag_add(word, pos, end_pos)
                text.tag_config(
                    word, foreground=color, font=("Helvetica", 11, "bold")
                )
                start = end_pos

        text.config(state="disabled")

        def close_help(_ev=None):
            safe_close_modal(help_win, ipo_win)

        btn = tk.Button(
            help_win,
            text="Close",
            command=close_help,
            font=("Helvetica", 11, "bold"),
            bg="#ef4444",
            fg="white",
            padx=15,
            pady=5,
            cursor="hand2",
        )
        btn.pack(side="bottom", pady=15)
        help_win.bind("<Escape>", close_help)
        help_win.bind("<Return>", close_help)
        btn.focus_set()

    # --- Submission Logic ---
    def _on_submit(_event=None):
        company = company_name_var.get().strip()
        if company not in company_to_id:
            show_colorful_error(
                ipo_win,
                "Validation Error",
                "Please select a valid company from the list.",
            )
            return

        id_stk = company_to_id[company]
        try:
            price = float(issue_price_var.get())
            applied_qty = int(applied_qty_var.get())
            allotted_qty = int(allotted_qty_var.get())
            allotted_amt = float(allotted_amt_var.get())

            if price < 0 or applied_qty < 0 or allotted_qty < 0:
                raise ValueError("Negative values are not allowed.")
        except (ValueError, tk.TclError):
            show_colorful_error(
                ipo_win,
                "Validation Error",
                "Please ensure Price and Quantities are valid numbers. They cannot be left blank.",
            )
            return

        try:
            ann_dt = ann_dt_entry.get_date().strftime("%Y-%m-%d")
            o_dt = open_dt_entry.get_date().strftime("%Y-%m-%d")
            c_dt = close_dt_entry.get_date().strftime("%Y-%m-%d")
            a_dt = allotment_dt_entry.get_date().strftime("%Y-%m-%d")
            l_dt = listing_dt_entry.get_date().strftime("%Y-%m-%d")
        except Exception:
            show_colorful_error(
                ipo_win, "Date Error", "Please ensure all dates are valid."
            )
            return

        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA foreign_keys = ON;")

                # 1. Insert into primary_offers
                cursor.execute(
                    """
                    INSERT INTO primary_offers (
                        id_stk, offer_type, offer_name, ann_dt, open_dt,
                        close_dt, allotment_dt, listing_dt, issue_price
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        id_stk,
                        issue_type_var.get(),
                        offer_name_var.get().strip(),
                        ann_dt,
                        o_dt,
                        c_dt,
                        a_dt,
                        l_dt,
                        price,
                    ),
                )
                id_offer = cursor.lastrowid

                # 2. Insert into offer_allotments
                cursor.execute(
                    """
                    INSERT INTO offer_allotments (id_stk, id_offer, exchange, applied_qty, allotted_qty, allotted_amt, status, note_allot, allotment_dt)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        id_stk,
                        id_offer,
                        exchange_var.get(),
                        applied_qty,
                        allotted_qty,
                        allotted_amt,
                        status_var.get(),
                        note_allot_var.get(),
                        a_dt,
                    ),
                )
                id_allot = cursor.lastrowid

                # NEW STEP 3: Call the utility function, passing the active cursor
                process_allotment(id_allot, cursor=cursor)

                conn.commit()

            # Record session entry
            sr_no = len(current_session_ipos) + 1
            current_session_ipos[sr_no] = {
                "Company": company,
                "Offer": offer_name_var.get().strip(),
                "Price": price,
                "Applied": applied_qty,
                "Allotted": allotted_qty,
                "Amount": allotted_amt,
            }

            compute_avg_price(id_stk)

            # Prompt user to add another entry
            show_colorful_info(
                ipo_win,
                "Success",
                f"IPO/FPO recorded successfully for {company}.",
            )
            response = show_colorful_yesno(
                ipo_win,
                "🔄 Add Another IPO?",
                "Do you want to add another IPO entry?",
            )
            if response:
                reset_form_for_new_ipo()
            else:
                _close_ipo()

        except sqlite3.Error as e:
            logger.error("Database error saving IPO: %s", e)
            show_colorful_error(
                ipo_win, "Database Error", f"Failed to save record: {e}"
            )

    def _close_ipo(_event=None):
        if _event and hasattr(_event, "widget") and _event.widget:
            try:
                if _event.widget.winfo_toplevel() != ipo_win:
                    return
            except tk.TclError:
                pass

        try:
            enable_parent(modal_id)
            safe_close_modal(ipo_win, parent)
        except tk.TclError:
            pass

    # Optional logic to trigger button submission if Enter is pressed while focused
    def _on_enter(_event=None) -> None:
        focused_widget = ipo_win.focus_get()
        if focused_widget in (save_btn, cancel_btn):
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

    # ==========================================
    # UI LAYOUT & FRAMES
    # ==========================================

    # Header
    header_frame = tk.Frame(ipo_win, bg=headbg, relief="raised", bd=3)
    header_frame.pack(fill="x", padx=5, pady=0)
    tk.Label(
        header_frame,
        text="💼 PRIMARY MARKET ENTRY 💼",
        font=("Comic Sans MS", 18, "bold"),
        bg=headbg,
        fg=titlefg,
        pady=8,
        relief="ridge",
        bd=2,
    ).pack(fill="x")

    # Main wrapper frame
    main_frame = tk.Frame(
        ipo_win, bg=mainfrbg, padx=15, pady=10, relief="raised", bd=2
    )
    main_frame.pack(fill="both", expand=True, padx=10, pady=10)

    # 1. Company & Exchange Frame
    comp_frame = tk.Frame(
        main_frame, bg=compfrbg, relief="groove", bd=2, padx=10, pady=10
    )
    comp_frame.pack(fill="x", pady=(0, 10))

    tk.Label(
        comp_frame, text="Company", bg=compfrbg, font=("Helvetica", 13, "bold")
    ).pack(side="left", padx=(5, 5))
    # Matched width=38 to trade_add.py
    company_combo = ttk.Combobox(
        comp_frame,
        textvariable=company_name_var,
        values=companies,
        width=38,
        font=("Helvetica", 13),
    )
    company_combo.pack(side="left", padx=(0, 20))
    progressive_selection(company_combo, companies)
    company_combo.bind("<FocusOut>", on_company_focus_out, add="+")

    tk.Label(
        comp_frame,
        text="Exchange",
        bg=compfrbg,
        font=("Helvetica", 13, "bold"),
    ).pack(side="left", padx=(10, 5))
    radio_nse = tk.Radiobutton(
        comp_frame,
        text="NSE",
        variable=exchange_var,
        value="NSE",
        bg=compfrbg,
        font=("Helvetica", 12),
    )
    radio_nse.pack(side="left")
    radio_bse = tk.Radiobutton(
        comp_frame,
        text="BSE",
        variable=exchange_var,
        value="BSE",
        bg=compfrbg,
        font=("Helvetica", 12),
    )
    radio_bse.pack(side="left")

    # 2. Offer Details Frame
    offer_frame = tk.Frame(
        main_frame, bg=appfrbg, relief="groove", bd=2, padx=10, pady=10
    )
    offer_frame.pack(fill="x", pady=(0, 10))

    tk.Label(
        offer_frame,
        text="Offer Name",
        bg=appfrbg,
        font=("Helvetica", 13, "bold"),
    ).pack(side="left", padx=(5, 5))
    offer_name_entry = tk.Entry(
        offer_frame,
        textvariable=offer_name_var,
        width=25,
        font=("Helvetica", 13),
    )
    offer_name_entry.pack(side="left", padx=(0, 30))

    tk.Label(
        offer_frame, text="Type", bg=appfrbg, font=("Helvetica", 13, "bold")
    ).pack(side="left", padx=(5, 5))
    issue_type_combo = ttk.Combobox(
        offer_frame,
        textvariable=issue_type_var,
        values=["IPO", "FPO", "SME IPO", "OFS"],
        width=10,
        state="readonly",
        font=("Helvetica", 13),
    )
    issue_type_combo.pack(side="left", padx=(0, 30))

    tk.Label(
        offer_frame,
        text="App Status",
        bg=appfrbg,
        font=("Helvetica", 13, "bold"),
    ).pack(side="left", padx=(5, 5))
    status_combo = ttk.Combobox(
        offer_frame,
        textvariable=status_var,
        values=["APPLIED", "ALLOTTED", "REJECTED", "REFUNDED"],
        state="readonly",
        width=15,
        font=("Helvetica", 13),
    )
    status_combo.pack(side="left")

    # 3. Dates Frames
    date_frame1 = tk.Frame(
        main_frame, bg=datefrbg, relief="ridge", bd=2, padx=10, pady=10
    )
    date_frame1.pack(fill="x", pady=(0, 5))

    tk.Label(
        date_frame1,
        text="Announcement Dt",
        bg=datefrbg,
        font=("Helvetica", 13, "bold"),
    ).pack(side="left", padx=(5, 5))
    ann_dt_entry = DateEntry(
        date_frame1,
        date_pattern="dd-mm-yyyy",
        font=("Helvetica", 13),
        width=10,
    )
    ann_dt_entry.set_date(date(1900, 1, 1))
    ann_dt_entry.pack(side="left", padx=(0, 25))

    # Matched width=10 to DateEntry fields in trade_add.py
    tk.Label(
        date_frame1,
        text="Open Dt",
        bg=datefrbg,
        font=("Helvetica", 13, "bold"),
    ).pack(side="left", padx=(5, 5))
    open_dt_entry = DateEntry(
        date_frame1,
        date_pattern="dd-mm-yyyy",
        font=("Helvetica", 13),
        width=10,
    )
    open_dt_entry.pack(side="left", padx=(0, 25))
    open_dt_entry.bind("<<DateEntrySelected>>", _update_subsequent_dates)
    open_dt_entry.bind("<FocusOut>", _update_subsequent_dates, add="+")

    tk.Label(
        date_frame1,
        text="Close Dt",
        bg=datefrbg,
        font=("Helvetica", 13, "bold"),
    ).pack(side="left", padx=(5, 5))
    close_dt_entry = DateEntry(
        date_frame1,
        date_pattern="dd-mm-yyyy",
        font=("Helvetica", 13),
        width=10,
    )
    close_dt_entry.pack(side="left")

    date_frame2 = tk.Frame(
        main_frame, bg=datefrbg, relief="ridge", bd=2, padx=10, pady=10
    )
    date_frame2.pack(fill="x", pady=(0, 10))

    tk.Label(
        date_frame2,
        text="Allotment Dt",
        bg=datefrbg,
        font=("Helvetica", 13, "bold"),
    ).pack(side="left", padx=(5, 5))
    allotment_dt_entry = DateEntry(
        date_frame2,
        date_pattern="dd-mm-yyyy",
        font=("Helvetica", 13),
        width=10,
    )
    allotment_dt_entry.pack(side="left", padx=(0, 25))

    tk.Label(
        date_frame2,
        text="Listing Dt",
        bg=datefrbg,
        font=("Helvetica", 13, "bold"),
    ).pack(side="left", padx=(5, 5))
    listing_dt_entry = DateEntry(
        date_frame2,
        date_pattern="dd-mm-yyyy",
        font=("Helvetica", 13),
        width=10,
    )
    listing_dt_entry.pack(side="left")

    bind_date_spin(ann_dt_entry)
    bind_date_spin(open_dt_entry, callback=_update_subsequent_dates)
    bind_date_spin(close_dt_entry)
    bind_date_spin(allotment_dt_entry)
    bind_date_spin(listing_dt_entry)

    # 4. Pricing & Quantities Frame
    qty_frame = tk.Frame(
        main_frame, bg=allotfrbg, relief="ridge", bd=2, padx=10, pady=10
    )
    qty_frame.pack(fill="x", pady=(0, 10))

    tk.Label(
        qty_frame,
        text="Issue Price",
        bg=allotfrbg,
        font=("Helvetica", 13, "bold"),
    ).pack(side="left", padx=(5, 5))
    issue_price_entry = tk.Entry(
        qty_frame,
        textvariable=issue_price_var,
        width=10,
        font=("Helvetica", 13),
    )
    issue_price_entry.pack(side="left", padx=(0, 25))
    issue_price_entry.bind("<KeyRelease>", _calculate_allotted_amount)
    issue_price_entry.bind("<FocusOut>", validate_positive_numeric, add="+")

    # Matched width=6 to qty spinboxes in trade_add.py
    tk.Label(
        qty_frame,
        text="Applied Qty",
        bg=allotfrbg,
        font=("Helvetica", 13, "bold"),
    ).pack(side="left", padx=(5, 5))
    applied_qty_entry = tk.Spinbox(
        qty_frame,
        from_=0,
        to=999999,
        textvariable=applied_qty_var,
        width=6,
        font=("Helvetica", 13),
    )
    applied_qty_entry.pack(side="left", padx=(0, 25))
    applied_qty_entry.bind("<FocusOut>", validate_positive_numeric, add="+")

    tk.Label(
        qty_frame,
        text="Allotted Qty",
        bg=allotfrbg,
        font=("Helvetica", 13, "bold"),
    ).pack(side="left", padx=(5, 5))
    allotted_qty_entry = tk.Spinbox(
        qty_frame,
        from_=0,
        to=999999,
        textvariable=allotted_qty_var,
        width=6,
        font=("Helvetica", 13),
    )
    allotted_qty_entry.pack(side="left", padx=(0, 25))
    allotted_qty_entry.bind("<KeyRelease>", _calculate_allotted_amount)
    allotted_qty_entry.bind("<FocusOut>", validate_positive_numeric, add="+")

    tk.Label(
        qty_frame,
        text="Allotted Amt",
        bg=allotfrbg,
        font=("Helvetica", 13, "bold"),
    ).pack(side="left", padx=(5, 5))
    allotted_amt_entry = tk.Entry(
        qty_frame,
        textvariable=allotted_amt_var,
        width=12,
        font=("Helvetica", 13),
        state="readonly",
    )
    allotted_amt_entry.pack(side="left")

    # 5. Notes Frame
    note_frame = tk.Frame(
        main_frame, bg=notefrbg, relief="ridge", bd=2, padx=10, pady=10
    )
    note_frame.pack(fill="x", pady=(0, 10))

    tk.Label(
        note_frame,
        text="Notes / Remarks",
        bg=notefrbg,
        font=("Helvetica", 13, "bold"),
    ).pack(side="left", padx=(5, 5))
    notes_entry = tk.Entry(
        note_frame,
        textvariable=note_allot_var,
        width=70,
        font=("Helvetica", 13),
    )
    notes_entry.pack(side="left", padx=(0, 10))

    # --- Apply Global Styles & Hovers ---
    theme_widgets = {
        "company_combo": company_combo,
        "offer_name_entry": offer_name_entry,
        "issue_type_combo": issue_type_combo,
        "status_combo": status_combo,
        "ann_dt_entry": ann_dt_entry,
        "open_dt_entry": open_dt_entry,
        "close_dt_entry": close_dt_entry,
        "allotment_dt_entry": allotment_dt_entry,
        "listing_dt_entry": listing_dt_entry,
        "issue_price_entry": issue_price_entry,
        "applied_qty_entry": applied_qty_entry,
        "allotted_qty_entry": allotted_qty_entry,
        "allotted_amt_entry": allotted_amt_entry,
        "notes_entry": notes_entry,
    }

    for key, widget in theme_widgets.items():
        is_ro = key in [
            "allotted_amt_entry",
            "status_combo",
            "issue_type_combo",
        ]
        apply_entry_theme(widget, is_readonly=is_ro)

    for w in [
        offer_name_entry,
        issue_price_entry,
        applied_qty_entry,
        allotted_qty_entry,
        notes_entry,
    ]:
        bind_entry_hover(w)

    # --- Buttons Frame ---
    btn_frame = tk.Frame(ipo_win, pady=10, bg=btnfrbg, relief="ridge", bd=2)
    btn_frame.pack(fill="x", anchor="e", padx=10, pady=(0, 10))

    hint_label = tk.Label(
        btn_frame,
        text="Press F1 for help, F2 for session entries, or Esc to close.",
        font=("Helvetica", 15, "italic"),
        bg=btnfrbg,
        fg="#BF2525",
    )
    hint_label.pack(side="left", padx=10)

    save_btn = tk.Button(
        btn_frame,
        text="🚀 Save Entry 🚀",
        command=_on_submit,
        font=("Comic Sans MS", 12, "bold"),
        bg=submitusualbg,
        fg="white",
        activebackground=submitactivebg,
        activeforeground="white",
        width=16,
        cursor="hand2",
    )
    save_btn.pack(side="right", padx=10)

    cancel_btn = tk.Button(
        btn_frame,
        text="❌ Cancel ❌",
        command=_close_ipo,
        font=("Comic Sans MS", 12, "bold"),
        bg=cancelusualbg,
        fg="white",
        width=12,
        cursor="hand2",
    )
    cancel_btn.pack(side="right", padx=5)

    apply_button_animations(save_btn, submitusualbg, "#2563eb")
    apply_button_animations(cancel_btn, cancelusualbg, cancelactivebg)

    # --- Tooltip Bindings ---
    bind_tooltip(
        company_combo,
        tooltip_var,
        "Choose the company applying for the primary market offer.",
    )
    bind_tooltip(offer_name_entry, tooltip_var, "E.g., 'Hyundai IPO 2024'.")
    bind_tooltip(
        issue_type_combo,
        tooltip_var,
        "Select whether this is an IPO, FPO, or SME IPO.",
    )
    bind_tooltip(
        radio_nse,
        tooltip_var,
        "Select the exchange where the issue will be listed.",
    )
    bind_tooltip(
        radio_bse,
        tooltip_var,
        "Select the exchange where the issue will be listed.",
    )
    bind_tooltip(
        issue_price_entry,
        tooltip_var,
        "The final per-share price of the issue.",
    )
    bind_tooltip(
        ann_dt_entry,
        tooltip_var,
        "Announcement date for the offer. Defaults to 01-01-1900.",
    )
    bind_tooltip(
        open_dt_entry,
        tooltip_var,
        "Selecting an Open Date will auto-estimate the subsequent dates.",
    )
    bind_tooltip(close_dt_entry, tooltip_var, "The date the bidding closes.")
    bind_tooltip(
        allotment_dt_entry,
        tooltip_var,
        "The date shares are credited to your demat account.",
    )
    bind_tooltip(
        listing_dt_entry,
        tooltip_var,
        "The date the shares start trading on the exchange.",
    )
    bind_tooltip(
        applied_qty_entry,
        tooltip_var,
        "The total number of shares you bid for.",
    )
    bind_tooltip(
        status_combo, tooltip_var, "Current status of your application."
    )
    bind_tooltip(
        allotted_qty_entry,
        tooltip_var,
        "The exact number of shares credited to you.",
    )
    bind_tooltip(
        allotted_amt_entry,
        tooltip_var,
        "Auto-calculated based on Allotted Qty and Issue Price.",
    )
    bind_tooltip(
        notes_entry,
        tooltip_var,
        "Any extra remarks about this IPO application.",
    )

    # Global Hotkeys
    ipo_win.bind("<Escape>", _close_ipo)
    ipo_win.bind("<F1>", show_help)
    ipo_win.bind("<F2>", show_session_ipos)
    ipo_win.bind(
        "<Return>",
        lambda e: on_enter_focus_next(e, ipo_win, save_btn, cancel_btn),
    )
    ipo_win.protocol("WM_DELETE_WINDOW", _close_ipo)

    # Set Initial Focus
    company_combo.focus_set()

    parent.wait_window(ipo_win)
    try:
        if parent.winfo_exists():
            parent.grab_set()
    except tk.TclError:
        pass
