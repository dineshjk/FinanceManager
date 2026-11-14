# -*- coding: utf-8 -*-
# Shared/style_utils.py

"""
ttk Styling Configuration, Theme Presets, and Widget Appearance.

This module configures the global `ttk.Style` engine for the application. It establishes
uniform color schemes, button appearances, active/hover pseudo-states, font standards,
and custom widget style definitions used throughout the user interface.

Key Responsibilities:
    • Centralized Style Registration: Defines and registers application-wide ttk styles:
        - `MainMenu.TButton`: Large, prominent navigation buttons for main hubs.
        - `Action.TButton`: Primary execution buttons (Save, Update, Calculate).
        - `Warning.TButton` / `Danger.TButton`: High-visibility deletion or rollback buttons.
        - `Heading.TLabel`: Standardized section header typography.
    • Idempotent Initialization: Ensures styles are initialized once per application session
      to prevent redundant Tkinter styling reconfiguration overhead.

Key Functions:
    • `apply_style(widget, style_key)`: Applies a pre-configured style preset to a widget.
    • `ensure_ttk_style(style_name)`: Verifies that a specific ttk style has been initialized.
    • `get_style_configuration()`: Returns the master dictionary of application style presets.
"""

import tkinter as tk
import tkinter.ttk as ttk

# Tracks which styles have been initialized
_initialized_styles = {}

STYLE_CONFIGS = {
    "MainMenu.TButton": {
        "font": ("Helvetica", 12),
        "color_map": {
            "foreground": [
                ("hover", "black"),
                ("active", "white"),
                ("focus", "white"),
                ("!active", "black"),
            ],
            "background": [
                ("hover", "#F8BEC7"),
                ("active", "#0078D7"),
                ("focus", "#0078D7"),
                ("!active", "SystemButtonFace"),
            ],
        },
    },
    "Menu.TButton": {
        "font": ("Helvetica", 12),
        "color_map": {
            "foreground": [
                ("hover", "black"),
                ("active", "white"),
                ("focus", "white"),
                ("!active", "black"),
            ],
            "background": [
                ("hover", "#F871C7"),
                ("active", "#0078D7"),
                ("focus", "#0078D7"),
                ("!active", "SystemButtonFace"),
            ],
        },
    },
}


def apply_style(widget, style_key):
    """
    Apply style configuration from STYLE_CONFIGS to a given widget.

    Args:
        widget: The Tkinter widget to style.
        style_key (str): The key in STYLE_CONFIGS for the desired style.
    """
    style = STYLE_CONFIGS.get(style_key, {})
    for k, v in style.items():
        try:
            widget[k] = v
        except (AttributeError, tk.TclError):
            pass


def ensure_ttk_style(style_name):
    """
    Ensure a ttk style is initialized only once for the given style name.
    If the style is not already initialized, configure it using the
    settings in STYLE_CONFIGS.

    Args:
        style_name (str): The ttk style name (e.g., 'MainMenu.TButton').
    """
    if style_name not in _initialized_styles and style_name in STYLE_CONFIGS:
        cfg = STYLE_CONFIGS[style_name]
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            style_name, font=cfg["font"], padding=6, width=25.0, anchor="w"
        )
        style.map(style_name, **cfg["color_map"])
        _initialized_styles[style_name] = True
