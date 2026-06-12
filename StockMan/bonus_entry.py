# -*- coding: utf-8 -*-
# StockMan/bonus_entry.py

"""
This module handles the management of Bonus Share corporate actions
within the stock portfolio.
"""

from typing import Union
import tkinter as tk
from tkinter import ttk
import sqlite3
from tkcalendar import DateEntry
from datetime import timedelta, datetime

# Local project imports
from Shared.globals import get_db_connection, logger, MSG
from Shared.dialog_utils import (
    show_colorful_info,
    show_colorful_error,
    show_colorful_yesno,
)
from .company_add import add_company
from .company_ex_import import export_company
from .trade_utils import compute_avg_price, fetch_holding_on_date
from Shared.modal_utils import disable_parent
from Shared.window_manager import push_window, safe_close_modal
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


def bonus_shares(
    parent: Union[tk.Toplevel, tk.Tk],
    calling_button: tk.Widget | None = None,
    edit_id: int | None = None,
) -> None:
    """
    Opens a modal window for Bonus Shares data entry and saves it to the database.
    """

    # --- Distinct Color Theme Variables (Wealth/Growth Theme) ---
    # We keep the frame colors local to maintain the distinct visual identity of the Bonus window
    winbg = "#f0fdf4"  # Green 50
    headbg = "#064e3b"  # Emerald 900
    titlefg = "#fef08a"  # Yellow 200 (Gold)
    mainfrbg = "#6ee7b7"  # Emerald 300
    compfrbg = "#ecfdf5"  # Emerald 50
    datefrbg = "#d1fae5"  # Emerald 100
    ratiofrbg = "#a7f3d0"  # Emerald 200
    notefrbg = "#f8fafc"  # Slate 50
    btnfrbg = "#f0fdfa"  # Teal 50
    submitusualbg = "#059669"  # Emerald 600
    submitactivebg = "#047857"  # Emerald 700
    cancelusualbg = "#475569"  # Slate 600
    cancelactivebg = "#334155"  # Slate 700

    modal_id = disable_parent(parent, calling_button=calling_button)
    bonus_win = tk.Toplevel(parent)
    bonus_win.title("✨ Bonus Shares Entry ✨")

    bonus_win.geometry("960x680")
    bonus_win.resizable(False, False)
    bonus_win.configure(bg=winbg)
    bonus_win.transient(parent)
    bonus_win.grab_set()
    push_window(bonus_win, parent)

    tooltip_var = setup_footer_tooltip(
        bonus_win, bg_color=winbg, fg_color=headbg
    )

    # --- Fetch Companies & Initialize Session ---
    companies = []
    company_to_id = {}
    current_session_bonus = {}

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
            logger.error(MSG["err_db_fetch"].format(e))

        if combo_widget:
            combo_widget["values"] = companies
            progressive_selection(combo_widget, companies)

    _refresh_company_data()

    # --- Standardized UI Variables ---
    company_name_var = tk.StringVar()
    exchange_var = tk.StringVar(value="NSE")

    ratio_old_var = tk.IntVar(value=1)
    ratio_new_var = tk.IntVar(value=1)

    held_qty_var = tk.IntVar(value=0)  # Refactored from record_qty_var
    allotted_qty_var = tk.IntVar(value=0)  # Refactored from bonus_qty_var

    note_var = tk.StringVar()

    # --- Dynamic Helpers & Animations ---
    def _calculate_allotment(*_args):
        """Calculates bonus shares automatically based on ratio and held quantity."""
        try:
            held = int(held_qty_var.get())
            r_old = int(ratio_old_var.get())
            r_new = int(ratio_new_var.get())

            if r_old > 0 and held > 0:
                # Standard practice: integer division for full shares allotted
                bonus_qty = int((held / r_old) * r_new)
                allotted_qty_var.set(bonus_qty)
            else:
                allotted_qty_var.set(0)
        except (ValueError, tk.TclError):
            allotted_qty_var.set(0)

    def _update_holdings(*_args):
        company = company_name_var.get().strip()
        if company in company_to_id:
            try:
                id_stk = company_to_id[company]
                rec_dt_str = record_dt_entry.get_date().strftime("%Y-%m-%d")
                holding = fetch_holding_on_date(id_stk, rec_dt_str)
                held_qty_var.set(holding)
                _calculate_allotment()
            except Exception:
                pass

    def _update_subsequent_dates(event=None):
        try:
            record_date = record_dt_entry.get_date()
            allotment_dt_entry.set_date(record_date + timedelta(days=15))
        except Exception:
            pass
        _update_holdings()

    def on_company_focus_out(_event=None):
        name = company_name_var.get().strip()
        if not name:
            return
        if name not in company_to_id:
            response = show_colorful_yesno(
                bonus_win,
                "Company Not Found",
                f"The company '{name}' was not found. Would you like to add it now?",
            )
            if response:
                add_company(bonus_win)
                export_company(bonus_win)
                _refresh_company_data(company_combo)
                company_combo.focus_set()
            else:
                show_colorful_error(
                    bonus_win, "Invalid Company", MSG["err_invalid_comp"]
                )
                company_combo.focus_set()
                company_combo.select_range(0, "end")
        else:
            _update_holdings()

    def reset_form_for_new_bonus():
        company_name_var.set("")
        ratio_old_var.set(1)
        ratio_new_var.set(1)
        held_qty_var.set(0)
        allotted_qty_var.set(0)
        exchange_var.set("NSE")
        note_var.set("")
        company_combo.focus_set()

    def show_session_bonus(_event=None):
        if not current_session_bonus:
            try:
                show_colorful_info(
                    bonus_win,
                    "No Entries",
                    "No Bonus Shares have been recorded in this session yet.",
                )
            except tk.TclError:
                pass
            return

        bonus_win.unbind("<Escape>")

        session_entries = list(current_session_bonus.items())
        idx = {"i": 0}

        viewer = tk.Toplevel(bonus_win)
        viewer.title("Session Bonus Viewer")
        viewer.transient(bonus_win)
        viewer.grab_set()
        viewer.resizable(False, False)
        viewer.geometry("520x280")
        viewer.configure(bg=winbg)

        push_window(viewer, bonus_win)
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
            content, wrap="word", height=9, bg="#f8fafc", bd=0, relief="flat"
        )
        info_text.pack(fill="both", expand=True, padx=10, pady=6)

        info_text.tag_configure(
            "label", font=("Helvetica", 11, "bold"), foreground=headbg
        )
        info_text.tag_configure(
            "value", font=("Helvetica", 11), foreground="#0f172a"
        )
        info_text.tag_configure(
            "net", font=("Helvetica", 11, "bold"), foreground=submitusualbg
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
            info_text.insert("end", "Ratio: ", "label")
            info_text.insert("end", f"{t.get('Ratio')}\n", "value")
            info_text.insert("end", "Held Qty: ", "label")
            info_text.insert("end", f"{t.get('Held')}\n", "value")
            info_text.insert("end", "Bonus Qty Allotted: ", "label")
            info_text.insert("end", f"{t.get('Bonus')}\n", "net")
            info_text.config(state="disabled")

            left_btn.config(state="disabled" if i == 0 else "normal")
            if i >= len(session_entries) - 1:
                right_btn.config(state="disabled")
                status_label.config(text="Last Entry", fg="#b91c1c")
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
            safe_close_modal(viewer, bonus_win)
            bonus_win.bind("<Escape>", close_bonus)
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
        help_win = tk.Toplevel(bonus_win)
        help_win.transient(bonus_win)
        help_win.grab_set()
        help_win.title("Help - Bonus Issue Entry")
        help_win.configure(bg="#fffaf0")
        help_win.geometry("640x620")
        help_win.resizable(False, False)
        push_window(help_win, bonus_win)

        header = tk.Label(
            help_win,
            text="Bonus Issue Entry Help",
            font=("Helvetica", 16, "bold"),
            bg=submitusualbg,
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
            "This form tracks Bonus Shares received from a company.\n",
            "• Company Name: Choose the company issuing the bonus.",
            "• Ratio: Read carefully! Enter how many shares you must HOLD, and how many NEW shares you receive.",
            "  (E.g. A 1:1 Bonus means For every 1 Held, you receive 1 Bonus).",
            "• Record Date: The cutoff date to be eligible for the bonus.",
            "• Record Qty (Held): The number of shares you held on the Record Date.",
            "• Bonus Qty: Automatically calculated based on the Ratio and Held Qty.\n",
            "Notes on Data Handling:",
            "Bonus shares act as a free 'BUY' trade. This automatically reduces your average holding cost per share. It does not deduct any money from your bank balance.\n",
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
            "Bonus Qty:": "#8b008b",
            "Notes on Data Handling:": "#000000",
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
            return safe_close_modal(help_win, bonus_win)

        # # Dedicated frame for the button to enforce layout sizing
        # btn_frame = tk.Frame(help_win, bg="#fffaf0")
        # btn_frame.pack(side="bottom", pady=(10, 20))

        btn = tk.Button(
            help_win,
            text="Close",
            command=close_help,
            font=("Helvetica", 11, "bold"),
            bg="#475569",
            fg="white",
            padx=15,
            pady=6,
            cursor="hand2",
        )
        btn.pack(side="bottom", pady=10)

        help_win.bind("<Escape>", close_help)
        help_win.bind("<Return>", close_help)
        btn.focus_set()

    # --- Submission Logic ---
    def _on_submit(_event=None):
        company = company_name_var.get().strip()
        if company not in company_to_id:
            show_colorful_error(
                bonus_win,
                "Validation Error",
                MSG["err_invalid_comp"],
            )
            return

        id_stk = company_to_id[company]
        try:
            r_old = int(ratio_old_var.get())
            r_new = int(ratio_new_var.get())
            held_qty = int(held_qty_var.get())
            bonus_qty = int(allotted_qty_var.get())

            if r_old <= 0 or r_new <= 0 or held_qty < 0 or bonus_qty <= 0:
                raise ValueError(
                    "Values must be positive. Bonus Qty cannot be zero."
                )
        except (ValueError, tk.TclError):
            show_colorful_error(
                bonus_win,
                "Validation Error",
                MSG["err_positive_num"],
            )
            return

        try:
            rec_dt = record_dt_entry.get_date().strftime("%Y-%m-%d")
            a_dt = allotment_dt_entry.get_date().strftime("%Y-%m-%d")
        except Exception:
            show_colorful_error(
                bonus_win, "Date Error", MSG["err_invalid_date"]
            )
            return

        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA foreign_keys = ON;")

                details = f"{r_new}:{r_old} Bonus Issue"

                if edit_id is not None:
                    # --- UPDATE EXISTING RECORD ---
                    cursor.execute(
                        """
                        UPDATE corp_acts
                        SET act_dt = ?, details_act = ?, ratio_old = ?, ratio_new = ?, note_act = ?
                        WHERE id_act = ?
                        """,
                        (
                            rec_dt,
                            details,
                            r_old,
                            r_new,
                            note_var.get().strip(),
                            edit_id,
                        ),
                    )

                    cont_no = f"BONUS_{edit_id}"

                    # Fetch the existing transaction ID to link it
                    cursor.execute(
                        "SELECT id_trd FROM transactions WHERE cont_no = ?",
                        (cont_no,),
                    )
                    trd_row = cursor.fetchone()
                    id_trd = trd_row[0] if trd_row else None

                    # Update or Insert into the new bonus_issues table
                    cursor.execute(
                        "SELECT id_bonus FROM bonus_issues WHERE id_act = ?",
                        (edit_id,),
                    )
                    if cursor.fetchone():
                        cursor.execute(
                            """
                            UPDATE bonus_issues
                            SET ex_dt = ?, record_dt = ?, ratio_old = ?, ratio_new = ?, held_qty = ?, bonus_qty = ?, note_bonus = ?
                            WHERE id_act = ?
                            """,
                            (
                                rec_dt,
                                rec_dt,
                                r_old,
                                r_new,
                                held_qty,
                                bonus_qty,
                                note_var.get().strip(),
                                edit_id,
                            ),
                        )
                    else:
                        cursor.execute(
                            """
                            INSERT INTO bonus_issues (id_act, id_stk, id_trd, ex_dt, record_dt, ratio_old, ratio_new, held_qty, bonus_qty, note_bonus)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                edit_id,
                                id_stk,
                                id_trd,
                                rec_dt,
                                rec_dt,
                                r_old,
                                r_new,
                                held_qty,
                                bonus_qty,
                                note_var.get().strip(),
                            ),
                        )

                    cursor.execute(
                        "UPDATE contracts SET trd_dt = ?, settle_dt = ? WHERE cont_no = ?",
                        (a_dt, a_dt, cont_no),
                    )

                    cursor.execute(
                        """
                        UPDATE transactions
                        SET trd_dt = ?, qty_trd = ?, note_trd = ?
                        WHERE cont_no = ?
                        """,
                        (
                            a_dt,
                            bonus_qty,
                            f"Bonus Shares Allocation ({details})",
                            cont_no,
                        ),
                    )
                else:
                    # --- INSERT NEW RECORD ---
                    cursor.execute(
                        """
                        INSERT INTO corp_acts (id_stk, act_dt, type_act, details_act, ratio_old, ratio_new, note_act)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            id_stk,
                            rec_dt,
                            "BONUS",
                            details,
                            r_old,
                            r_new,
                            note_var.get().strip(),
                        ),
                    )
                    id_act = cursor.lastrowid

                    cont_no = f"BONUS_{id_act}"
                    settle_no = int(f"222{id_act}")

                    cursor.execute(
                        """
                        INSERT INTO contracts (cont_no, trd_dt, settle_no, settle_dt, no_of_trades, net_amt_cont, net_amt_cont_applicable)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (cont_no, a_dt, settle_no, a_dt, 1, 0.0, 0.0),
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
                            a_dt,
                            company,
                            "BUY",
                            exchange_var.get(),
                            bonus_qty,
                            0.0,
                            0.0,
                            0.0,
                            0.0,
                            f"Bonus Shares Allocation ({details})",
                        ),
                    )
                    id_trd = cursor.lastrowid

                    cursor.execute(
                        """
                        INSERT INTO bonus_issues (
                            id_act, id_stk, id_trd, ex_dt, record_dt,
                            ratio_old, ratio_new, held_qty, bonus_qty, note_bonus
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            id_act,
                            id_stk,
                            id_trd,
                            rec_dt,
                            rec_dt,
                            r_old,
                            r_new,
                            held_qty,
                            bonus_qty,
                            note_var.get().strip(),
                        ),
                    )

                conn.commit()

            # Record session entry
            sr_no = len(current_session_bonus) + 1
            current_session_bonus[sr_no] = {
                "Company": company,
                "Ratio": details,
                "Held": held_qty,
                "Bonus": bonus_qty,
            }

            compute_avg_price(id_stk)

            # Prompt user based on execution type
            if edit_id is not None:
                show_colorful_info(
                    bonus_win,
                    "Update Success",
                    f"Bonus Issue updated successfully for {company}.",
                )
                close_bonus()
            else:
                show_colorful_info(
                    bonus_win,
                    "Success",
                    MSG["succ_saved"].format("Bonus Issue", company),
                )
                response = show_colorful_yesno(
                    bonus_win,
                    "🔄 Add Another Bonus Issue?",
                    MSG["succ_prompt_next"].format("Bonus Issue"),
                )
                if response:
                    reset_form_for_new_bonus()
                else:
                    close_bonus()

        except sqlite3.Error as e:
            logger.error(MSG["err_db_save"].format(e))
            show_colorful_error(
                bonus_win, "Database Error", MSG["err_db_save"].format(e)
            )

    def close_bonus(event=None):
        return safe_close_modal(bonus_win, parent, calling_button)

    # ==========================================
    # UI LAYOUT & FRAMES
    # ==========================================

    # Header
    header_frame = tk.Frame(bonus_win, bg=headbg, relief="raised", bd=3)
    header_frame.pack(fill="x", padx=5, pady=0)
    tk.Label(
        header_frame,
        text="💼 BONUS SHARES ENTRY 💼",
        font=("Comic Sans MS", 18, "bold"),
        bg=headbg,
        fg=titlefg,
        pady=8,
        relief="ridge",
        bd=2,
    ).pack(fill="x")

    # Main wrapper frame
    main_frame = tk.Frame(
        bonus_win, bg=mainfrbg, padx=15, pady=10, relief="raised", bd=2
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
        fg=headbg,
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
    company_combo.bind("<<ComboboxSelected>>", _update_holdings, add="+")

    tk.Label(
        comp_frame,
        text="Exchange",
        bg=compfrbg,
        font=("Helvetica", 13, "bold"),
        fg=headbg,
    ).pack(side="left", padx=(10, 5))

    radio_nse = tk.Radiobutton(
        comp_frame,
        text="NSE",
        variable=exchange_var,
        value="NSE",
        bg=compfrbg,
        font=("Helvetica", 12),
        fg=headbg,
    )
    radio_nse.pack(side="left")

    radio_bse = tk.Radiobutton(
        comp_frame,
        text="BSE",
        variable=exchange_var,
        value="BSE",
        bg=compfrbg,
        font=("Helvetica", 12),
        fg=headbg,
    )
    radio_bse.pack(side="left")

    # 2. Dates Frame
    date_frame = tk.Frame(
        main_frame, bg=datefrbg, relief="ridge", bd=2, padx=10, pady=10
    )
    date_frame.pack(fill="x", pady=(0, 10))

    tk.Label(
        date_frame,
        text="Record Date",
        bg=datefrbg,
        font=("Helvetica", 13, "bold"),
        fg=submitusualbg,
    ).pack(side="left", padx=(5, 5))

    record_dt_entry = DateEntry(
        date_frame, date_pattern="dd-mm-yyyy", font=("Helvetica", 13), width=12
    )
    record_dt_entry.pack(side="left", padx=(0, 40))

    record_dt_entry.bind("<<DateEntrySelected>>", _update_subsequent_dates)
    record_dt_entry.bind("<FocusOut>", _update_subsequent_dates, add="+")

    tk.Label(
        date_frame,
        text="Allotment Date",
        bg=datefrbg,
        font=("Helvetica", 13, "bold"),
        fg=submitusualbg,
    ).pack(side="left", padx=(5, 5))

    allotment_dt_entry = DateEntry(
        date_frame, date_pattern="dd-mm-yyyy", font=("Helvetica", 13), width=12
    )
    allotment_dt_entry.pack(side="left", padx=(0, 25))

    bind_date_spin(record_dt_entry, callback=_update_subsequent_dates)
    bind_date_spin(allotment_dt_entry)

    # 3. Ratio and Quantities Frame
    ratio_frame = tk.Frame(
        main_frame, bg=ratiofrbg, relief="ridge", bd=2, padx=10, pady=15
    )
    ratio_frame.pack(fill="x", pady=(0, 10))

    # Sub-frame for Ratio
    r_top = tk.Frame(ratio_frame, bg=ratiofrbg)
    r_top.pack(fill="x", pady=(0, 10))
    tk.Label(
        r_top,
        text="For Every",
        bg=ratiofrbg,
        font=("Helvetica", 13, "bold"),
        fg=headbg,
    ).pack(side="left", padx=(5, 5))

    ratio_old_entry = tk.Spinbox(
        r_top,
        from_=1,
        to=1000,
        textvariable=ratio_old_var,
        width=5,
    )
    ratio_old_entry.pack(side="left", padx=(0, 5))

    tk.Label(
        r_top,
        text="Shares Held,",
        bg=ratiofrbg,
        font=("Helvetica", 13, "bold"),
        fg=headbg,
    ).pack(side="left", padx=(0, 30))

    tk.Label(
        r_top,
        text="Receive",
        bg=ratiofrbg,
        font=("Helvetica", 13, "bold"),
        fg=headbg,
    ).pack(side="left", padx=(5, 5))

    ratio_new_entry = tk.Spinbox(
        r_top,
        from_=1,
        to=1000,
        textvariable=ratio_new_var,
        width=5,
    )
    ratio_new_entry.pack(side="left", padx=(0, 5))

    tk.Label(
        r_top,
        text="Bonus Shares.",
        bg=ratiofrbg,
        font=("Helvetica", 13, "bold"),
        fg=headbg,
    ).pack(side="left", padx=(0, 5))

    # Sub-frame for Quantities
    r_bot = tk.Frame(ratio_frame, bg=ratiofrbg)
    r_bot.pack(fill="x")
    tk.Label(
        r_bot,
        text="Record Qty (Held)",
        bg=ratiofrbg,
        font=("Helvetica", 13, "bold"),
        fg="#166534",
    ).pack(side="left", padx=(5, 5))

    held_qty_entry = tk.Spinbox(
        r_bot,
        from_=0,
        to=999999,
        textvariable=held_qty_var,
        width=10,
    )
    held_qty_entry.pack(side="left", padx=(0, 35))

    tk.Label(
        r_bot,
        text="Bonus Qty Allotted",
        bg=ratiofrbg,
        font=("Helvetica", 13, "bold"),
        fg="#166534",
    ).pack(side="left", padx=(5, 5))

    allotted_qty_entry = tk.Entry(
        r_bot,
        textvariable=allotted_qty_var,
        width=12,
        state="readonly",
    )
    allotted_qty_entry.pack(side="left")

    # Bind calculations
    ratio_old_entry.bind("<KeyRelease>", _calculate_allotment)
    ratio_old_entry.bind("<FocusOut>", _calculate_allotment, add="+")
    ratio_new_entry.bind("<KeyRelease>", _calculate_allotment)
    ratio_new_entry.bind("<FocusOut>", _calculate_allotment, add="+")
    held_qty_entry.bind("<KeyRelease>", _calculate_allotment)
    held_qty_entry.bind("<FocusOut>", validate_positive_numeric, add="+")
    held_qty_entry.bind("<FocusOut>", _calculate_allotment, add="+")

    # 4. Notes Frame
    note_frame = tk.Frame(
        main_frame, bg=notefrbg, relief="ridge", bd=2, padx=10, pady=10
    )
    note_frame.pack(fill="x", pady=(0, 10))

    tk.Label(
        note_frame,
        text="Notes / Remarks",
        bg=notefrbg,
        font=("Helvetica", 13, "bold"),
        fg="#334155",
    ).pack(side="left", padx=(5, 5))

    notes_entry = tk.Entry(note_frame, textvariable=note_var, width=68)
    notes_entry.pack(side="left", padx=(0, 10))

    # --- Buttons Frame ---
    btn_frame = tk.Frame(bonus_win, pady=10, bg=btnfrbg, relief="ridge", bd=2)
    btn_frame.pack(fill="x", anchor="e", padx=10, pady=(0, 10))

    hint_label = tk.Label(
        btn_frame,
        text="Press F1 for help, F2 for session entries, or Esc to close.",
        font=("Helvetica", 15, "italic"),
        bg=btnfrbg,
        fg=submitactivebg,
    )
    hint_label.pack(side="left", padx=10)

    save_btn = tk.Button(
        btn_frame,
        text="🚀 Save Entry 🚀",
        command=_on_submit,
        font=("Comic Sans MS", 12, "bold"),
        bg=submitusualbg,
        fg="white",
        width=16,
        cursor="hand2",
        activebackground=submitactivebg,
        activeforeground="white",
        relief="raised",
        bd=3,
    )
    save_btn.pack(side="right", padx=10)

    cancel_btn = tk.Button(
        btn_frame,
        text="❌ Cancel ❌",
        command=close_bonus,
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

    # Hover & Focus animations
    apply_button_animations(save_btn, submitusualbg, "#2563eb")
    apply_button_animations(cancel_btn, cancelusualbg, cancelactivebg)

    # --- Apply Global Styles & Entry Hovers ---
    entries = {
        "company_combo": company_combo,
        "record_dt_entry": record_dt_entry,
        "allotment_dt_entry": allotment_dt_entry,
        "ratio_old_entry": ratio_old_entry,
        "ratio_new_entry": ratio_new_entry,
        "held_qty_entry": held_qty_entry,
        "allotted_qty_entry": allotted_qty_entry,
        "notes_entry": notes_entry,
    }

    for key, widget in entries.items():
        # Identify readonly fields to apply the specific readonly styling
        is_ro = key == "allotted_qty_entry"
        apply_entry_theme(widget, is_readonly=is_ro)

    # --- Tooltip Bindings ---
    bind_tooltip(
        company_combo,
        tooltip_var,
        "Choose the company issuing the bonus shares.",
    )
    bind_tooltip(
        radio_nse, tooltip_var, "Select the exchange for the corporate action."
    )
    bind_tooltip(
        radio_bse, tooltip_var, "Select the exchange for the corporate action."
    )
    bind_tooltip(
        record_dt_entry,
        tooltip_var,
        "The cutoff date to be eligible for the bonus.",
    )
    bind_tooltip(
        allotment_dt_entry,
        tooltip_var,
        "The date shares are credited to your demat account.",
    )
    bind_tooltip(
        ratio_old_entry,
        tooltip_var,
        "The number of shares you must HOLD to be eligible.",
    )
    bind_tooltip(
        ratio_new_entry,
        tooltip_var,
        "The number of NEW shares you receive for holding the required amount.",
    )
    bind_tooltip(
        held_qty_entry,
        tooltip_var,
        "The total number of shares you held on the Record Date.",
    )
    bind_tooltip(
        allotted_qty_entry,
        tooltip_var,
        "Auto-calculated: The exact number of bonus shares credited to you.",
    )
    bind_tooltip(
        notes_entry, tooltip_var, "Any extra remarks about this bonus issue."
    )

    # Global Hotkeys
    bonus_win.bind("<Escape>", close_bonus)
    bonus_win.bind("<F1>", show_help)
    bonus_win.bind("<F2>", show_session_bonus)
    bonus_win.bind(
        "<Return>",
        lambda e: on_enter_focus_next(e, bonus_win, save_btn, cancel_btn),
    )
    bonus_win.protocol("WM_DELETE_WINDOW", close_bonus)

    # Set Initial Focus
    company_combo.focus_set()

    # --- UPDATE ENGINE: PRE-FILL DATA ---
    if edit_id is not None:
        bonus_win.title("✨ Update Bonus Shares ✨")
        save_btn.config(text="🚀 Update Entry 🚀")
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT
                        s.company_name,
                        c.act_dt,
                        IFNULL(b.ratio_old, c.ratio_old),
                        IFNULL(b.ratio_new, c.ratio_new),
                        IFNULL(b.note_bonus, c.note_act),
                        t.trd_dt
                    FROM corp_acts c
                    JOIN stocks s ON c.id_stk = s.id_stk
                    LEFT JOIN bonus_issues b ON c.id_act = b.id_act
                    LEFT JOIN transactions t ON t.cont_no = 'BONUS_' || c.id_act
                    WHERE c.id_act = ?
                    """,
                    (edit_id,),
                )
                row = cursor.fetchone()

            if row:
                company_name_var.set(row[0])
                company_combo.config(
                    state="disabled"
                )  # Lock company to prevent orphan records

                try:
                    rec_dt_obj = datetime.strptime(row[1], "%Y-%m-%d").date()
                    record_dt_entry.set_date(rec_dt_obj)
                except ValueError:
                    pass

                ratio_old_var.set(row[2])
                ratio_new_var.set(row[3])
                note_var.set(row[4] if row[4] else "")

                if row[5]:
                    try:
                        allot_dt_obj = datetime.strptime(
                            row[5], "%Y-%m-%d"
                        ).date()
                        allotment_dt_entry.set_date(allot_dt_obj)
                    except ValueError:
                        pass

                # Trigger holding validation and ratio calculations
                _update_holdings()

        except sqlite3.Error as e:
            logger.error(MSG["err_db_fetch"].format(e))

    parent.wait_window(bonus_win)
    try:
        if parent.winfo_exists():
            parent.grab_set()
    except tk.TclError:
        pass
