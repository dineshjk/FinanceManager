# -*- coding: utf-8 -*-
# File: C:\Data\Personal\Finance_and_Investment\finprog\FinanceManager\finance_dashboard.py

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
from Shared.globals import UNIVERSAL_APP_TITLE


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

    menu_config = {
        "title": UNIVERSAL_APP_TITLE,
        "geometry": "400x530",
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
