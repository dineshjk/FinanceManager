# -*- coding: utf-8 -*-
# BankMan/manage_transactions_menu.py

"""
Manage Transactions menu for the BankMan application.
Provides navigation to module-specific transaction-management sub-menus.
"""

import tkinter as tk
from Shared.menu_factory import create_menu_window
from Shared.modal_utils import disable_parent, enable_parent
from Shared.window_manager import push_window, pop_window
from .manage_cc import show_cc_transactions_manager
from .manage_bank import show_bank_transactions_manager
from .manage_fd import show_fd_transactions_manager
from .manage_loan import show_loan_transactions_manager
from .manage_ppf import show_ppf_transactions_manager


def show_manage_transactions_menu(parent, come_back_index=None):
    """
    Displays the Manage Transactions menu for BankMan.
    """

    modal_id = disable_parent(parent)

    def close_modal() -> None:
        pop_window()
        enable_parent(parent, modal_id)
        menu_window.destroy()

    menu_config = {
        "title": "Manage Transactions",
        "geometry": "400x450",
        "style": "Menu.TButton",
        "parent": parent,
        "modal": True,
        "bg": "#f7c5d0",
        "buttons": [
            {
                "text": "Bank",
                "hotkey": "B",
                "command": lambda: show_bank_transactions_manager(menu_window),
            },
            {
                "text": "Credit Card",
                "hotkey": "C",
                "command": lambda: show_cc_transactions_manager(menu_window),
            },
            {
                "text": "Fixed Deposit",
                "hotkey": "D",
                "command": lambda: show_fd_transactions_manager(menu_window),
            },
            {
                "text": "Loan",
                "hotkey": "L",
                "command": lambda: show_loan_transactions_manager(menu_window),
            },
            {
                "text": "PPF",
                "hotkey": "F",
                "command": lambda: show_ppf_transactions_manager(menu_window),
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
    enable_parent(parent, modal_id)
