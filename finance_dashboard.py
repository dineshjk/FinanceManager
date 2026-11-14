# -*- coding: utf-8 -*-
# finance_dashboard.py

"""Master Application Launcher & Central Dashboard.

This module serves as the primary root entry point for the Universal
Finance Manager desktop application. It initializes the main Tkinter
root window, sets up the master navigation hub, binds universal keyboard
shortcuts, and orchestrates launching the primary financial subsystems:
StockMan (Equity Portfolio & Market Intelligence), BankMan (Banking,
Passbook, & Budgeting), MFMan (Mutual Funds), and InsMan (Insurance).

Key Responsibilities:
    • Root Window Initialization: Creates the master `tk.Tk()` instance,
      sets geometry, applies titles, and ensures aggressive OS focus.
    • Subsystem Navigation: Hosts buttons with single-key hotkeys:
        - [S] Launch StockMan: Equity trades, corporate actions, reports.
        - [B] Launch BankMan: Bank accounts, double-entry passbook, budgets.
        - [M] Launch MFMan: Mutual fund folios, SIPs, and NAV valuation.
        - [I] Launch InsMan: Life, health, and vehicle policies/premiums.
        - [X] Exit: Graceful shutdown and cleanup.
    • Global Keyboard Handlers:
        - Ctrl+F1: Launches the Global Help Center from any active screen.
        - F1: Displays contextual help and FAQ for the dashboard.
        - Escape / X: Closes the application.
    • Dynamic Background Customization: Automatically detects custom
      wallpapers located in `Pics/` (e.g. `dashboard_bg.jpg`,
      `dashboard_bg.png`, `DN.jpg`), dynamically adjusting widget
      positioning, top spacing, and styling to keep image subjects
      visible. Falls back to clean original blue theme.

Primary Functions:
    • `main()`: Instantiates the root Tkinter application, configures
      global bindings, evaluates wallpaper availability, builds the
      menu configuration, and starts the Tkinter event loop.
    • `_get_dashboard_help_data()`: Generates the guide lines and FAQ data
      passed to `Shared.help_utils.show_standard_help` for F1 help.

Dependencies & Architecture:
    • `Shared.menu_factory.create_menu_window`: Declarative menu creation.
    • `Shared.global_help.show_global_help`: System-wide help center.
    • `StockMan.stocks.show_stock_portfolio_menu`: StockMan launcher.
    • `BankMan.banks.show_bank_main_menu`: BankMan subsystem launcher.
    • `BankMan.manage_mf.show_mf_main_menu`: MFMan subsystem launcher.
    • `BankMan.manage_ins.show_ins_main_menu`: InsMan subsystem launcher.
"""

import tkinter as tk
import sys
import os

# Add current dir to sys.path so we can import from StockMan and BankMan
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from Shared.menu_factory import create_menu_window  # noqa: E402
from StockMan.stocks import show_stock_portfolio_menu  # noqa: E402
from BankMan.banks import show_bank_main_menu  # noqa: E402
from BankMan.manage_mf import show_mf_main_menu  # noqa: E402
from BankMan.manage_ins import show_ins_main_menu  # noqa: E402
from Shared.globals import UNIVERSAL_APP_TITLE  # noqa: E402
from Shared.global_help import show_global_help  # noqa: E402
from Shared.help_utils import show_standard_help  # noqa: E402


def _get_dashboard_help_data():
    guide_lines = [
        "Welcome to the Universal Finance Manager Dashboard.",
        "",
        "This is the central launchpad for all financial modules.",
        (
            "• Launch StockMan: Manage your stock portfolio, trades, "
            "and corporate actions."
        ),
        (
            "• Launch BankMan: Manage bank accounts, passbook entries, "
            "and categorical budgets."
        ),
        "• Launch MFMan: Manage Mutual Fund investments.",
        "• Launch InsMan: Track Insurance policies and premiums.",
        "",
        "Custom Background Picture:",
        (
            "• If you want a custom background picture on the dashboard, "
            "create a folder"
        ),
        ("  named 'Pics' in FinanceManager and place an image file there"),
        "  (e.g. 'dashboard_bg.jpg', 'dashboard_bg.png', or 'DN.jpg').",
        (
            "• If no picture is present in 'Pics', the dashboard "
            "automatically loads with"
        ),
        "  its clean original theme background color.",
    ]
    faq_data = [
        (
            "Q: How do I exit the application?",
            (
                "A: You can click the 'Exit' button, use the hotkey 'X', "
                "or press Escape to close the Dashboard."
            ),
        ),
        (
            "Q: Can I run multiple modules at once?",
            (
                "A: The application currently opens one module at a time. "
                "Close a module to return to this dashboard and open another."
            ),
        ),
        (
            "Q: How do I configure a custom dashboard background picture?",
            (
                "A: Create a folder named 'Pics' inside FinanceManager and "
                "place an image named 'dashboard_bg.jpg' "
                "(or 'dashboard_bg.png', 'DN.jpg') inside it. When absent, "
                "the original background color is used automatically."
            ),
        ),
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
    root.bind(
        "<F1>",
        lambda e: (
            None
            if getattr(e, "state", 0) & 0x0004
            else show_standard_help(
                root, "Dashboard Help", *_get_dashboard_help_data()
            )
        ),
    )

    # Optional background image: look for supported image in Pics directory
    pics_dir = os.path.join(current_dir, "Pics")
    supported_image_names = [
        "dashboard_bg.jpg",
        "dashboard_bg.png",
        "DN.jpg",
        "Dwiju_and_Nana.jpg",
    ]
    bg_image_path = None
    if os.path.isdir(pics_dir):
        for candidate in supported_image_names:
            p = os.path.join(pics_dir, candidate)
            if os.path.isfile(p):
                bg_image_path = p
                break

    menu_config = {
        "title": UNIVERSAL_APP_TITLE,
        "geometry": "400x650",
        "style": "MainMenu.TButton",
        "parent": root,
        "modal": False,
        "bg": "#d0eff1",  # Original light blue background
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
            {"text": "Exit", "hotkey": "X", "command": root.destroy},
        ],
        "padx": 60,
        "pady": 5,
    }

    # If background image is present, apply picture-specific layout & styling
    if bg_image_path:
        menu_config.update(
            {
                "bg_image": bg_image_path,
                "bg_centering": (0.5, 0.35),
                "top_spacer": 260,  # Leaves gap for wallpaper subject
                "title_bg": "#1e293b",
                "title_fg": "#ffffff",
                "title_relief": "groove",
                "title_bd": 1,
            }
        )

    create_menu_window(menu_config)
    root.mainloop()


if __name__ == "__main__":
    main()
