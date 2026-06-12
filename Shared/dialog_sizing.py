# -*- coding: utf-8 -*-
# File: C:\Data\Personal\Finance_and_Investment\finprog\FinanceManager\StockMan\dialog_sizing.py


"""
Dynamic dialog sizing calculations for the Stock Portfolio Management System.

This module provides functions to automatically calculate optimal dialog
dimensions based on content length and complexity, ensuring professional
appearance and always-visible buttons.
"""
import tkinter as tk


def calculate_dialog_size(
    message,
    title="",
    min_width=400,
    min_height=200,
    max_width=800,
    max_height=600,
):
    """
    Calculate optimal dialog dimensions based on content length and complexity.

    Args:
        message (str): The message text to display
        title (str): The dialog title
        min_width (int): Minimum dialog width
        min_height (int): Minimum dialog height
        max_width (int): Maximum dialog width
        max_height (int): Maximum dialog height

    Returns:
        tuple: (width, height) for optimal dialog size
    """
    # Count lines and estimate text complexity
    lines = message.split("\n")
    line_count = len(lines)
    max_line_length = max(len(line) for line in lines) if lines else 0
    total_chars = len(message)

    # Base calculations
    # Width: Based on longest line (roughly 10 pixels per character for font size 14) + padding
    estimated_width = max(max_line_length * 10 + 100, len(title) * 12 + 200)

    # Height: Base height + line count consideration + extra space for buttons
    base_height = 200  # Header + button area
    text_height = (
        line_count * 30
    )  # Approximately 30 pixels per line for font size 14
    estimated_height = base_height + text_height

    # Apply scaling factors for very long messages
    if total_chars > 500:
        estimated_width = int(estimated_width * 1.2)
        estimated_height = int(estimated_height * 1.1)

    # Ensure minimum and maximum bounds
    width = max(min_width, min(estimated_width, max_width))
    height = max(min_height, min(estimated_height, max_height))

    return width, height


def get_screen_center_position(dialog_width, dialog_height):
    """
    Calculate position to center dialog on screen.

    Args:
        dialog_width (int): Width of the dialog
        dialog_height (int): Height of the dialog

    Returns:
        tuple: (x, y) position for centering the dialog
    """
    try:
        root = tk.Tk()
        root.withdraw()  # Hide the root window

        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()

        x = (screen_width - dialog_width) // 2
        y = (screen_height - dialog_height) // 2

        root.destroy()
        return x, y
    except (ImportError, tk.TclError):
        # Fallback position if screen detection fails
        return 100, 100


def calculate_wraplength(dialog_width, padding=40):
    """Calculate appropriate text wraplength for dialog content.

    Args:
        dialog_width (int): Width of the dialog
        padding (int): Padding to leave on sides

    Returns:
        int: Optimal wraplength for text widgets
    """
    return max(200, dialog_width - padding)


# File: C:\Data\Personal\Finance_and_Investment\finprog\FinanceManager\StockMan\dialog_sizing.py
