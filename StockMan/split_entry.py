# -*- coding: utf-8 -*-
# StockMan/split_entry.py

"""
This module handles the management of Stock Splits
within the stock portfolio.
"""

from typing import Union
import tkinter as tk
from tkinter import ttk
import sqlite3
from tkcalendar import DateEntry
from datetime import timedelta, datetime

from Shared.globals import get_db_connection, logger
from Shared.dialog_utils import (
    show_colorful_info,
    show_colorful_error,
    show_colorful_yesno,
)
from .trade_utils import compute_avg_price, fetch_holding_on_date
from Shared.modal_utils import disable_parent, enable_parent
from Shared.window_manager import push_window, pop_window, safe_close_modal
from Shared.gui_progressive import progressive_selection
from Shared.gui_utils import (
    bind_tooltip,
    on_enter_focus_next,
    apply_button_animations,
    apply_entry_theme,
    setup_footer_tooltip,
    bind_date_spin,
)
from Shared.validation_utils import validate_positive_numeric


def add_split_share(
    parent: Union[tk.Toplevel, tk.Tk],
    calling_button: tk.Widget | None = None,
    edit_id: int | None = None,
) -> None:
    # --- Blue/Indigo Theme for Splits ---
    winbg = "#eff6ff"  # Blue 50
    headbg = "#1e3a8a"  # Blue 900
    titlefg = "#bfdbfe"  # Blue 200
    mainfrbg = "#93c5fd"  # Blue 300
    compfrbg = "#dbeafe"  # Blue 100
    datefrbg = "#e0e7ff"  # Indigo 100
    ratiofrbg = "#c7d2fe"  # Indigo 200
    notefrbg = "#f8fafc"  # Slate 50
    btnfrbg = "#eff6ff"  # Blue 50
    submitusualbg = "#2563eb"  # Blue 600
    submitactivebg = "#1d4ed8"  # Blue 700
    cancelusualbg = "#475569"  # Slate 600
    cancelactivebg = "#334155"  # Slate 700

    modal_id = disable_parent(parent, calling_button=calling_button)
    split_win = tk.Toplevel(parent)
    split_win.title("✨ Stock Split Entry ✨")
    split_win.geometry("960x700")
    split_win.resizable(False, False)
    split_win.configure(bg=winbg)
    split_win.transient(parent)
    split_win.grab_set()
    push_window(split_win, parent)

    tooltip_var = setup_footer_tooltip(
        split_win, bg_color=winbg, fg_color=headbg
    )

    companies = []
    company_to_data = {}
    current_session_splits = {}

    def _refresh_company_data(combo_widget=None):
        companies.clear()
        company_to_data.clear()
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                # ONLY fetch active companies to prevent splitting delisted stocks
                cursor.execute(
                    "SELECT company_name, id_stk, face_value FROM stocks WHERE is_active = 1 ORDER BY company_name"
                )
                for row in cursor.fetchall():
                    companies.append(row[0])
                    company_to_data[row[0]] = {
                        "id_stk": row[1],
                        "face_value": row[2] or 10.0,
                    }
        except sqlite3.Error as e:
            logger.error("Failed to fetch companies for Split: %s", e)

        if combo_widget:
            combo_widget["values"] = companies
            progressive_selection(combo_widget, companies)

    _refresh_company_data()

    # --- UI Variables ---
    company_name_var = tk.StringVar()
    exchange_var = tk.StringVar(value="NSE")
    old_fv_var = tk.DoubleVar(value=10.0)
    new_fv_var = tk.DoubleVar(value=5.0)
    held_qty_var = tk.IntVar(value=0)
    allotted_qty_var = tk.IntVar(value=0)
    note_var = tk.StringVar()

    def _calculate_allotment(*_args):
        try:
            old_fv = float(old_fv_var.get())
            new_fv = float(new_fv_var.get())
            held = int(held_qty_var.get())

            if old_fv > 0 and new_fv > 0 and held > 0:
                ratio = old_fv / new_fv
                total_new_qty = int(held * ratio)
                allotted_qty = total_new_qty - held

                # We only support standard splits here (where old > new FV)
                if allotted_qty < 0:
                    allotted_qty = 0
                allotted_qty_var.set(allotted_qty)
            else:
                allotted_qty_var.set(0)
        except ValueError:
            allotted_qty_var.set(0)

    def _on_company_selected(*_args):
        company = company_name_var.get().strip()
        if company in company_to_data:
            current_fv = company_to_data[company]["face_value"]
            old_fv_var.set(current_fv)
            _update_holdings()

    def _update_holdings(*_args):
        company = company_name_var.get().strip()
        if company in company_to_data:
            id_stk = company_to_data[company]["id_stk"]
            try:
                rec_date_str = record_dt_entry.get_date().strftime("%Y-%m-%d")
                holding = fetch_holding_on_date(id_stk, rec_date_str)
                held_qty_var.set(holding)
                _calculate_allotment()
            except Exception:
                pass

    def _on_submit(_event=None):
        company = company_name_var.get().strip()
        if company not in company_to_data:
            show_colorful_error(
                split_win, "Validation Error", "Please select a valid company."
            )
            return

        id_stk = company_to_data[company]["id_stk"]
        current_db_fv = company_to_data[company]["face_value"]

        try:
            o_fv = float(old_fv_var.get())
            n_fv = float(new_fv_var.get())
            h_qty = int(held_qty_var.get())
            a_qty = int(allotted_qty_var.get())

            if o_fv <= n_fv:
                show_colorful_error(
                    split_win,
                    "Face Value Error",
                    "Old Face Value must be greater than New Face Value for a standard split.",
                )
                return
            if a_qty <= 0:
                show_colorful_error(
                    split_win,
                    "Quantity Error",
                    "Allotted quantity must be greater than zero.",
                )
                return

            rec_dt = record_dt_entry.get_date().strftime("%Y-%m-%d")
            ex_dt = ex_dt_entry.get_date().strftime("%Y-%m-%d")
        except ValueError:
            show_colorful_error(
                split_win,
                "Data Error",
                "Please ensure all numbers and dates are valid.",
            )
            return

        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA foreign_keys = ON;")

                # 1. Update Face Value if necessary
                if current_db_fv == o_fv:
                    cursor.execute(
                        "UPDATE stocks SET face_value = ? WHERE id_stk = ?",
                        (n_fv, id_stk),
                    )

                details = f"Split FV ₹{o_fv} to ₹{n_fv}"

                if edit_id is not None:
                    # --- UPDATE EXISTING RECORD ---
                    existing_id_act = edit_id

                    # 1. Update Master Ledger (corp_acts)
                    cursor.execute(
                        """
                        UPDATE corp_acts
                        SET act_dt = ?, details_act = ?, ratio_old = ?, ratio_new = ?, note_act = ?
                        WHERE id_act = ?
                        """,
                        (
                            rec_dt,
                            details,
                            int(o_fv),
                            int(n_fv),
                            note_var.get().strip(),
                            existing_id_act,
                        ),
                    )

                    # Get existing split record to update downstream tables
                    cursor.execute(
                        "SELECT id_split, id_trd, record_dt FROM splits WHERE id_act = ?",
                        (existing_id_act,),
                    )
                    row = cursor.fetchone()

                    if not row:
                        # Fallback for unlinked older data
                        cursor.execute(
                            "SELECT act_dt FROM corp_acts WHERE id_act = ?",
                            (existing_id_act,),
                        )
                        act_dt_row = cursor.fetchone()
                        act_dt = act_dt_row[0] if act_dt_row else rec_dt
                        cursor.execute(
                            "SELECT id_split, id_trd, record_dt FROM splits WHERE id_stk = ? AND record_dt = ?",
                            (id_stk, act_dt),
                        )
                        row = cursor.fetchone()

                    if row:
                        existing_id_split = row[0]
                        existing_id_trd = row[1]
                        cont_no = f"SPLIT_{existing_id_split}"

                        # 2. Update Transactions
                        cursor.execute(
                            "UPDATE contracts SET trd_dt = ?, settle_dt = ? WHERE cont_no = ?",
                            (rec_dt, rec_dt, cont_no),
                        )

                        cursor.execute(
                            """
                            UPDATE transactions
                            SET trd_dt = ?, qty_trd = ?, note_trd = ?
                            WHERE cont_no = ?
                            """,
                            (rec_dt, a_qty, details, cont_no),
                        )

                        if not existing_id_trd:
                            cursor.execute(
                                "SELECT id_trd FROM transactions WHERE cont_no = ?",
                                (cont_no,),
                            )
                            trd_row = cursor.fetchone()
                            if trd_row:
                                existing_id_trd = trd_row[0]

                        # 3. Update Splits Table
                        cursor.execute(
                            """
                            UPDATE splits
                            SET id_act = ?, id_trd = ?, ex_dt = ?, record_dt = ?, old_fv = ?, new_fv = ?, old_qty = ?, new_allotted_qty = ?, note_split = ?
                            WHERE id_split = ?
                            """,
                            (
                                existing_id_act,
                                existing_id_trd,
                                ex_dt,
                                rec_dt,
                                o_fv,
                                n_fv,
                                h_qty,
                                a_qty,
                                note_var.get().strip(),
                                existing_id_split,
                            ),
                        )

                else:
                    # --- INSERT NEW RECORD ---
                    # 1. Master Ledger (Get id_act)
                    cursor.execute(
                        """
                        INSERT INTO corp_acts (id_stk, act_dt, type_act, details_act, ratio_old, ratio_new, note_act)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            id_stk,
                            rec_dt,
                            "SPLIT",
                            details,
                            int(o_fv),
                            int(n_fv),
                            note_var.get().strip(),
                        ),
                    )
                    id_act = cursor.lastrowid

                    # 2. Splits Table (Insert with id_act, get id_split)
                    cursor.execute(
                        """
                        INSERT INTO splits (id_act, id_stk, ex_dt, record_dt, old_fv, new_fv, old_qty, new_allotted_qty, note_split)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            id_act,
                            id_stk,
                            ex_dt,
                            rec_dt,
                            o_fv,
                            n_fv,
                            h_qty,
                            a_qty,
                            note_var.get().strip(),
                        ),
                    )
                    id_split = cursor.lastrowid

                    cont_no = f"SPLIT_{id_split}"
                    settle_no = int(f"444{id_split}")

                    # 3. Transactions (Get id_trd)
                    cursor.execute(
                        """
                        INSERT INTO contracts (cont_no, trd_dt, settle_no, settle_dt, no_of_trades, net_amt_cont, net_amt_cont_applicable)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (cont_no, rec_dt, settle_no, rec_dt, 1, 0.0, 0.0),
                    )

                    cursor.execute(
                        """
                        INSERT INTO transactions (
                            id_stk, cont_no, trd_dt, company_name, trade_type_trd, exchange,
                            qty_trd, wap_unit_trd, price_lot_trd, net_amt_trd, net_amt_trd_applicable, note_trd
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            id_stk,
                            cont_no,
                            rec_dt,
                            company,
                            "BUY",
                            exchange_var.get(),
                            a_qty,
                            0.0,
                            0.0,
                            0.0,
                            0.0,
                            details,
                        ),
                    )
                    id_trd = cursor.lastrowid

                    # 4. Final Link: Update splits with the new id_trd
                    cursor.execute(
                        "UPDATE splits SET id_trd = ? WHERE id_split = ?",
                        (id_trd, id_split),
                    )

                conn.commit()

            compute_avg_price(id_stk)

            # Prompt user based on execution type
            if edit_id is not None:
                show_colorful_info(
                    split_win,
                    "Update Success",
                    f"Stock Split updated successfully for {company}.",
                )
                close_split()
            else:
                response = show_colorful_yesno(
                    split_win,
                    "Success",
                    f"Stock Split recorded successfully for {company}.\n\nDo you want to add another split?",
                )

                if response:
                    # Reset Form
                    company_name_var.set("")
                    old_fv_var.set(10.0)
                    new_fv_var.set(5.0)
                    held_qty_var.set(0)
                    allotted_qty_var.set(0)
                    note_var.set("")
                    company_combo.focus_set()
                else:
                    close_split()

        except sqlite3.Error as e:
            logger.error("Database error saving Split: %s", e)
            show_colorful_error(
                split_win, "Database Error", f"Failed to save record: {e}"
            )

    def close_split(_event=None):
        return safe_close_modal(split_win, parent, calling_button)

    # --- UI LAYOUT ---
    header_frame = tk.Frame(split_win, bg=headbg, relief="raised", bd=3)
    header_frame.pack(fill="x", padx=5, pady=0)
    tk.Label(
        header_frame,
        text="✂️ STOCK SPLIT ENTRY ✂️",
        font=("Comic Sans MS", 18, "bold"),
        bg=headbg,
        fg=titlefg,
        pady=8,
    ).pack(fill="x")

    main_frame = tk.Frame(
        split_win, bg=mainfrbg, padx=15, pady=10, relief="raised", bd=2
    )
    main_frame.pack(fill="both", expand=True, padx=10, pady=10)

    # 1. Company Frame
    comp_frame = tk.Frame(
        main_frame, bg=compfrbg, relief="groove", bd=2, padx=10, pady=10
    )
    comp_frame.pack(fill="x", pady=(0, 10))
    tk.Label(
        comp_frame,
        text="Company",
        bg=compfrbg,
        font=("Helvetica", 13, "bold"),
        fg=headbg,
    ).pack(side="left", padx=5)

    company_combo = ttk.Combobox(
        comp_frame,
        textvariable=company_name_var,
        values=companies,
        width=38,
        font=("Helvetica", 13),
    )
    company_combo.pack(side="left", padx=15)
    progressive_selection(company_combo, companies)
    company_name_var.trace_add("write", _on_company_selected)

    tk.Label(
        comp_frame,
        text="Exchange",
        bg=compfrbg,
        font=("Helvetica", 13, "bold"),
        fg=headbg,
    ).pack(side="left", padx=(15, 5))
    tk.Radiobutton(
        comp_frame,
        text="NSE",
        variable=exchange_var,
        value="NSE",
        bg=compfrbg,
        font=("Helvetica", 12),
    ).pack(side="left")
    tk.Radiobutton(
        comp_frame,
        text="BSE",
        variable=exchange_var,
        value="BSE",
        bg=compfrbg,
        font=("Helvetica", 12),
    ).pack(side="left")

    # 2. Dates Frame
    date_frame = tk.Frame(
        main_frame, bg=datefrbg, relief="ridge", bd=2, padx=10, pady=15
    )
    date_frame.pack(fill="x", pady=(0, 10))

    tk.Label(
        date_frame,
        text="Record Date",
        bg=datefrbg,
        font=("Helvetica", 13, "bold"),
        fg=headbg,
    ).pack(side="left", padx=5)
    record_dt_entry = DateEntry(
        date_frame, date_pattern="dd-mm-yyyy", font=("Helvetica", 13), width=12
    )
    record_dt_entry.pack(side="left", padx=(0, 30))
    record_dt_entry.bind("<<DateEntrySelected>>", _update_holdings)
    record_dt_entry.bind("<FocusOut>", _update_holdings, add="+")

    tk.Label(
        date_frame,
        text="Ex-Date",
        bg=datefrbg,
        font=("Helvetica", 13, "bold"),
        fg=headbg,
    ).pack(side="left", padx=5)
    ex_dt_entry = DateEntry(
        date_frame, date_pattern="dd-mm-yyyy", font=("Helvetica", 13), width=12
    )
    ex_dt_entry.pack(side="left", padx=5)

    bind_date_spin(record_dt_entry, callback=_update_holdings)
    bind_date_spin(ex_dt_entry)

    # 3. FV and Quantities Frame
    calc_frame = tk.Frame(
        main_frame, bg=ratiofrbg, relief="ridge", bd=2, padx=10, pady=15
    )
    calc_frame.pack(fill="x", pady=(0, 10))

    c_top = tk.Frame(calc_frame, bg=ratiofrbg)
    c_top.pack(fill="x", pady=(0, 15))
    tk.Label(
        c_top,
        text="Old Face Value (₹)",
        bg=ratiofrbg,
        font=("Helvetica", 13, "bold"),
        fg="#1e3a8a",
    ).pack(side="left", padx=5)
    old_fv_entry = tk.Entry(
        c_top, textvariable=old_fv_var, width=10, font=("Helvetica", 13)
    )
    old_fv_entry.pack(side="left", padx=(0, 30))

    tk.Label(
        c_top,
        text="New Face Value (₹)",
        bg=ratiofrbg,
        font=("Helvetica", 13, "bold"),
        fg="#1e3a8a",
    ).pack(side="left", padx=5)
    new_fv_entry = tk.Entry(
        c_top, textvariable=new_fv_var, width=10, font=("Helvetica", 13)
    )
    new_fv_entry.pack(side="left", padx=5)

    c_bot = tk.Frame(calc_frame, bg=ratiofrbg)
    c_bot.pack(fill="x")
    tk.Label(
        c_bot,
        text="Held Qty (Record Dt)",
        bg=ratiofrbg,
        font=("Helvetica", 13, "bold"),
        fg="#047857",
    ).pack(side="left", padx=5)
    held_qty_entry = tk.Entry(
        c_bot, textvariable=held_qty_var, width=12, font=("Helvetica", 13)
    )
    held_qty_entry.pack(side="left", padx=(0, 20))

    tk.Label(
        c_bot,
        text="New Allotted Shares",
        bg=ratiofrbg,
        font=("Helvetica", 13, "bold"),
        fg="#b91c1c",
    ).pack(side="left", padx=5)
    allotted_qty_entry = tk.Entry(
        c_bot,
        textvariable=allotted_qty_var,
        width=14,
        font=("Helvetica", 13, "bold"),
        state="readonly",
    )
    allotted_qty_entry.pack(side="left", padx=5)

    old_fv_entry.bind("<KeyRelease>", _calculate_allotment)
    new_fv_entry.bind("<KeyRelease>", _calculate_allotment)
    held_qty_entry.bind("<KeyRelease>", _calculate_allotment)

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
    ).pack(side="left", padx=5)
    note_entry = tk.Entry(
        note_frame, textvariable=note_var, width=68, font=("Helvetica", 13)
    )
    note_entry.pack(side="left", padx=10)

    # --- Apply Global Styles & Entry Hovers ---
    entries = {
        "company_combo": company_combo,
        "record_dt_entry": record_dt_entry,
        "ex_dt_entry": ex_dt_entry,
        "old_fv_entry": old_fv_entry,
        "new_fv_entry": new_fv_entry,
        "held_qty_entry": held_qty_entry,
        "allotted_qty_entry": allotted_qty_entry,
        "notes_entry": note_entry,
    }

    for key, widget in entries.items():
        is_ro = key == "allotted_qty_entry"
        apply_entry_theme(widget, is_readonly=is_ro)

    # --- Tooltip Bindings ---
    bind_tooltip(
        company_combo,
        tooltip_var,
        "Select the company undergoing the stock split.",
    )
    bind_tooltip(
        record_dt_entry,
        tooltip_var,
        "The date set by the company to determine eligible shareholders.",
    )
    bind_tooltip(
        ex_dt_entry,
        tooltip_var,
        "The date the stock starts trading at the new split-adjusted price.",
    )
    bind_tooltip(
        old_fv_entry,
        tooltip_var,
        "The face value of the stock before the split.",
    )
    bind_tooltip(
        new_fv_entry,
        tooltip_var,
        "The new face value of the stock after the split.",
    )
    bind_tooltip(
        held_qty_entry,
        tooltip_var,
        "The number of shares held on the Record Date (calculated automatically).",
    )
    bind_tooltip(
        allotted_qty_entry,
        tooltip_var,
        "The additional shares you will receive due to the split.",
    )
    bind_tooltip(
        note_entry,
        tooltip_var,
        "Any personal notes or remarks regarding this corporate action.",
    )

    # --- Buttons Frame ---
    btn_frame = tk.Frame(split_win, pady=10, bg=btnfrbg, relief="ridge", bd=2)
    btn_frame.pack(fill="x", anchor="e", padx=10, pady=(0, 10))

    save_btn = tk.Button(
        btn_frame,
        text="🚀 Save Entry 🚀",
        command=_on_submit,
        font=("Comic Sans MS", 12, "bold"),
        bg="#22c55e",
        activebackground="#16a34a",
        activeforeground="white",
        fg="white",
        width=16,
        cursor="hand2",
    )
    save_btn.pack(side="right", padx=10)

    cancel_btn = tk.Button(
        btn_frame,
        text="❌ Cancel ❌",
        command=close_split,
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

    # Enter key execution is now handled globally on the window via on_enter_focus_next

    split_win.bind(
        "<Return>",
        lambda e: on_enter_focus_next(e, split_win, save_btn, cancel_btn),
    )
    split_win.bind("<Escape>", close_split)
    split_win.protocol("WM_DELETE_WINDOW", close_split)
    company_combo.focus_set()

    # --- UPDATE ENGINE: PRE-FILL DATA ---
    if edit_id is not None:
        split_win.title("✨ Update Stock Split ✨")
        save_btn.config(text="🚀 Update Entry 🚀")
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT s.company_name, sp.record_dt, sp.old_fv, sp.new_fv, sp.note_split, sp.ex_dt
                    FROM splits sp
                    JOIN stocks s ON sp.id_stk = s.id_stk
                    WHERE sp.id_act = ?
                    """,
                    (edit_id,),
                )
                row = cursor.fetchone()

                if not row:
                    # Fallback for unlinked historical data
                    cursor.execute(
                        """
                        SELECT s.company_name, sp.record_dt, sp.old_fv, sp.new_fv, sp.note_split, sp.ex_dt
                        FROM corp_acts c
                        JOIN splits sp ON c.id_stk = sp.id_stk AND c.act_dt = sp.record_dt
                        JOIN stocks s ON c.id_stk = s.id_stk
                        WHERE c.id_act = ? AND c.type_act = 'SPLIT'
                        """,
                        (edit_id,),
                    )
                    row = cursor.fetchone()

            if row:
                company_name_var.set(row[0])
                company_combo.config(state="disabled")  # Lock company

                try:
                    rec_dt_obj = datetime.strptime(row[1], "%Y-%m-%d").date()
                    record_dt_entry.set_date(rec_dt_obj)
                except ValueError:
                    pass

                old_fv_var.set(row[2])
                new_fv_var.set(row[3])
                note_var.set(row[4] if row[4] else "")

                if row[5]:
                    try:
                        ex_dt_obj = datetime.strptime(
                            row[5], "%Y-%m-%d"
                        ).date()
                        ex_dt_entry.set_date(ex_dt_obj)
                    except ValueError:
                        pass

                _update_holdings()

        except sqlite3.Error as e:
            logger.error(f"Failed to fetch split data: {e}")

    parent.wait_window(split_win)
    try:
        if parent.winfo_exists():
            parent.grab_set()
    except tk.TclError:
        pass
