# -*- coding: utf-8 -*-
# BankMan/ppf_data_entry_menu.py

"""
PPF Data Entry menu for the BankMan application.
"""

import tkinter as tk
from Shared.menu_factory import create_menu_window
from Shared.modal_utils import disable_parent, enable_parent
from Shared.window_manager import push_window, pop_window
from .ppf_master_add import add_ppf_master_main
from .ppf_transactions_add import add_ppf_transaction_main


def show_ppf_data_entry_menu(parent, come_back_index=None):
    """
    Displays the PPF Data Entry menu for BankMan.
    """

    modal_id = disable_parent(parent)

    def close_modal() -> None:
        pop_window()
        enable_parent(parent, modal_id)
        ppf_menu_window.destroy()

    menu_config = {
        "title": "PPF Data Entry",
        "geometry": "400x350",
        "style": "Menu.TButton",
        "parent": parent,
        "modal": True,
        "bg": "#d6eaff",
        "buttons": [
            {
                "text": "PPF Master",
                "hotkey": "M",
                "command": lambda: add_ppf_master_main(ppf_menu_window),
            },
            {
                "text": "PPF Transactions",
                "hotkey": "T",
                "command": lambda: add_ppf_transaction_main(ppf_menu_window),
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
    ppf_menu_window, _ = create_menu_window(menu_config)

    # When the modal window's close button (X) is clicked, handle it gracefully
    ppf_menu_window.protocol("WM_DELETE_WINDOW", close_modal)

    push_window(ppf_menu_window, parent)
    parent.wait_window(ppf_menu_window)
    parent.grab_set()
    enable_parent(modal_id)
