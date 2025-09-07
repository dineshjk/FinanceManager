# -*- coding: utf-8 -*-
# File: c:\Users\aumji\source\repos\Finance\FinanceManager\GUIStock\dialogs\sizing.py

"""
Dynamic dialog sizing calculations for the Stock Portfolio Management System.

This module provides functions to automatically calculate optimal dialog
dimensions based on content length and complexity, ensuring professional
appearance and always-visible buttons.
"""


def calculate_dialog_size(message, title="", min_width=400, min_height=200,
                         max_width=800, max_height=600):
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
    lines = message.split('\n')
    line_count = len(lines)
    max_line_length = max(len(line) for line in lines) if lines else 0
    total_chars = len(message)

    # Base calculations
    # Width: Based on longest line (roughly 8 pixels per character) + padding
    estimated_width = max(max_line_length * 8 + 100, len(title) * 12 + 200)

    # Height: Base height + line count consideration + extra space for buttons
    base_height = 200  # Header + button area
    text_height = line_count * 25  # Approximately 25 pixels per line
    estimated_height = base_height + text_height

    # Apply scaling factors for very long messages
    if total_chars > 500:
        estimated_width = int(estimated_width * 1.2)
        estimated_height = int(estimated_height * 1.1)

    # Ensure minimum and maximum bounds
    width = max(min_width, min(estimated_width, max_width))
    height = max(min_height, min(estimated_height, max_height))

    return width, height
