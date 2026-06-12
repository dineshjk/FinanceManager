# -*- coding: utf-8 -*-
# File: # File: C:\Data\Personal\Finance_and_Investment\finprog\FinanceManager\StockMan\dividend.py

"""
This module handles the management of dividends within the stock portfolio.
It includes automatic calculation of holdings based on the record date,
ex-date generation, payment date generation, and multi-table ledger updates.
"""

from typing import Union
import tkinter as tk
from tkinter import ttk
import sqlite3
from datetime import timedelta, datetime
from tkcalendar import DateEntry

# Local project imports
from Shared.globals import get_db_connection, logger
from Shared.dialog_utils import (
    show_colorful_info,
    show_colorful_error,
    show_colorful_yesno,
)
from Shared.modal_utils import disable_parent, enable_parent
from Shared.window_manager import push_window, pop_window, safe_close_modal
from Shared.gui_progressive import progressive_selection
from .trade_utils import fetch_holding_on_date
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


def get_previous_working_day(dt):
    """Returns the previous working day (skips weekends)."""
    dt -= timedelta(days=1)
    while dt.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
        dt -= timedelta(days=1)
    return dt


def get_next_working_day(dt):
    """Returns the next working day (skips weekends)."""
    while dt.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
        dt += timedelta(days=1)
    return dt


def get_financial_year(date_obj):
    """
    Returns the Indian Financial Year string (e.g., 'FY26')
    based on a given datetime.date object.
    """
    if date_obj.month >= 4:
        return f"FY{str(date_obj.year + 1)[-2:]}"
    else:
        return f"FY{str(date_obj.year)[-2:]}"


def add_dividend(
    parent: Union[tk.Toplevel, tk.Tk],
    calling_button: tk.Widget | None = None,
    edit_id: int | None = None,
) -> None:
    """
    Opens a modal window for Dividend data entry and saves it to the database.
    """
    ratwinbg = "#e0f2f1"  # Very light teal
    headbg = "#004d40"  # Deep teal
    titlefg = "#ffb300"  # Amber
    ratframebg = "#b2dfdb"  # Soft teal
    compisinbg = "#e8f5e9"  # Light green
    qoqbg = "#fff3e0"  # Light orange
    rbnnbg = "#e3f2fd"  # Light blue
    wbtbg = "#fce4ec"  # Light pink
    gssbg = "#fffde7"  # Light yellow
    btnfrbg = "#f5f5f5"  # Light grey
    hintbg = "#b2dfdb"  # Matches ratframe
    hintfg = "#800000"  # Dark Maroon for high contrast
    submitusualbg = "#0288d1"  # Blue
    submitactivebg = "#01579b"  # Darker blue
    cancelusualbg = "#d32f2f"  # Red
    cancelactivebg = "#c62828"  # Darker red

    modal_id = disable_parent(parent, calling_button=calling_button)
    div_win = tk.Toplevel(parent)
    div_win.title("✨ Data Entry - Dividend ✨")
    div_win.geometry("1100x750")
    div_win.resizable(False, False)
    div_win.configure(bg=ratwinbg)
    div_win.transient(parent)
    div_win.grab_set()
    push_window(div_win, parent)

    tooltip_var = setup_footer_tooltip(
        div_win, bg_color=hintbg, fg_color=hintfg
    )

    current_session_dividends = {}
    _check_tracker = {"id_stk": 0, "date": ""}

    companies = []
    company_to_data = {}
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT company_name, id_stk, isin, face_value FROM stocks ORDER BY company_name"
            )
            for row in cursor.fetchall():
                companies.append(row[0])
                company_to_data[row[0]] = {
                    "id_stk": row[1],
                    "isin": row[2] or "",
                    "face_value": row[3] or 10.0,
                }
    except sqlite3.Error as e:
        logger.error("Failed to fetch companies for Dividend: %s", e)

    company_name_var = tk.StringVar()
    isin_var = tk.StringVar()
    face_value_var = tk.DoubleVar()
    div_type_var = tk.StringVar(value="FINAL")
    entitled_qty_var = tk.IntVar(value=0)
    div_percent_var = tk.DoubleVar(value=0.0)
    per_share_amt_var = tk.DoubleVar(value=0.0)
    gross_amt_var = tk.DoubleVar(value=0.0)
    tds_amt_var = tk.DoubleVar(value=0.0)
    net_amt_var = tk.DoubleVar(value=0.0)
    initial_fy = get_financial_year(datetime.now().date())
    fy_label_var = tk.StringVar(value=initial_fy)
    note_var = tk.StringVar()

    current_id_act_var = tk.IntVar(value=0)
    current_id_div_var = tk.IntVar(value=0)

    entries = {}

    def _create_context_menu(widget):
        menu = tk.Menu(div_win, tearoff=0)
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

    def _calculate_amounts(*_args):
        try:
            fv = float(face_value_var.get())
            pct = float(div_percent_var.get())
            qty = int(entitled_qty_var.get())
            tds = float(tds_amt_var.get())

            per_share = round(fv * (pct / 100), 4)
            per_share_amt_var.set(per_share)
            gross = round(qty * per_share, 2)
            gross_amt_var.set(gross)
            net_amt_var.set(round(gross - tds, 2))
        except ValueError:
            pass

    def _update_dates_and_holdings():
        """Silently calculates related dates and current holdings."""
        try:
            rec_date = record_dt_entry.get_date()
            ex_date = get_previous_working_day(rec_date)
            raw_credit_date = rec_date + timedelta(days=15)
            credit_date = get_next_working_day(raw_credit_date)

            ex_dt_entry.set_date(ex_date)
            credit_dt_entry.set_date(credit_date)
            fy_label_var.set(get_financial_year(credit_date))

            company = company_name_var.get().strip()
            if company in company_to_data:
                id_stk = company_to_data[company]["id_stk"]
                rec_date_str = rec_date.strftime("%Y-%m-%d")
                holding = fetch_holding_on_date(id_stk, rec_date_str)
                entitled_qty_var.set(holding)
                _calculate_amounts()
        except Exception:
            pass

    def _check_existing_record(event=None):
        """Checks the DB for existing records explicitly when interacting with Record Date."""
        # Update UI silently first based on the new date
        _update_dates_and_holdings()

        company = company_name_var.get().strip()
        if company not in company_to_data:
            return

        id_stk = company_to_data[company]["id_stk"]
        try:
            rec_date = record_dt_entry.get_date()
            rec_date_str = rec_date.strftime("%Y-%m-%d")
        except Exception:
            return

        # Debounce: prevent popup if we just checked this specific company+date combination
        if (
            _check_tracker["id_stk"] == id_stk
            and _check_tracker["date"] == rec_date_str
        ):
            return

        _check_tracker["id_stk"] = id_stk
        _check_tracker["date"] = rec_date_str

        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT d.id_div, d.id_act, d.ex_dt, d.credit_dt, d.div_type,
                           d.entitled_qty, d.per_share_amt, d.tds_amt, d.fy_label, d.note_div,
                           c.div_percent_act
                    FROM dividends d
                    JOIN corp_acts c ON d.id_act = c.id_act
                    WHERE d.id_stk = ? AND d.record_dt = ?
                    """,
                    (id_stk, rec_date_str),
                )
                row = cursor.fetchone()

                if row:
                    current_id_div_var.set(row[0])
                    current_id_act_var.set(row[1])
                    ex_dt_entry.set_date(
                        datetime.strptime(row[2], "%Y-%m-%d").date()
                    )
                    credit_dt_entry.set_date(
                        datetime.strptime(row[3], "%Y-%m-%d").date()
                    )
                    div_type_var.set(row[4])
                    entitled_qty_var.set(row[5])
                    tds_amt_var.set(row[7])
                    fy_label_var.set(row[8] if row[8] else "")
                    note_var.set(row[9] if row[9] else "")
                    div_percent_var.set(row[10])

                    _calculate_amounts()
                    show_colorful_info(
                        div_win,
                        "Record Found",
                        f"Existing dividend record found for {company}.\nData auto-populated for editing.",
                    )
                else:
                    current_id_div_var.set(0)
                    current_id_act_var.set(0)
        except sqlite3.Error as e:
            logger.error(f"Error checking existing dividend: {e}")

    def _on_company_selected(*_args):
        """Triggered only when the company dropdown changes."""
        company = company_name_var.get().strip()
        if company in company_to_data:
            data = company_to_data[company]
            isin_var.set(data["isin"])
            face_value_var.set(data["face_value"])

            # Reset trackers so if they eventually tab out of the date, it re-checks
            _check_tracker["id_stk"] = 0
            _check_tracker["date"] = ""

            # Update holdings silently, do NOT pop up record info immediately
            _update_dates_and_holdings()
        else:
            isin_var.set("")
            face_value_var.set(0.0)
            current_id_act_var.set(0)
            current_id_div_var.set(0)

    def reset_form():
        company_name_var.set("")
        isin_var.set("")
        face_value_var.set(0.0)
        div_type_var.set("FINAL")
        entitled_qty_var.set(0)
        div_percent_var.set(0.0)
        per_share_amt_var.set(0.0)
        gross_amt_var.set(0.0)
        tds_amt_var.set(0.0)
        net_amt_var.set(0.0)
        fy_label_var.set("")
        note_var.set("")
        current_id_act_var.set(0)
        current_id_div_var.set(0)
        _check_tracker["id_stk"] = 0
        _check_tracker["date"] = ""
        company_combo.focus_set()

    def _on_submit(_event=None):
        company = company_name_var.get().strip()
        if company not in company_to_data:
            show_colorful_error(
                div_win, "Validation Error", "Please select a valid company."
            )
            return

        id_stk = company_to_data[company]["id_stk"]

        try:
            rec_dt = record_dt_entry.get_date().strftime("%Y-%m-%d")
            ex_dt = ex_dt_entry.get_date().strftime("%Y-%m-%d")
            cred_dt = credit_dt_entry.get_date().strftime("%Y-%m-%d")
            display_rec_dt = record_dt_entry.get_date().strftime("%d-%m-%Y")
        except Exception:
            show_colorful_error(
                div_win, "Date Error", "Please ensure all dates are valid."
            )
            return

        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA foreign_keys = ON;")

                div_type = div_type_var.get()
                details = f"{div_type} Dividend"

                id_act = current_id_act_var.get()
                id_div = current_id_div_var.get()

                if id_act > 0:
                    # --- UPDATE EXISTING RECORD ---
                    cursor.execute(
                        """
                        UPDATE corp_acts
                        SET act_dt=?, type_act=?, details_act=?, div_percent_act=?, div_amount_act=?, note_act=?
                        WHERE id_act=?
                        """,
                        (
                            rec_dt,
                            "DIVIDEND",
                            details,
                            div_percent_var.get(),
                            per_share_amt_var.get(),
                            note_var.get(),
                            id_act,
                        ),
                    )

                    if id_div > 0:
                        cursor.execute(
                            """
                            UPDATE dividends
                            SET id_act=?, ex_dt=?, record_dt=?, credit_dt=?, div_type=?, div_percent=?, entitled_qty=?, per_share_amt=?, tds_amt=?, fy_label=?, note_div=?
                            WHERE id_div=?
                            """,
                            (
                                id_act,
                                ex_dt,
                                rec_dt,
                                cred_dt,
                                div_type,
                                div_percent_var.get(),
                                entitled_qty_var.get(),
                                per_share_amt_var.get(),
                                tds_amt_var.get(),
                                fy_label_var.get(),
                                note_var.get(),
                                id_div,
                            ),
                        )
                    else:
                        # Legacy update: Create the missing dividend row
                        cursor.execute(
                            """
                            INSERT INTO dividends (
                                id_stk, id_act, ex_dt, record_dt, credit_dt, div_type,
                                div_percent, entitled_qty, per_share_amt, tds_amt, fy_label, note_div
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                id_stk,
                                id_act,
                                ex_dt,
                                rec_dt,
                                cred_dt,
                                div_type,
                                div_percent_var.get(),
                                entitled_qty_var.get(),
                                per_share_amt_var.get(),
                                tds_amt_var.get(),
                                fy_label_var.get(),
                                note_var.get(),
                            ),
                        )
                        id_div = cursor.lastrowid
                        current_id_div_var.set(id_div)

                    cont_no = f"DIV_{id_div}"

                    cursor.execute(
                        "DELETE FROM computed_bank WHERE cont_no=?", (cont_no,)
                    )
                    net_amount = net_amt_var.get()
                    if net_amount > 0:
                        desc = f"Dividend from {company}"
                        cursor.execute(
                            """
                            INSERT INTO computed_bank (cont_no, comp_bt_dt, comp_bt_type, comp_bt_amt, comp_bt_amt_applicable, comp_bt_desc)
                            VALUES (?, ?, ?, ?, ?, ?)
                            """,
                            (
                                cont_no,
                                cred_dt,
                                "CREDIT",
                                net_amount,
                                net_amount,
                                desc,
                            ),
                        )
                        cursor.execute(
                            "UPDATE dividends SET id_comp_bt=? WHERE id_div=?",
                            (cursor.lastrowid, id_div),
                        )
                    else:
                        cursor.execute(
                            "UPDATE dividends SET id_comp_bt=NULL WHERE id_div=?",
                            (id_div,),
                        )

                else:
                    # --- INSERT NEW RECORD ---
                    cursor.execute(
                        """
                        INSERT INTO corp_acts (
                            id_stk, act_dt, type_act, details_act, div_percent_act, div_amount_act, note_act
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            id_stk,
                            rec_dt,
                            "DIVIDEND",
                            details,
                            div_percent_var.get(),
                            per_share_amt_var.get(),
                            note_var.get(),
                        ),
                    )
                    id_act = cursor.lastrowid

                    cursor.execute(
                        """
                        INSERT INTO dividends (
                            id_stk, id_act, ex_dt, record_dt, credit_dt, div_type,
                            div_percent, entitled_qty, per_share_amt, tds_amt, fy_label, note_div
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            id_stk,
                            id_act,
                            ex_dt,
                            rec_dt,
                            cred_dt,
                            div_type,
                            div_percent_var.get(),
                            entitled_qty_var.get(),
                            per_share_amt_var.get(),
                            tds_amt_var.get(),
                            fy_label_var.get(),
                            note_var.get(),
                        ),
                    )
                    id_div = cursor.lastrowid

                    net_amount = net_amt_var.get()
                    if net_amount > 0:
                        cont_no = f"DIV_{id_div}"
                        desc = f"Dividend from {company}"
                        cursor.execute(
                            """
                            INSERT INTO computed_bank (cont_no, comp_bt_dt, comp_bt_type, comp_bt_amt, comp_bt_amt_applicable, comp_bt_desc)
                            VALUES (?, ?, ?, ?, ?, ?)
                            """,
                            (
                                cont_no,
                                cred_dt,
                                "CREDIT",
                                net_amount,
                                net_amount,
                                desc,
                            ),
                        )
                        cursor.execute(
                            "UPDATE dividends SET id_comp_bt=? WHERE id_div=?",
                            (cursor.lastrowid, id_div),
                        )

                conn.commit()

            sr = len(current_session_dividends) + 1
            current_session_dividends[sr] = {
                "Company": company,
                "Type": div_type,
                "Record Dt": display_rec_dt,
                "Qty": entitled_qty_var.get(),
                "Percent": div_percent_var.get(),
                "Net": net_amt_var.get(),
            }

            msg = "updated" if (id_act > 0 and id_div > 0) else "saved"
            response = show_colorful_yesno(
                div_win,
                "🎉 Dividend Recorded",
                f"Dividend for {company} {msg} successfully.\n\nDo you want to add another dividend entry?",
            )
            if response:
                reset_form()
            else:
                _close_div()

        except sqlite3.Error as e:
            logger.error("Database error saving Dividend: %s", e)
            show_colorful_error(
                div_win, "Database Error", f"Failed to save record: {e}"
            )

    def _close_div(_event=None):
        if _event and hasattr(_event, "widget") and _event.widget:
            try:
                if _event.widget.winfo_toplevel() != div_win:
                    return
            except tk.TclError:
                pass

        try:
            enable_parent(modal_id)
            safe_close_modal(div_win, parent)
        except tk.TclError:
            pass

    def show_help(_event=None):
        div_win.unbind("<Escape>")

        help_win = tk.Toplevel(div_win)
        help_win.title("Help — Dividend Entry")
        help_win.geometry("640x550")
        help_win.configure(bg="#f4fbf8")
        help_win.transient(div_win)
        help_win.grab_set()
        push_window(help_win, div_win)

        try:
            help_win.focus_set()
        except tk.TclError:
            pass

        header = tk.Label(
            help_win,
            text="🌟 Dividend Data Entry Guide 🌟",
            font=("Helvetica", 16, "bold"),
            bg="#004d40",
            fg="#ffb300",
            pady=10,
        )
        header.pack(fill="x")

        body = tk.Frame(help_win, bg="#f4fbf8", padx=15, pady=15)
        body.pack(fill="both", expand=True)

        text = tk.Text(
            body,
            wrap="word",
            bg="#f4fbf8",
            bd=0,
            font=("Helvetica", 12),
            height=14,
        )
        text.pack(fill="both", expand=True)

        help_content = (
            "Welcome to the Dividend Entry System!\n\n"
            "This module allows you to track and log corporate dividend actions efficiently. "
            "Please ensure accuracy when entering the following key fields:\n\n"
            "• Company: Select the stock. The ISIN and Face Value will auto-populate.\n"
            "• Record Date: The cut-off date. Your holding quantity will be automatically fetched based on this date.\n"
            "• Ex-Date & Payment Date: These are auto-estimated but can be manually adjusted if the company specifies differently.\n"
            "• Div Percent (%): Enter the declared percentage. The amount per share is calculated against the Face Value.\n"
            "• TDS Deducted: Enter any tax deducted at source to calculate your exact Net Benefit.\n\n"
            "Navigation Shortcuts:\n"
            "  [Enter]  : Move to the next field rapidly.\n"
            "  [Esc]    : Cancel the current entry.\n"
            "  [F2]     : View all dividends recorded during this active session."
        )
        text.insert("1.0", help_content)

        highlights = {
            "Company": "#00695c",
            "Record Date": "#d84315",
            "Div Percent (%)": "#0277bd",
            "TDS Deducted": "#c62828",
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
                    word, foreground=color, font=("Helvetica", 12, "bold")
                )
                start = end_pos
        text.config(state="disabled")

        def close_help(e=None):
            safe_close_modal(help_win, div_win)
            div_win.bind("<Escape>", _close_div)
            return "break"

        help_win.bind("<Escape>", close_help)
        help_win.protocol("WM_DELETE_WINDOW", close_help)

        ok_btn = tk.Button(
            help_win,
            text="Got It",
            font=("Helvetica", 11, "bold"),
            bg="#004d40",
            fg="white",
            width=10,
            command=close_help,
        )
        ok_btn.pack(pady=10)
        try:
            ok_btn.focus_set()
        except tk.TclError:
            pass

    def show_session_dividends(_event=None):
        if not current_session_dividends:
            try:
                show_colorful_info(
                    div_win,
                    "No Dividends",
                    "No dividends have been recorded in this session yet.",
                )
            except tk.TclError as exc:
                logger.debug(
                    "show_colorful_info failed in session viewer: %s", exc
                )
            return

        div_win.unbind("<Escape>")

        session_entries = list(current_session_dividends.items())
        idx = {"i": 0}

        viewer = tk.Toplevel(div_win)
        viewer.title("Session Dividends Viewer")
        viewer.transient(div_win)
        viewer.grab_set()
        viewer.resizable(False, False)
        viewer.geometry("520x280")
        viewer.configure(bg="#e8f4f8")

        try:
            push_window(viewer, div_win)
        except (RuntimeError, tk.TclError) as exc:
            logger.debug("push_window for viewer failed: %s", exc)

        try:
            viewer.focus_set()
        except tk.TclError:
            pass

        content = tk.Frame(viewer, bg="#e8f4f8")
        content.pack(fill="both", expand=True, padx=10, pady=10)

        left_btn = tk.Button(content, text="◀", width=3, bg="#b2dfdb")
        left_btn.pack(side="left", padx=(10, 5), pady=6)
        right_btn = tk.Button(content, text="▶", width=3, bg="#b2dfdb")
        right_btn.pack(side="right", padx=(5, 10), pady=6)

        info_text = tk.Text(
            content, wrap="word", height=9, bg="#ffffff", bd=1, relief="solid"
        )
        info_text.pack(fill="both", expand=True, padx=10, pady=6)

        try:
            info_text.tag_configure(
                "label", font=("Helvetica", 11, "bold"), foreground="#004d40"
            )
            info_text.tag_configure(
                "value", font=("Helvetica", 11), foreground="#37474f"
            )
            info_text.tag_configure(
                "net", font=("Helvetica", 11, "bold"), foreground="#1b5e20"
            )
        except tk.TclError as exc:
            logger.debug("info_text.tag_configure failed: %s", exc)

        info_text.config(state="disabled")

        status_label = tk.Label(
            content, text="", font=("Helvetica", 10, "bold"), bg="#e8f4f8"
        )
        status_label.pack(side="bottom", pady=(0, 6))

        def update_view():
            i = idx["i"]
            sr, d = session_entries[i]
            try:
                info_text.config(state="normal")
                info_text.delete("1.0", "end")
                info_text.insert("end", "Sr. No: ", "label")
                info_text.insert("end", f"{sr}\n", "value")
                info_text.insert("end", "Company: ", "label")
                info_text.insert("end", f"{d.get('Company')}\n", "value")
                info_text.insert("end", "Type: ", "label")
                info_text.insert("end", f"{d.get('Type')}\n", "value")
                info_text.insert("end", "Record Dt: ", "label")
                info_text.insert("end", f"{d.get('Record Dt')}\n", "value")
                info_text.insert("end", "Entitled Qty: ", "label")
                info_text.insert("end", f"{d.get('Qty')}\n", "value")
                info_text.insert("end", "Div Percent: ", "label")
                info_text.insert("end", f"{d.get('Percent')}%\n", "value")
                info_text.insert("end", "Net Benefit: ", "label")
                info_text.insert("end", f"₹{d.get('Net'):.2f}\n", "net")
            except Exception as e:
                logger.debug("info_text update failed: %s", e)
            finally:
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
            safe_close_modal(viewer, div_win)
            div_win.bind("<Escape>", _close_div)
            return "break"

        viewer.bind("<Escape>", close_viewer)
        viewer.protocol("WM_DELETE_WINDOW", close_viewer)
        viewer.bind("<Return>", close_viewer)

        ok_v_btn = tk.Button(
            content,
            text="OK",
            width=10,
            command=close_viewer,
            bg="#004d40",
            fg="white",
        )
        ok_v_btn.pack(side="bottom", pady=(0, 8))
        try:
            ok_v_btn.focus_set()
        except tk.TclError:
            pass

        update_view()

    # --- UI Layout Design (Two-Row Grids per Frame) ---

    header_frame = tk.Frame(div_win, bg=headbg, relief="raised", bd=3)
    header_frame.pack(fill="x", padx=5, pady=0)
    title_label = tk.Label(
        header_frame,
        text="💼 DIVIDEND ENTRY SYSTEM 💼",
        font=("Comic Sans MS", 18, "bold"),
        bg=headbg,
        fg=titlefg,
        pady=8,
    )
    title_label.pack(fill="x")

    rat_frame = tk.Frame(
        div_win, bg=ratframebg, padx=15, pady=0, relief="raised", bd=2
    )
    rat_frame.pack(fill="both", expand=True, padx=10, pady=10)

    # 1. Company Frame
    comp_frame = tk.Frame(
        rat_frame, bg=compisinbg, relief="groove", bd=2, padx=10, pady=5
    )
    comp_frame.pack(fill="x", pady=5)
    tk.Label(
        comp_frame,
        bg=compisinbg,
        text="Company",
        font=("Helvetica", 12, "bold"),
    ).grid(row=0, column=0, sticky="w", padx=5)
    tk.Label(
        comp_frame, bg=compisinbg, text="ISIN", font=("Helvetica", 12, "bold")
    ).grid(row=0, column=1, sticky="w", padx=15)
    tk.Label(
        comp_frame,
        bg=compisinbg,
        text="Face Val",
        font=("Helvetica", 12, "bold"),
    ).grid(row=0, column=2, sticky="w", padx=15)

    company_combo = ttk.Combobox(
        comp_frame,
        font=("Helvetica", 14),
        textvariable=company_name_var,
        values=companies,
        width=40,
    )
    company_combo.grid(row=1, column=0, padx=5, pady=5)
    progressive_selection(company_combo, companies)
    company_name_var.trace_add("write", _on_company_selected)

    isin_entry = tk.Entry(
        comp_frame,
        font=("Helvetica", 14),
        textvariable=isin_var,
        state="readonly",
        width=16,
    )
    isin_entry.grid(row=1, column=1, padx=15, pady=5)

    fv_entry = tk.Entry(
        comp_frame,
        font=("Helvetica", 14),
        textvariable=face_value_var,
        state="normal",
        width=10,
    )
    fv_entry.grid(row=1, column=2, padx=15, pady=5)
    fv_entry.bind("<KeyRelease>", _calculate_amounts)
    entries["fv"] = fv_entry

    # 2. Date Frame
    date_frame = tk.Frame(
        rat_frame, bg=qoqbg, relief="ridge", bd=2, padx=10, pady=5
    )
    date_frame.pack(fill="x", pady=5)
    tk.Label(
        date_frame, bg=qoqbg, text="Nature", font=("Helvetica", 12, "bold")
    ).grid(row=0, column=0, sticky="w", padx=5)
    tk.Label(
        date_frame,
        bg=qoqbg,
        text="Record Date",
        font=("Helvetica", 12, "bold"),
    ).grid(row=0, column=1, sticky="w", padx=15)
    tk.Label(
        date_frame, bg=qoqbg, text="Ex-Date", font=("Helvetica", 12, "bold")
    ).grid(row=0, column=2, sticky="w", padx=15)

    type_combo = ttk.Combobox(
        date_frame,
        font=("Helvetica", 14),
        textvariable=div_type_var,
        values=["INTERIM", "FINAL", "SPECIAL", "YEARLY"],
        state="readonly",
        width=14,
    )
    type_combo.grid(row=1, column=0, padx=5, pady=5)

    record_dt_entry = DateEntry(
        date_frame, date_pattern="dd-mm-yyyy", font=("Helvetica", 14), width=12
    )
    record_dt_entry.grid(row=1, column=1, padx=15, pady=5)

    # Corrected Record Date bindings
    record_dt_entry.bind("<<DateEntrySelected>>", _check_existing_record)
    record_dt_entry.bind("<FocusOut>", _check_existing_record, add="+")

    ex_dt_entry = DateEntry(
        date_frame, date_pattern="dd-mm-yyyy", font=("Helvetica", 14), width=12
    )
    ex_dt_entry.grid(row=1, column=2, padx=15, pady=5)

    bind_date_spin(record_dt_entry, callback=_check_existing_record)
    bind_date_spin(ex_dt_entry)

    # 3. Quantities Frame
    qty_frame = tk.Frame(
        rat_frame, bg=rbnnbg, relief="ridge", bd=2, padx=10, pady=5
    )
    qty_frame.pack(fill="x", pady=5)
    tk.Label(
        qty_frame,
        bg=rbnnbg,
        text="Entitled Qty",
        font=("Helvetica", 12, "bold"),
    ).grid(row=0, column=0, sticky="w", padx=5)
    tk.Label(
        qty_frame,
        bg=rbnnbg,
        text="Div Percent (%)",
        font=("Helvetica", 12, "bold"),
    ).grid(row=0, column=1, sticky="w", padx=15)
    tk.Label(
        qty_frame,
        bg=rbnnbg,
        text="Amt/Share (₹)",
        font=("Helvetica", 12, "bold"),
    ).grid(row=0, column=2, sticky="w", padx=15)

    qty_entry = tk.Entry(
        qty_frame,
        font=("Helvetica", 14),
        textvariable=entitled_qty_var,
        width=14,
    )
    qty_entry.grid(row=1, column=0, padx=5, pady=5)
    qty_entry.bind("<KeyRelease>", _calculate_amounts)
    entries["qty"] = qty_entry

    pct_entry = tk.Entry(
        qty_frame,
        font=("Helvetica", 14),
        textvariable=div_percent_var,
        width=14,
    )
    pct_entry.grid(row=1, column=1, padx=15, pady=5)
    pct_entry.bind("<KeyRelease>", _calculate_amounts)
    entries["pct"] = pct_entry

    ps_entry = tk.Entry(
        qty_frame,
        font=("Helvetica", 14),
        textvariable=per_share_amt_var,
        state="readonly",
        width=14,
    )
    ps_entry.grid(row=1, column=2, padx=15, pady=5)

    # 4. Totals Frame
    amt_frame = tk.Frame(
        rat_frame, bg=wbtbg, relief="groove", bd=2, padx=10, pady=5
    )
    amt_frame.pack(fill="x", pady=5)
    tk.Label(
        amt_frame,
        bg=wbtbg,
        text="Gross Amt (₹)",
        font=("Helvetica", 12, "bold"),
    ).grid(row=0, column=0, sticky="w", padx=5)
    tk.Label(
        amt_frame,
        bg=wbtbg,
        text="TDS Deducted (₹)",
        font=("Helvetica", 12, "bold"),
    ).grid(row=0, column=1, sticky="w", padx=15)

    tk.Label(
        amt_frame, bg=wbtbg, text="Payment Dt", font=("Helvetica", 12, "bold")
    ).grid(row=0, column=2, sticky="w", padx=15)

    tk.Label(
        amt_frame,
        bg=wbtbg,
        text="Net Benefit (₹)",
        font=("Helvetica", 12, "bold"),
    ).grid(row=0, column=3, sticky="w", padx=15)

    gross_entry = tk.Entry(
        amt_frame,
        font=("Helvetica", 14),
        textvariable=gross_amt_var,
        state="readonly",
        width=14,
    )
    gross_entry.grid(row=1, column=0, padx=5, pady=5)

    tds_entry = tk.Entry(
        amt_frame, font=("Helvetica", 14), textvariable=tds_amt_var, width=14
    )
    tds_entry.grid(row=1, column=1, padx=15, pady=5)
    tds_entry.bind("<KeyRelease>", _calculate_amounts)
    entries["tds"] = tds_entry

    credit_dt_entry = DateEntry(
        amt_frame, date_pattern="dd-mm-yyyy", font=("Helvetica", 14), width=12
    )
    credit_dt_entry.grid(row=1, column=2, padx=15, pady=5)
    bind_date_spin(credit_dt_entry)

    net_entry = tk.Entry(
        amt_frame,
        font=("Helvetica", 14),
        textvariable=net_amt_var,
        state="readonly",
        width=14,
        fg="#c62828",
    )
    net_entry.grid(row=1, column=3, padx=15, pady=5)

    # 5. Metadata Frame
    meta_frame = tk.Frame(
        rat_frame, bg=gssbg, relief="ridge", bd=2, padx=10, pady=5
    )
    meta_frame.pack(fill="x", pady=5)
    tk.Label(
        meta_frame, bg=gssbg, text="FY Label", font=("Helvetica", 12, "bold")
    ).grid(row=0, column=0, sticky="w", padx=5)
    tk.Label(
        meta_frame, bg=gssbg, text="Notes", font=("Helvetica", 12, "bold")
    ).grid(row=0, column=1, sticky="w", padx=15)

    fy_entry = tk.Entry(
        meta_frame, font=("Helvetica", 14), textvariable=fy_label_var, width=12
    )
    fy_entry.grid(row=1, column=0, padx=5, pady=5)
    entries["fy"] = fy_entry

    note_entry = tk.Entry(
        meta_frame, font=("Helvetica", 14), textvariable=note_var, width=64
    )
    note_entry.grid(row=1, column=1, padx=15, pady=5)
    entries["note"] = note_entry

    # --- Apply Global Styles ---
    theme_widgets = {
        "company_combo": company_combo,
        "isin_entry": isin_entry,
        "fv_entry": fv_entry,
        "type_combo": type_combo,
        "record_dt_entry": record_dt_entry,
        "ex_dt_entry": ex_dt_entry,
        "credit_dt_entry": credit_dt_entry,
        "qty_entry": qty_entry,
        "pct_entry": pct_entry,
        "ps_entry": ps_entry,
        "gross_entry": gross_entry,
        "tds_entry": tds_entry,
        "net_entry": net_entry,
        "fy_entry": fy_entry,
        "note_entry": note_entry,
    }

    for key, widget in theme_widgets.items():
        is_ro = key in ["isin_entry", "ps_entry", "gross_entry", "net_entry"]
        apply_entry_theme(widget, is_readonly=is_ro)

    # Add Context Menus & Tooltips
    for widget in entries.values():
        _create_context_menu(widget)

    bind_tooltip(
        company_combo,
        tooltip_var,
        "Type to search and select the company. ISIN and Face Value will auto-populate.",
    )
    bind_tooltip(
        isin_entry,
        tooltip_var,
        "The unique International Securities Identification Number (auto-populated).",
    )
    bind_tooltip(
        fv_entry,
        tooltip_var,
        "The face value of the stock. Used to calculate the dividend amount per share.",
    )
    bind_tooltip(
        type_combo,
        tooltip_var,
        "Select the nature of the dividend (Interim, Final, Special, etc.).",
    )
    bind_tooltip(
        record_dt_entry,
        tooltip_var,
        "The cut-off date to determine which shareholders receive the dividend.",
    )
    bind_tooltip(
        ex_dt_entry,
        tooltip_var,
        "The date the stock starts trading without the value of its next dividend payment.",
    )
    bind_tooltip(
        credit_dt_entry,
        tooltip_var,
        "The estimated date when the dividend amount will hit your bank account.",
    )
    bind_tooltip(
        qty_entry,
        tooltip_var,
        "Quantity of shares held on the Record Date. This auto-calculates if records exist.",
    )
    bind_tooltip(
        pct_entry,
        tooltip_var,
        "Dividend percentage declared by the company. Usually based on Face Value.",
    )
    bind_tooltip(
        ps_entry,
        tooltip_var,
        "The calculated dividend amount per single share (Face Value × Div Percent).",
    )
    bind_tooltip(
        gross_entry,
        tooltip_var,
        "The total gross dividend amount before any tax deductions (Qty × Amt/Share).",
    )
    bind_tooltip(
        tds_entry,
        tooltip_var,
        "Tax Deducted at Source, if any. This will be subtracted from the Gross Amount.",
    )
    bind_tooltip(
        net_entry,
        tooltip_var,
        "The final net amount that will be credited to your bank account (Gross - TDS).",
    )
    bind_tooltip(
        fy_entry,
        tooltip_var,
        "Financial Year label (e.g., FY25) for accounting purposes.",
    )
    bind_tooltip(
        note_entry,
        tooltip_var,
        "Any extra remarks or details about this specific dividend transaction.",
    )

    # --- Buttons Frame ---
    btn_frame = tk.Frame(div_win, pady=12, bg=btnfrbg, relief="ridge", bd=2)
    btn_frame.pack(fill="x", anchor="e", padx=10, pady=(0, 10))

    hint_label = tk.Label(
        btn_frame,
        text="[F1] Help  |  [F2] Session Summary  |  [Esc] Cancel",
        font=("Helvetica", 14, "bold"),
        bg=btnfrbg,
        fg="#004d40",
    )
    hint_label.pack(side="left", padx=15)

    save_btn = tk.Button(
        btn_frame,
        text="✅ Save Entry ✅",
        font=("Comic Sans MS", 12, "bold"),
        bg="#22c55e",
        fg="white",
        width=16,
        cursor="hand2",
        activebackground="#16a34a",
        activeforeground="white",
        relief="raised",
        bd=3,
        command=_on_submit,
    )
    save_btn.pack(side="right", padx=15)

    cancel_btn = tk.Button(
        btn_frame,
        text="❌ Cancel ❌",
        font=("Comic Sans MS", 12, "bold"),
        bg=cancelusualbg,
        fg="white",
        width=12,
        cursor="hand2",
        activebackground=cancelactivebg,
        activeforeground="white",
        relief="raised",
        bd=3,
        command=_close_div,
    )
    cancel_btn.pack(side="right", padx=5)

    apply_button_animations(save_btn, "#22c55e", "#2563eb")
    apply_button_animations(cancel_btn, cancelusualbg, cancelactivebg)

    # --- Key Bindings ---
    div_win.bind(
        "<Return>",
        lambda e: on_enter_focus_next(e, div_win, save_btn, cancel_btn),
    )
    div_win.bind("<Escape>", _close_div)
    div_win.bind("<F1>", show_help)
    div_win.bind("<F2>", show_session_dividends)
    div_win.protocol("WM_DELETE_WINDOW", _close_div)

    company_combo.focus_set()

    # --- UPDATE ENGINE: PRE-FILL DATA ---
    if edit_id is not None:
        div_win.title("✨ Update Dividend ✨")
        save_btn.config(text="🚀 Update Entry 🚀")
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT s.company_name, d.id_div, c.id_act, IFNULL(d.ex_dt, c.act_dt), d.credit_dt, d.div_type,
                           d.entitled_qty, d.tds_amt, d.fy_label, IFNULL(d.note_div, c.note_act),
                           c.div_percent_act, d.record_dt, c.div_amount_act
                    FROM corp_acts c
                    JOIN stocks s ON c.id_stk = s.id_stk
                    LEFT JOIN dividends d ON c.id_stk = d.id_stk AND (d.id_act = c.id_act OR d.record_dt = c.act_dt OR d.ex_dt = c.act_dt)
                    WHERE c.id_act = ?
                    """,
                    (edit_id,),
                )
                row = cursor.fetchone()

            if row:
                company_name_var.set(row[0])
                company_combo.config(state="disabled")  # Lock company

                current_id_div_var.set(row[1] if row[1] else 0)
                current_id_act_var.set(row[2])

                try:
                    if row[3]:
                        ex_dt_entry.set_date(
                            datetime.strptime(row[3], "%Y-%m-%d").date()
                        )
                    if row[4]:
                        credit_dt_entry.set_date(
                            datetime.strptime(row[4], "%Y-%m-%d").date()
                        )
                    if row[11]:
                        record_dt_entry.set_date(
                            datetime.strptime(row[11], "%Y-%m-%d").date()
                        )
                except ValueError:
                    pass

                div_type_var.set(row[5] if row[5] else "FINAL")
                entitled_qty_var.set(row[6] if row[6] else 0)
                tds_amt_var.set(row[7] if row[7] else 0.0)
                fy_label_var.set(row[8] if row[8] else "")
                note_var.set(row[9] if row[9] else "")
                div_percent_var.set(row[10] if row[10] else 0.0)
                if row[12]:
                    per_share_amt_var.set(row[12])

                # Update face value and amounts
                if row[0] in company_to_data:
                    face_value_var.set(company_to_data[row[0]]["face_value"])
                _calculate_amounts()

        except sqlite3.Error as e:
            logger.error(f"Failed to fetch dividend data: {e}")

    parent.wait_window(div_win)
    try:
        if parent.winfo_exists():
            parent.grab_set()
    except tk.TclError:
        pass


# File: # File: C:\Data\Personal\Finance_and_Investment\finprog\FinanceManager\StockMan\dividend.py ends here
