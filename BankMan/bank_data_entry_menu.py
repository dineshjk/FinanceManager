# -*- coding: utf-8 -*-
# C:\Data\Personal\Finance_and_Investment\finprog\FinanceManager\BankMan\bank_data_entry_menu.py

"""
Data entry menu for the BankMan application.
"""

import tkinter as tk
from Shared.menu_factory import create_menu_window
from Shared.modal_utils import disable_parent, enable_parent
from Shared.window_manager import push_window, pop_window
from .banks_add import add_bank
from .budget_head_add import add_account_type_main
from .accounts_add import add_account_main
from .accounts_edit import edit_account
from .bank_transactions_add import add_bank_transaction_main


def show_data_entry_menu(parent, come_back_index=None):
    """
    Displays the data entry menu for BankMan using the centralized menu factory.
    """

    modal_id = disable_parent(parent)

    def close_modal() -> None:
        pop_window()
        bank_data_window.destroy()

    menu_config = {
        "title": "BankMan - Data Entry",
        "geometry": "400x450",
        "style": "Menu.TButton",
        "parent": parent,
        "modal": True,
        "bg": "#fcc9cf",
        "buttons": [
            {
                "text": "Add Bank",
                "hotkey": "B",
                "command": lambda: add_bank(bank_data_window),
            },
            {
                "text": "Add Budget Category",
                "hotkey": "T",
                "command": lambda: add_account_type_main(bank_data_window),
            },
            {
                "text": "Add Account",
                "hotkey": "A",
                "command": lambda: add_account_main(bank_data_window),
            },
            {
                "text": "Edit Account",
                "hotkey": "E",
                "command": lambda: edit_account(bank_data_window),
            },
            {
                "text": "Add Transaction",
                "hotkey": "R",
                "command": lambda: add_bank_transaction_main(bank_data_window),
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

    # create_menu_window returns the window and the buttons
    bank_data_window, _ = create_menu_window(menu_config)

    # When the modal window's close button (X) is clicked, handle it gracefully
    bank_data_window.protocol("WM_DELETE_WINDOW", close_modal)

    push_window(bank_data_window, parent)
    parent.wait_window(bank_data_window)
    parent.grab_set()
    enable_parent(modal_id)
