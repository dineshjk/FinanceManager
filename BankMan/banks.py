# -*- coding: utf-8 -*-
# BankMan/banks.py

import tkinter as tk
import sys
import os

# Ensure absolute imports from the Shared package work correctly
# This MUST be placed before importing from the Shared module
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from .bank_database_setup import create_bankman_database
from Shared.dialog_utils import show_colorful_info
from Shared.globals import BANK_APP_TITLE
from Shared.menu_factory import create_menu_window
from Shared.modal_utils import disable_parent, enable_parent
from Shared.window_manager import push_window, pop_window
from Shared.help_utils import show_standard_help

from .data_entry_menu import show_top_data_entry_menu
from .import_menu import show_import_menu
from .export_menu import show_export_menu
from .manage_bh import show_bh_manager
from .manage_master_menu import show_manage_master_menu
from .manage_transactions_menu import show_manage_transactions_menu


def get_core_bank_buttons(get_parent_func):
    """Returns the common buttons. 'get_parent_func' is a callable that returns the target window."""
    return [
        {
            "text": "Create Bank Database",
            "hotkey": "C",
            "command": lambda: create_bank_database_gui(get_parent_func()),
        },
        {
            "text": "Data Entry",
            "hotkey": "D",
            "command": lambda: show_top_data_entry_menu(get_parent_func()),
        },
        {
            "text": "Import",
            "hotkey": "I",
            "command": lambda: show_import_menu(get_parent_func()),
        },
        {
            "text": "Export",
            "hotkey": "E",
            "command": lambda: show_export_menu(get_parent_func()),
        },
        {
            "text": "Manage Budget Heads",
            "hotkey": "H",
            "command": lambda: show_bh_manager(get_parent_func()),
        },
        {
            "text": "Manage Master",
            "hotkey": "M",
            "command": lambda: show_manage_master_menu(get_parent_func()),
        },
        {
            "text": "Manage Transactions",
            "hotkey": "T",
            "command": lambda: show_manage_transactions_menu(get_parent_func()),
        },
    ]


def create_bank_database_gui(parent):
    """GUI wrapper to show the result of creating the BankMan
    database."""
    success, message = create_bankman_database(parent)
    if success:
        show_colorful_info(parent, "Database Status", message)
    else:
        show_colorful_info(parent, "Database Status", message, icon="error")


def _get_banks_help_data():
    guide_lines = [
        "Welcome to the BankMan Main Menu.",
        "",
        "• Create Bank Database: Initializes or safely migrates your SQLite database.",
        "• Data Entry: The gateway to adding new passbook transactions or financial products.",
        "• Import / Export: Tools for bulk loading CSV statements or backing up your ledgers.",
        "• Manage Budget Heads: Organise your income and expense categories.",
        "• Manage Master: View, edit, or safely delete structural records (Banks, Accounts, MFs, etc.).",
        "• Manage Transactions: The central viewer grid to search, edit, or delete passbook entries."
    ]
    faq_data = [
        (
            "Q: Where do I start if I am setting up BankMan for the first time?",
            "A: 1. Click 'Create Bank Database'.\n2. Go to 'Manage Master' to add your Banks and Accounts.\n3. Go to 'Data Entry' to start logging your transactions."
        ),
        (
            "Q: What is the difference between 'Data Entry' and 'Manage Master'?",
            "A: 'Data Entry' is for logging new events. 'Manage Master' allows you to view, edit, or safely delete the underlying structure (like correcting a misspelled bank name)."
        )
    ]
    return guide_lines, faq_data


def show_bank_main_menu(parent, come_back_index=None):
    """
    Shows the bank management menu as a modal window.
    """
    modal_id = disable_parent(parent)

    def close_modal() -> None:
        pop_window()
        bank_menu_window.destroy()

    window_ref = []

    core_buttons = get_core_bank_buttons(lambda: window_ref[0])

    core_buttons.append(
        {
            "text": "Previous Menu",
            "hotkey": "P",
            "command": close_modal,
        }
    )

    menu_config = {
        "title": "BankMan - Main Menu",
        "geometry": "400x490",
        "style": "Menu.TButton",
        "parent": parent,
        "modal": True,
        "bg": "#76d693",
        "buttons": core_buttons,
        "padx": 60,
        "pady": 5,
        "come_back_index": come_back_index,
    }

    bank_menu_window, _ = create_menu_window(menu_config)
    window_ref.append(bank_menu_window)

    bank_menu_window.protocol("WM_DELETE_WINDOW", close_modal)

    bank_menu_window.bind(
        "<F1>",
        lambda e: show_standard_help(
            bank_menu_window,
            "BankMan Main Menu Help",
            *_get_banks_help_data()
        )
    )

    push_window(bank_menu_window, parent)
    parent.wait_window(bank_menu_window)
    try:
        parent.grab_set()
    except Exception:
        pass
    enable_parent(modal_id)


def main():
    """
    Initialize and run the bank application window for Bank Account
    Management using the universal menu factory.
    """
    root = tk.Tk()

    # Fixed: Passing root as a lambda callable
    core_buttons = get_core_bank_buttons(lambda: root)
    core_buttons.append({"text": "Exit", "hotkey": "X", "command": root.destroy})

    menu_config = {
        "title": BANK_APP_TITLE,
        "geometry": "400x490",
        "style": "MainMenu.TButton",
        "parent": root,
        "modal": False,
        "bg": "#76d693",
        "buttons": core_buttons,
        "padx": 60,
        "pady": 5,
    }

    create_menu_window(menu_config)

    root.bind(
        "<F1>",
        lambda e: show_standard_help(
            root,
            "BankMan Main Menu Help",
            *_get_banks_help_data()
        )
    )

    root.mainloop()


if __name__ == "__main__":
    main()
