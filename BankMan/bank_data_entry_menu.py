# -*- coding: utf-8 -*-
# BankMan/bank_data_entry_menu.py

"""
Data entry menu for the BankMan application.
"""

from Shared.menu_factory import create_menu_window
from Shared.modal_utils import disable_parent, enable_parent
from Shared.window_manager import push_window, pop_window
from Shared.help_utils import show_standard_help
from .banks_add import add_bank
from .budget_head_add import add_account_type_main
from .accounts_add import add_account_main
from .accounts_edit import edit_account
from .bank_transactions_add import add_bank_transaction_main


def _get_bank_data_entry_help_data():
    guide_lines = [
        "This menu is specifically for logging new bank-related masters and passbook entries.",
        "",
        "• Add Bank: Register a new financial institution (e.g., HDFC, SBI).",
        "• Add Budget Category: Create new Income or Expense heads for tracking.",
        "• Add Account: Register a new Savings, Current, or Overdraft account.",
        "• Edit Account: Quickly fix account details without navigating to Manage Master.",
        "• Add Transaction: Open the passbook entry form to log deposits, withdrawals, and asset transfers."
    ]
    faq_data = [
        (
            "Q: How do I add a new Mutual Fund, Insurance Policy, or FD from here?",
            "A: Click on 'Add Transaction'. When logging your bank entry, select the respective Module Type (MF, INS, FD) and use the 'New' button to create the master record on the fly!"
        )
    ]
    return guide_lines, faq_data


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

    def _show_help(_e=None):
        guide, faq = _get_bank_data_entry_help_data()
        show_standard_help(
            parent=bank_data_window,
            title="Bank Data Entry Help",
            guide_lines=guide,
            faq_data=faq
        )
    bank_data_window.bind("<F1>", lambda e: None if getattr(e, "state", 0) & 0x0004 else _show_help(e))

    push_window(bank_data_window, parent)
    parent.wait_window(bank_data_window)
    try:
        parent.grab_set()
    except Exception:
        pass
    enable_parent(modal_id)
