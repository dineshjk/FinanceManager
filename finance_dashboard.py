# -*- coding: utf-8 -*-
# finance_dashboard.py

import tkinter as tk
import sys
import os

# Add current dir to sys.path so we can import from StockMan and BankMan
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from Shared.menu_factory import create_menu_window
# from Shared.dialog_utils import show_colorful_info
from StockMan.stocks import show_stock_portfolio_menu
from BankMan.banks import show_bank_main_menu
from BankMan.manage_mf import show_mf_main_menu
from BankMan.manage_ins import show_ins_main_menu
from Shared.globals import UNIVERSAL_APP_TITLE
from Shared.global_help import show_global_help
from Shared.help_utils import show_standard_help


def _get_dashboard_help_data():
    guide_lines = [
        "Welcome to the Universal Finance Manager Dashboard.",
        "",
        "This is the central launchpad for all financial modules.",
        "• Launch StockMan: Manage your stock portfolio, trades, and corporate actions.",
        "• Launch BankMan: Manage bank accounts, passbook entries, and categorical budgets.",
        "• Launch MFMan: Manage Mutual Fund investments.",
        "• Launch InsMan: Track Insurance policies and premiums."
    ]
    faq_data = [
        (
            "Q: How do I exit the application?",
            "A: You can click the 'Exit' button, use the hotkey 'X', or press Escape to close the Dashboard."
        ),
        (
            "Q: Can I run multiple modules at once?",
            "A: The application currently opens one module at a time. Close a module to return to this dashboard and open another."
        )
    ]
    return guide_lines, faq_data


def main():
    """
    Initialize and run the main application window for
    Universal Finance Manager. Presently it contains two
    branches: StockMan for stock portfolio management and
    BankMan for bank account management. The main menu is designed
    to serve as the central hub for navigating between these modules.
    """
    root = tk.Tk()

    # Force OS focus aggressively on the new window
    root.lift()
    try:
        root.attributes("-topmost", True)
        root.after_idle(root.attributes, "-topmost", False)
    except tk.TclError:
        pass
    root.focus_force()

    # Bind Global Help to Ctrl+F1 globally across all windows
    root.bind_all("<Control-F1>", lambda e: show_global_help(root))

    # Bind screen-specific Help to F1
    root.bind("<F1>", lambda e: None if getattr(e, "state", 0) & 0x0004 else show_standard_help(
        root,
        "Dashboard Help",
        *_get_dashboard_help_data()
    ))

    menu_config = {
        "title": UNIVERSAL_APP_TITLE,
        "geometry": "400x650",
        "style": "MainMenu.TButton",
        "parent": root,
        "modal": False,
        "bg": "#d0eff1",  # Light blue for main window
        "buttons": [
            {
                "text": "Launch StockMan",
                "hotkey": "S",
                "command": lambda: show_stock_portfolio_menu(root),
            },
            {
                "text": "Launch BankMan",
                "hotkey": "B",
                "command": lambda: show_bank_main_menu(root),
            },
            {
                "text": "Launch MFMan (Mutual Funds)",
                "hotkey": "M",
                "command": lambda: show_mf_main_menu(root),
            },
            {
                "text": "Launch InsMan (Insurance)",
                "hotkey": "I",
                "command": lambda: show_ins_main_menu(root),
            },
            {
                "text": "Exit",
                "hotkey": "X",
                "command": root.destroy
            },
        ],
        "padx": 60,
        "pady": 5,
    }
    create_menu_window(menu_config)
    root.mainloop()


if __name__ == "__main__":
    main()
