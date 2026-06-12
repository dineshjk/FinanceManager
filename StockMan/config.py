# -*- coding: utf-8 -*-
# StockMan/config.py
import logging

# Centralized UI Theme (Decoupled from StockMan)
UI_THEME = {
    "dark_slate": "#1e293b",
    "charcoal": "#334155",
    "slate_light": "#475569",
    "gold": "#FFD700",
    "white": "#ffffff",
    "red_alert": "#ef4444",
    "bg_header": "#1e293b",
    "fg_header": "#ffffff",
    "bg_input": "black",
    "fg_input": "yellow",
    "bg_readonly": "black",
    "fg_readonly": "yellow",
    "bg_disabled": "black",
    "fg_disabled": "yellow",
    "bg_hover": "#8a1e62",
    "fg_hover": "#FFD700",
    "bg_focus": "red",
    "fg_focus": "yellow",
    "bg_select": "blue",
    "bg_error": "#ffcccc",
    "font_main": ("Helvetica", 14, "bold"),
    "font_bold": ("Helvetica", 14, "bold"),
    "font_title": ("Helvetica", 16, "bold"),
}

# Shared logger for UI components
logger = logging.getLogger("FinanceManagerUI")
