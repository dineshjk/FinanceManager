# -*- coding: utf-8 -*-
# File: C:\Data\Personal\Finance_and_Investment\finprog\FinanceManager\StockMan\rights.py


"""
This module handles the management of Rights Issues within the stock portfolio.
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
from .company_add import add_company
from .company_ex_import import export_company
from .trade_utils import compute_avg_price, process_allotment
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


def rights(
    parent: Union[tk.Toplevel, tk.Tk], calling_button: tk.Widget | None = None
) -> None:
    """
    Opens a modal window for Rights Issue data entry and saves it to the database.
    """

    # --- Distinct Color Theme Variables (Warm/Sunset Theme) ---
    winbg = "#fff7ed"  # Orange 50
    headbg = "#9a3412"  # Orange 800
    titlefg = "#fef08a"  # Yellow 200
    mainfrbg = "#fdba74"  # Orange 300
    compfrbg = "#ffedd5"  # Orange 100
    appfrbg = "#fef9c3"  # Yellow 100
    datefrbg = "#ccfbf1"  # Teal 100
    allotfrbg = "#fee2e2"  # Red 100
    notefrbg = "#f3f4f6"  # Gray 100
    btnfrbg = "#fffbeb"  # Amber 50
    submitusualbg = "#ea580c"  # Orange 600
    submitactivebg = "#c2410c"  # Orange 700
    cancelusualbg = "#475569"  # Slate 600
    cancelactivebg = "#334155"  # Slate 700

    modal_id = disable_parent(parent, calling_button=calling_button)
    rights_win = tk.Toplevel(parent)
    rights_win.title("✨ Rights Issue Entry ✨")

    # Taller geometry to fit extra Right Issue fields comfortably
    rights_win.geometry("960x780")
    rights_win.resizable(False, False)
    rights_win.configure(bg=winbg)
    rights_win.transient(parent)
    rights_win.grab_set()
    push_window(rights_win, parent)

    tooltip_var = setup_footer_tooltip(
        rights_win, bg_color=mainfrbg, fg_color="#431407"
    )

    # --- Fetch Companies & Initialize Session ---
    companies = []
    company_to_id = {}
    current_session_rights = {}

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
            logger.error("Failed to fetch companies for Rights: %s", e)

        if combo_widget:
            combo_widget["values"] = companies
            progressive_selection(combo_widget, companies)

    _refresh_company_data()

    # --- UI Variables ---
    company_name_var = tk.StringVar()
    exchange_var = tk.StringVar(value="NSE")
    offer_name_var = tk.StringVar()
    ratio_var = tk.StringVar()
    issue_price_var = tk.DoubleVar()

    record_qty_var = tk.IntVar()
    entitlement_qty_var = tk.IntVar()
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
            close_dt_entry.set_date(open_date + timedelta(days=15))
            allotment_dt_entry.set_date(open_date + timedelta(days=22))
            listing_dt_entry.set_date(open_date + timedelta(days=26))
        except Exception:
            pass

    def on_company_focus_out(_event=None):
        name = company_name_var.get().strip()
        if not name:
            return
        if name not in company_to_id:
            response = show_colorful_yesno(
                rights_win,
                "Company Not Found",
                f"The company '{name}' was not found. Would you like to add it now?",
            )
            if response:
                add_company(rights_win)
                export_company(rights_win)
                _refresh_company_data(company_combo)
                company_combo.focus_set()
            else:
                show_colorful_error(
                    rights_win,
                    "Invalid Company",
                    "You cannot change the company here. Please select a valid company.",
                )
                company_combo.focus_set()
                company_combo.select_range(0, "end")

    def reset_form_for_new_rights():
        company_name_var.set("")
        offer_name_var.set("")
        ratio_var.set("")
        issue_price_var.set(0.0)
        record_qty_var.set(0)
        entitlement_qty_var.set(0)
        applied_qty_var.set(0)
        allotted_qty_var.set(0)
        allotted_amt_var.set(0.0)
        status_var.set("APPLIED")
        exchange_var.set("NSE")
        note_allot_var.set("")
        company_combo.focus_set()

    def show_session_rights(_event=None):
        if not current_session_rights:
            try:
                show_colorful_info(
                    rights_win,
                    "No Entries",
                    "No Rights Issues have been recorded in this session yet.",
                )
            except tk.TclError:
                pass
            return

        rights_win.unbind("<Escape>")

        session_entries = list(current_session_rights.items())
        idx = {"i": 0}

        viewer = tk.Toplevel(rights_win)
        viewer.title("Session Rights Viewer")
        viewer.transient(rights_win)
        viewer.grab_set()
        viewer.resizable(False, False)
        viewer.geometry("520x300")
        viewer.configure(bg=winbg)

        push_window(viewer, rights_win)
        try:
            viewer.focus_set()
        except tk.TclError:
            pass

        content = tk.Frame(viewer, bg=winbg)
        content.pack(fill="both", expand=True, padx=10, pady=10)

        left_btn = tk.Button(content, text="◀", width=3)
        left_btn.pack(side="left", padx=(10, 5), pady=6)
        right_btn = tk.Button(content, text="▶", width=3)
        right_btn.pack(side="right", padx=(5, 10), pady=6)

        info_text = tk.Text(
            content, wrap="word", height=10, bg="#f8fafc", bd=0, relief="flat"
        )
        info_text.pack(fill="both", expand=True, padx=10, pady=6)

        info_text.tag_configure(
            "label", font=("Helvetica", 11, "bold"), foreground="#9a3412"
        )
        info_text.tag_configure(
            "value", font=("Helvetica", 11), foreground="#0f172a"
        )
        info_text.tag_configure(
            "net", font=("Helvetica", 11, "bold"), foreground="#15803d"
        )
        info_text.config(state="disabled")

        status_label = tk.Label(
            content, text="", font=("Helvetica", 10, "bold"), bg=winbg
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
            info_text.insert("end", "Held Qty: ", "label")
            info_text.insert("end", f"{t.get('Held')}\n", "value")
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
            safe_close_modal(viewer, rights_win)
            rights_win.bind("<Escape>", _close_rights)
            return "break"

        viewer.bind("<Escape>", close_viewer)
        viewer.protocol("WM_DELETE_WINDOW", close_viewer)
        viewer.bind("<Return>", close_viewer)
        ok_btn_viewer = tk.Button(
            content,
            text="OK",
            width=10,
            command=close_viewer,
            bg=submitusualbg,
            fg="white",
            font=("Helvetica", 10, "bold"),
        )
        ok_btn_viewer.pack(side="bottom", pady=(0, 8))
        try:
            ok_btn_viewer.focus_set()
        except tk.TclError:
            pass
        update_view()

    def show_help(_event=None):
        help_win = tk.Toplevel(rights_win)
        help_win.transient(rights_win)
        help_win.grab_set()
        help_win.title("Help - Rights Issue Entry")
        help_win.configure(bg="#fffaf0")
        help_win.geometry("620x580")
        help_win.resizable(False, False)
        push_window(help_win, rights_win)

        header = tk.Label(
            help_win,
            text="Rights Issue Entry Help",
            font=("Helvetica", 16, "bold"),
            bg="#ea580c",
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
            "This form tracks your Rights Issue applications.\n",
            "• Company Name: Choose the company issuing the rights.",
            "• Ratio: The entitlement ratio (e.g., '1:15' means 1 share for every 15 held).",
            "• Record Date: The cutoff date to be eligible for the rights.",
            "• Record Qty (Held): The number of shares you held on the Record Date.",
            "• Entitlement Qty: The baseline number of rights shares you are offered.",
            "• Applied Qty: The total number of shares you applied for (can include extra).",
            "• Status: Select APPLIED, ALLOTTED, REJECTED, or RENOUNCED.",
            "• Allotted Amt: Automatically calculated based on Issue Price.\n",
            "Hotkeys:",
            "  F1: Show this help window.",
            "  F2: Show session entries.",
            "  Esc: Close help or close the main entry window.",
            "  Enter: Advance cursor or execute focused button.",
        ]

        text.insert("1.0", "\n".join(help_lines))
        highlights = {
            "Company Name:": "#d2691e",
            "Ratio:": "#2e8b57",
            "Record Date:": "#4682b4",
            "Record Qty (Held):": "#b22222",
            "Entitlement Qty:": "#8b008b",
            "Status:": "#2f4f4f",
            "Allotted Amt:": "#b22222",
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
            safe_close_modal(help_win, rights_win)

        btn = tk.Button(
            help_win,
            text="Close",
            command=close_help,
            font=("Helvetica", 11, "bold"),
            bg="#475569",
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
                rights_win,
                "Validation Error",
                "Please select a valid company from the list.",
            )
            return

        id_stk = company_to_id[company]
        try:
            price = float(issue_price_var.get())
            record_qty = int(record_qty_var.get())
            entitlement_qty = int(entitlement_qty_var.get())
            applied_qty = int(applied_qty_var.get())
            allotted_qty = int(allotted_qty_var.get())
            allotted_amt = float(allotted_amt_var.get())

            if (
                price < 0
                or applied_qty < 0
                or allotted_qty < 0
                or record_qty < 0
            ):
                raise ValueError("Negative values are not allowed.")
        except (ValueError, tk.TclError):
            show_colorful_error(
                rights_win,
                "Validation Error",
                "Please ensure Price and Quantities are valid positive numbers.",
            )
            return

        try:
            ann_dt = ann_dt_entry.get_date().strftime("%Y-%m-%d")
            rec_dt = record_dt_entry.get_date().strftime("%Y-%m-%d")
            o_dt = open_dt_entry.get_date().strftime("%Y-%m-%d")
            c_dt = close_dt_entry.get_date().strftime("%Y-%m-%d")
            a_dt = allotment_dt_entry.get_date().strftime("%Y-%m-%d")
            l_dt = listing_dt_entry.get_date().strftime("%Y-%m-%d")
        except Exception:
            show_colorful_error(
                rights_win, "Date Error", "Please ensure all dates are valid."
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
                        id_stk, offer_type, offer_name, ann_dt, record_dt,
                        open_dt, close_dt, allotment_dt, listing_dt,
                        issue_price, ratio
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        id_stk,
                        "RIGHTS",
                        offer_name_var.get().strip(),
                        ann_dt,
                        rec_dt,
                        o_dt,
                        c_dt,
                        a_dt,
                        l_dt,
                        price,
                        ratio_var.get().strip(),
                    ),
                )
                id_offer = cursor.lastrowid

                # 2. Insert into offer_allotments
                cursor.execute(
                    """
                    INSERT INTO offer_allotments (
                        id_stk,
                        id_offer,
                        exchange,
                        record_qty,
                        entitlement_qty,
                        applied_qty,
                        allotted_qty,
                        allotted_amt,
                        status,
                        note_allot,
                        allotment_dt
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        id_stk,
                        id_offer,
                        exchange_var.get(),
                        record_qty,
                        entitlement_qty,
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
            sr_no = len(current_session_rights) + 1
            current_session_rights[sr_no] = {
                "Company": company,
                "Offer": offer_name_var.get().strip(),
                "Price": price,
                "Held": record_qty,
                "Applied": applied_qty,
                "Allotted": allotted_qty,
                "Amount": allotted_amt,
            }

            compute_avg_price(id_stk)

            # Prompt user to add another entry
            show_colorful_info(
                rights_win,
                "Success",
                f"Rights Issue recorded successfully for {company}.",
            )
            response = show_colorful_yesno(
                rights_win,
                "🔄 Add Another Rights Issue?",
                "Do you want to add another Rights Issue entry?",
            )
            if response:
                reset_form_for_new_rights()
            else:
                _close_rights()

        except sqlite3.Error as e:
            logger.error("Database error saving Rights Issue: %s", e)
            show_colorful_error(
                rights_win, "Database Error", f"Failed to save record: {e}"
            )

    def _close_rights(_event=None):
        if _event and hasattr(_event, "widget") and _event.widget:
            try:
                if _event.widget.winfo_toplevel() != rights_win:
                    return
            except tk.TclError:
                pass

        try:
            enable_parent(modal_id)
            safe_close_modal(rights_win, parent)
        except tk.TclError:
            pass

    # ==========================================
    # UI LAYOUT & FRAMES
    # ==========================================

    # Header
    header_frame = tk.Frame(rights_win, bg=headbg, relief="raised", bd=3)
    header_frame.pack(fill="x", padx=5, pady=0)
    tk.Label(
        header_frame,
        text="💼 RIGHTS ISSUE ENTRY 💼",
        font=("Comic Sans MS", 18, "bold"),
        bg=headbg,
        fg=titlefg,
        pady=8,
        relief="ridge",
        bd=2,
    ).pack(fill="x")

    # Main wrapper frame
    main_frame = tk.Frame(
        rights_win, bg=mainfrbg, padx=15, pady=10, relief="raised", bd=2
    )
    main_frame.pack(fill="both", expand=True, padx=10, pady=10)

    # 1. Company & Exchange Frame
    comp_frame = tk.Frame(
        main_frame, bg=compfrbg, relief="groove", bd=2, padx=10, pady=10
    )
    comp_frame.pack(fill="x", pady=(0, 10))

    tk.Label(
        comp_frame,
        text="Company",
        bg=compfrbg,
        font=("Helvetica", 13, "bold"),
        fg="#431407",
    ).pack(side="left", padx=(5, 5))
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
        fg="#431407",
    ).pack(side="left", padx=(10, 5))
    radio_nse = tk.Radiobutton(
        comp_frame,
        text="NSE",
        variable=exchange_var,
        value="NSE",
        bg=compfrbg,
        font=("Helvetica", 12),
        fg="#431407",
    )
    radio_nse.pack(side="left")
    radio_bse = tk.Radiobutton(
        comp_frame,
        text="BSE",
        variable=exchange_var,
        value="BSE",
        bg=compfrbg,
        font=("Helvetica", 12),
        fg="#431407",
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
        fg="#431407",
    ).pack(side="left", padx=(5, 5))
    offer_name_entry = tk.Entry(
        offer_frame,
        textvariable=offer_name_var,
        width=25,
        font=("Helvetica", 13),
    )
    offer_name_entry.pack(side="left", padx=(0, 20))

    tk.Label(
        offer_frame,
        text="Ratio",
        bg=appfrbg,
        font=("Helvetica", 13, "bold"),
        fg="#431407",
    ).pack(side="left", padx=(5, 5))
    ratio_entry = tk.Entry(
        offer_frame,
        textvariable=ratio_var,
        width=10,
        font=("Helvetica", 13),
    )
    ratio_entry.pack(side="left", padx=(0, 20))

    tk.Label(
        offer_frame,
        text="App Status",
        bg=appfrbg,
        font=("Helvetica", 13, "bold"),
        fg="#431407",
    ).pack(side="left", padx=(5, 5))
    status_combo = ttk.Combobox(
        offer_frame,
        textvariable=status_var,
        values=["APPLIED", "ALLOTTED", "REJECTED", "RENOUNCED"],
        state="readonly",
        width=15,
        font=("Helvetica", 13),
    )
    status_combo.pack(side="left")

    # 3. Dates Frames (Split into two rows to prevent crowding)
    date_frame1 = tk.Frame(
        main_frame, bg=datefrbg, relief="ridge", bd=2, padx=10, pady=10
    )
    date_frame1.pack(fill="x", pady=(0, 5))

    tk.Label(
        date_frame1,
        text="Announcement Dt",
        bg=datefrbg,
        font=("Helvetica", 13, "bold"),
        fg="#0f766e",
    ).pack(side="left", padx=(5, 5))
    ann_dt_entry = DateEntry(
        date_frame1,
        date_pattern="dd-mm-yyyy",
        font=("Helvetica", 13),
        width=11,
    )
    ann_dt_entry.set_date(date(1900, 1, 1))
    ann_dt_entry.pack(side="left", padx=(0, 25))

    tk.Label(
        date_frame1,
        text="Record Dt",
        bg=datefrbg,
        font=("Helvetica", 13, "bold"),
        fg="#0f766e",
    ).pack(side="left", padx=(5, 5))
    record_dt_entry = DateEntry(
        date_frame1,
        date_pattern="dd-mm-yyyy",
        font=("Helvetica", 13),
        width=11,
    )
    record_dt_entry.pack(side="left", padx=(0, 25))

    tk.Label(
        date_frame1,
        text="Open Dt",
        bg=datefrbg,
        font=("Helvetica", 13, "bold"),
        fg="#0f766e",
    ).pack(side="left", padx=(5, 5))
    open_dt_entry = DateEntry(
        date_frame1,
        date_pattern="dd-mm-yyyy",
        font=("Helvetica", 13),
        width=11,
    )
    open_dt_entry.pack(side="left", padx=(0, 25))
    open_dt_entry.bind("<<DateEntrySelected>>", _update_subsequent_dates)
    open_dt_entry.bind("<FocusOut>", _update_subsequent_dates, add="+")

    tk.Label(
        date_frame1,
        text="Close Dt",
        bg=datefrbg,
        font=("Helvetica", 13, "bold"),
        fg="#0f766e",
    ).pack(side="left", padx=(5, 5))
    close_dt_entry = DateEntry(
        date_frame1,
        date_pattern="dd-mm-yyyy",
        font=("Helvetica", 13),
        width=11,
    )
    close_dt_entry.pack(side="left", padx=(0, 25))

    date_frame2 = tk.Frame(
        main_frame, bg=datefrbg, relief="ridge", bd=2, padx=10, pady=10
    )
    date_frame2.pack(fill="x", pady=(0, 10))

    tk.Label(
        date_frame2,
        text="Allotment Dt",
        bg=datefrbg,
        font=("Helvetica", 13, "bold"),
        fg="#0f766e",
    ).pack(side="left", padx=(5, 5))
    allotment_dt_entry = DateEntry(
        date_frame2,
        date_pattern="dd-mm-yyyy",
        font=("Helvetica", 13),
        width=11,
    )
    allotment_dt_entry.pack(side="left", padx=(0, 25))

    tk.Label(
        date_frame2,
        text="Listing Dt",
        bg=datefrbg,
        font=("Helvetica", 13, "bold"),
        fg="#0f766e",
    ).pack(side="left", padx=(5, 5))
    listing_dt_entry = DateEntry(
        date_frame2,
        date_pattern="dd-mm-yyyy",
        font=("Helvetica", 13),
        width=11,
    )
    listing_dt_entry.pack(side="left")

    bind_date_spin(ann_dt_entry)
    bind_date_spin(record_dt_entry)
    bind_date_spin(open_dt_entry, callback=_update_subsequent_dates)
    bind_date_spin(close_dt_entry)
    bind_date_spin(allotment_dt_entry)
    bind_date_spin(listing_dt_entry)

    # 4. Pricing & Quantities Frames (Split into two rows)
    qty_frame1 = tk.Frame(
        main_frame, bg=allotfrbg, relief="ridge", bd=2, padx=10, pady=10
    )
    qty_frame1.pack(fill="x", pady=(0, 5))

    tk.Label(
        qty_frame1,
        text="Issue Price",
        bg=allotfrbg,
        font=("Helvetica", 13, "bold"),
        fg="#991b1b",
    ).pack(side="left", padx=(5, 5))
    issue_price_entry = tk.Entry(
        qty_frame1,
        textvariable=issue_price_var,
        width=10,
        font=("Helvetica", 13),
    )
    issue_price_entry.pack(side="left", padx=(0, 25))
    issue_price_entry.bind("<KeyRelease>", _calculate_allotted_amount)
    issue_price_entry.bind("<FocusOut>", validate_positive_numeric, add="+")

    tk.Label(
        qty_frame1,
        text="Record Qty",
        bg=allotfrbg,
        font=("Helvetica", 13, "bold"),
        fg="#991b1b",
    ).pack(side="left", padx=(5, 5))
    record_qty_entry = tk.Spinbox(
        qty_frame1,
        from_=0,
        to=999999,
        textvariable=record_qty_var,
        width=8,
        font=("Helvetica", 13),
    )
    record_qty_entry.pack(side="left", padx=(0, 25))
    record_qty_entry.bind("<FocusOut>", validate_positive_numeric, add="+")

    tk.Label(
        qty_frame1,
        text="Entitlement Qty",
        bg=allotfrbg,
        font=("Helvetica", 13, "bold"),
        fg="#991b1b",
    ).pack(side="left", padx=(5, 5))
    entitlement_qty_entry = tk.Spinbox(
        qty_frame1,
        from_=0,
        to=999999,
        textvariable=entitlement_qty_var,
        width=8,
        font=("Helvetica", 13),
    )
    entitlement_qty_entry.pack(side="left", padx=(0, 25))
    entitlement_qty_entry.bind(
        "<FocusOut>", validate_positive_numeric, add="+"
    )

    qty_frame2 = tk.Frame(
        main_frame, bg=allotfrbg, relief="ridge", bd=2, padx=10, pady=10
    )
    qty_frame2.pack(fill="x", pady=(0, 10))

    tk.Label(
        qty_frame2,
        text="Applied Qty",
        bg=allotfrbg,
        font=("Helvetica", 13, "bold"),
        fg="#991b1b",
    ).pack(side="left", padx=(5, 5))
    applied_qty_entry = tk.Spinbox(
        qty_frame2,
        from_=0,
        to=999999,
        textvariable=applied_qty_var,
        width=8,
        font=("Helvetica", 13),
    )
    applied_qty_entry.pack(side="left", padx=(0, 20))
    applied_qty_entry.bind("<FocusOut>", validate_positive_numeric, add="+")

    tk.Label(
        qty_frame2,
        text="Allotted Qty",
        bg=allotfrbg,
        font=("Helvetica", 13, "bold"),
        fg="#991b1b",
    ).pack(side="left", padx=(5, 5))
    allotted_qty_entry = tk.Spinbox(
        qty_frame2,
        from_=0,
        to=999999,
        textvariable=allotted_qty_var,
        width=8,
        font=("Helvetica", 13),
    )
    allotted_qty_entry.pack(side="left", padx=(0, 20))
    allotted_qty_entry.bind("<KeyRelease>", _calculate_allotted_amount)
    allotted_qty_entry.bind("<FocusOut>", validate_positive_numeric, add="+")

    tk.Label(
        qty_frame2,
        text="Allotted Amt",
        bg=allotfrbg,
        font=("Helvetica", 13, "bold"),
        fg="#991b1b",
    ).pack(side="left", padx=(5, 5))
    allotted_amt_entry = tk.Entry(
        qty_frame2,
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
        fg="#1f2937",
    ).pack(side="left", padx=(5, 5))
    notes_entry = tk.Entry(
        note_frame,
        textvariable=note_allot_var,
        width=68,
        font=("Helvetica", 13),
    )
    notes_entry.pack(side="left", padx=(0, 10))

    # --- Apply Entry Hovers & Theme ---
    theme_widgets = {
        "company_combo": company_combo,
        "offer_name_entry": offer_name_entry,
        "ratio_entry": ratio_entry,
        "status_combo": status_combo,
        "ann_dt_entry": ann_dt_entry,
        "record_dt_entry": record_dt_entry,
        "open_dt_entry": open_dt_entry,
        "close_dt_entry": close_dt_entry,
        "allotment_dt_entry": allotment_dt_entry,
        "listing_dt_entry": listing_dt_entry,
        "issue_price_entry": issue_price_entry,
        "record_qty_entry": record_qty_entry,
        "entitlement_qty_entry": entitlement_qty_entry,
        "applied_qty_entry": applied_qty_entry,
        "allotted_qty_entry": allotted_qty_entry,
        "allotted_amt_entry": allotted_amt_entry,
        "notes_entry": notes_entry,
    }

    for key, widget in theme_widgets.items():
        is_ro = key in ["allotted_amt_entry", "status_combo"]
        apply_entry_theme(widget, is_readonly=is_ro)

    for w in [
        offer_name_entry,
        ratio_entry,
        issue_price_entry,
        record_qty_entry,
        entitlement_qty_entry,
        applied_qty_entry,
        allotted_qty_entry,
        notes_entry,
    ]:
        bind_entry_hover(w)

    # --- Buttons Frame ---
    btn_frame = tk.Frame(rights_win, pady=10, bg=btnfrbg, relief="ridge", bd=2)
    btn_frame.pack(fill="x", anchor="e", padx=10, pady=(0, 10))

    hint_label = tk.Label(
        btn_frame,
        text="Press F1 for help, F2 for session entries, or Esc to close.",
        font=("Helvetica", 15, "italic"),
        bg=btnfrbg,
        fg="#9a3412",
    )
    hint_label.pack(side="left", padx=10)

    save_btn = tk.Button(
        btn_frame,
        text="🚀 Save Entry 🚀",
        command=_on_submit,
        font=("Comic Sans MS", 12, "bold"),
        bg="#22c55e",
        fg="white",
        width=16,
        cursor="hand2",
        activebackground="#16a34a",
        activeforeground="white",
        relief="raised",
        bd=3,
    )
    save_btn.pack(side="right", padx=10)

    cancel_btn = tk.Button(
        btn_frame,
        text="❌ Cancel ❌",
        command=_close_rights,
        font=("Comic Sans MS", 12, "bold"),
        bg=cancelusualbg,
        fg="white",
        width=12,
        cursor="hand2",
        activebackground=cancelactivebg,
        activeforeground="white",
        relief="raised",
        bd=3,
    )
    cancel_btn.pack(side="right", padx=5)

    # Hover & Focus animations for buttons
    apply_button_animations(save_btn, "#22c55e", "#2563eb")
    apply_button_animations(cancel_btn, cancelusualbg, cancelactivebg)

    # --- Tooltip Bindings ---
    bind_tooltip(
        company_combo, tooltip_var, "Choose the company issuing the rights."
    )
    bind_tooltip(
        offer_name_entry, tooltip_var, "E.g., 'Reliance Rights Issue 2024'."
    )
    bind_tooltip(
        ratio_entry, tooltip_var, "The entitlement ratio (e.g., '1:15')."
    )
    bind_tooltip(
        radio_nse, tooltip_var, "Select the exchange for the rights issue."
    )
    bind_tooltip(
        radio_bse, tooltip_var, "Select the exchange for the rights issue."
    )
    bind_tooltip(
        ann_dt_entry,
        tooltip_var,
        "Announcement date for the offer. Defaults to 01-01-1900.",
    )
    bind_tooltip(
        record_dt_entry,
        tooltip_var,
        "The cutoff date to be eligible for the rights.",
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
        listing_dt_entry, tooltip_var, "The date the shares start trading."
    )
    bind_tooltip(
        issue_price_entry,
        tooltip_var,
        "The final per-share price of the issue.",
    )
    bind_tooltip(
        record_qty_entry,
        tooltip_var,
        "The number of shares you held on the Record Date.",
    )
    bind_tooltip(
        entitlement_qty_entry,
        tooltip_var,
        "The baseline number of rights shares you are offered.",
    )
    bind_tooltip(
        applied_qty_entry,
        tooltip_var,
        "The total number of shares you applied for.",
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
        status_combo, tooltip_var, "Current status of your application."
    )
    bind_tooltip(
        notes_entry, tooltip_var, "Any extra remarks about this application."
    )

    # Global Hotkeys
    rights_win.bind("<Escape>", _close_rights)
    rights_win.bind("<F1>", show_help)
    rights_win.bind("<F2>", show_session_rights)
    rights_win.bind(
        "<Return>",
        lambda e: on_enter_focus_next(e, rights_win, save_btn, cancel_btn),
    )
    rights_win.protocol("WM_DELETE_WINDOW", _close_rights)

    # Set Initial Focus
    company_combo.focus_set()

    parent.wait_window(rights_win)
    try:
        if parent.winfo_exists():
            parent.grab_set()
    except tk.TclError:
        pass


# File: C:\Data\Personal\Finance_and_Investment\finprog\FinanceManager\StockMan\rights.py ends here
