# -*- coding: utf-8 -*-
# BankMan/cc_data_entry_menu.py

"""
Credit Card Data Entry menu for the BankMan application.
"""

from Shared.menu_factory import create_menu_window
from Shared.modal_utils import disable_parent, enable_parent
from Shared.window_manager import push_window, pop_window
from .cc_master_add import add_cc_master_main
from .cc_transactions_add import add_cc_transaction_main
from .rewards_points_add import add_rewards_points_main
from Shared.help_utils import show_standard_help

def _get_cc_data_entry_help_data():
    guide_lines = [
        "This menu manages the data entry for your Credit Card ecosystem.",
        "",
        "• Credit Card Master: Register a new credit card (set billing cycle, limits, linked bank account).",
        "• Credit Card Transactions: Log individual card swipes, merchant refunds, and annual fees.",
        "• Rewards Points Entry: Track the accumulation and redemption of credit card reward points."
    ]
    faq_data = [
        (
            "Q: How do I record my monthly credit card bill payment?",
            "A: Do NOT enter the payment here! Go to 'Data Entry' -> 'Bank' -> 'Add Transaction'. Record a Withdrawal from your Savings account, set the Entry Type to TRANSFER, select 'CC' as the Module Type, and pick your card. This moves cash out of your bank and automatically pays down the card's outstanding balance."
        )
    ]
    return guide_lines, faq_data

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

    def _show_help(_e=None):
        guide, faq = _get_cc_data_entry_help_data()
        show_standard_help(
            parent=cc_menu_window,
            title="CC Data Entry Help",
            guide_lines=guide,
            faq_data=faq
        )
    cc_menu_window.bind("<F1>", lambda e: None if getattr(e, "state", 0) & 0x0004 else _show_help(e))

    push_window(cc_menu_window, parent)
    parent.wait_window(cc_menu_window)
    try:
        parent.grab_set()
    except Exception:
        pass
    enable_parent(parent, modal_id)
