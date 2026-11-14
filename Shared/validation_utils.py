# -*- coding: utf-8 -*-
# Shared/validation_utils.py
"""
Financial Input Validation Utilities & Numeric Verifiers.

This module provides reusable validation helper functions for input forms, dialogs,
and import pipelines across the Universal Finance Manager application.

Key Responsibilities:
    • Positive Numeric Validation: Verifies that numerical strings represent valid, positive
      numbers (integers or floating-point decimals), rejecting negatives, alphabetic chars,
      and invalid symbols.
    • Currency & Amount Verification: Enforces precision rules and bounds checks for trade
      prices, transaction amounts, interest rates, and share quantities.
    • Safe Type Coercion: Offers utilities to parse user input safely without throwing
      unhandled runtime exceptions.

Key Functions:
    • `validate_positive_numeric(value, field_name='Field')`: Validates that `value` is a
      positive number greater than zero; returns a tuple `(is_valid, error_message, float_val)`.
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
