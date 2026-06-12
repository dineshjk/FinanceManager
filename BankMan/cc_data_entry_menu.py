# -*- coding: utf-8 -*-
# BankMan/cc_data_entry_menu.py

"""
Credit Card Data Entry menu for the BankMan application.
"""

import tkinter as tk
from Shared.menu_factory import create_menu_window
from Shared.modal_utils import disable_parent, enable_parent
from Shared.window_manager import push_window, pop_window
from .cc_master_add import add_cc_master_main
from .cc_transactions_add import add_cc_transaction_main
from .rewards_points_add import add_rewards_points_main

def show_cc_data_entry_menu(parent, come_back_index=None):
    """
    Displays the Credit Card Data Entry menu for BankMan.
    """

    modal_id = disable_parent(parent)

    def close_modal() -> None:
        pop_window()
        enable_parent(parent, modal_id)
        cc_menu_window.destroy()

    menu_config = {
        "title": "CC Data Entry",
        "geometry": "400x350",
        "style": "Menu.TButton",
        "parent": parent,
        "modal": True,
        "bg": "#f9d0e0",
        "buttons": [
            {
                "text": "Credit Card Master",
                "hotkey": "M",
                "command": lambda: add_cc_master_main(cc_menu_window),
            },
            {
                "text": "Credit Card Transactions",
                "hotkey": "T",
                "command": lambda: add_cc_transaction_main(cc_menu_window),
            },
            {
                "text": "Rewards Points Entry",
                "hotkey": "R",
                "command": lambda: add_rewards_points_main(cc_menu_window),
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
    cc_menu_window, _ = create_menu_window(menu_config)

    # When the modal window's close button (X) is clicked, handle it gracefully
    cc_menu_window.protocol("WM_DELETE_WINDOW", close_modal)

    push_window(cc_menu_window, parent)
    parent.wait_window(cc_menu_window)
    parent.grab_set()
    enable_parent(parent, modal_id)
