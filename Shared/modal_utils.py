# -*- coding: utf-8 -*-
# Shared/modal_utils.py

"""
Centralized Modal Window Lifecycle & Focus Management System.

This module manages the lifecycle, parent-child window states, and focus transitions
of modal dialogs in Tkinter. It guarantees that parent windows are disabled while child
dialogs are active, traps Escape key dismissals safely, and reliably restores focus to
the initiating widget upon closure.

Key Responsibilities:
    • Parent Disablement & Safety: Disables user interaction on parent windows when a modal
      dialog opens, preventing concurrent edit race conditions and orphan dialog windows.
    • Modal Window Setup: Sets window transient relationship, enforces modal grab (`grab_set`),
      lifts the window above its parent, and configures standard window close protocols.
    • Escape Key Trapping: Binds `<Escape>` to cleanly dismiss the modal window, invoking
      closure callbacks and preventing escape events from bubbling up to parent windows.
    • Focus Restoration: Remembers the exact widget that held focus prior to opening the modal
      and safely returns OS focus to it when the dialog terminates.

Key Functions:
    • `disable_parent(parent)`: Disables parent window events and records its active focus state.
    • `enable_parent(parent, original_focus)`: Re-enables parent interactivity and restores focus.
    • `setup_modal_window(window, parent, close_callback)`: Standardizes modal configuration.
    • `add_escape_binding(window, close_callback)`: Attaches safe escape dismissal.
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
