# -*- coding: utf-8 -*-
# BankMan/loan_data_entry_menu.py

"""
Loan Data Entry menu for the BankMan application.
"""

from Shared.menu_factory import create_menu_window
from Shared.modal_utils import disable_parent, enable_parent
from Shared.window_manager import push_window, pop_window
from .loan_master_add import add_loan_master_main
from .loan_transactions_add import add_loan_transaction_main
from .loan_master_edit import edit_loan_master
from Shared.help_utils import show_standard_help

def _get_loan_data_entry_help_data():
    guide_lines = [
        "This menu manages the data entry for your Loan and EMI ecosystem.",
        "",
        "• Loan Master: Register a new Loan product (set the principal amount, interest rate, and linked account).",
        "• Edit Loan Master: Modify the master details of an existing loan, such as updating a floating interest rate.",
        "• Loan Transactions: Log standalone events like periodic interest accruals or penalty fees that do not directly hit your bank passbook."
    ]
    faq_data = [
        (
            "Q: How do I record my monthly EMI payment?",
            "A: Do NOT enter the actual money movement here! Go to 'Data Entry' -> 'Bank' -> 'Add Transaction'. Record a Withdrawal from your Savings account, set the Entry Type to TRANSFER, select 'LOAN' as the Module Type, and pick your Loan. BankMan will automatically split the EMI into Principal and Interest components."
        )
    ]
    return guide_lines, faq_data


def show_loan_data_entry_menu(parent, come_back_index=None):
    """
    Displays the Loan Data Entry menu for BankMan.
    """

    modal_id = disable_parent(parent)

    def close_modal() -> None:
        pop_window()
        enable_parent(parent, modal_id)
        loan_menu_window.destroy()

    menu_config = {
        "title": "Loan Data Entry",
        "geometry": "400x420",
        "style": "Menu.TButton",
        "parent": parent,
        "modal": True,
        "bg": "#fff3cd",
        "buttons": [
            {
                "text": "Loan Master",
                "hotkey": "M",
                "command": lambda: add_loan_master_main(loan_menu_window),
            },
            {
                "text": "Edit Loan Master",
                "hotkey": "E",
                "command": lambda: edit_loan_master(loan_menu_window),
            },
            {
                "text": "Loan Transactions",
                "hotkey": "T",
                "command": lambda: add_loan_transaction_main(loan_menu_window),
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
    loan_menu_window, _ = create_menu_window(menu_config)

    # When the modal window's close button (X) is clicked, handle it gracefully
    loan_menu_window.protocol("WM_DELETE_WINDOW", close_modal)

    def _show_help(_e=None):
        guide, faq = _get_loan_data_entry_help_data()
        show_standard_help(
            parent=loan_menu_window,
            title="Loan Data Entry Help",
            guide_lines=guide,
            faq_data=faq
        )
    loan_menu_window.bind("<F1>", lambda e: None if getattr(e, "state", 0) & 0x0004 else _show_help(e))

    push_window(loan_menu_window, parent)
    parent.wait_window(loan_menu_window)
    try:
        parent.grab_set()
    except Exception:
        pass
    enable_parent(parent, modal_id)
