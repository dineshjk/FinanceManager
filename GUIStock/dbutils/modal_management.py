# -*- coding: utf-8 -*-
"""
Centralized Modal Window Management System

This module provides a unified system for managing modal windows with automatic
focus restoration and parent window state management.

Usage:
    from dbutils.modal_management import disable_parent, enable_parent

    # In your modal window function:
    modal_id = disable_parent(parent)
    # ... create and show modal window ...
    enable_parent(modal_id)

Features:
    - Automatic focus restoration to next button
    - Parent window state management
    - Error handling and debugging
    - Minimal API with just 2 function calls
"""

import tkinter as tk
from typing import Optional
import uuid

# Import logger using the new package structure
from FinanceManager.GUIStock.config import logger


# =====================================================
# CENTRALIZED MODAL WINDOW MANAGEMENT SYSTEM
# =====================================================

# Global storage for parent window states
_parent_window_states = {}


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
    print(f"DEBUG: find_next_focusable_widget called with start_widget={start_widget}")
    logger.debug(f"Finding next focusable widget after {start_widget}")

    if not start_widget or not parent_window:
        print("DEBUG: start_widget or parent_window is None")
        logger.debug("start_widget or parent_window is None")
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
        logger.debug(f"Found {len(focusable_widgets)} focusable widgets")

        if not focusable_widgets:
            logger.debug("No focusable widgets found")
            return None

        # Find the current widget in the list
        try:
            current_index = focusable_widgets.index(start_widget)
            logger.debug(f"Current widget found at index {current_index}")
            # Return the next widget, or wrap to first if at the end
            next_index = (current_index + 1) % len(focusable_widgets)
            next_widget = focusable_widgets[next_index]
            logger.debug(f"Next widget at index {next_index}: {next_widget}")
            return next_widget
        except (ValueError, IndexError):
            logger.debug("start_widget not found in list, returning first focusable widget")
            # If start_widget not found, return first focusable widget
            return focusable_widgets[0] if focusable_widgets else None

    except Exception as e:
        logger.error(f"Error finding next focusable widget: {e}")
        return None


def disable_parent(parent_window: tk.Widget,
                  modal_id: str = None,
                  calling_button: tk.Widget = None) -> str:
    """
    Disable parent window and store its current state for later restoration.

    Args:
        parent_window: The parent window to disable
        modal_id: Optional ID for this modal (auto-generated if None)
        calling_button: Optional specific button that called this modal

    Returns:
        str: The modal ID for use with enable_parent()

    Usage:
        modal_id = disable_parent(parent, calling_button=button)
        # ... create and show modal window ...
        enable_parent(modal_id)
    """
    if modal_id is None:
        modal_id = str(uuid.uuid4())[:8]  # Short unique ID

    logger.debug(f"Disabling parent window with modal_id: {modal_id}")

    try:
        # Use provided calling button or auto-detect from current focus
        if calling_button:
            current_focus = calling_button
            logger.debug(f"Using provided calling button: {calling_button}")
        else:
            current_focus = parent_window.focus_get()
            logger.debug(f"Auto-detected current focus widget: {current_focus}")

        # Store parent window state
        _parent_window_states[modal_id] = {
            'parent_window': parent_window,
            'calling_button': current_focus,
            'was_disabled': False  # Will be updated if parent was already disabled
        }

        # Check if parent is already disabled
        try:
            current_state = parent_window.cget('-disabled')
            _parent_window_states[modal_id]['was_disabled'] = bool(current_state)
            logger.debug(f"Parent was already disabled: {bool(current_state)}")
        except Exception:
            _parent_window_states[modal_id]['was_disabled'] = False

        # Disable the parent window using grab_set
        try:
            # Store the current grab state
            current_grab = parent_window.grab_current()
            _parent_window_states[modal_id]['previous_grab'] = current_grab

            # Don't actually disable the parent, just store it for focus restoration
            logger.debug("Stored parent window for modal management")
        except Exception as e:
            logger.warning(f"Failed to store grab state: {e}")
        logger.debug("Parent window prepared for modal behavior")

    except Exception as e:
        logger.error(f"Error in disable_parent: {e}")
        # Store minimal state for fallback
        _parent_window_states[modal_id] = {
            'parent_window': parent_window,
            'calling_button': None,
            'was_disabled': False
        }

    return modal_id


def enable_parent(modal_id: str, delay_ms: int = 100) -> None:
    """
    Enable parent window and restore focus to the next button in sequence.

    Args:
        modal_id: The ID returned by disable_parent()
        delay_ms: Delay in milliseconds before setting focus (default: 50)

    Usage:
        modal_id = disable_parent(parent)
        # ... modal window code ...
        enable_parent(modal_id)
    """
    print(f"DEBUG: Enabling parent for modal_id: {modal_id}")
    logger.debug(f"Enabling parent window with modal_id: {modal_id}")

    if modal_id not in _parent_window_states:
        logger.warning(f"Modal ID {modal_id} not found in stored states")
        return

    state = _parent_window_states[modal_id]
    parent_window = state['parent_window']
    calling_button = state['calling_button']

    try:
        # Restore grab state if needed
        previous_grab = state.get('previous_grab')
        if previous_grab:
            try:
                previous_grab.grab_set()
                logger.debug(f"Restored grab to: {previous_grab}")
            except Exception:
                pass

        logger.debug(f"Parent window focus restoration: {parent_window}")
        logger.debug("Parent window modal behavior restored")

        # Always restore focus and bring to front
        parent_window.focus_force()  # Use focus_force instead of focus_set
        parent_window.lift()
        parent_window.attributes('-topmost', True)  # Temporarily make topmost
        parent_window.attributes('-topmost', False)  # Then remove topmost
        parent_window.update_idletasks()  # Force UI update

        # Find and focus the next button if we have a calling button
        if calling_button:
            logger.debug(f"Finding next widget after calling button: {calling_button}")
            next_widget = find_next_focusable_widget(calling_button,
                                                   parent_window)
            if next_widget:
                logger.info(f"Focus will be set to next widget: {next_widget}")
                # Small delay to ensure window is ready

                def set_focus_to_next():
                    try:
                        next_widget.focus_set()
                        logger.debug(f"Focus successfully set to: {next_widget}")
                    except Exception as e:
                        logger.warning(f"Failed to set focus to {next_widget}: {e}")
                parent_window.after(delay_ms, set_focus_to_next)
            else:
                logger.debug("No next widget found, setting focus to parent")
                parent_window.after(delay_ms, lambda: parent_window.focus_set())
        else:
            logger.debug("No calling button stored, setting focus to parent")
            parent_window.after(delay_ms, lambda: parent_window.focus_set())

    except Exception as e:
        logger.error("Error in enable_parent: %s", e)
        try:
            # Fallback: just focus the parent window (no disable/enable needed)
            parent_window.focus_set()
        except Exception:
            pass

    # Clean up stored state
    del _parent_window_states[modal_id]
    logger.debug("Cleaned up modal state for %s", modal_id)


def setup_modal_window(modal_window: tk.Toplevel,
                      parent_window: tk.Widget,
                      title: str = "Modal Window",
                      geometry: str = "400x300",
                      resizable: tuple = (False, False)) -> None:
    """
    Set up standard modal window properties.

    Args:
        modal_window: The Toplevel window to configure
        parent_window: The parent window
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
        with ModalWindowManager(parent) as modal_mgr:
            modal_mgr.setup_window("My Modal", "500x400")
            modal_mgr.add_escape_binding(modal_mgr.window.destroy)
            # ... build your modal content ...
            modal_mgr.window.wait_window()
        # Focus is automatically restored when exiting the context
    """

    def __init__(self, parent_window: tk.Widget):
        self.parent_window = parent_window
        self.modal_id = None
        self.window = None

    def __enter__(self):
        self.modal_id = disable_parent(self.parent_window)
        self.window = tk.Toplevel(self.parent_window)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.modal_id:
            enable_parent(self.modal_id)

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


# =====================================================
# UTILITY FUNCTIONS FOR EXISTING CODE COMPATIBILITY
# =====================================================

def restore_focus_to_next_button(parent_window: tk.Widget,
                                calling_button: Optional[tk.Widget] = None,
                                delay_ms: int = 50) -> None:
    """
    Legacy compatibility function for existing code.

    This function provides backward compatibility for code that was using
    the old restore_focus_to_next_button function. New code should use
    the disable_parent/enable_parent pattern instead.
    """
    logger.debug("Using legacy restore_focus_to_next_button - consider updating to disable_parent/enable_parent")

    try:
        # Focus parent window (no disable/enable needed)
        parent_window.focus_set()
        parent_window.lift()

        # If we have a calling button, find the next button to focus
        if calling_button:
            next_widget = find_next_focusable_widget(calling_button, parent_window)
            if next_widget:
                logger.info(f"Focus restored to next widget: {next_widget}")
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
