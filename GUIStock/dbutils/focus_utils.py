# -*- coding: utf-8 -*-
"""
Centralized Focus Restoration Utilities for Modal Windows

This module provides a reusable focus restoration system that automatically
moves focus to the next button when modal windows close.

Usage:
    from dbutils.focus_utils import restore_focus_to_next_button

    # In your modal window function:
    modal_window.wait_window()
    restore_focus_to_next_button(parent_window, calling_button)
"""

import tkinter as tk
from typing import Optional
import logging

# Create logger for this module
logger = logging.getLogger(__name__)


def find_next_focusable_widget(start_widget: tk.Widget,
                             parent_window: tk.Widget) -> Optional[tk.Widget]:
    """
    Find the next focusable widget after the given widget in the parent window.

    Args:
        start_widget: The widget to start searching from
        parent_window: The parent window containing all widgets

    Returns:
        The next focusable widget, or None if not found
    """
    if not start_widget or not parent_window:
        return None

    try:
        def get_all_focusable_widgets(widget):
            """Recursively find all focusable widgets."""
            focusable_list = []
            try:
                for child in widget.winfo_children():
                    # Check if widget can take focus
                    if (hasattr(child, 'focus_set') and
                        child.winfo_viewable() and
                        str(child.cget('state') if hasattr(child, 'cget')
                            else 'normal') != 'disabled'):

                        widget_class = child.winfo_class()
                        focusable_classes = [
                            'Button', 'Entry', 'Text', 'Listbox',
                            'Scale', 'Checkbutton', 'Radiobutton', 'Combobox'
                        ]
                        if widget_class in focusable_classes:
                            focusable_list.append(child)

                    # Recursively check children
                    focusable_list.extend(get_all_focusable_widgets(child))
            except Exception:
                pass
            return focusable_list

        focusable_widgets = get_all_focusable_widgets(parent_window)

        if not focusable_widgets:
            return None

        # Find the current widget in the list
        try:
            current_index = focusable_widgets.index(start_widget)
            # Return the next widget, or wrap to first if at the end
            next_index = (current_index + 1) % len(focusable_widgets)
            return focusable_widgets[next_index]
        except (ValueError, IndexError):
            # If start_widget not found, return first focusable widget
            return focusable_widgets[0] if focusable_widgets else None

    except Exception as e:
        logger.debug(f"Error finding next focusable widget: {e}")
        return None


def restore_focus_to_next_button(parent_window: tk.Widget,
                                calling_button: Optional[tk.Widget] = None,
                                delay_ms: int = 50) -> None:
    """
    CENTRALIZED FOCUS RESTORATION UTILITY

    Automatically restores focus to the next button after a modal window closes.
    This is the main function that should be called by all modal windows.

    Args:
        parent_window: The parent window to restore focus to
        calling_button: The button that opened the modal (auto-detected if None)
        delay_ms: Delay in milliseconds before setting focus (default: 50)

    Example:
        # In your modal window function:
        modal_window.wait_window()
        restore_focus_to_next_button(parent, calling_button)
    """
    try:
        # Auto-detect the calling button if not provided
        if calling_button is None:
            try:
                calling_button = parent_window.focus_get()
                logger.debug(f"Auto-detected calling button: {calling_button}")
            except Exception:
                calling_button = None
                logger.debug("Could not auto-detect calling button")

        # Re-enable parent window (removed attributes disable - now just focus)
        parent_window.focus_set()
        parent_window.lift()

        # If we have a calling button, find the next button to focus
        if calling_button:
            next_widget = find_next_focusable_widget(calling_button, parent_window)
            if next_widget:
                logger.info(f"Focus restored to next widget: {next_widget}")
                # Small delay to ensure window is ready
                parent_window.after(delay_ms, lambda: next_widget.focus_set())
            else:
                logger.debug("No next widget found, setting focus to parent")
                parent_window.after(delay_ms, lambda: parent_window.focus_set())
        else:
            logger.debug("No calling button provided, setting focus to parent")
            parent_window.after(delay_ms, lambda: parent_window.focus_set())

    except Exception as e:
        logger.error(f"Error in focus restoration: {e}")
        try:
            # Fallback: just focus the parent window (no disable/enable needed)
            parent_window.focus_set()
        except Exception:
            pass


def setup_modal_window(modal_window: tk.Toplevel,
                      parent_window: tk.Widget,
                      title: str = "Modal Window",
                      geometry: str = "400x300",
                      resizable: tuple = (False, False)) -> None:
    """
    Set up standard modal window properties with parent disabling.

    Args:
        modal_window: The Toplevel window to configure
        parent_window: The parent window to disable
        title: Window title
        geometry: Window size as "widthxheight"
        resizable: Tuple of (width_resizable, height_resizable)
    """
    try:
        modal_window.title(title)
        modal_window.geometry(geometry)
        modal_window.resizable(resizable[0], resizable[1])
        modal_window.transient(parent_window)
        modal_window.grab_set()

        # Modal behavior handled by grab_set() and transient() - no need to disable parent

        logger.debug(f"Modal window '{title}' configured successfully")

    except Exception as e:
        logger.error(f"Error setting up modal window: {e}")


def add_escape_binding(modal_window: tk.Toplevel,
                      close_callback: callable) -> None:
    """
    Add standard Escape key binding to close modal window.

    Args:
        modal_window: The modal window to bind Escape key
        close_callback: Function to call when Escape is pressed
    """
    try:
        modal_window.bind("<Escape>", lambda e: close_callback())
        logger.debug("Escape key binding added to modal window")
    except Exception as e:
        logger.error(f"Error adding escape binding: {e}")


# =====================================================
# CONVENIENCE WRAPPER FOR COMMON MODAL PATTERN
# =====================================================

class ModalWindowManager:
    """
    Context manager for modal windows with automatic focus restoration.

    Usage:
        with ModalWindowManager(parent, calling_button) as modal:
            modal.setup_window("My Modal", "500x400")
            modal.add_escape_binding(modal.window.destroy)
            # ... build your modal content ...
            modal.window.wait_window()
        # Focus is automatically restored when exiting the context
    """

    def __init__(self, parent_window: tk.Widget,
                 calling_button: Optional[tk.Widget] = None):
        self.parent_window = parent_window
        self.calling_button = calling_button
        self.window = None

    def __enter__(self):
        self.window = tk.Toplevel(self.parent_window)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.window:
            restore_focus_to_next_button(self.parent_window, self.calling_button)

    def setup_window(self, title: str = "Modal Window",
                    geometry: str = "400x300",
                    resizable: tuple = (False, False)):
        """Set up the modal window properties."""
        if self.window:
            setup_modal_window(self.window, self.parent_window,
                             title, geometry, resizable)

    def add_escape_binding(self, close_callback: callable):
        """Add Escape key binding."""
        if self.window:
            add_escape_binding(self.window, close_callback)
