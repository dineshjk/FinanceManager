# -*- coding: utf-8 -*-
# BankMan/import_menu.py

"""
Import Data menu for the BankMan application.
Provides navigation to module-specific import sub-menus.
"""

from Shared.menu_factory import create_menu_window
from Shared.modal_utils import disable_parent, enable_parent
from Shared.window_manager import push_window, pop_window
from .budget_head_ex_import import import_budget_head
from .banks_ex_import import import_banks
from .cc_ex_import_menu import show_cc_import_menu
from .fd_ex_import_menu import show_fd_import_menu
from .loan_ex_import_menu import show_loan_import_menu
from .ppf_ex_import_menu import show_ppf_import_menu


def show_import_menu(parent, come_back_index=None):
    """
    Displays the Import Data menu for BankMan.
    """

    modal_id = disable_parent(parent)

    def close_modal() -> None:
        pop_window()
        menu_window.destroy()

    menu_config = {
        "title": "Import Data",
        "geometry": "400x510",
        "style": "Menu.TButton",
        "parent": parent,
        "modal": True,
        "bg": "#f7e4c5",
        "buttons": [
            {
                "text": "Bank",
                "hotkey": "B",
                "command": lambda: import_banks(menu_window),
            },
            {
                "text": "Credit Card",
                "hotkey": "C",
                "command": lambda: show_cc_import_menu(menu_window),
            },
            {
                "text": "Fixed Deposit",
                "hotkey": "D",
                "command": lambda: show_fd_import_menu(menu_window),
            },
            {
                "text": "Loan",
                "hotkey": "L",
                "command": lambda: show_loan_import_menu(menu_window),
            },
            {
                "text": "PPF",
                "hotkey": "F",
                "command": lambda: show_ppf_import_menu(menu_window),
            },
            {
                "text": "Budget Heads",
                "hotkey": "H",
                "command": lambda: import_budget_head(menu_window),
            },
            {
                "text": "Previous Menu",
                "hotkey": "P",
                "command": close_modal,
            },
        ],
        "padx": 60,
        "pady": 5,
        "come_back_index": come_back_index,
    }

    menu_window, _ = create_menu_window(menu_config)
    menu_window.protocol("WM_DELETE_WINDOW", close_modal)

    push_window(menu_window, parent)
    parent.wait_window(menu_window)
    parent.grab_set()
    enable_parent(modal_id)
