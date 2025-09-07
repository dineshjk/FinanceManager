# -*- coding: utf-8 -*-
"""
Custom Dialog Components Package
================================

This package provides custom dialog components with consistent styling
and behavior for the Stock Portfolio Management System. All dialogs
follow a unified design pattern with automatic sizing, proper modal
behavior, and accessibility features.

Key Features:
- Professional styled dialog components
- Dynamic sizing based on content
- Consistent color themes and typography
- Modal behavior with proper focus management
- Keyboard navigation support
- Accessibility features

Modules:
    info_dialogs: Information, error, and confirmation dialogs
    sizing: Dynamic dialog sizing utilities

Usage:
    # Information dialogs
    from FinanceManager.GUIStock.dialogs import show_colorful_info
    show_colorful_info(parent, "Success", "Operation completed successfully")

    # Error dialogs
    from FinanceManager.GUIStock.dialogs import show_colorful_error
    show_colorful_error(parent, "Error", "An error occurred")

    # Confirmation dialogs
    from FinanceManager.GUIStock.dialogs import show_colorful_yesno
    if show_colorful_yesno(parent, "Confirm", "Are you sure?"):
        # User clicked Yes
        pass
"""

# Import dialog functions and utilities
from .info_dialogs import (
    show_colorful_info,
    show_colorful_error,
    show_colorful_yesno
)
from .sizing import calculate_dialog_size

# Make dialog functions available at package level
__all__ = [
    'show_colorful_info',
    'show_colorful_error',
    'show_colorful_yesno',
    'calculate_dialog_size'
]
