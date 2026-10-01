# -*- coding: utf-8 -*-
# BankMan/data_entry_menu.py

"""
Top-level Data Entry menu for the BankMan application.
Provides navigation to module-specific data-entry sub-menus.
"""

from Shared.menu_factory import create_menu_window
from Shared.modal_utils import disable_parent, enable_parent
from Shared.window_manager import push_window, pop_window
from Shared.help_utils import show_standard_help
from .bank_data_entry_menu import show_data_entry_menu as show_bank_data_entry_menu
from .cc_data_entry_menu import show_cc_data_entry_menu
from .fd_data_entry_menu import show_fd_data_entry_menu
from .loan_data_entry_menu import show_loan_data_entry_menu
from .ppf_data_entry_menu import show_ppf_data_entry_menu


def _get_data_entry_help_data():
    guide_lines = [
        "This is your primary hub for logging new financial transactions.",
        "",
        "• Bank: Opens the passbook entry screen to log all savings/current account movements (including MFs, Insurance, and StockMan links).",
        "• Credit Card: Record independent credit card expenses or statement generations.",
        "• Fixed Deposit / Loan / PPF: Log standalone events that do not directly hit your bank passbook (e.g., yearly PPF interest accrual or loan rate changes)."
    ]
    faq_data = [
        (
            "Q: Where are the Mutual Fund and Insurance data entry buttons?",
            "A: You can log Mutual Fund purchases/redemptions and Insurance premium payments directly from the 'Bank' Data Entry screen! Just select 'MF' or 'INS' under the Module Type dropdown when logging your bank withdrawal/deposit."
        )
    ]
    return guide_lines, faq_data


def show_top_data_entry_menu(parent, come_back_index=None):
    """
    Displays the top-level Data Entry menu for BankMan.
    """

    modal_id = disable_parent(parent)

    def close_modal() -> None:
        pop_window()
        menu_window.destroy()

    # Create an empty list to hold our window reference for the lambdas
    window_ref = []

    menu_config = {
        "title": "Data Entry Menu",
        "geometry": "400x450",
        "style": "Menu.TButton",
        "parent": parent,
        "modal": True,
        "bg": "#c5e8f7",
        "buttons": [
            {
                "text": "Bank",
                "hotkey": "B",
                "command": lambda: show_bank_data_entry_menu(window_ref[0]),
            },
            {
                "text": "Credit Card",
                "hotkey": "C",
                "command": lambda: show_cc_data_entry_menu(window_ref[0]),
            },
            {
                "text": "Fixed Deposit",
                "hotkey": "D",
                "command": lambda: show_fd_data_entry_menu(window_ref[0]),
            },
            {
                "text": "Loan",
                "hotkey": "L",
                "command": lambda: show_loan_data_entry_menu(window_ref[0]),
            },
            {
                "text": "PPF",
                "hotkey": "F",
                "command": lambda: show_ppf_data_entry_menu(window_ref[0]),
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
    menu_window, _ = create_menu_window(menu_config)

    # Append the newly created window to the list so the lambdas can access it
    window_ref.append(menu_window)

    # When the modal window's close button (X) is clicked, handle it gracefully
    menu_window.protocol("WM_DELETE_WINDOW", close_modal)

    def _show_help(_e=None):
        guide, faq = _get_data_entry_help_data()
        show_standard_help(
            parent=menu_window,
            title="Data Entry Menu Help",
            guide_lines=guide,
            faq_data=faq
        )
    menu_window.bind("<F1>", lambda e: None if getattr(e, "state", 0) & 0x0004 else _show_help(e))

    push_window(menu_window, parent)
    parent.wait_window(menu_window)
    try:
        parent.grab_set()
    except Exception:
        pass
    enable_parent(modal_id)
