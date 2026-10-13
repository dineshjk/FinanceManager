# -*- coding: utf-8 -*-
# BankMan/mf_data_entry_menu.py

"""
Mutual Fund Data Entry menu for the BankMan application.
"""

from Shared.menu_factory import create_menu_window
from Shared.modal_utils import disable_parent, enable_parent
from Shared.window_manager import push_window, pop_window
from .mf_master_add import add_mf_master_main
from .mf_transactions_add import add_mf_transaction_main
from Shared.help_utils import show_standard_help

def _get_mf_data_entry_help_data():
    guide_lines = [
        "This menu manages the data entry for your Mutual Fund ecosystem.",
        "",
        "  MF Master: Register a new Mutual Fund Folio (set the AMC, scheme name, etc).",
        "  MF Transactions: Log standalone events like dividend reinvestments or internal switches that do not directly hit your bank passbook."
    ]
    faq_data = [
        (
            "Q: How do I record SIPs, lumpsum purchases, or redemptions?",
            "A: Do NOT enter the actual money movement here! Go to 'Data Entry' -> 'Bank' -> 'Add Transaction'. Record a Withdrawal (for purchase) or Deposit (for redemption) in your Savings account, set the Entry Type to TRANSFER, select 'MF' as the Module Type, and pick your MF Folio. This ensures your bank balance stays perfectly synced."
        )
    ]
    return guide_lines, faq_data


def show_mf_data_entry_menu(parent, come_back_index=None):
    """
    Displays the Mutual Fund Data Entry menu for BankMan.
    """

    modal_id = disable_parent(parent)

    def close_modal() -> None:
        pop_window()
        enable_parent(parent, modal_id)
        mf_menu_window.destroy()

    menu_config = {
        "title": "MF Data Entry",
        "geometry": "400x350",
        "style": "Menu.TButton",
        "parent": parent,
        "modal": True,
        "bg": "#e0ffff",
        "buttons": [
            {
                "text": "MF Master",
                "hotkey": "M",
                "command": lambda: add_mf_master_main(mf_menu_window),
            },
            {
                "text": "MF Transactions",
                "hotkey": "T",
                "command": lambda: add_mf_transaction_main(mf_menu_window),
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
    mf_menu_window, _ = create_menu_window(menu_config)

    # When the modal window's close button (X) is clicked, handle it gracefully
    mf_menu_window.protocol("WM_DELETE_WINDOW", close_modal)

    def _show_help(_e=None):
        guide, faq = _get_mf_data_entry_help_data()
        show_standard_help(
            parent=mf_menu_window,
            title="MF Data Entry Help",
            guide_lines=guide,
            faq_data=faq
        )
    mf_menu_window.bind("<F1>", lambda e: None if getattr(e, "state", 0) & 0x0004 else _show_help(e))

    push_window(mf_menu_window, parent)
    parent.wait_window(mf_menu_window)
    try:
        parent.grab_set()
    except Exception:
        pass
    enable_parent(parent, modal_id)
