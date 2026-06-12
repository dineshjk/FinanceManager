# -*- coding: utf-8 -*-
# File: C:\Data\Personal\Finance_and_Investment\finprog\FinanceManager\StockMan\window_manager.py

"""
Centralized window stack manager for modal dialogs in Tkinter.
Disables previous window when a new modal opens, re-enables when closed.
"""

import tkinter as tk
from .modal_utils import disable_parent, enable_parent
from .globals import logger

_window_stack = []


def activate_previous_window():
    """
    Bring the previous window in the stack to the front and set focus.
    """
    if _window_stack:
        prev_win, _ = _window_stack[-1]
        try:
            prev_win.deiconify()
            prev_win.lift()
            prev_win.focus_set()
            prev_win.grab_set()
            prev_win.transient(prev_win.master)
        except (tk.TclError, RuntimeError) as exc:
            logger.debug("activate_previous_window failed: %s", exc)


def push_window(win, parent):
    """
    Add a new window to the stack, disable parent.
    Call after creating a new Toplevel/modal window.
    """
    try:
        logger.debug("push_window: pushing window %s, parent=%s", win, parent)
    except (AttributeError, TypeError, ValueError) as exc:
        logger.debug("push_window: logger.debug failed: %s", exc)
    disable_parent(parent)
    _window_stack.append((win, parent))

    # Attach a safe close handler so that if the window is closed via the
    # window manager (titlebar close) or destroyed unexpectedly, the
    # stack is cleaned up and the parent is re-enabled.
    def _safe_close(_event=None):
        try:
            # Only pop if this window is the top of the stack
            if _window_stack and _window_stack[-1][0] is win:
                try:
                    logger.debug("_safe_close: popping window %s", win)
                except (AttributeError, TypeError) as exc:
                    logger.debug("_safe_close logger failed: %s", exc)
                _window_stack.pop()
                try:
                    enable_parent(parent)
                except (RuntimeError, tk.TclError) as exc:
                    logger.debug("_safe_close enable_parent failed: %s", exc)
        except (RuntimeError, tk.TclError) as exc:
            logger.debug("_safe_close outer handler failed: %s", exc)
        # If the window still exists, destroy it
        try:
            if win.winfo_exists():
                win.destroy()
        except (tk.TclError,) as exc:
            logger.debug("_safe_close: win.destroy failed: %s", exc)

    try:
        # Avoid rebinding if already bound
        if not getattr(win, "_wm_close_hooked", False):
            win.protocol("WM_DELETE_WINDOW", _safe_close)
            win.bind("<Destroy>", lambda e: _safe_close())
            setattr(win, "_wm_close_hooked", True)
    except (AttributeError, tk.TclError) as exc:
        # Best-effort: ignore failures to attach handlers but log
        logger.debug("push_window: failed to attach handlers: %s", exc)


def pop_window():
    """
    Remove the top window from the stack, enable previous parent.
    Call before destroying the current window.
    """
    if _window_stack:
        try:
            win, parent = _window_stack.pop()
            try:
                logger.debug(
                    "pop_window: popped window %s, enabling parent %s",
                    win,
                    parent,
                )
            except (AttributeError, TypeError) as exc:
                logger.debug("pop_window: logger failed: %s", exc)
            try:
                enable_parent(parent)
            except (RuntimeError, tk.TclError) as exc:
                logger.debug("pop_window: enable_parent failed: %s", exc)
        except (RuntimeError, tk.TclError, IndexError) as exc:
            # Handle expected windowing/runtime errors and log for diagnosis
            logger.exception("pop_window unexpected error: %s", exc)


def current_window():
    """
    Return the current top window (if any).
    """
    if _window_stack:
        return _window_stack[-1][0]
    return None


def stack_size():
    return len(_window_stack)


def safe_close_modal(window, parent=None, calling_button=None):
    """
    Safely closes a modal window, pops the window stack, and restores focus
    to the parent or specific calling button.
    """
    try:
        window.grab_release()
    except (RuntimeError, tk.TclError, AttributeError):
        pass

    try:
        pop_window()
    except (RuntimeError, tk.TclError, AttributeError) as e:
        logger.debug("safe_close_modal: pop_window() failed: %s", e)

    try:
        window.destroy()
    except (RuntimeError, tk.TclError, AttributeError) as e:
        logger.debug("safe_close_modal: window.destroy() failed: %s", e)

    if parent:
        try:
            parent.lift()
            parent.focus_force()
        except (RuntimeError, tk.TclError, AttributeError):
            try:
                parent.focus_set()
            except (RuntimeError, tk.TclError, AttributeError):
                pass

    if calling_button:
        try:
            calling_button.focus_set()
        except (RuntimeError, tk.TclError, AttributeError):
            pass

    return "break"


# File: C:\Data\Personal\Finance_and_Investment\finprog\FinanceManager\StockMan\window_manager.py ends here
