# -*- coding: utf-8 -*-
# StockMan/finance_dashboard.py
import tkinter as tk
from Shared.menu_factory import create_menu_window

# Import main entry points from sub-projects once they are refactored
# from StockMan.stocks import main as launch_stockman
# from BankMan.banks import main as launch_bankman


def launch_stockman(root):
    from Shared.dialog_utils import show_colorful_info

    show_colorful_info(root, "Routing", "Will launch StockMan dashboard here!")


def launch_bankman(root):
    from Shared.dialog_utils import show_colorful_info

    show_colorful_info(root, "Routing", "Will launch BankMan dashboard here!")


def main():
    root = tk.Tk()
    menu_config = {
        "title": "Universal Finance Manager",
        "geometry": "400x300",
        "style": "MainMenu.TButton",
        "parent": root,
        "modal": False,
        "bg": "#1e293b",
        "buttons": [
            {
                "text": "📈 Launch StockMan",
                "hotkey": "S",
                "command": lambda: launch_stockman(root),
            },
            {
                "text": "🏦 Launch BankMan",
                "hotkey": "B",
                "command": lambda: launch_bankman(root),
            },
            {"text": "Exit", "hotkey": "X", "command": root.destroy},
        ],
        "padx": 60,
        "pady": 10,
    }
    create_menu_window(menu_config)
    root.mainloop()


if __name__ == "__main__":
    main()
