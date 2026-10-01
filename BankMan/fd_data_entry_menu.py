# -*- coding: utf-8 -*-
# BankMan/fd_data_entry_menu.py

"""
Fixed Deposit Data Entry menu for the BankMan application.
"""

from Shared.menu_factory import create_menu_window
from Shared.modal_utils import disable_parent, enable_parent
from Shared.window_manager import push_window, pop_window
from .fd_master_add import add_fd_master_main
from .fd_transactions_add import add_fd_transaction_main
from Shared.help_utils import show_standard_help

def _get_fd_data_entry_help_data():
    guide_lines = [
        "This menu manages the data entry for your Fixed Deposit ecosystem.",
        "",
        "• FD Master: Register a new Fixed Deposit product (set the principal amount, interest rate, and maturity date).",
        "• FD Transactions: Log standalone events like yearly interest accruals or TDS deductions that do not directly hit your bank passbook."
    ]
    faq_data = [
        (
            "Q: How do I record the initial money I put into the FD, or the final maturity payout?",
            "A: Do NOT enter the actual money movement here! Go to 'Data Entry' -> 'Bank' -> 'Add Transaction'. Record a Withdrawal (for opening) or Deposit (for maturity) in your Savings account, set the Entry Type to TRANSFER, select 'FD' as the Module Type, and pick your FD. This ensures your bank balance stays perfectly synced."
        )
    ]
    return guide_lines, faq_data


def show_fd_data_entry_menu(parent, come_back_index=None):
    """
    Displays the Fixed Deposit Data Entry menu for BankMan.
    """

    modal_id = disable_parent(parent)

    def close_modal() -> None:
        pop_window()
        enable_parent(parent, modal_id)
        fd_menu_window.destroy()

    menu_config = {
        "title": "FD Data Entry",
        "geometry": "400x350",
        "style": "Menu.TButton",
        "parent": parent,
        "modal": True,
        "bg": "#d4edda",
        "buttons": [
            {
                "text": "FD Master",
                "hotkey": "M",
                "command": lambda: add_fd_master_main(fd_menu_window),
            },
            {
                "text": "FD Transactions",
                "hotkey": "T",
                "command": lambda: add_fd_transaction_main(fd_menu_window),
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
    fd_menu_window, _ = create_menu_window(menu_config)

    # When the modal window's close button (X) is clicked, handle it gracefully
    fd_menu_window.protocol("WM_DELETE_WINDOW", close_modal)

    def _show_help(_e=None):
        guide, faq = _get_fd_data_entry_help_data()
        show_standard_help(
            parent=fd_menu_window,
            title="FD Data Entry Help",
            guide_lines=guide,
            faq_data=faq
        )
    fd_menu_window.bind("<F1>", lambda e: None if getattr(e, "state", 0) & 0x0004 else _show_help(e))

    push_window(fd_menu_window, parent)
    parent.wait_window(fd_menu_window)
    try:
        parent.grab_set()
    except Exception:
        pass
    enable_parent(parent, modal_id)
