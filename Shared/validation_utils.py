# -*- coding: utf-8 -*-
"""
This module provides validation utility functions for the FinanceManager application.
"""

import tkinter as tk
from Shared.gui_utils import UI_THEME


def validate_positive_numeric(event=None):
    """Validates that a Tkinter Entry contains a positive numeric value, blinking if invalid."""
    bg_normal = UI_THEME["bg_input"]
    bg_error = UI_THEME["bg_error"]

    if event is not None and hasattr(event, "widget"):
        widget = event.widget
        try:
            val = float(widget.get())
            if val < 0:
                raise ValueError("Negative value")
            widget.config(bg=bg_normal)
        except (ValueError, TypeError):

            def blink(w, colors, delay=100, count=0):
                try:
                    if count < len(colors):
                        w.config(bg=colors[count])
                        w.after(delay, blink, w, colors, delay, count + 1)
                    else:
                        w.config(bg=bg_error)
                except tk.TclError:
                    pass

            blink(widget, [bg_error, bg_normal] * 5)
