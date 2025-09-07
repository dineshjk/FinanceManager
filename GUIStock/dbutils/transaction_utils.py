# -*- coding: utf-8 -*-
# File: c:\Users\aumji\source\repos\Finance\FinanceManager\GUIStock\dbutils\transaction_utils.py

# Core imports
import tkinter as tk
from tkcalendar import DateEntry
import sqlite3
from datetime import datetime
from tkinter import ttk
import logging

# Local imports using new package structure
from FinanceManager.GUIStock.config.globals import (
    get_db_connection, ETCN, ETCB, BROK, GST, SEBI, STT
)
from FinanceManager.GUIStock.dialogs import (
    show_colorful_info, show_colorful_error, show_colorful_yesno
)
from FinanceManager.GUIStock.core.date_utils import next_working_day
from FinanceManager.GUIStock.dbutils.modal_management import (
    disable_parent as centralized_disable_parent,
    enable_parent as centralized_enable_parent
)

# Configure logging for debugging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


# Old disable/enable functions removed - now using centralized modal management
# These functions were causing unresponsive window issues by incorrectly using
# parent.attributes('-disabled', True/False) which doesn't work properly in tkinter


def add_trade(parent: tk.Toplevel, calling_button: tk.Widget = None) -> None:
    """
    Opens a modal window for trade data entry, initializes form widgets, and manages parent window modality.
    Args:
        parent (tk.Toplevel): The parent window to which the modal is attached.
        calling_button (tk.Widget): The button that called this function (for focus restoration).
    Side Effects:
        - Displays an informational message box.
        - Creates and displays a modal data entry window for trade details.
        - Uses centralized modal management for proper focus restoration.
        - Initializes and packs form widgets for contract and trade details.
        - Calls helper functions to create additional widgets and manage window state.
    """
    #messagebox.showinfo("Info", "Add Trade clicked", parent=parent)

    # Use centralized modal window management
    modal_id = centralized_disable_parent(parent, calling_button=calling_button)


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
        "check_qty" : 0,  # This will be updated later
        "total_order_price": 0.0,
        "average_rate": 0.0,
        "levies": 0.0,
    }

    entries = {}
    current_trade_no = 1

    # rat_win private functions

    def fetch_existing_contract(event=None):
        """
        Fetch and populate contract details when the contract number field loses focus.

        Args:
            event: Tkinter event object (optional, for event binding compatibility).

        Side Effects:
            - Updates data["cont_no"] with the stripped contract number from the entry
            - Calls populate_from_contract() to fill contract details if found
            - Sets focus to trade date entry if no contract details found
        """
        data["cont_no"] = cont_no_entry.get().strip()
        if not data["cont_no"]:
            return
        filled = populate_from_contract(data["cont_no"])
        if not filled:
            trd_date_entry.focus_set()

    def populate_from_contract(cont_no) -> bool:
        """
        Populate form fields with contract details if the contract number exists.

        Args:
            cont_no (str): The contract number to look up.

        Action:
            - Queries the database for contract details using the provided contract number.
            - If found, sets the trade date, settlement number, settlement date, and number of trades fields with the retrieved values.
            - Allows the user to edit these fields.

        Returns:
            bool: True if contract details were found and fields populated, False otherwise.
        """
        try:
            q = """
                SELECT trd_dt, settle_no, settle_dt, no_of_trades
                FROM contracts
                WHERE cont_no = ?
                ORDER BY trd_dt DESC
                LIMIT 1
            """
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(q, (cont_no,))
                row = cursor.fetchone()
                cursor.close()
            if row:
                data["trd_dt"], data["settle_no"], data["settle_dt"], data["no_of_trades"] = row
                if data["trd_dt"]:
                    trd_date_entry.set_date(data["trd_dt"]) # Set the value obtained in box
                if data["settle_no"] is not None:
                    settle_no_entry.delete(0, "end") # From position 0 to "end" in the box delete everything
                    settle_no_entry.insert(0, str(data["settle_no"])) # Insert the value obtained in the box
                    settle_no_var.set(str(data["settle_no"])) # Also set the corresponding variable of the class.
                if data["settle_dt"]:
                    settle_date_entry.set_date(data["settle_dt"]) # Set the value obtained in box
                if data["no_of_trades"] is not None:
                    trades_spin.delete(0, "end")
                    trades_spin.insert(0, str(data["no_of_trades"]))
                return True
        except Exception:
            pass
        return False

    def update_settle_no_on_focus(event=None):
        """
        Calculate and update the settlement number when trade date field gets focus.

        Args:
            event: Tkinter event object (optional, for event binding compatibility).

        Side Effects:
            - Retrieves trade date from trd_date_entry widget
            - Calculates settlement number using compute_settle_no_from_db()
            - Updates settlement number entry widget's range and value
            - Sets minimum allowed value to year * 1000 (e.g., 2025000 for year 2025)
            - If any error occurs, falls back to a basic calculation or default
        """
        try:
            trade_date = trd_date_entry.get_date()
            settle_no_calc = compute_settle_no_from_db(trade_date)
            min_allowed = trade_date.year * 1000
            settle_no_entry.config(from_=min_allowed, to=9999999)
            settle_no_var.set(str(settle_no_calc))
        except Exception:
            try:
                settle_no_var.set(str(trd_date_entry.get_date().year * 1000 + 1))
            except Exception:
                pass

    def compute_settle_no_from_db(trade_date) -> int:
        """
        Args:
            trade_date (datetime.date): The trade date for which to compute the settlement number.

        Computes the settlement number, which is yyyynnn, where nnn
        is the current working day number in the year yyyy.
        First it obtains the trade date entered above. Then it searches for
        the immediate preceding date of trade in the database and adds the difference
        between them to the previous settlement number.
        In case, this is not computable, it defaults to yyyy001.
        """
        try:
            q = """
                SELECT trd_dt, settle_no
                FROM contracts
                WHERE trd_dt < ?
                ORDER BY trd_dt DESC
                LIMIT 1
            """
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(q, (trade_date.strftime("%Y-%m-%d"),))
                row = cursor.fetchone()
                cursor.close()
            if row:
                prev_trd_dt_str, prev_settle_no = row[0], row[1]
                prev_trd_date = datetime.strptime(prev_trd_dt_str, "%Y-%m-%d").date()
                try:
                    prev_settle_no_int = int(prev_settle_no) if prev_settle_no not in (None, "") else (prev_trd_date.year * 1000 + 1)
                except Exception:
                    prev_settle_no_int = prev_trd_date.year * 1000 + 1
                day_diff = max((trade_date - prev_trd_date).days, 0)
                return prev_settle_no_int + day_diff
            else:
                return trade_date.year * 1000 + 1
        except Exception:
            return trade_date.year * 1000 + 1


    def update_settle_date_on_focus(event=None):
        """
        Update the settlement date field when the trade date field is focused.
        It uses next_working_day function to compute the next working day.

        Args:
            event (_type_, optional): _description_. Defaults to None.
        """
        try:
            trade_date = trd_date_entry.get_date()
            settle_date_entry.set_date(next_working_day(trade_date))
        except Exception:
            try:
                settle_date_entry.set_date(trd_date_entry.get_date())
            except Exception:
                pass

    def on_radio_key(event, radio_btn, value):
        """
        Handle key events for radio buttons.

        Args:
            event (tk.Event): The key event.
            radio_btn (tk.Radiobutton): The radio button instance.
            value (str): The value associated with the radio button.
        Action:
        If the space key is pressed, select the radio button.
            If the right or left arrow key is pressed, select the other radio button.
        """
        if event.keysym == "space":
            buy_sell_var.set(value)
            radio_btn.select()
            # Trigger Net Total EO update when Buy/Sell changes via keyboard
            update_brok_unit_eo_focus_in()
        elif event.keysym in ("Right", "Left"):
            # Toggle focus between Buy and Sell on Left/Right arrow
            if radio_btn == buy_radio:
                sell_radio.focus_set()
                sell_radio.select()
            else:
                buy_radio.focus_set()
                buy_radio.select()

    # === FORMATTING FUNCTIONS ===

    def format_rate_eo_on_focus_out(event=None):
        """
        Format Rate EO field to 2 decimal places when focus is lost.

        Args:
            event: Tkinter focus event (optional, defaults to None).

        Side Effects:
            - Formats rate_eo_var to exactly 2 decimal places
            - Handles conversion errors gracefully
            - Triggers recalculation of dependent fields
        """
        try:
            current_value = rate_eo_var.get()
            formatted_value = round(current_value, 2)
            rate_eo_var.set(f"{formatted_value:.2f}")
            # Trigger dependent calculations
            update_brok_unit_eo_focus_in()
        except (ValueError, tk.TclError):
            # Handle any conversion errors gracefully
            pass

    def format_wap_on_focus_out(event=None):
        """
        Format Weighted Average Price field to 4 decimal places when focus is lost.

        Args:
            event: Tkinter focus event (optional, defaults to None).

        Side Effects:
            - Formats wap_var to exactly 4 decimal places
            - Handles conversion errors gracefully
        """
        try:
            current_value = wap_var.get()
            formatted_value = round(current_value, 4)
            wap_var.set(f"{formatted_value:.4f}")
        except (ValueError, tk.TclError):
            # Handle any conversion errors gracefully
            pass

    def recalculate_from_wap_change(event=None):
        """
        Recalculate all dependent fields when Weighted Average Price changes.

        This function cascades changes from WAP to:
        - Brokerage Per Share (WAP * BROK)
        - Lot Price (WAP * quantity)
        - Lot Brokerage (Lot Price * BROK)
        - All levy calculations
        - Net Trade Amount

        Args:
            event: Tkinter event (optional, defaults to None).

        Side Effects:
            - Updates brs_var, lp_var, tot_brok_var
            - Recalculates all levy fields (etc, sebi, gst, stt, etc.)
            - Updates net_trade_var
            - Formats all values to appropriate decimal places
        """
        try:
            wap_value = wap_var.get()
            qty_trd_value = qty_trd_var.get()

            if wap_value <= 0 or qty_trd_value <= 0:
                return

            # Calculate Brokerage Per Share (WAP * BROK)
            brs_value = round(wap_value * BROK, 4)
            brs_var.set(f"{brs_value:.4f}")

            # Calculate Lot Price (WAP * quantity)
            lp_value = round(wap_value * qty_trd_value, 4)
            lp_var.set(f"{lp_value:.4f}")

            # Calculate Lot Brokerage (Lot Price * BROK)
            tot_brok_value = round(lp_value * BROK, 4)
            tot_brok_var.set(f"{tot_brok_value:.4f}")

            # Reset levies accumulator
            data["levies"] = tot_brok_value

            # Calculate Exchange Charge (ETC)
            etc_rate = ETCN if exchange_var.get() == "NSE" else ETCB
            etc_value = round((lp_value + tot_brok_value) * etc_rate, 4)
            etc_var.set(f"{etc_value:.4f}")
            data["levies"] += etc_value

            # Calculate SEBI Charge
            sebi_value = round(lp_value * SEBI, 4)
            sebi_var.set(f"{sebi_value:.4f}")
            data["levies"] += sebi_value

            # Calculate GST
            gst_value = round((tot_brok_value + etc_value + sebi_value) * GST, 4)
            gst_var.set(f"{gst_value:.4f}")
            data["levies"] += gst_value

            # Calculate STT
            stt_value = round(lp_value * STT, 4)
            stt_var.set(f"{stt_value:.4f}")
            data["levies"] += stt_value

            # Add current values of other levy fields
            data["levies"] += stamp_duty_var.get()
            data["levies"] += igst_var.get()
            data["levies"] += sell_charge_var.get()

            # Calculate Net Trade Amount
            if buy_sell_var.get() == "BUY":
                net_trade_value = lp_value + data["levies"]
            else:
                net_trade_value = lp_value - data["levies"]

            net_trade_var.set(f"{net_trade_value:.4f}")

            # Update all entry widgets
            for entry in [brs_entry, lp_entry, tot_brok_entry, etc_entry,
                         sebi_entry, gst_entry, stt_entry, net_trade_entry]:
                entry.update_idletasks()

        except (ValueError, tk.TclError, KeyError):
            # Handle any conversion or variable access errors
            pass

    def format_financial_field_on_focus_out(field_var, decimal_places=4):
        """
        Generic function to format financial fields to specified decimal places.

        Args:
            field_var: The tkinter variable to format
            decimal_places: Number of decimal places (default: 4)

        Returns:
            Callable function for use with event binding
        """
        def format_field(event=None):
            try:
                current_value = field_var.get()
                if current_value == 0:
                    formatted_value = 0.0
                else:
                    formatted_value = round(current_value, decimal_places)
                field_var.set(f"{formatted_value:.{decimal_places}f}")
            except (ValueError, tk.TclError):
                pass
        return format_field

    def validate_positive_financial_input(event=None):
        """
        Validate that financial input fields contain only positive numbers.

        Args:
            event: Tkinter event containing the widget

        Side Effects:
            - Highlights invalid entries with red background
            - Resets invalid entries to 0
        """
        try:
            widget = event.widget
            value = float(widget.get())
            if value < 0:
                widget.config(bg="#ffcccc")  # Light red background
                widget.after(1000, lambda: widget.config(bg="white"))
                # Optionally reset to 0
                # widget.delete(0, tk.END)
                # widget.insert(0, "0.00")
            else:
                widget.config(bg="white")
        except (ValueError, tk.TclError):
            # Invalid input - highlight in red
            event.widget.config(bg="#ffcccc")
            event.widget.after(1000, lambda: event.widget.config(bg="white"))

    # Select radio button when clicked
    def on_radio_click(radio_btn, value):
        buy_sell_var.set(value)
        radio_btn.select()
        radio_btn.focus_set()
        # Trigger Net Total EO update when Buy/Sell changes
        update_brok_unit_eo_focus_in()


    def on_ex_radio_key(event, radio_btn, value):
        """
        Handle key events for radio buttons.

        Args:
            event (tk.Event): The key event.
            radio_btn (tk.Radiobutton): The radio button instance.
            value (str): The value associated with the radio button.
        Action:
        If the space key is pressed, select the radio button.
            If the right or left arrow key is pressed, select the other radio button.
        """
        if event.keysym == "space":
            exchange_var.set(value)
            radio_btn.select()
        elif event.keysym in ("Right", "Left"):
            # Toggle focus between Buy and Sell on Left/Right arrow
            if radio_btn == nse_radio:
                bse_radio.focus_set()
                bse_radio.select()
            else:
                nse_radio.focus_set()
                nse_radio.select()
    # Triggers and Helping Functions

    # Bind Enter and Escape keys for OK/Cancel actions
    def on_enter(event=None) -> None:
        """
        When the Enter key is pressed, this function is triggered.
        First it checks if the focus is on the Cancel button. If so,
        then it triggers the cancel action. In all the other cases it
        triggers the OK action.

        Args:
            event (_type_, optional): _description_. Defaults to None.
        """
        if rat_win.focus_get() == cancel_btn:
            cancel_btn.invoke()
        else:
            ok_btn.invoke()

    def on_escape(event=None) -> None:
        cleanup_and_close()

    def cleanup_and_close():
        """Clean up and close the window with proper focus restoration."""
        centralized_enable_parent(modal_id)
        rat_win.destroy()

    #On clicking OK or pressing enter in add trade
    def on_ok() -> None:
        # This marks end of the current trade in the existing contract.
        nonlocal current_trade_no

        try:
            # Update transactions table with final values
            with get_db_connection() as conn:
                cursor = conn.cursor()

                # Update the transactions table with all calculated values
                cursor.execute("""
                    UPDATE transactions
                    SET wap_unit_trd = ?, brok_unit_trd = ?, price_lot_trd = ?,
                        brok_lot_trd = ?, etc_trd = ?, sebi_trd = ?,
                        sell_chrg_trd = ?, gst_trd = ?, stamp_trd = ?,
                        stt_trd = ?, igst_trd = ?, net_amt_trd = ?
                    WHERE cont_no = ? AND company_name = ? AND id_trd = ?
                """, (
                    wap_var.get(),           # wap_unit_trd
                    brs_var.get(),           # brok_unit_trd
                    lp_var.get(),            # price_lot_trd
                    tot_brok_var.get(),      # brok_lot_trd
                    etc_var.get(),           # etc_trd
                    sebi_var.get(),          # sebi_trd
                    sell_charge_var.get(),   # sell_chrg_trd
                    gst_var.get(),           # gst_trd
                    stamp_duty_var.get(),    # stamp_trd
                    stt_var.get(),           # stt_trd
                    igst_var.get(),          # igst_trd
                    net_trade_var.get(),     # net_amt_trd
                    data["cont_no"],         # WHERE cont_no
                    data["company_name"],    # WHERE company_name
                    data["id_trd"]           # WHERE id_trd
                ))

                # Update the contracts table with aggregated values
                cursor.execute("""
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
                        no_of_trades = (SELECT COUNT(*) FROM transactions WHERE cont_no = ?)
                    WHERE cont_no = ?
                """, (data["cont_no"], data["cont_no"], data["cont_no"], data["cont_no"],
                      data["cont_no"], data["cont_no"], data["cont_no"], data["cont_no"],
                      data["cont_no"], data["cont_no"], data["cont_no"]))

                # Commit the changes
                conn.commit()

        except Exception as e:
            # Handle any database errors gracefully
            logging.error(f"Error updating transactions table: {str(e)}")

        # Check if there are more trades to enter in this contract
        if current_trade_no < no_of_trades_var.get():
            # Increment current trade number
            current_trade_no += 1
            current_trade_no_var.set(current_trade_no)

            # Reset trade-specific fields for next trade entry
            # Reset data dictionary for next trade
            data["check_qty"] = 0
            data["total_order_price"] = 0.0
            data["average_rate"] = 0.0
            data["levies"] = 0.0

            # Clear trade-specific form fields but keep contract details
            qty_trd_var.set(0)
            ord_no_var.set(0)
            trd_no_var.set(0)
            qty_eo_var.set(0)
            rate_eo_var.set(0.0)
            brok_unit_eo_var.set(0.0)
            net_rate_eo_var.set(0.0)
            net_total_eo_var.set(0.0)

            # Clear calculated fields
            wap_var.set(0.0)
            brs_var.set(0.0)
            lp_var.set(0.0)
            tot_brok_var.set(0.0)
            etc_var.set(0.0)
            sebi_var.set(0.0)
            gst_var.set(0.0)
            stt_var.set(0.0)
            stamp_duty_var.set(0.0)
            igst_var.set(0.0)
            sell_charge_var.set(0.0)
            net_trade_var.set(0.0)

            # For subsequent trades, keep contract-level fields disabled
            # Only enable trade-specific fields
            # Contract fields remain disabled: cont_no_entry, trd_date_entry,
            # settle_date_entry, settle_no_entry, trades_spin
            # current_trade_no_entry remains readonly (it's already readonly)

            # Enable trade-specific fields for next trade
            company_entry.config(state="normal")
            buy_radio.config(state="normal")
            sell_radio.config(state="normal")

            # Clear company selection for new trade
            company_name_var.set("")
            isin_var.set("")

            # Reset buy/sell to default
            buy_sell_var.set("BUY")

            # Set focus to company name field for next trade
            company_entry.focus_set()

            # Show message about next trade
            show_colorful_info(rat_win, "✅ Trade Complete",
                              f"Trade {current_trade_no - 1} completed successfully.\n"
                              f"Please enter details for Trade {current_trade_no}.")
        else:
            # All trades completed, close the window
            show_colorful_info(rat_win, "🎉 Contract Complete",
                              f"All {no_of_trades_var.get()} trades for "
                              f"contract {data['cont_no']} have been completed successfully.")

            # Ask if user wants to add another trade
            response = show_colorful_yesno(rat_win, "🔄 Add Another Trade?",
                                           "Do you want to add another trade?")

            if response:  # User clicked Yes
                # Reset everything for a fresh start
                reset_form_for_new_contract()
            else:  # User clicked No
                cleanup_and_close()

    def reset_form_for_new_contract():
        """
        Reset the entire form to initial state for adding a new contract/trade.
        All fields are enabled except permanently disabled ones (current_trade_no, isin).
        """
        nonlocal current_trade_no

        # Reset current trade number to 1
        current_trade_no = 1
        current_trade_no_var.set(current_trade_no)

        # Reset all data dictionary values
        data.clear()
        data.update({
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
        })

        # Clear all form fields
        # Contract level fields
        cont_no_var.set("")
        trd_dt_var.set("")
        settle_no_var.set(0)
        settle_dt_var.set("")
        no_of_trades_var.set(1)

        # Company and trade type fields
        company_name_var.set("")
        isin_var.set("")
        buy_sell_var.set("BUY")

        # Trade specific fields
        qty_trd_var.set(0)
        ord_no_var.set(0)
        trd_no_var.set(0)
        qty_eo_var.set(0)
        rate_eo_var.set(0.0)
        brok_unit_eo_var.set(0.0)
        net_rate_eo_var.set(0.0)
        net_total_eo_var.set(0.0)
        exchange_var.set("NSE")

        # Calculated fields
        wap_var.set(0.0)
        brs_var.set(0.0)
        lp_var.set(0.0)
        tot_brok_var.set(0.0)
        etc_var.set(0.0)
        sebi_var.set(0.0)
        gst_var.set(0.0)
        stt_var.set(0.0)
        stamp_duty_var.set(0.0)
        igst_var.set(0.0)
        sell_charge_var.set(0.0)
        net_trade_var.set(0.0)

        # Enable all fields except permanently disabled ones
        # Contract level fields - enable all
        cont_no_entry.config(state="normal")
        trd_date_entry.config(state="normal")
        settle_no_entry.config(state="normal")
        settle_date_entry.config(state="normal")
        trades_spin.config(state="normal")

        # Company and trade fields - enable all
        company_entry.config(state="normal")
        buy_radio.config(state="normal")
        sell_radio.config(state="normal")

        # Trade specific fields should already be enabled
        # Exchange radio buttons should already be enabled

        # Submit button should be enabled
        submit_btn.config(state="normal")
        nse_radio.config(state="normal")
        bse_radio.config(state="normal")

        # current_trade_no_entry remains readonly (permanently disabled)
        # isin_entry remains readonly (permanently disabled)

        # Set focus to contract number field to start fresh
        cont_no_entry.focus_set()
        cont_no_entry.select_range(0, "end")

    def update_isin(*args):
        """
        Update the ISIN field based on the selected company name.

        Args:
            *args: Variable arguments (for trace callback compatibility).

        Side Effects:
            - Queries the database for the ISIN of the selected company
            - Updates the isin_var with the found ISIN or empty string if not found
            - Manages database connection automatically using context manager
        """
        selected_company = company_name_var.get()
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT isin FROM stocks WHERE company_name = ?", (selected_company,))
            row = cursor.fetchone()
            cursor.close()
        isin_var.set(row[0] if row else "")

    def on_company_key(event):
        """
        Handle keyboard navigation in the company combobox for quick company selection.

        Args:
            event: Tkinter keyboard event containing the pressed key information.

        Returns:
            str: "break" to prevent default event handling, None otherwise.

        Behavior:
            - For alphabetic keys: Cycles through companies starting with that letter
            - For Return/Space: Confirms current selection and keeps focus
            - If no companies match the typed character, prevents further processing

        Side Effects:
            - Changes the current selection in the company combobox
            - Updates company_name_var with the selected company name
            - Sets cursor position to end of text for Return/Space keys
        """
        if not companies:
            return

        char = event.char.lower()
        if char and char.isalpha():
            current_idx = company_entry.current()

            # Find all companies starting with this character
            matches = [i for i, name in enumerate(companies) if name.lower().startswith(char)]
            if not matches:
                return "break"

            # If current selection starts with the same character, cycle to next
            if current_idx in matches:
                current_pos = matches.index(current_idx)
                next_idx = matches[(current_pos + 1) % len(matches)]
            else:
                # Jump to first match if current doesn't start with this character
                next_idx = matches[0]

            # Set the new selection
            company_entry.current(next_idx)
            company_name_var.set(companies[next_idx])
            return "break"

        elif event.keysym in ("Return", "space"):
            # Select current value, keep focus
            company_name_var.set(company_entry.get())
            company_entry.icursor(tk.END)
            company_entry.focus_set()
            return "break"

    def on_qty_trd_focus(event=None):
        """
        Update database tables when quantity trade field gets focus.

        Handles contract and transaction record creation/updating when user
        focuses on the quantity trade field, indicating they're ready to
        enter trade quantity information.

        Args:
            event: Tkinter focus event (optional, defaults to None).

        Side Effects:
            - Creates or updates records in contracts table
            - Creates or updates records in transactions table
            - Makes company_name, cont_no, and trd_dt fields readonly
            - Sets focus to qty_trd_entry field
            - Updates GUI state to reflect database operations
            - May display error messages if database operations fail
        """
        try:
            # Get current form values
            cont_no = cont_no_var.get().strip()
            company_name = company_name_var.get().strip()

            # Skip if essential data is missing
            if not cont_no or not company_name:
                return

            # Populate data dictionary with current form values
            data["cont_no"] = cont_no
            data["trd_dt"] = trd_dt_var.get()
            data["settle_no"] = settle_no_var.get()
            data["settle_dt"] = settle_dt_var.get()
            data["no_of_trades"] = no_of_trades_var.get()
            data["company_name"] = company_name
            data["trade_type_trd"] = buy_sell_var.get()

            # Database operations for contracts and transactions tables
            with get_db_connection() as conn:
                cursor = conn.cursor()

                # First, get the id_stk for the selected company
                cursor.execute("SELECT id_stk FROM stocks WHERE company_name = ?", (data["company_name"],))
                stock_result = cursor.fetchone()
                if not stock_result:
                    return

                id_stk = stock_result[0]
                data["id_stk"] = id_stk

                # Handle contracts table - update if exists, insert if not
                cursor.execute("SELECT COUNT(*) FROM contracts WHERE cont_no = ?", (data["cont_no"],))
                contract_exists = cursor.fetchone()[0] > 0

                if contract_exists:
                    # Update existing contract
                    cursor.execute("""
                        UPDATE contracts
                        SET trd_dt = ?, settle_no = ?, settle_dt = ?, no_of_trades = ?
                        WHERE cont_no = ?
                    """, (data["trd_dt"], data["settle_no"], data["settle_dt"],
                          data["no_of_trades"], data["cont_no"]))
                else:
                    # Insert new contract
                    cursor.execute("""
                        INSERT INTO contracts (cont_no, trd_dt, settle_no, settle_dt, no_of_trades)
                        VALUES (?, ?, ?, ?, ?)
                    """, (data["cont_no"], data["trd_dt"], data["settle_no"],
                          data["settle_dt"], data["no_of_trades"]))

                # Handle transactions table - check if combination exists (including id_stk)
                cursor.execute("""
                    SELECT id_trd FROM transactions
                    WHERE cont_no = ? AND company_name = ? AND id_stk = ?
                """, (data["cont_no"], data["company_name"], id_stk))

                result = cursor.fetchone()
                if result:
                    # Update existing transaction
                    data["id_trd"] = result[0]
                    cursor.execute("""
                        UPDATE transactions
                        SET trd_dt = ?, trade_type_trd = ?
                        WHERE id_trd = ?
                    """, (data["trd_dt"], data["trade_type_trd"], data["id_trd"]))
                else:
                    # Insert new transaction with id_stk
                    cursor.execute("""
                        INSERT INTO transactions (cont_no, trd_dt, company_name, trade_type_trd, id_stk)
                        VALUES (?, ?, ?, ?, ?)
                    """, (data["cont_no"], data["trd_dt"], data["company_name"], data["trade_type_trd"], id_stk))
                    data["id_trd"] = cursor.lastrowid

                # Commit all changes
                conn.commit()

                # After successful database operations, make fields readonly
                cont_no_entry.config(state="readonly")

                # DateEntry widgets need special handling
                trd_date_entry.config(state="disabled")
                settle_date_entry.config(state="disabled")

                # Spinbox widgets
                settle_no_entry.config(state="disabled")
                trades_spin.config(state="disabled")

                # Combobox widget
                company_entry.config(state="disabled")

                # Radio buttons
                buy_radio.config(state="disabled")
                sell_radio.config(state="disabled")

                # Set focus to quantity trade field
                qty_trd_entry.focus_set()

        except Exception as e:
            # Handle errors gracefully without disrupting user experience
            pass

    def update_qty_eo_during_qty_trd(*args):
        """
        Update quantity EO to match quantity trade value when trade quantity changes.

        Automatically sets the execution order quantity to match the trade quantity,
        assuming full execution of the trade. Also updates the spinbox range to
        allow values from 1 to the calculated quantity.

        Args:
            *args: Variable arguments (for trace callback compatibility).

        Side Effects:
            - Updates qty_eo_var to match qty_trd_var value
            - Reconfigures qty_eo_entry spinbox range (from_=1, to=calculated_qty_eo)
            - Sets minimum quantity to 1 if calculated value is 0 or negative
        """
        try:
            qty_trd_value = qty_trd_var.get()
            if qty_trd_value > 0:
                calculated_qty_eo = qty_trd_value
                qty_eo_var.set(calculated_qty_eo)
                # Update the Spinbox range to allow values from 1 to calculated_qty_eo
                qty_eo_entry.config(from_=1, to=calculated_qty_eo)
            else:
                # If calculated value is 0 or negative, set to 1
                qty_eo_var.set(1)
                qty_eo_entry.config(from_=1, to=1)
        except (ValueError, tk.TclError):
            # Handle any conversion or widget errors
            pass

    def update_ord_dt_on_focus(event=None):
        """
        Update the order date field with trade date when it gets focus.

        Automatically copies the trade date to the order date field when the
        order date field receives focus, ensuring consistency between dates.

        Args:
            event: Tkinter focus event (optional, defaults to None).

        Side Effects:
            - Updates ord_date_entry with the current trade date value
            - Handles conversion errors gracefully
        """
        try:
            # Get the current trade date
            trade_date = trd_date_entry.get_date()
            # Set the order date to the same as trade date
            ord_dt_entry.set_date(trade_date)
        except Exception:
            # If there's any error, silently pass
            pass

    def update_check_qty_on_focus_out_of_qty_eo(event=None):
        """
        Update check quantity when quantity EO field loses focus.

        Adds the current execution order quantity to the running total of
        checked quantities, tracking how much of the trade has been allocated
        to execution orders.

        Args:
            event: Tkinter focus event (optional, defaults to None).

        Side Effects:
            - Increments data["check_qty"] by the current qty_eo_value
            - Handles conversion errors and undefined variable access gracefully
        """
        try:
            qty_eo_value = qty_eo_var.get()
            data["check_qty"] += qty_eo_value
        except (ValueError, tk.TclError, NameError):
            # Handle any conversion or variable access errors
            pass

    def update_qty_eo_on_focus_in(event=None):
        """
        Update quantity EO when the field gets focus.

        Calculates and sets the remaining quantity that can be allocated to
        execution orders by subtracting already checked quantities from the
        total trade quantity.

        Args:
            event: Tkinter focus event (optional, defaults to None).

        Side Effects:
            - Updates qty_eo_var with calculated remaining quantity
            - Uses global data["check_qty"] for calculation
        """
        remaining_qty = qty_trd_var.get() - data["check_qty"]
        qty_eo_var.set(remaining_qty)

    def update_brok_unit_eo_focus_in(event=None):
        """
        Calculate and update brokerage and net values when brok_unit_eo gets focus.

        Performs automatic calculations for brokerage, net rate, and net total
        when the brokerage unit EO field receives focus, ensuring all financial
        calculations remain synchronized.

        Args:
            event: Tkinter focus event (optional, defaults to None).

        Side Effects:
            - Calculates and updates brok_unit_eo_var based on rate_eo and BROK constant
            - Updates net_rate_eo_var by adding rate_eo and brok_unit_eo
            - Calculates and updates net_total_eo_var based on qty_eo and net_rate_eo
            - Formats all values to 4 decimal places
            - Handles calculation errors gracefully
        """
        try:
            rate_eo_value = float(rate_eo_var.get())
            brok_unit_eo_value = round(BROK * rate_eo_value, 4)
            brok_unit_eo_var.set(f"{brok_unit_eo_value:.4f}")
            net_rate_eo_value = round(rate_eo_value + brok_unit_eo_value, 4) if buy_sell_var.get() == "BUY" else round(rate_eo_value + brok_unit_eo_value, 4)
            net_rate_eo_var.set(f"{net_rate_eo_value:.4f}")
            net_total_eo_value = round(qty_eo_var.get() * net_rate_eo_value, 4)
            net_total_eo_var.set(f"{net_total_eo_value:.4f}")
            qty_trd_value = qty_trd_var.get()
            qty_eo_value = qty_eo_var.get()
        except Exception:
            # Handle any conversion or widget errors
            pass

    # Function to update sell_charge_entry state based on buy_sell_var
    def update_sell_charge_state(*args):
        """
        Update the sell charge entry field state based on buy/sell selection.

        Controls the accessibility of the sell charge field - makes it readonly
        for BUY transactions and normal (editable) for SELL transactions.

        Args:
            *args: Variable arguments (for trace callback compatibility).

        Side Effects:
            - Sets sell_charge_entry to readonly state for BUY transactions
            - Sets sell_charge_entry to normal state for SELL transactions
        """
        if buy_sell_var.get().upper() == "BUY":
            sell_charge_entry.config(state="readonly")
        else:
            sell_charge_entry.config(state="normal")

    def on_submit(event=None):
        """
        Handle form submission and database operations for trading transactions.

        This is the main submission handler that processes all trading data,
        validates quantities, updates database records, and manages the GUI state.
        It handles both creation and updates of exchange orders and transactions.

        Args:
            event: Tkinter event (optional, defaults to None).

        Process Flow:
            1. Disables UI controls during processing
            2. Validates ordered quantity against traded quantity
            3. Handles cleanup if validation fails
            4. Updates transactions table with current form data
            5. Creates or updates exchange_orders records
            6. Resets form fields for next entry or closes window

        Side Effects:
            - Disables submit button and radio buttons during processing
            - Updates transactions table with qty_trd and exchange data
            - Creates or updates exchange_orders table records
            - Deletes related records if quantity validation fails
            - Resets form fields for continued data entry
            - May close the window and exit on validation errors
            - Updates data dictionary with current form values
            - Manages database transactions with proper error handling
            - Updates GUI state and focus for user workflow
        """

        # Disable submit button and radio buttons during processing
        submit_btn.config(state="disabled")
        nse_radio.config(state="disabled")
        bse_radio.config(state="disabled")

        # Check if ordered quantity exceeds traded quantity
        if data["check_qty"] > qty_trd_var.get():
            show_colorful_error(rat_win, "⚠️ Quantity Error",
                "Ordered quantity is greater than the traded quantity.")

            # Delete current trade and related records
            try:
                with get_db_connection() as conn:
                    cursor = conn.cursor()

                    # Delete all exchange orders with current id_trd
                    cursor.execute("""
                        DELETE FROM exchange_orders
                        WHERE id_trd = ?
                    """, (data["id_trd"],))

                    # Delete the current trade from transactions
                    cursor.execute("""
                        DELETE FROM transactions
                        WHERE cont_no = ? AND company_name = ?
                    """, (data["cont_no"], data["company_name"]))

                    # Check if there are any other trades with the same contract number
                    cursor.execute("""
                        SELECT COUNT(*) FROM transactions
                        WHERE cont_no = ?
                    """, (data["cont_no"],))

                    if cursor.fetchone()[0] == 0:
                        # No other trades with this contract, delete from contracts table
                        cursor.execute("""
                            DELETE FROM contracts
                            WHERE cont_no = ?
                        """, (data["cont_no"],))

                    conn.commit()

            except Exception as e:
                logging.error(f"Error deleting records: {str(e)}")

            # Close the window and exit completely
            cleanup_and_close()
            return

        try:
            # Populate data dictionary with current form values
            data["qty_trd"] = qty_trd_var.get()
            data["exchange"] = exchange_var.get()
            # data["id_trd"] already set from on_qty_trd_focus
            data["ord_no"] = ord_no_var.get()
            data["ord_dt"] = ord_dt_var.get()
            data["trd_no"] = trd_no_var.get()
            data["qty_eo"] = qty_eo_var.get()
            data["rate_eo"] = rate_eo_var.get()
            data["brok_unit_eo"] = brok_unit_eo_var.get()
            data["net_rate_eo"] = net_rate_eo_var.get()
            data["net_total_eo"] = net_total_eo_var.get()
            data["total_order_price"] += data["qty_eo"] * data["rate_eo"]
            # data["cont_no"] and data["company_name"] already set

            # Validate critical data before proceeding
            required_fields = ["cont_no", "company_name", "id_trd"]
            missing_fields = [field for field in required_fields if field not in data or data[field] is None]

            if missing_fields:
                return  # Exit early if critical data is missing

            with get_db_connection() as conn:
                cursor = conn.cursor()
                # Update transactions table
                cursor.execute("""
                    UPDATE transactions
                    SET qty_trd = ?, exchange = ?
                    WHERE cont_no = ? AND company_name = ?
                """, (data["qty_trd"], data["exchange"], data["cont_no"], data["company_name"]))

                # Need to change this tomorrow
                # if data["check_qty"] < data["qty_trd"] then we should execute this.
                if data["check_qty"] < data["qty_trd"]:
                    # Add qty_eo * rate_eo to total_order_price

                    # Check if exchange_orders row exists
                    cursor.execute("""
                        SELECT COUNT(*) FROM exchange_orders
                        WHERE ord_no = ? AND ord_dt = ?
                    """, (data["ord_no"], data["ord_dt"]))

                    if cursor.fetchone()[0] > 0:
                        # Update existing exchange_orders row
                        cursor.execute("""
                            UPDATE exchange_orders
                            SET id_trd = ?, trd_no = ?, qty_eo = ?, rate_eo = ?,
                                brok_unit_eo = ?, net_rate_eo = ?, net_total_eo = ?
                            WHERE ord_no = ? AND ord_dt = ?
                        """, (data["id_trd"], data["trd_no"], data["qty_eo"], data["rate_eo"],
                              data["brok_unit_eo"], data["net_rate_eo"], data["net_total_eo"],
                              data["ord_no"], data["ord_dt"]))
                    else:
                        # Insert new exchange_orders row
                        cursor.execute("""
                            INSERT INTO exchange_orders
                            (id_trd, ord_no, ord_dt, trd_no, qty_eo, rate_eo, brok_unit_eo, net_rate_eo, net_total_eo)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (data["id_trd"], data["ord_no"], data["ord_dt"], data["trd_no"],
                              data["qty_eo"], data["rate_eo"], data["brok_unit_eo"],
                              data["net_rate_eo"], data["net_total_eo"]))

                    # Reset fields and set focus to ord_no_entry
                    ord_no_var.set(0)
                    trd_no_var.set(0)
                    rate_eo_var.set(0.0)
                    brok_unit_eo_var.set(0.0)
                    net_rate_eo_var.set(0.0)
                    net_total_eo_var.set(0.0)

                    # Set qty_eo maximum limit to check_qty
                    # Ensure check_qty is valid before setting
                    if data["check_qty"] < 1:
                        data["check_qty"] = 1

                    # Force widget update by setting both from and to
                    qty_eo_entry.config(from_=1, to=data["qty_trd"] - data["check_qty"])

                    # Force widget refresh
                    qty_eo_entry.update_idletasks()

                    # Set focus to ord_no_entry
                    ord_no_entry.focus_set()
                    ord_no_entry.select_range(0, "end")

                else:  # check_qty == data["qty_trd"]
                    # Check if exchange_orders row exists
                    cursor.execute("""
                        SELECT COUNT(*) FROM exchange_orders
                        WHERE ord_no = ? AND ord_dt = ?
                    """, (data["ord_no"], data["ord_dt"]))

                    if cursor.fetchone()[0] > 0:
                        # Update existing exchange_orders row
                        cursor.execute("""
                            UPDATE exchange_orders
                            SET id_trd = ?, trd_no = ?, qty_eo = ?, rate_eo = ?,
                                brok_unit_eo = ?, net_rate_eo = ?, net_total_eo = ?
                            WHERE ord_no = ? AND ord_dt = ?
                        """, (data["id_trd"], data["trd_no"], data["qty_eo"], data["rate_eo"],
                              data["brok_unit_eo"], data["net_rate_eo"], data["net_total_eo"],
                              data["ord_no"], data["ord_dt"]))
                    else:
                        # Insert new exchange_orders row
                        cursor.execute("""
                            INSERT INTO exchange_orders
                            (id_trd, ord_no, ord_dt, trd_no, qty_eo, rate_eo, brok_unit_eo, net_rate_eo, net_total_eo)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (data["id_trd"], data["ord_no"], data["ord_dt"], data["trd_no"],
                              data["qty_eo"], data["rate_eo"], data["brok_unit_eo"],
                              data["net_rate_eo"], data["net_total_eo"]))

                    # Calculate average rate and populate form fields
                    data["average_rate"] = data["total_order_price"] / data["qty_trd"]

                    # Reset levies to zero before calculating
                    data["levies"] = 0.0

                    # Set wap_entry (weighted average price)
                    wap_var.set(data['average_rate'])
                    wap_entry.update_idletasks()

                    # Set brs_entry (brokerage per share)
                    brs_value = data["average_rate"] * BROK
                    brs_var.set(f"{brs_value:.4f}")
                    brs_entry.update_idletasks()

                    # Set lp_entry (lot price)
                    lp_value = data["average_rate"] * data["qty_trd"]
                    lp_var.set(f"{lp_value:.4f}")
                    lp_entry.update_idletasks()

                    # Set tot_brok_entry (total brokerage)
                    tot_brok_value = lp_value * BROK
                    tot_brok_var.set(f"{tot_brok_value:.4f}")
                    tot_brok_entry.update_idletasks()
                    data["levies"] += tot_brok_value

                    # Set etc_entry (exchange charge)
                    etc_rate = ETCN if data["exchange"] == "NSE" else ETCB
                    etc_value = (lp_value + tot_brok_value) * etc_rate
                    etc_var.set(f"{etc_value:.4f}")
                    etc_entry.update_idletasks()
                    data["levies"] += etc_value

                    # Set sebi_entry (SEBI charge)
                    sebi_value = lp_value * SEBI
                    sebi_var.set(f"{sebi_value:.4f}")
                    sebi_entry.update_idletasks()
                    data["levies"] += sebi_value

                    # Set gst_entry (GST)
                    gst_value = (tot_brok_value + etc_value + sebi_value) * GST
                    gst_var.set(f"{gst_value:.4f}")
                    gst_entry.update_idletasks()
                    data["levies"] += gst_value

                    # Set stt_entry (STT)
                    stt_value = lp_value * STT
                    stt_var.set(f"{stt_value:.4f}")
                    stt_entry.update_idletasks()
                    data["levies"] += stt_value

                    # Set stamp_duty_entry (set to 0 or calculated value)
                    stamp_duty_value = 0.0  # Can be calculated if needed
                    stamp_duty_var.set(f"{stamp_duty_value:.4f}")
                    stamp_duty_entry.update_idletasks()
                    data["levies"] += stamp_duty_value

                    # Set igst_entry (set to 0 or calculated value)
                    igst_value = 0.0  # Can be calculated if needed
                    igst_var.set(f"{igst_value:.4f}")
                    igst_entry.update_idletasks()
                    data["levies"] += igst_value

                    # Set sell_charge_entry (set to 0 or calculated value)
                    sell_charge_value = 0.0  # Can be calculated if needed
                    sell_charge_var.set(f"{sell_charge_value:.4f}")
                    sell_charge_entry.update_idletasks()
                    data["levies"] += sell_charge_value

                    # Set net_trade_entry based on buy/sell
                    if buy_sell_var.get() == "BUY":
                        net_trade_value = lp_value + data["levies"]
                    else:
                        net_trade_value = lp_value - data["levies"]
                    net_trade_var.set(f"{net_trade_value:.4f}")
                    net_trade_entry.update_idletasks()                    # Set focus to wap_entry
                    wap_entry.focus_set()
                    wap_entry.select_range(0, "end")
                # Commit all changes
                conn.commit()

        except Exception as e:
            # Handle errors gracefully
            logging.error(f"Error occurred: {str(e)}")
            logging.error(f"Data at time of error: {data}")
            logging.error(f"check_qty value: {data['check_qty']}")
            pass


    # rat_win creation with enhanced styling
    rat_win = tk.Toplevel(parent) # A Toplevel Window
    rat_win.title("✨ Data Entry - Trade ✨") # Enhanced title with emojis
    rat_win.geometry("1078x855") # Size of the Window
    rat_win.resizable(False, False) # Disable resizing

    # Set a beautiful gradient-like background
    rat_win.configure(bg="#f0f8ff")  # Alice blue background
    # The transient popup stays on top of its parent.
    # It minimizes/restores with the parent.
    # It doesn’t appear separately in the taskbar.
    rat_win.transient(parent) # Set as transient to parent
    # It grabs all clicks and other activities while open restricting every other window
    rat_win.grab_set()
    # Set focus to the new window and take all keyboard input
    rat_win.focus_set()

    # --- Integer Validation Settlement No ---
    def validate_int(P):
        return P.isdigit() or P == ""
    int_vcmd = (rat_win.register(validate_int), "%P")


    # Enhanced Heading with gradient effect
    header_frame = tk.Frame(rat_win, bg="#1e3a8a", relief="raised", bd=3)
    header_frame.pack(fill="x", padx=5, pady=5)

    # Main title with fancy styling
    title_label = tk.Label(header_frame, text="💼 DATA ENTRY SYSTEM 💼",
                          font=("Comic Sans MS", 18, "bold"),
                          bg="#1e3a8a", fg="#ffd700", pady=8,
                          relief="ridge", bd=2)
    title_label.pack(fill="x")

    # Subtitle with different color scheme
    subtitle_label = tk.Label(header_frame, text="📊 Contract & Trade Details 📊",
                             font=("Arial", 14, "italic"),
                             bg="#dc2626", fg="#ffffff", pady=4,
                             relief="groove", bd=1)
    subtitle_label.pack(fill="x")

    # Add a decorative separator with rainbow-like colors
    rainbow_frame = tk.Frame(rat_win, height=8, relief="flat")
    rainbow_frame.pack(fill="x", padx=5)

    # Create rainbow strip effect
    colors = ["#ff0000", "#ff8000", "#ffff00", "#80ff00", "#00ff00",
              "#00ff80", "#00ffff", "#0080ff", "#0000ff", "#8000ff",
              "#ff00ff", "#ff0080"]
    for i, color in enumerate(colors):
        strip = tk.Frame(rainbow_frame, bg=color, height=2)
        strip.pack(side="left", fill="both", expand=True)

    # rat_frame starting point with enhanced styling
    # This is the area reserved for the form to contain widgets
    rat_frame = tk.Frame(rat_win, bg="#f8fafc", padx=15, pady=15,
                        relief="raised", bd=2)
    rat_frame.pack(fill="both", expand=True, padx=10, pady=5)

    # Create a two line frame to hold three fields with enhanced styling
    cont_frame = tk.Frame(rat_frame, bg="#e0f2fe", relief="ridge", bd=2,
                         padx=10, pady=8)
    cont_frame.grid(row=1, column=0, rowspan=2, columnspan=5, sticky="ew",
                   pady=10)

    # cont_frame starts
    # Label and Entry within cont_frame with enhanced styling
    cont_label_frame = tk.Frame(cont_frame, bg="#e0f2fe")
    cont_label_frame.pack(fill="x", pady=(0, 5))

    cont_entry_frame = tk.Frame(cont_frame, bg="#e0f2fe")
    cont_entry_frame.pack(fill="x", pady=(0, 5))

    # Enhanced decorative separator with multiple colors and effects
    separator4 = tk.Frame(rat_frame, height=15, relief="raised", bd=3)
    separator4.grid(row=3, column=0, columnspan=4, sticky="ew", pady=15)

    # Create a fancy separator with gradient-like effect
    sep_colors = ["#fbbf24", "#f59e0b", "#d97706", "#b45309", "#92400e"]
    for i, color in enumerate(sep_colors):
        sep_strip = tk.Frame(separator4, bg=color, height=3)
        sep_strip.pack(fill="both", expand=True)
    separator4.grid(row=3, column=0, columnspan=4, sticky="ew", pady=8)

    # Create one line frame for company and isin with enhanced styling
    company_isin_frame = tk.Frame(rat_frame, bg="#fef3c7", relief="groove",
                                 bd=2, padx=8, pady=6)
    company_isin_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=5)

    # Create a two line frame to hold three fields with enhanced styling
    qoq_frame = tk.Frame(rat_frame, bg="#dcfce7", relief="ridge", bd=2,
                        padx=8, pady=6)
    qoq_frame.grid(row=5, column=0, rowspan=2, columnspan=3, sticky="ew",
                  pady=5)

    # Create a horizontal frame for the labels (first row) with styling
    qoq_label_frame = tk.Frame(qoq_frame, bg="#dcfce7")
    qoq_label_frame.pack(fill="x", pady=(0, 2))

    # Create a horizontal frame for the entry widgets (second row) with styling
    qoq_entry_frame = tk.Frame(qoq_frame, bg="#dcfce7")
    qoq_entry_frame.pack(fill="x", pady=(0, 2))

    # Create a two line frame to hold three fields with enhanced styling
    rbnn_frame = tk.Frame(rat_frame, bg="#fce7f3", relief="ridge", bd=2,
                         padx=8, pady=6)
    rbnn_frame.grid(row=7, column=0, rowspan=2, columnspan=4, sticky="ew",
                   pady=5)

    # Create a horizontal frame for the labels with styling
    rbnn_label_frame = tk.Frame(rbnn_frame, bg="#fce7f3")
    rbnn_label_frame.pack(fill="x", pady=(0, 2))

    # Create a horizontal frame for the entry widgets with styling
    rbnn_entry_frame = tk.Frame(rbnn_frame, bg="#fce7f3")
    rbnn_entry_frame.pack(fill="x", pady=(0, 2))

    # Create a horizontal frame for the entry widgets with enhanced styling
    wbt_frame = tk.Frame(rat_frame, bg="#ede9fe", relief="groove", bd=2,
                        padx=8, pady=6)
    wbt_frame.grid(row=9, column=0, rowspan=2, columnspan=4, sticky="ew",
                  pady=5)

    wbt_label_frame = tk.Frame(wbt_frame, bg="#ede9fe")
    wbt_label_frame.pack(fill="x", pady=(0, 2))

    wbt_entry_frame = tk.Frame(wbt_frame, bg="#ede9fe")
    wbt_entry_frame.pack(fill="x", pady=(0, 2))

    # Create a horizontal frame for the entry widgets with enhanced styling
    gss_frame = tk.Frame(rat_frame, bg="#f0fdf4", relief="ridge", bd=2,
                        padx=8, pady=6)
    gss_frame.grid(row=11, column=0, rowspan=2, columnspan=4, sticky="ew",
                  pady=5)

    gss_label_frame = tk.Frame(gss_frame, bg="#f0fdf4")
    gss_label_frame.pack(fill="x", pady=(0, 2))

    gss_entry_frame = tk.Frame(gss_frame, bg="#f0fdf4")
    gss_entry_frame.pack(fill="x", pady=(0, 2))


# cont_frame starts here
    # --- Contract No field starts here ---
    tk.Label(cont_label_frame, text="Cont No",font=("Helvetica", 14)).pack(side="left", padx=(10, 0))
    cont_no_var = tk.StringVar()
    cont_no_entry = tk.Entry(cont_entry_frame, textvariable=cont_no_var, width=25, font=("Helvetica", 14))
    cont_no_entry.pack(side="left", padx=(10, 0))
    cont_no_entry.focus_set()
    entries["cont_no"] = cont_no_entry
    # --- Contract No field ends here ---


    # --- Trade Date field starts here ---
    tk.Label(cont_label_frame, text="Trade Dt", font=("Helvetica", 14)).pack(side="left", padx=(215, 0))
    trd_dt_var = tk.StringVar()
    trd_date_entry = DateEntry(cont_entry_frame, textvariable=trd_dt_var, date_pattern="yyyy-mm-dd", width=10, font=("Helvetica", 14))
    trd_date_entry.pack(side="left", padx=15)
    entries["trd_dt"] = trd_date_entry
    # --- Trade Date field ends here ---


    # --- Settlement No field starts here ---
    tk.Label(cont_label_frame, text="Settle No", font=("Helvetica", 14)).pack(side="left", padx=(80,0))
    settle_no_var = tk.IntVar()
    settle_no_entry = tk.Spinbox(cont_entry_frame, from_=0, to=9999999, width=7, textvariable=settle_no_var, validate="key", validatecommand=int_vcmd, font=("Helvetica", 14))
    settle_no_entry.pack(side="left", padx=15)
    entries["settle_no"] = settle_no_entry
    # --- Settlement No field ends here ---

    # --- Settlement Date field starts here ---
    tk.Label(cont_label_frame, text="Settle Dt", font=("Helvetica", 14)).pack(side="left", padx=(50,0))
    settle_dt_var = tk.StringVar()
    settle_date_entry = DateEntry(cont_entry_frame, textvariable=settle_dt_var, date_pattern="yyyy-mm-dd", width=10, font=("Helvetica", 14))
    settle_date_entry.pack(side="left", padx=15)
    entries["settle_dt"] = settle_date_entry
    # --- Settlement Date field ends here ---

    # --- No of Trades field starts here ---
    tk.Label(cont_label_frame, text="No of Trades", font=("Helvetica", 14)).pack(side="left", padx=(80,0))
    no_of_trades_var = tk.IntVar()
    trades_spin = tk.Spinbox(cont_entry_frame, from_=1, to=10, width=6, textvariable=no_of_trades_var, validate="key", validatecommand=int_vcmd, font=("Helvetica", 14))
    trades_spin.pack(side="left", padx=15)
    entries["no_of_trades"] = trades_spin
    # --- No of Trades field ends here ---

    # --- Current Trade No field starts here ---
    tk.Label(cont_label_frame, text="Current Trade No", font=("Helvetica", 14)).pack(side="left", padx=(15,0))
    current_trade_no_var = tk.IntVar(value = current_trade_no)
    current_trade_no_entry = tk.Entry(cont_entry_frame, textvariable=current_trade_no_var, width=6, font=("Helvetica", 14), state="readonly")
    current_trade_no_entry.pack(side="left", padx=40)
    entries["current_trade_no"] = current_trade_no_entry
    # --- Current Trade No field ends here ---


# cont_frame ends here

# company_isin_frame starts here

    # --- Company and ISIN fields start here ---
    tk.Label(company_isin_frame, text="Company", font=("Helvetica", 14)).pack(side="left", padx=(5, 0))
    # Create a Combobox for company selection, populated from DB

    # Fetch companies from DB
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT company_name, isin FROM stocks ORDER BY company_name ASC")
        companies = [row[0] for row in cursor.fetchall()]
        cursor.close()

    company_name_var = tk.StringVar()
    isin_var = tk.StringVar()
    company_entry = ttk.Combobox(company_isin_frame, textvariable=company_name_var, values=companies, width=38, font=("Helvetica", 14))
    company_entry.pack(side="left", padx=15)
    entries["company"] = company_entry

    # ISIN display (uneditable)
    tk.Label(company_isin_frame, text="ISIN", font=("Helvetica", 14)).pack(side="left", padx=(3, 0))
    isin_entry = tk.Entry(company_isin_frame, textvariable=isin_var, width=12, font=("Helvetica", 14), state="readonly")
    isin_entry.pack(side="left", padx=15)
    entries["isin"] = isin_entry

    company_name_var.trace_add("write", lambda *args: update_isin())
    # Set initial ISIN if company is pre-selected
    if company_name_var.get():
        update_isin()

    entries["company"] = company_entry
    # --- Company and ISIN fields end here ---


    # --- Buy/Sell radio buttons start here ---
    tk.Label(company_isin_frame, text="BUY/SELL", font=("Helvetica", 14)).pack(side="left", padx=(10, 0), pady=2)
    buy_sell_var = tk.StringVar(value="BUY")

    buy_radio = tk.Radiobutton(company_isin_frame, text="BUY", variable=buy_sell_var, value="BUY", font=("Helvetica", 14))
    buy_radio.pack(side="left", padx=10)
    sell_radio = tk.Radiobutton(company_isin_frame, text="SELL", variable=buy_sell_var, value="SELL", font=("Helvetica", 14))
    sell_radio.pack(side="left")
    entries["trade_type_trd"] = buy_sell_var
    # --- Buy/Sell radio buttons end here ---
# company_isin_frame ends here

# qoq_frame starts here

    # --- Quantity Trade field starts here ---

    tk.Label(qoq_label_frame, text="Qty Trade", font=("Helvetica", 14)).pack(side="left", padx=(0, 0), pady=4)
    qty_trd_var = tk.IntVar()
    qty_trd_entry = tk.Spinbox(qoq_entry_frame, from_=1, to=100000, width=4, textvariable=qty_trd_var, validate="key", validatecommand=int_vcmd, font=("Helvetica", 14))
    qty_trd_entry.pack(side="left", padx=(0, 5), pady=4)
    entries["qty_trd"] = qty_trd_entry
    # --- Quantity Trade field ends here ---

    # --- Order No field starts here ---
    tk.Label(qoq_label_frame, text="Order No", font=("Helvetica", 14)).pack(side="left", padx=(7, 0))
    ord_no_var = tk.IntVar()
    ord_no_entry = tk.Entry(qoq_entry_frame, textvariable=ord_no_var, validate="key", validatecommand=int_vcmd, width=21, font=("Helvetica", 14))
    ord_no_entry.pack(side="left", padx=(30, 0))
    entries["ord_no"] = ord_no_entry

    # --- Order No field ends here ---

    # --- Order Date field starts here ---

    tk.Label(qoq_label_frame, text="Order Date", font=("Helvetica", 14)).pack(side="left", padx=(180,0))
    ord_dt_var = tk.StringVar()
    ord_dt_entry = DateEntry(qoq_entry_frame, textvariable=ord_dt_var, date_pattern="yyyy-mm-dd", width=10, font=("Helvetica", 14))
    ord_dt_entry.pack(side="left", padx=(30, 0))
    entries["ord_dt"] = ord_dt_entry
    # --- Order Date field ends here ---

    # --- Trade No field starts here ---
    tk.Label(qoq_label_frame, text="Trade No", font=("Helvetica", 14)).pack(side="left", padx=(60,0))
    trd_no_var = tk.IntVar()
    trd_no_entry = tk.Entry(qoq_entry_frame, textvariable=trd_no_var, validate="key", validatecommand=int_vcmd, width=21, font=("Helvetica", 14))
    trd_no_entry.pack(side="left", padx=(30, 0))
    entries["trd_no"] = trd_no_entry
    # --- Trade No field ends here ---

    # --- Qty EO field starts here ---
    tk.Label(qoq_label_frame, text="Qty EO", font=("Helvetica", 14)).pack(side="left", padx=(185,0))
    qty_eo_var = tk.IntVar()
    qty_eo_entry = tk.Spinbox(qoq_entry_frame, from_=1, to=100000, width=6, textvariable=qty_eo_var, validate="key", validatecommand=int_vcmd, font=("Helvetica", 14))
    qty_eo_entry.pack(side="left", padx=(30, 0))
    entries["qty_eo"] = qty_eo_entry

    # Now that both qty_trd_var and qty_eo_var are defined, bind the update function
    qty_trd_var.trace_add("write", update_qty_eo_during_qty_trd)

    # def update_qty_eo_on_focus_in_ord_no(event=None):
    #     """Update qty_eo_var when ord_no_entry gets focus"""
    #     nonlocal check_qty
    #     remaining_qty = qty_trd_var.get() - check_qty
    #     qty_eo_var.set(remaining_qty)

    # --- Qty EO field ends here ---

# qoq_frame ends here

# rbnn_frame starts here
    # --- Rate EO field starts here ---
    tk.Label(rbnn_label_frame, text="Rate EO", font=("Helvetica", 14)).pack(side="left", padx=(0,0))
    rate_eo_var = tk.DoubleVar()
    rate_eo_entry = tk.Entry(rbnn_entry_frame, textvariable=rate_eo_var, width=11, font=("Helvetica", 14))
    rate_eo_entry.pack(side="left", padx=(0,5))
    entries["rate_eo"] = rate_eo_entry
    # --- Rate EO field ends here ---

    # --- Brok Unit EO field starts here ---
    tk.Label(rbnn_label_frame, text="Brok Unit EO", font=("Helvetica", 14)).pack(side="left", padx=(70,0))
    brok_unit_eo_var = tk.DoubleVar()
    brok_unit_eo_entry = tk.Entry(rbnn_entry_frame, textvariable=brok_unit_eo_var, width=11, font=("Helvetica", 14))
    brok_unit_eo_entry.pack(side="left", padx=15)
    entries["brok_unit_eo"] = brok_unit_eo_entry
    # --- Brok Unit EO field ends here ---

    # --- Net Rate EO field starts here ---
    tk.Label(rbnn_label_frame, text="Net Rate EO", font=("Helvetica", 14)).pack(side="left", padx=(35,0))
    net_rate_eo_var = tk.DoubleVar()
    net_rate_eo_entry = tk.Entry(rbnn_entry_frame, textvariable=net_rate_eo_var, width=11, font=("Helvetica", 14))
    net_rate_eo_entry.pack(side="left", padx=15)
    entries["net_rate_eo"] = net_rate_eo_entry
    # --- Net Rate EO field ends here ---

    # --- Net Total EO field starts here ---
    tk.Label(rbnn_label_frame, text="Net Total EO", font=("Helvetica", 14)).pack(side="left", padx=(40, 0))
    net_total_eo_var = tk.DoubleVar()
    net_total_eo_entry = tk.Entry(rbnn_entry_frame, textvariable=net_total_eo_var, width=11, font=("Helvetica", 14))
    net_total_eo_entry.pack(side="left", padx=15)
    entries["net_total_eo"] = net_total_eo_entry

    # --- Net Total EO field ends here ---

    # --- Exchange radio buttons field starts here ---
    tk.Label(rbnn_label_frame, text="Exchange", font=("Helvetica", 14)).pack(side="left", padx=(70, 0), pady=2)
    exchange_var = tk.StringVar(value="NSE")


    nse_radio = tk.Radiobutton(rbnn_entry_frame, text="NSE", variable=exchange_var, value="NSE", font=("Helvetica", 14))
    nse_radio.pack(side="left", padx=10)
    bse_radio = tk.Radiobutton(rbnn_entry_frame, text="BSE", variable=exchange_var, value="BSE", font=("Helvetica", 14))
    bse_radio.pack(side="left")

    # Bind FocusOut event to both radio buttons
    # nse_radio.bind("<FocusOut>", on_exchange_focus_out)
    # bse_radio.bind("<FocusOut>", on_exchange_focus_out)
    entries["exchange"] = exchange_var
    # --- Exchange radio buttons field ends here ---


    # --- Submit button field starts here with fancy styling ---
    submit_btn = tk.Button(rbnn_entry_frame, text="🚀 Submit 🚀", width=15,
                           font=("Comic Sans MS", 14, "bold"),
                           bg="#22c55e", fg="white",
                           activebackground="#16a34a",
                           activeforeground="white",
                           relief="raised", bd=3,
                           cursor="hand2",
                           command=on_submit)
    submit_btn.pack(side="left", padx=30)

    # Function to enable submit button when qty_eo_entry gets focus
    def enable_submit_on_qty_eo_focus(event=None):
        """Enable submit button when qty_eo_entry gets focus"""
        submit_btn.config(state="normal")

    # --- Submit button field ends here ---




# wbt_frame starts here

    # --- Weighted Average Price field starts here ---
    tk.Label(wbt_label_frame, text="Wgt.Av.Price.", font=("Helvetica", 14)).pack(side="left", padx=(0, 0), pady=2)
    wap_var = tk.DoubleVar()
    wap_entry = tk.Entry(wbt_entry_frame, textvariable=wap_var, width=11, font=("Helvetica", 14))
    wap_entry.pack(side="left", padx=0)
    entries["wap_unit_trd"] = wap_entry
    # --- Weighted Average Price field ends here ---

    # --- Brokerage per Share field starts here ---
    tk.Label(wbt_label_frame, text="Brok/Share", font=("Helvetica", 14)).pack(side="left", padx=(25, 0), pady=2)
    brs_var = tk.DoubleVar()
    brs_entry = tk.Entry(wbt_entry_frame, textvariable=brs_var, width=11, font=("Helvetica", 14))
    brs_entry.pack(side="left", padx=15)
    entries["brok_unit_trd"] = brs_entry
    # --- Brokerage per Share field ends here ---

    # --- Lot Price field starts here ---
    tk.Label(wbt_label_frame, text="Lot Price", font=("Helvetica", 14)).pack(side="left", padx=(50, 0), pady=2)
    lp_var = tk.DoubleVar()
    lp_entry = tk.Entry(wbt_entry_frame, textvariable=lp_var, width=11, font=("Helvetica", 14))
    lp_entry.pack(side="left", padx=15)
    entries["price_lot_trd"] = lp_entry
    # --- Lot Price field ends here ---

    # --- Lot Brok field starts here ---
    tk.Label(wbt_label_frame, text="Lot Brok", font=("Helvetica", 14)).pack(side="left", padx=(70, 0), pady=2)
    tot_brok_var = tk.DoubleVar()
    tot_brok_entry = tk.Entry(wbt_entry_frame, textvariable=tot_brok_var, width=11, font=("Helvetica", 14))
    tot_brok_entry.pack(side="left", padx=15)
    entries["brok_lot_trd"] = tot_brok_entry
    # --- Lot Brok field ends here ---

    # --- Exchange Charge field starts here ---
    tk.Label(wbt_label_frame, text="ETC", font=("Helvetica", 14)).pack(side="left", padx=(75, 0), pady=2)
    etc_var = tk.DoubleVar()
    etc_entry = tk.Entry(wbt_entry_frame, textvariable=etc_var, width=11, font=("Helvetica", 14))
    etc_entry.pack(side="left", padx=15)
    entries["etc"] = etc_entry
    # --- Exchange Charge field ends here ---

    # --- SEBI Charge field starts here ---
    tk.Label(wbt_label_frame, text="SEBI Charge", font=("Helvetica", 14)).pack(side="left", padx=(110, 0), pady=2)
    sebi_var = tk.DoubleVar()
    sebi_entry = tk.Entry(wbt_entry_frame, textvariable=sebi_var, width=11, font=("Helvetica", 14))
    sebi_entry.pack(side="left", padx=15)
    entries["sebi"] = sebi_entry
    # --- SEBI Charge field ends here ---

    # --- Sell Charge field starts here ---
    tk.Label(wbt_label_frame, text="Sell Charge", font=("Helvetica", 14)).pack(side="left", padx=(40, 0), pady=2)
    sell_charge_var = tk.DoubleVar()
    sell_charge_entry = tk.Entry(wbt_entry_frame, textvariable=sell_charge_var, width=11, font=("Helvetica", 14), state="readonly" if buy_sell_var.get().upper() == "BUY" else "normal")
    sell_charge_entry.pack(side="left", padx=15)
    entries["sell_charge"] = sell_charge_entry

    # Trace buy_sell_var changes to update entry state
    buy_sell_var.trace_add("write", lambda *a: update_sell_charge_state())
    # Initial state update
    update_sell_charge_state()

    def update_levies_and_net_trade(event=None):
        """Update levies and net_trade_entry when any levy field value changes"""
        try:
            # Recalculate levies with all components
            data["levies"] = (
                tot_brok_var.get() +      # brok_lot_trd
                etc_var.get() +           # etc_trd
                sebi_var.get() +          # sebi_trd
                gst_var.get() +           # gst_trd
                stamp_duty_var.get() +    # stamp_trd
                stt_var.get() +           # stt_trd
                igst_var.get() +          # igst_trd
                sell_charge_var.get()     # sell_chrg_trd
            )

            # Recalculate net trade amount
            lp_value = lp_var.get()  # lot price
            if buy_sell_var.get() == "BUY":
                net_trade_value = lp_value + data["levies"]
            else:
                net_trade_value = lp_value - data["levies"]

            # Update net_trade_entry
            net_trade_var.set(f"{net_trade_value:.4f}")
            net_trade_entry.update_idletasks()

        except (ValueError, tk.TclError):
            # Handle any conversion or widget errors
            pass

    # Bind the update function to sell_charge_entry KeyRelease event
    # (Removed - using centralized bindings instead)

    # Bind the update function to tot_brok_entry KeyRelease and FocusOut events
    # (Removed - using centralized bindings instead)

    # Bind the update function to etc_entry KeyRelease and FocusOut events
    # (Removed - using centralized bindings instead)

    # Bind the update function to sebi_entry KeyRelease and FocusOut events
    # (Removed - using centralized bindings instead)
    # --- Sell Charge field ends here ---

# rbnn_frame starts here
    # --- GST field starts here ---
    tk.Label(gss_label_frame, text="GST", font=("Helvetica", 14)).pack(side="left", padx=(0, 0), pady=2)
    gst_var = tk.DoubleVar()
    gst_entry = tk.Entry(gss_entry_frame, textvariable=gst_var, width=11, font=("Helvetica", 14))
    gst_entry.pack(side="left", padx=(0, 5))
    entries["gst"] = gst_entry

    # --- GST field ends here ---

    # --- Stamp Duty field starts here ---
    tk.Label(gss_label_frame, text="Stamp Duty", font=("Helvetica", 14)).pack(side="left", padx=(100, 0), pady=2)
    stamp_duty_var = tk.DoubleVar()
    stamp_duty_entry = tk.Entry(gss_entry_frame, textvariable=stamp_duty_var, width=11, font=("Helvetica", 14))
    stamp_duty_entry.pack(side="left", padx=15)
    entries["stamp_duty"] = stamp_duty_entry

    # --- Stamp Duty field ends here ---

    # --- STT field starts here ---
    tk.Label(gss_label_frame, text="STT", font=("Helvetica", 14)).pack(side="left", padx=(50, 0), pady=2)
    stt_var = tk.DoubleVar()
    stt_entry = tk.Entry(gss_entry_frame, textvariable=stt_var, width=11, font=("Helvetica", 14))
    stt_entry.pack(side="left", padx=15)
    entries["stt"] = stt_entry

    # --- STT field ends here ---

    # --- IGST field starts here ---
    tk.Label(gss_label_frame, text="IGST", font=("Helvetica", 14)).pack(side="left", padx=(110, 0), pady=2)
    igst_var = tk.DoubleVar()
    igst_entry = tk.Entry(gss_entry_frame, textvariable=igst_var, width=11, font=("Helvetica", 14))
    igst_entry.pack(side="left", padx=15)
    entries["igst"] = igst_entry

    # --- IGST field ends here ---

    # --- Net Trade Amount field starts here ---
    tk.Label(gss_label_frame, text="Net Trade Amt.", font=("Helvetica", 14)).pack(side="left", padx=(100, 0), pady=2)
    net_trade_var = tk.DoubleVar()
    net_trade_entry = tk.Entry(gss_entry_frame, textvariable=net_trade_var, width=11, font=("Helvetica", 14))
    net_trade_entry.pack(side="left", padx=15)
    entries["net_trade"] = net_trade_entry
    # --- Net Trade Amount field ends here ---



    # Create a fancy horizontal frame for OK and Cancel buttons.
    btn_frame = tk.Frame(rat_win, pady=10, bg="#f8fafc", relief="ridge", bd=2)
    btn_frame.pack(fill="x", anchor="e", padx=10)


    # ------------------------------
    # Buttons with fancy styling
    # ------------------------------
    ok_btn = tk.Button(btn_frame, text="✅ OK ✅", width=12,
                       font=("Comic Sans MS", 12, "bold"),
                       bg="#3b82f6", fg="white",
                       activebackground="#1e40af",
                       activeforeground="white",
                       relief="raised", bd=3,
                       cursor="hand2",
                       command=on_ok)
    ok_btn.pack(side="right", padx=5)
    cancel_btn = tk.Button(btn_frame, text="❌ Cancel ❌", width=12,
                           font=("Comic Sans MS", 12, "bold"),
                           bg="#ef4444", fg="white",
                           activebackground="#dc2626",
                           activeforeground="white",
                           relief="raised", bd=3,
                           cursor="hand2",
                           command=cleanup_and_close)
    cancel_btn.pack(side="right", padx=5)

    # Configure window close protocol to use cleanup function
    rat_win.protocol("WM_DELETE_WINDOW", cleanup_and_close)




    # ======================================================================
    # ALL EVENT BINDINGS - Centralized for better maintainability
    # ======================================================================

    # --- Window-level bindings ---
    rat_win.bind("<Return>", on_enter)
    rat_win.bind("<Escape>", on_escape)

    # --- Contract fields bindings ---
    cont_no_entry.bind("<FocusOut>", fetch_existing_contract)
    settle_no_entry.bind("<FocusIn>", update_settle_no_on_focus)
    settle_date_entry.bind("<FocusIn>", update_settle_date_on_focus)

    # --- Company and ISIN bindings ---
    company_entry.bind("<Key>", on_company_key)

    # --- Buy/Sell radio button bindings ---
    buy_radio.bind("<Button-1>", lambda e: on_radio_click(buy_radio, "BUY"))
    sell_radio.bind("<Button-1>", lambda e: on_radio_click(sell_radio, "SELL"))
    buy_radio.bind("<Key>", lambda e: on_radio_key(e, buy_radio, "BUY"))
    sell_radio.bind("<Key>", lambda e: on_radio_key(e, sell_radio, "SELL"))

    # --- Quantity and Order fields bindings ---
    qty_trd_entry.bind("<FocusIn>", on_qty_trd_focus)
    ord_dt_entry.bind("<FocusIn>", update_ord_dt_on_focus)
    qty_eo_entry.bind("<FocusIn>", update_qty_eo_on_focus_in)
    qty_eo_entry.bind("<FocusOut>", update_check_qty_on_focus_out_of_qty_eo)
    qty_eo_entry.bind("<FocusIn>", enable_submit_on_qty_eo_focus, add=True)
    qty_eo_entry.bind("<KeyRelease>", update_brok_unit_eo_focus_in)
    qty_eo_entry.bind("<FocusOut>", update_brok_unit_eo_focus_in, add=True)
    ord_no_entry.bind("<FocusIn>", update_qty_eo_on_focus_in)

    # --- Rate and Brokerage fields bindings ---
    brok_unit_eo_entry.bind("<FocusIn>", update_brok_unit_eo_focus_in)
    rate_eo_entry.bind("<FocusIn>", update_brok_unit_eo_focus_in)
    rate_eo_entry.bind("<KeyRelease>", update_brok_unit_eo_focus_in)
    rate_eo_entry.bind("<FocusOut>", format_rate_eo_on_focus_out)
    net_rate_eo_entry.bind("<FocusIn>", update_brok_unit_eo_focus_in)
    net_total_eo_entry.bind("<FocusIn>", update_brok_unit_eo_focus_in)

    # --- Weighted Average Price field bindings ---
    wap_entry.bind("<FocusOut>", format_wap_on_focus_out)
    wap_entry.bind("<KeyRelease>", recalculate_from_wap_change)
    wap_entry.bind("<FocusOut>", recalculate_from_wap_change, add=True)

    # --- Additional financial field formatting bindings ---
    # Format brokerage fields to 4 decimal places
    brs_entry.bind("<FocusOut>", format_financial_field_on_focus_out(brs_var, 4))
    lp_entry.bind("<FocusOut>", format_financial_field_on_focus_out(lp_var, 4))
    tot_brok_entry.bind("<FocusOut>", format_financial_field_on_focus_out(tot_brok_var, 4))

    # Format levy fields to 4 decimal places
    etc_entry.bind("<FocusOut>", format_financial_field_on_focus_out(etc_var, 4), add=True)
    sebi_entry.bind("<FocusOut>", format_financial_field_on_focus_out(sebi_var, 4), add=True)
    gst_entry.bind("<FocusOut>", format_financial_field_on_focus_out(gst_var, 4), add=True)
    stt_entry.bind("<FocusOut>", format_financial_field_on_focus_out(stt_var, 4), add=True)
    stamp_duty_entry.bind("<FocusOut>", format_financial_field_on_focus_out(stamp_duty_var, 4), add=True)
    igst_entry.bind("<FocusOut>", format_financial_field_on_focus_out(igst_var, 4), add=True)
    sell_charge_entry.bind("<FocusOut>", format_financial_field_on_focus_out(sell_charge_var, 4), add=True)
    net_trade_entry.bind("<FocusOut>", format_financial_field_on_focus_out(net_trade_var, 4))

    # Format execution order fields to appropriate decimal places
    brok_unit_eo_entry.bind("<FocusOut>", format_financial_field_on_focus_out(brok_unit_eo_var, 4))
    net_rate_eo_entry.bind("<FocusOut>", format_financial_field_on_focus_out(net_rate_eo_var, 4))
    net_total_eo_entry.bind("<FocusOut>", format_financial_field_on_focus_out(net_total_eo_var, 4))

    # --- Exchange radio button bindings ---
    nse_radio.bind("<Button-1>", lambda e: on_radio_click(nse_radio, "NSE"))
    bse_radio.bind("<Button-1>", lambda e: on_radio_click(bse_radio, "BSE"))
    nse_radio.bind("<Key>", lambda e: on_ex_radio_key(e, nse_radio, "NSE"))
    bse_radio.bind("<Key>", lambda e: on_ex_radio_key(e, bse_radio, "BSE"))

    # --- Levy fields bindings (Real-time levies and net trade updates) ---
    tot_brok_entry.bind("<KeyRelease>", update_levies_and_net_trade)
    tot_brok_entry.bind("<FocusOut>", update_levies_and_net_trade)
    etc_entry.bind("<KeyRelease>", update_levies_and_net_trade)
    etc_entry.bind("<FocusOut>", update_levies_and_net_trade)
    sebi_entry.bind("<KeyRelease>", update_levies_and_net_trade)
    sebi_entry.bind("<FocusOut>", update_levies_and_net_trade)
    sell_charge_entry.bind("<KeyRelease>", update_levies_and_net_trade)
    sell_charge_entry.bind("<FocusOut>", update_levies_and_net_trade)
    gst_entry.bind("<KeyRelease>", update_levies_and_net_trade)
    gst_entry.bind("<FocusOut>", update_levies_and_net_trade)
    stamp_duty_entry.bind("<KeyRelease>", update_levies_and_net_trade)
    stamp_duty_entry.bind("<FocusOut>", update_levies_and_net_trade)
    stt_entry.bind("<KeyRelease>", update_levies_and_net_trade)
    stt_entry.bind("<FocusOut>", update_levies_and_net_trade)
    igst_entry.bind("<KeyRelease>", update_levies_and_net_trade)
    igst_entry.bind("<FocusOut>", update_levies_and_net_trade)

    # ======================================================================

    # All actions




    # Wait for the window to close before returning
    rat_win.wait_window(rat_win)

    # Use centralized modal window management for focus restoration
    centralized_enable_parent(modal_id)

# add_trade_window function ends here