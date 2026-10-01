# -*- coding: utf-8 -*-
# BankMan/ppf_data_entry_menu.py

"""
PPF Data Entry menu for the BankMan application.
"""

from Shared.menu_factory import create_menu_window
from Shared.modal_utils import disable_parent, enable_parent
from Shared.window_manager import push_window, pop_window
from .ppf_master_add import add_ppf_master_main
from .ppf_transactions_add import add_ppf_transaction_main
from Shared.help_utils import show_standard_help


def _get_ppf_data_entry_help_data():
    guide_lines = [
        "This menu acts as the central hub for managing your Public Provident Fund (PPF) data entry.",
        "",
        "• PPF Master: Register a new PPF account, setting its maturity parameters and linked bank account.",
        "• PPF Transactions: Log standalone events like yearly compounding interest accrual, which happen internally within the PPF account."
    ]
    faq_data = [
        (
            "Q: How do I record my yearly or monthly PPF deposits?",
            "A: Do NOT enter the actual money movement here! Go to 'Data Entry' -> 'Bank' -> 'Add Transaction'. Record a Withdrawal from your Savings account, set the Entry Type to TRANSFER, select 'PPF' as the Module Type, and pick your PPF account. This ensures the cash leaving your bank perfectly matches the cash entering your PPF ledger."
        )
    ]
    return guide_lines, faq_data


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

    def _show_help(_e=None):
        guide, faq = _get_ppf_data_entry_help_data()
        show_standard_help(
            parent=ppf_menu_window,
            title="PPF Data Entry Help",
            guide_lines=guide,
            faq_data=faq
        )
    ppf_menu_window.bind("<F1>", lambda e: None if getattr(e, "state", 0) & 0x0004 else _show_help(e))

    push_window(ppf_menu_window, parent)
    parent.wait_window(ppf_menu_window)
    try:
        parent.grab_set()
    except Exception:
        pass
    enable_parent(modal_id)
