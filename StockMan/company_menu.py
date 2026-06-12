# -*- coding: utf-8 -*-
# StockMan/company_menu.py
# File:


"""
Company management menu window for the Stock Portfolio Management System.

Provides access to:
- Add Company
- Update Company
- Remove Company
- Bulk Entry Company
"""

# import tkinter as tk


# from .gui_progressive import test_modal_window
from .company_bulk_entry import bulk_entry_company
from .company_add import add_company
from .company_update import update_company
from .company_remove import remove_company
from Shared.menu_factory import create_menu_window
from Shared.modal_utils import disable_parent, enable_parent
from Shared.window_manager import push_window, pop_window
from .company_ex_import import export_company, import_company

DEFAULT_GEOMETRY = "400x450"


def show_company_menu_modal(parent, come_back_index=None):
    """Show the company management menu as a modal window.

    Uses the menu_factory system. Optionally accepts
    come_back_index to restore focus to the next button in parent.
    """
    modal_id = disable_parent(parent)

    def close_modal() -> None:
        pop_window()
        modal_win.destroy()

    menu_config = {
        "title": "Company Menu",
        "geometry": DEFAULT_GEOMETRY,
        "style": "Menu.TButton",
        "parent": parent,
        "modal": True,
        "bg": "#888e90",  # Light gray for modal
        "buttons": [
            {
                "text": "Bulk Entry",
                "hotkey": "B",
                "command": lambda: bulk_entry_company(modal_win),
            },
            {
                "text": "Export Company List",
                "hotkey": "E",
                "command": lambda: export_company(modal_win),
            },
            {
                "text": "Import Company List",
                "hotkey": "I",
                "command": lambda: import_company(modal_win),
            },
            {
                "text": "Add Company",
                "hotkey": "A",
                "command": lambda: add_company(modal_win),
            },
            {
                "text": "Update Company",
                "hotkey": "U",
                "command": lambda: update_company(modal_win),
            },
            {
                "text": "Remove Company",
                "hotkey": "R",
                "command": lambda: remove_company(modal_win),
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
    modal_win, _ = create_menu_window(menu_config)

    # Ensure window manager stack is popped if the user clicks the 'X' button
    modal_win.protocol("WM_DELETE_WINDOW", close_modal)

    push_window(modal_win, parent)
    parent.wait_window(modal_win)
    parent.grab_set()
    enable_parent(modal_id)


# File:
