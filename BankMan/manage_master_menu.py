# -*- coding: utf-8 -*-
# BankMan/manage_master_menu.py

"""
Manage Master menu for the BankMan application.
Provides navigation to module-specific master-management sub-menus.
"""

from Shared.menu_factory import create_menu_window
from Shared.modal_utils import disable_parent, enable_parent
from Shared.window_manager import push_window, pop_window
from Shared.help_utils import show_standard_help
from .manage_bank import show_bank_manager
from .manage_cc import show_cc_manager
from .manage_fd import show_fd_manager
from .manage_loan import show_loan_manager
from .manage_ppf import show_ppf_manager
from .manage_mf import show_mf_main_menu
from .manage_ins import show_ins_main_menu


def _get_manage_master_help_data():
    guide_lines = [
        "This hub allows you to access the management grids for all your structural financial records.",
        "",
        "• Bank: View, edit, or delete registered banks (e.g., correcting an IFSC).",
        "• Credit Card: Update limits, billing cycles, or remove old cards.",
        "• Fixed Deposit / Loan / PPF: Safely edit product details or track maturity parameters.",
        "• Mutual Funds / Insurance: Track Folios, AMCs, Policies, and Life Assured details."
    ]
    faq_data = [
        (
            "Q: Can I add new records from this menu?",
            "A: No, this menu is strictly for managing existing records. To add new ones, go to 'Data Entry' or use the 'New' buttons dynamically while adding a bank transaction."
        )
    ]
    return guide_lines, faq_data


def show_manage_master_menu(parent, come_back_index=None):
    """
    Displays the Manage Master menu for BankMan.
    """

    modal_id = disable_parent(parent)

    def close_modal() -> None:
        pop_window()
        menu_window.destroy()

    menu_config = {
        "title": "Manage Master",
        "geometry": "400x560",
        "style": "Menu.TButton",
        "parent": parent,
        "modal": True,
        "bg": "#c5f7e4",
        "buttons": [
            {
                "text": "Bank",
                "hotkey": "B",
                "command": lambda: show_bank_manager(menu_window),
            },
            {
                "text": "Credit Card",
                "hotkey": "C",
                "command": lambda: show_cc_manager(menu_window),
            },
            {
                "text": "Fixed Deposit",
                "hotkey": "D",
                "command": lambda: show_fd_manager(menu_window),
            },
            {
                "text": "Loan",
                "hotkey": "L",
                "command": lambda: show_loan_manager(menu_window),
            },
            {
                "text": "PPF",
                "hotkey": "F",
                "command": lambda: show_ppf_manager(menu_window),
            },
            {
                "text": "Mutual Funds",
                "hotkey": "M",
                "command": lambda: show_mf_main_menu(menu_window),
            },
            {
                "text": "Insurance",
                "hotkey": "I",
                "command": lambda: show_ins_main_menu(menu_window),
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

    menu_window, _ = create_menu_window(menu_config)
    menu_window.protocol("WM_DELETE_WINDOW", close_modal)

    def _show_help(_e=None):
        guide, faq = _get_manage_master_help_data()
        show_standard_help(
            parent=menu_window,
            title="Manage Master Help",
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
