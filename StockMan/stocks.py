# -*- coding: utf-8 -*-
# C:\Data\Personal\Finance_and_Investment\finprog\FinanceManager\StockMan\stocks.py

"""
Main entry point for Stock Portfolio Management GUI application.

This script launches the main window and menu system for the Stock
Portfolio Management System. It defines button actions, hotkey support,
and the main application loop.

Functions:
    create_stock_database_gui(): Show info dialog for stock database creation.
    show_company_menu(): Show info dialog for company management.
    show_trade_menu(): Show info dialog for transaction management.
    show_corporate_action_menu(): Show info dialog for corporate
        actions.
    show_maintenance_menu(): Show info dialog for maintenance.
    show_report_menu(): Show info dialog for reports.
    exit_program(): Show info dialog for exit.
    main(): Initialize and run the main application window.

Dependencies:
    - tkinter, tkinter.messagebox
    - (removed windows.py dependency)
    - globals (APP_TITLE)
    - menu_factory (create_menu_window)
"""

import tkinter as tk
import sys
import os

# Ensure absolute imports from the Shared package work correctly
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from .corpo_menu import show_corporate_menu_modal

from .report_menu import show_report_menu_modal

from Shared.dialog_utils import show_colorful_info, show_colorful_error
from Shared.globals import STOCK_APP_TITLE, STOCK_DB_PATH
from Shared.menu_factory import create_menu_window
from Shared.modal_utils import disable_parent, enable_parent
from Shared.window_manager import push_window, pop_window
from .stock_database_setup import create_stockman_database
from .company_menu import show_company_menu_modal
from .trade_menu import show_trade_menu_modal
from .maint_menu import show_maint_menu_modal
from .watchlist_menu import show_watchlist


def show_stock_portfolio_menu(parent, come_back_index=None):
    """
    Shows the stock portfolio management menu as a modal window.
    """

    modal_id = disable_parent(parent)

    def close_modal() -> None:
        pop_window()
        stock_menu_window.destroy()

    # This function will be called to close the modal
    # def on_close(window):
    #     if window:
    #         window.grab_release()
    #         window.destroy()

    menu_config = {
        "title": "Stock Portfolio Management",
        "geometry": "400x530",
        "style": "Menu.TButton",
        "parent": parent,
        "modal": True,  # This tells the factory to create a Toplevel window
        "bg": "#e6f7ff",
        "buttons": [
            {
                "text": "Create Database",
                "hotkey": "D",
                "command": lambda: create_stockman_database(stock_menu_window),
            },
            {
                "text": "Company Management",
                "hotkey": "C",
                "command": lambda: show_company_menu(stock_menu_window),
            },
            {
                "text": "Trade Management",
                "hotkey": "T",
                "command": lambda: show_trade_menu(stock_menu_window),
            },
            {
                "text": "Corporate Actions",
                "hotkey": "A",
                "command": lambda: show_corporate_action_menu(
                    stock_menu_window
                ),
            },
            {
                "text": "Maintenance",
                "hotkey": "M",
                "command": lambda: show_maint_menu(stock_menu_window),
            },
            {
                "text": "Reports",
                "hotkey": "R",
                "command": lambda: show_report_menu(stock_menu_window),
            },
            {
                "text": "Watchlist & Alerts",
                "hotkey": "W",
                "command": lambda: show_watchlist(stock_menu_window),
            },
            {
                "text": "Previous Menu",
                "hotkey": "P",
                # "command": lambda w: on_close(w),
                "command": close_modal,
            },
        ],
        "padx": 60,
        "pady": 5,
        "come_back_index": come_back_index,
    }

    # create_menu_window returns the window and the buttons
    stock_menu_window, _ = create_menu_window(menu_config)

    # When the modal window's close button (X) is clicked, handle it gracefully
    stock_menu_window.protocol("WM_DELETE_WINDOW", close_modal)

    push_window(stock_menu_window, parent)
    parent.wait_window(stock_menu_window)
    parent.grab_set()
    enable_parent(modal_id)


# Button specifications: (text, hotkey, function)


def create_stock_database_gui(parent=None):
    """Show an info dialog for database creation and call create_database.

    Returns success info via colorful dialogs.
    """
    success, msg = create_stock_database(parent)
    if success:
        show_colorful_info(parent, "Success!", msg)
    else:
        show_colorful_error(parent, "Error!", msg)


def show_company_menu(root=None):
    """
    Show the company management menu as a modal window (using menu_factory)
    and restore main button state.
    """
    parent = root
    main_buttons = getattr(parent, "_main_menu_buttons", [])
    idx = 0
    if parent is not None:
        focused = parent.focus_get()
        try:
            idx = main_buttons.index(focused)
        except ValueError:
            pass

    show_company_menu_modal(parent, come_back_index=idx)


def show_trade_menu(root=None):
    """
    Show the Trade management menu as a modal window (using menu_factory)
    and restore main button state.
    """
    parent = root
    main_buttons = getattr(parent, "_main_menu_buttons", [])
    idx = 0
    if parent is not None:
        focused = parent.focus_get()
        try:
            idx = main_buttons.index(focused)
        except ValueError:
            pass

    show_trade_menu_modal(parent, come_back_index=idx)


def show_maint_menu(root=None):
    """
    Show the Maintenance menu as a modal window (using menu_factory) and
    restore main button state.
    """
    parent = root
    main_buttons = getattr(parent, "_main_menu_buttons", [])
    idx = 0
    if parent is not None:
        focused = parent.focus_get()
        try:
            idx = main_buttons.index(focused)
        except ValueError:
            pass

    show_maint_menu_modal(parent, come_back_index=idx)


def show_corporate_action_menu(root=None):
    """
    Show an info dialog for the Corporate Action button and restore main
    button state.
    """
    parent = root
    main_buttons = getattr(parent, "_main_menu_buttons", [])
    idx = 0
    if parent is not None:
        focused = parent.focus_get()
        try:
            idx = main_buttons.index(focused)
        except ValueError:
            pass

    show_corporate_menu_modal(parent, come_back_index=idx)


def show_report_menu(root=None):
    """
    Show the Report management menu as a modal window (using menu_factory)
    and restore main button state.
    """
    parent = root
    main_buttons = getattr(parent, "_main_menu_buttons", [])
    idx = 0
    if parent is not None:
        focused = parent.focus_get()
        try:
            idx = main_buttons.index(focused)
        except ValueError:
            pass

    show_report_menu_modal(parent, come_back_index=idx)


def exit_program(root=None):
    """
    Show an info dialog for the Exit button and restore main button
    state.
    """
    show_colorful_info(root, STOCK_APP_TITLE, "Exiting program...")
    if root is not None:
        root.destroy()


def main():
    """
    Initialize and run the stock application window for Stock Portfolio
    Management using the universal menu factory.
    """
    root = tk.Tk()
    # No longer needed: windows.main_window_instance = root
    menu_config = {
        "title": STOCK_APP_TITLE,
        "geometry": "400x530",
        "style": "MainMenu.TButton",
        "parent": root,
        "modal": False,
        "bg": "#e6f7ff",  # Light blue for main window
        "buttons": [
            {
                "text": "Create Database",
                "hotkey": "D",
                "command": lambda: create_stockman_database(root),
            },
            {
                "text": "Company Management",
                "hotkey": "C",
                "command": lambda: show_company_menu(root),
            },
            {
                "text": "Trade Management",
                "hotkey": "T",
                "command": lambda: show_trade_menu(root),
            },
            {
                "text": "Corporate Actions",
                "hotkey": "A",
                "command": lambda: show_corporate_action_menu(root),
            },
            {
                "text": "Maintenance",
                "hotkey": "M",
                "command": lambda: show_maint_menu(root),
            },
            {
                "text": "Reports",
                "hotkey": "R",
                "command": lambda: show_report_menu(root),
            },
            {
                "text": "Watchlist & Alerts",
                "hotkey": "W",
                "command": lambda: show_watchlist(root),
            },
            {"text": "Exit", "hotkey": "X", "command": root.destroy},
        ],
        "padx": 60,
        "pady": 5,
    }
    create_menu_window(menu_config)
    root.mainloop()


if __name__ == "__main__":
    main()


# C:\Data\Personal\Finance_and_Investment\finprog\FinanceManager\StockMan\stocks.py ends here
