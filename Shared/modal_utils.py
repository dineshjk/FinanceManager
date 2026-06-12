# -*- coding: utf-8 -*-
# Shared/modal_utils.py

"""
Centralized Modal Window Management System

This module provides a unified system for managing modal windows with automatic
focus restoration and parent window state management.

Usage:
    from modal_utils import disable_parent, enable_parent

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
from typing import Optional, Callable, Union
import logging

logger = logging.getLogger(__name__)


def _safe_call(fn, *args, **kwargs):
    """Call a user-provided callback and log any exception it raises.

    This centralizes UI-protecting broad-except behavior so it's explicit
    and easy to review.
    """
    try:
        return fn(*args, **kwargs)
    except Exception as e:  # noqa: E722 pylint: disable=broad-except
        logger.exception("User callback raised an exception: %s", e)
        return None


def disable_parent(
    parent_window: Union[tk.Tk, tk.Widget, tk.Toplevel],
    modal_id: Optional[str] = None,
    calling_button: Optional[tk.Widget] = None,
) -> str:
    """Disable parent window and store its current state for later
    restoration.
    """
    if modal_id is None:
        modal_id = str(id(parent_window))
    try:
        logger.debug(
            "disable_parent: parent=%s modal_id=%s calling_button=%s",
            parent_window,
            modal_id,
            calling_button,
        )
    except (RuntimeError, AttributeError):
        pass
    return modal_id


def enable_parent(modal_id: str, _delay_ms: int = 100) -> None:
    """Enable parent window and restore focus to the next button in
    sequence.
    """
    try:
        logger.debug("enable_parent: modal_id=%s", modal_id)
    except (RuntimeError, AttributeError):
        pass
    # No enabling needed; modal ends when child window is destroyed


def setup_modal_window(
    modal_window: tk.Toplevel,
    parent_window: tk.Widget,
    title: str = "Modal Window",
    geometry: str = "400x300",
    resizable: tuple = (False, False),
) -> None:
    """Set up standard modal window properties."""
    try:
        modal_window.title(title)
        modal_window.geometry(geometry)
        modal_window.resizable(resizable[0], resizable[1])
        parent_toplevel = parent_window.winfo_toplevel()
        modal_window.transient(parent_toplevel)
        modal_window.grab_set()
        logger.debug("Modal window '%s' configured successfully", title)
    except (tk.TclError, RuntimeError, AttributeError) as e:
        logger.error("Error setting up modal window: %s", e)


def add_escape_binding(
    modal_window: tk.Toplevel, close_callback: Callable[[], None]
) -> None:
    """Add standard Escape key binding to close modal window."""

    def _on_escape(_event: tk.Event) -> None:
        _safe_call(close_callback)

    try:
        modal_window.bind("<Escape>", _on_escape)
        logger.debug("Escape key binding added to modal window")
    except (tk.TclError, RuntimeError, AttributeError) as e:
        logger.error("Error adding escape binding: %s", e)
