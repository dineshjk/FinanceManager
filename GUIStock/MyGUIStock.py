# -*- coding: utf-8 -*-
"""
MyGUIStock.py
============
A GUI application for Stock Portfolio Management. This module provides a
comprehensive interface for managing stock portfolios, including features for:

- Database management
- Stock entry and tracking
- Transaction recording
- Portfolio maintenance
- Financial reporting

The application uses SQLite for data storage and Tkinter for the GUI interface.
"""

# === Path Setup for IDE Compatibility ===
import sys
import os

# Add FinanceManager root to Python path if not already there
# This handles both direct execution and module execution
current_file = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(current_file))

# Check if we're in the right place - should find 'FinanceManager' directory
finance_root = os.path.dirname(project_root)
if os.path.basename(project_root) == 'FinanceManager' and finance_root not in sys.path:
    sys.path.insert(0, finance_root)
elif project_root not in sys.path:
    sys.path.insert(0, project_root)
# === End Path Setup ===

# Standard library imports
import sqlite3
import logging
from datetime import datetime, timedelta, date
from typing import Tuple, Optional, List, Generator, Union

# Third-party imports
import tkinter as tk
from tkinter import messagebox
from tkcalendar import DateEntry

# Application imports - try absolute imports first, fall back to relative
try:
    # When run as module or with proper path setup
    from FinanceManager.GUIStock.config import logger, APP_TITLE
    from FinanceManager.GUIStock.dbutils import (
        disable_parent, enable_parent,
        add_company, bulk_entry_company, update_company,
        add_trade, create_database
    )
    from FinanceManager.GUIStock.business import remove_trade
except ImportError:
    # When run directly from GUIStock directory or as GUIStock module
    try:
        from .config import logger, APP_TITLE
        from .dbutils import (
            disable_parent, enable_parent,
            add_company, bulk_entry_company, update_company,
            add_trade, create_database
        )
        from .business import remove_trade
    except ImportError:
        # Last resort - relative imports for direct execution
        from config.globals import logger, APP_TITLE
        from dbutils.modal_management import disable_parent, enable_parent
        from dbutils.company_utils import add_company, bulk_entry_company, update_company
        from dbutils.transaction_utils import add_trade
        from dbutils.initial_tasks import create_database
        from business.trade_operations import remove_trade

# Constants and Configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.abspath(os.path.join(BASE_DIR, 'Stocks', 'StockData', 'guimyfolio.db'))

# Application Constants (moved to config/globals.py)
APP_VERSION = "1.0"
DATA_ENTRY_TITLE = "Data Entry"




# Database Operations
def select_stock_id(parent: tk.Tk) -> Optional[int]:
    """
    Open a dialog to select a stock by ID.
    Returns the selected stock ID or None if cancelled.
    """
    from FinanceManager.GUIStock.config.globals import get_db_connection

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id_stk, company_name, stk_code, isin FROM stocks ORDER BY company_name")
    stocks = cursor.fetchall()
    conn.close()

    if not stocks:
        messagebox.showinfo("No Stocks", "No stocks found in the database.")
        return None

    # Create dialog window
    win = tk.Toplevel(parent)
    win.title("Select Stock")
    win.geometry("600x400")
    win.transient(parent)
    win.grab_set()

    # Create frame for listbox and scrollbar
    frame = tk.Frame(win)
    frame.pack(fill="both", expand=True, padx=10, pady=10)

    # Create scrollbar
    scrollbar = tk.Scrollbar(frame)
    scrollbar.pack(side="right", fill="y")

    # Create listbox
    listbox = tk.Listbox(frame, yscrollcommand=scrollbar.set, height=15, width=80)
    for stock in stocks:
        listbox.insert(tk.END, f"{stock[1]} - {stock[2]} (ISIN: {stock[3]})")
    listbox.pack(side="left", fill="both", expand=True)
    scrollbar.config(command=listbox.yview)

    # Variable to store selected stock ID
    selected_stock_id = tk.StringVar()

    def on_ok() -> None:
        selection = listbox.curselection()
        if selection:
            index = selection[0]
            selected_stock_id.set(stocks[index][0])
            win.destroy()
        else:
            messagebox.showwarning("No selection", "Please select a stock.")

    def on_cancel() -> None:
        selected_stock_id.set("")
        win.destroy()

    btn_frame = tk.Frame(win)
    btn_frame.pack(pady=5)
    tk.Button(btn_frame, text="OK", command=on_ok).pack(side="left", padx=5)
    tk.Button(btn_frame, text="Cancel", command=on_cancel).pack(side="left", padx=5)

    win.wait_window(win)

    return selected_stock_id.get() if selected_stock_id.get() else None



def trade_menu(parent: tk.Tk) -> None:
    """
    Launches the trade menu GUI window.
    Fixed window size and title.
    Trade Menu
        - Add Trade
        - Remove Trade
        - Update Trade
        - Previous Menu
    """
    # Use centralized modal window management
    modal_id = disable_parent(parent)

    tm = tk.Toplevel(parent)
    tm.title("Trade Menu")
    tm.geometry("400x300")
    tm.resizable(False, False)

    tk.Label(tm, text="Trade Menu", font=("Helvetica", 14)).pack(pady=20)

    btn_specs = [
        ("Add Trade", "A", None),  # Command will be set after button creation
        ("Remove Trade", "R", lambda: remove_trade(tm)),
        ("Update Trade", "U", lambda: update_trade(tm)),
        ("Previous Menu", "P", lambda: close_trade_menu())
    ]

    def close_trade_menu():
        """Close trade menu with proper modal management"""
        enable_parent(modal_id)
        tm.destroy()

    # Update button specs with the proper close function
    btn_specs[3] = ("Previous Menu", "P", lambda: close_trade_menu())

    buttons = []  # List to hold button references for navigation
    hotkey_map = {}  # Map hotkey (lowercase) to button invoke

    def on_focus_in(event):
        event.widget.config(bg="lightblue")

    def on_focus_out(event):
        event.widget.config(bg="SystemButtonFace")

    for label, hotkey, command in btn_specs:
        idx = label.lower().find(hotkey.lower())
        if idx == -1:
            underline_idx = 0
        else:
            underline_idx = idx
        # Create button with hotkey underline
            btn = tk.Button(
            tm,
            text=label,
            width=25,
            font=("Helvetica", 12),
            activeforeground="red",
            activebackground="lightblue",
            takefocus=True,
            command=command,
            underline=underline_idx
        )
        btn.bind("<FocusIn>", on_focus_in)
        btn.bind("<FocusOut>", on_focus_out)
        btn.pack(pady=5)
        buttons.append(btn)
        hotkey_map[hotkey.lower()] = btn

    # Set commands for buttons that need calling button reference
    if len(buttons) >= 1:
        buttons[0].config(command=lambda: add_trade(tm, buttons[0]))  # Add Trade

    def on_hotkey(event):
        key = event.keysym.lower()
        print(f"DEBUG: Key pressed in Trade Menu: {key}")
        if key == "escape":
            print("DEBUG: Escape key detected, calling close_trade_menu()")
            close_trade_menu()
        elif key in hotkey_map:
            hotkey_map[key].invoke()

    tm.bind("<Key>", on_hotkey)

    # Configure button navigation with custom escape handler for modal mgmt
    enable_button_navigation(tm, buttons,
                             custom_escape_handler=close_trade_menu)

    # Handle window close (X button)
    tm.protocol("WM_DELETE_WINDOW", close_trade_menu)

    tm.wait_window(tm)

# Place Holder Functions for Data Entry

def update_trade(parent: tk.Tk) -> None:
    messagebox.showinfo("Info", "Update Trade clicked", parent=parent)

# def add_company(parent: tk.Tk) -> None:
#     messagebox.showinfo("Info", "Add Company clicked", parent=parent)

def remove_company(parent: tk.Tk) -> None:
    messagebox.showinfo("Info", "Remove Company clicked", parent=parent)



# Place Holder Functions for root windows

def company_menu(parent: tk.Tk) -> None:
    """
    Launches the company menu GUI window.
    Fixed window size and title.
    Company Menu
        - Add Company
        - Update Company
        - Remove Company
        - Bulk Entry Company
        - Previous Menu
    """
    # Use centralized modal window management
    modal_id = disable_parent(parent)

    cm = tk.Toplevel(parent)
    cm.title("Company Menu")
    cm.geometry("400x300")
    cm.resizable(False, False)

    tk.Label(cm, text="Company Menu", font=("Helvetica", 14)).pack(pady=20)

    btn_specs = [
        ("Add Company", "A", None),  # Command will be set after button creation
        ("Update Company", "U", None),  # Command will be set after button creation
        ("Remove Company", "R", lambda: remove_company(cm)),
        ("Bulk Entry Company", "B", lambda: bulk_entry_company(cm)),
        ("Previous Menu", "P", lambda: close_company_menu())
    ]

    def close_company_menu():
        """Close company menu with proper modal management"""
        enable_parent(modal_id)
        cm.destroy()

    # Update button specs with the proper close function
    btn_specs[4] = ("Previous Menu", "P", lambda: close_company_menu())


    buttons = []  # List to hold button references for navigation
    hotkey_map = {}  # Map hotkey (lowercase) to button invoke

    def on_focus_in(event):
        event.widget.config(bg="lightblue")

    def on_focus_out(event):
        event.widget.config(bg="SystemButtonFace")

    for label, hotkey, command in btn_specs:
        idx = label.lower().find(hotkey.lower())
        if idx == -1:
            underline_idx = 0
        else:
            underline_idx = idx
        # Create button with hotkey underline
        btn = tk.Button(
            cm,
            text=label,
            width=25,
            font=("Helvetica", 12),
            activeforeground="red",
            activebackground="lightblue",
            takefocus=True,
            command=command,
            underline=underline_idx
        )
        btn.bind("<FocusIn>", on_focus_in)
        btn.bind("<FocusOut>", on_focus_out)
        btn.pack(pady=5)
        buttons.append(btn)
        hotkey_map[hotkey.lower()] = btn

    # Set commands for buttons that need calling button reference
    if len(buttons) >= 2:
        buttons[0].config(command=lambda: add_company(cm, buttons[0]))  # Add Company
        buttons[1].config(command=lambda: update_company(cm, buttons[1]))  # Update Company

    def on_hotkey(event):
        key = event.keysym.lower()
        if key in hotkey_map:
            hotkey_map[key].invoke()

    cm.bind("<Key>", on_hotkey)
    # Configure button navigation with custom escape handler for modal mgmt
    enable_button_navigation(cm, buttons,
                             custom_escape_handler=close_company_menu)

    # Handle window close (X button)
    cm.protocol("WM_DELETE_WINDOW", close_company_menu)

    cm.wait_window(cm)


def transaction_menu(parent: tk.Tk) -> None:
    messagebox.showinfo("Info", "Transaction Menu clicked", parent=parent)

def corporate_action_menu(parent: tk.Tk) -> None:
    messagebox.showinfo("Info", "Corporate Action Menu clicked", parent=parent)


def maintenance_menu(parent: tk.Tk) -> None:
    messagebox.showinfo("Info", "Maintenance Menu clicked", parent=parent)

def report_menu(parent: tk.Tk) -> None:
    messagebox.showinfo("Info", "Report Menu clicked", parent=parent)

def exit_program(root: tk.Tk) -> None:
    root.destroy()


def main_gui() -> None:
    """
    Launch the main GUI application window.

    Creates and configures the main application window with:
    - Title bar and application name
    - Fixed window size
    - Main menu buttons:
        - Create Database
        - Data Entry
        - Maintenance
        - Reports
        - Exit

    Features:
    - Keyboard navigation between buttons
    - Consistent styling and layout
    - Modal dialog handling
    - Error handling and user feedback

    Note:
        This is the main entry point of the application
    """
    root = tk.Tk()  # Create the main window
    root.title(APP_TITLE) # Set the title of the window
    root.geometry("400x480") # Set the size of the window
    root.resizable(False, False)

    title = tk.Label(root, text=APP_TITLE, font=("Helvetica", 16, "bold")) # Create a title label
    title.pack(pady=20) # Add some padding around the title


    # Define button specifications with hotkey info: (label, hotkey, command)
    def show_report_menu():
        return report_menu(root)

    btn_specs = [
        ("Create Database", "D", lambda: create_database_gui()),
        ("Manage Company", "C", lambda: company_menu(root)),
        ("Manage Transaction", "T", lambda: trade_menu(root)),
        ("Corporate Action", "A", lambda: corporate_action_menu(root)),
        ("Maintenance", "M", lambda: maintenance_menu(root)),
        ("Reports", "R", show_report_menu),
        ("Exit", "X", lambda: exit_program(root))
    ]

    buttons = []  # List to hold button references for navigation
    hotkey_map = {}  # Map hotkey (lowercase) to button invoke

    def on_focus_in(event):
        event.widget.config(bg="lightblue")

    def on_focus_out(event):
        event.widget.config(bg="SystemButtonFace")

    for label, hotkey, command in btn_specs:
        idx = label.lower().find(hotkey.lower())
        if idx == -1:
            underline_idx = 0
        else:
            underline_idx = idx
        btn = tk.Button(
            root,
            text=label,
            width=25,
            font=("Helvetica", 12),
            activeforeground="red",
            activebackground="lightblue",
            takefocus=True,
            command=command,
            underline=underline_idx
        )
        btn.bind("<FocusIn>", on_focus_in)
        btn.bind("<FocusOut>", on_focus_out)
        btn.pack(pady=5)
        buttons.append(btn)
        hotkey_map[hotkey.lower()] = btn

    def on_hotkey(event):
        key = event.keysym.lower()
        if key in hotkey_map:
            hotkey_map[key].invoke()

    root.bind("<Key>", on_hotkey)
    enable_button_navigation(root, buttons)  # ✅ Reusable navigation
    root.bind("<Escape>", lambda e: exit_program(root))  # Bind Escape key to exit

    root.mainloop()



def enable_button_navigation(window: tk.Tk, buttons: List[tk.Button],
                             custom_escape_handler=None) -> None:
    """
    Enables keyboard navigation for a list of Tkinter buttons.

    Implements keyboard navigation features:
    - Up/Down arrow keys to move between buttons
    - Enter key to activate the currently focused button
    - Circular navigation (wraps around at list ends)

    Args:
        window: The Tkinter window/widget to bind key events to
        buttons: List of Tkinter Button widgets to enable navigation for
        custom_escape_handler: Optional custom function to handle Escape key
                              (for modal management)

    Note:
        - Maintains focus tracking using a mutable list index
        - Initial focus is set to the first button
        - Supports circular navigation (last to first and vice versa)
    """
    current_index = [0]  # Mutable to allow inner function modification
    destroyed = [False]  # Flag to track if navigation should be disabled

    # Set initial focus safely
    if buttons and len(buttons) > 0:
        try:
            buttons[0].focus_set()
        except tk.TclError:
            # Button doesn't exist or window is destroyed
            pass

    def on_key(event: tk.Event) -> None:
        # Early exit if navigation is disabled
        if destroyed[0]:
            return

        # Check if the window and buttons still exist and are valid
        try:
            # Check if the window still exists
            if not window.winfo_exists():
                destroyed[0] = True
                return

            # Check if buttons list is valid
            if not buttons or current_index[0] >= len(buttons):
                return

            # Check if the current button is still valid
            current_button = buttons[current_index[0]]
            if not current_button.winfo_exists():
                destroyed[0] = True
                return

        except (tk.TclError, AttributeError, IndexError):
            # Window or button has been destroyed or is invalid
            destroyed[0] = True
            return

        key = event.keysym
        if key == "Down":
            current_index[0] = (current_index[0] + 1) % len(buttons)
            try:
                if buttons[current_index[0]].winfo_exists():
                    buttons[current_index[0]].focus_set()
            except (tk.TclError, IndexError):
                destroyed[0] = True
        elif key == "Up":
            current_index[0] = (current_index[0] - 1) % len(buttons)
            try:
                if buttons[current_index[0]].winfo_exists():
                    buttons[current_index[0]].focus_set()
            except (tk.TclError, IndexError):
                destroyed[0] = True
        elif key == "Return":
            try:
                if buttons[current_index[0]].winfo_exists():
                    buttons[current_index[0]].invoke()
                    current_index[0] = (current_index[0] + 1) % len(buttons)
                    if (current_index[0] < len(buttons) and
                            buttons[current_index[0]].winfo_exists()):
                        buttons[current_index[0]].focus_set()
            except (tk.TclError, IndexError):
                destroyed[0] = True

    def on_destroy(event=None):
        """Handle window destruction by disabling navigation"""
        destroyed[0] = True

    # Bind the destroy event to disable navigation
    try:
        window.bind("<Destroy>", on_destroy)
    except tk.TclError:
        pass

    window.bind("<Up>", on_key)
    window.bind("<Down>", on_key)
    window.bind("<Return>", on_key)

    # Centralized Escape key binding
    if custom_escape_handler:
        # Use the provided custom escape handler (for modal management)
        window.bind("<Escape>", lambda event: custom_escape_handler())
    elif isinstance(window, tk.Tk):
        # Main window - exit program
        window.bind("<Escape>", lambda event: exit_program(window))
    else:
        # Fallback for other windows (should not happen with proper modal mgmt)
        print("WARNING: Using fallback window.destroy() - "
              "consider using custom_escape_handler")
        window.bind("<Escape>", lambda event: window.destroy())


def create_database_gui():
    success, msg = create_database()
    if success:
        messagebox.showinfo("Success", msg)
    else:
        messagebox.showerror("Error", msg)


# Run the GUI
if __name__ == "__main__":
    main_gui()
