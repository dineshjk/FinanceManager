# -*- coding: utf-8 -*-
# File: C:\Data\Personal\Finance_and_Investment\finprog\FinanceManager\StockMan\menu_factory.py

"""
Universal menu window factory for Tkinter/ttk GUIs.

Creates both modal (Toplevel) and main (Tk) windows with consistent
navigation, hotkeys, and styling.
"""

import tkinter as tk
from tkinter import ttk
import inspect
from Shared.style_utils import ensure_ttk_style
from Shared.globals import logger


def create_menu_window(config):
    """
    Create a menu window (modal or main) with buttons, hotkeys, and navigation.
    Args:
        config (dict): Configuration for the window and buttons.
    Returns:
        window: The created Tk or Toplevel window.
        buttons: List of button widgets.
    """

    parent = config.get("parent")
    is_modal = config.get("modal", False)
    # come_back_index is handled per-parent on destroy; no local use here
    # Main window: create Tk if parent is None, else use parent
    if not is_modal:
        window = tk.Tk() if parent is None else parent
    else:
        window = tk.Toplevel(parent)
        window.transient(parent)
        window.grab_set()
    # Set background color if specified
    if config.get("bg"):
        window.configure(bg=config["bg"])

    # Set window properties
    if "title" in config:
        window.title(config["title"])

    else:
        window.title("Menu")
    if "geometry" in config:
        window.geometry(config["geometry"])
    else:
        window.geometry("400x400")
    if config.get("resizable") is not None:
        res = config["resizable"]
        if isinstance(res, (tuple, list)) and len(res) == 2:
            window.resizable(res[0], res[1])
        else:
            window.resizable(False, False)
    else:
        window.resizable(False, False)

    # Header
    if config.get("title"):
        label = tk.Label(window, text=config["title"], font=("Helvetica", 14))
        label.pack(pady=20)

    # Style
    style = config.get("style", "MainMenu.TButton")
    ensure_ttk_style(style)
    btn_padx = config.get("padx", 60)
    btn_pady = config.get("pady", 5)

    # Buttons with universal focus management
    buttons = []
    hotkey_map = {}

    def make_wrapped_command(idx, orig_command):
        def wrapped_command(*args, **kwargs):
            # Compute next index defensively (handles empty buttons list)
            try:
                new_idx = (idx + 1) % len(buttons)
            except ZeroDivisionError:
                new_idx = None

            # Log minimal info; avoid calling window.title() inside
            # debug string
            try:
                logger.debug(
                    "menu_factory: set _come_back_index idx=%s -> %s",
                    idx,
                    new_idx,
                )
            except (RuntimeError, AttributeError):
                # If logging fails, swallow — this is debug-only
                pass

            # Store the desired come-back index on the window (best-effort)
            try:
                # pylint: disable=protected-access
                setattr(window, "_come_back_index", new_idx)
            except (AttributeError, RuntimeError):
                pass

            # Clear button visual states (best-effort)
            for b in buttons:
                try:
                    b.state(["!focus", "!active"])
                except tk.TclError:
                    pass

            try:
                # If orig_command expects a window argument, pass the created
                # window
                if callable(orig_command):
                    try:
                        sig = inspect.signature(orig_command)
                        params = len(sig.parameters)
                    except (TypeError, ValueError):
                        params = 0
                    if params >= 1:
                        result = orig_command(window)
                    else:
                        result = orig_command()
                else:
                    result = orig_command(*args, **kwargs)
            finally:
                # Restore focus to the next button after command finishes
                def set_focus_and_state():
                    try:
                        next_btn = buttons[(idx + 1) % len(buttons)]
                        if next_btn.winfo_exists() and window.winfo_exists():
                            for b in buttons:
                                try:
                                    b.state(["!focus", "!active"])
                                except tk.TclError:
                                    pass
                            next_btn.focus_set()
                            try:
                                next_btn.state(["focus", "active"])
                            except tk.TclError:
                                pass
                    except (IndexError, tk.TclError, AttributeError):
                        # Best-effort: ignore focus restoration errors
                        pass

                window.after(10, set_focus_and_state)
            return result

        return wrapped_command

    for idx, btn_spec in enumerate(config["buttons"]):
        text = btn_spec["text"]
        hotkey = btn_spec.get("hotkey")
        command = btn_spec["command"]
        btn_label = text
        if hotkey:
            btn_label = f"   [{hotkey.upper()}] {text}"
        btn = ttk.Button(
            window,
            text=btn_label,
            command=make_wrapped_command(idx, command),
            style=style,
            takefocus=1,
            width=30,
        )
        btn.pack(pady=btn_pady, fill="x", padx=btn_padx)
        buttons.append(btn)
        if hotkey:
            hotkey_map[hotkey.lower()] = btn

    # Navigation logic (robust, per original)
    def clear_button_states():
        for b in buttons:
            try:
                b.state(["!focus", "!active"])
            except tk.TclError:
                pass

    def get_focused_button_index():
        fg = window.focus_get()
        for i, btn in enumerate(buttons):
            if btn == fg:
                return i
        # Fallback: if no button has keyboard focus, prefer a visually
        # focused/active button
        for i, btn in enumerate(buttons):
            try:
                states = tuple(btn.state())
            except tk.TclError:
                states = ()
            if "focus" in states or "active" in states:
                return i
        return 0

    def on_key(event):
        key = event.keysym
        idx = get_focused_button_index()
        if key.lower() in hotkey_map:
            btn = hotkey_map[key.lower()]
            clear_button_states()
            btn.focus_set()
            try:
                btn.state(["focus", "active"])
            except tk.TclError:
                pass
            btn.invoke()
            return "break"
        if key in ("Down", "Tab"):
            if buttons:
                clear_button_states()
                next_idx = (idx + 1) % len(buttons)
                buttons[next_idx].focus_set()
                try:
                    buttons[next_idx].state(["focus", "active"])
                except tk.TclError:
                    pass
            return "break"
        elif key == "Up":
            if buttons:
                clear_button_states()
                prev_idx = (idx - 1) % len(buttons)
                buttons[prev_idx].focus_set()
                try:
                    buttons[prev_idx].state(["focus", "active"])
                except tk.TclError:
                    pass
            return "break"
        elif key in ("Return", "space"):
            if buttons:
                buttons[idx].invoke()
            return "break"
        elif key == "Escape":
            # Always close the current window
            window.destroy()
            return "break"
        return None

    # Bind navigation keys to each button
    for btn in buttons:
        btn.bind("<Tab>", on_key)
        btn.bind("<Down>", on_key)
        btn.bind("<Up>", on_key)
        btn.bind("<Return>", on_key)
        btn.bind("<space>", on_key)
        btn.bind("<Escape>", on_key)

        def _on_button_click(_event, b=btn):
            clear_button_states()
            b.focus_set()
            try:
                b.state(["focus", "active"])
            except tk.TclError:
                pass

        btn.bind("<Button-1>", _on_button_click)

        def _on_button_double(_event, b=btn):
            try:
                b.invoke()
            except tk.TclError:
                pass

        btn.bind("<Double-Button-1>", _on_button_double)

    # Bind hotkey handler only to the window
    window.bind("<Key>", on_key)

    # Focus first button and style
    window.focus_force()
    if buttons:
        clear_button_states()
        buttons[0].focus_set()
        try:
            buttons[0].state(["focus", "active"])
        except tk.TclError:
            pass

    # Universal focus restoration for all menu windows
    if parent is not None:
        # Store the buttons list on the window for access by children
        setattr(window, "_menu_buttons", buttons)
    if is_modal and parent is not None:

        def on_destroy(_event=None):
            btns = getattr(parent, "_menu_buttons", None)
            come_back_index = getattr(parent, "_come_back_index", None)
            if btns is not None and come_back_index is not None:
                # Defensive: ensure come_back_index is in range; if not, clamp
                # and warn
                try:
                    total = len(btns)
                except (TypeError, AttributeError):
                    total = 0
                safe_idx = 0
                if isinstance(come_back_index, int) and total > 0:
                    if 0 <= come_back_index < total:
                        safe_idx = come_back_index
                    else:
                        try:
                            logger.warning(
                                (
                                    "menu_factory.on_destroy: "
                                    "come_back_index out of range (%s), "
                                    "clamping to 0"
                                ),
                                come_back_index,
                            )
                        except (RuntimeError, AttributeError):
                            # Fallback to stdout if logger misbehaves
                            try:
                                print(
                                    (
                                        "menu_factory.on_destroy: "
                                        "come_back_index out of range ("
                                        + str(come_back_index)
                                        + "). Clamping to 0"
                                    )
                                )
                            except (RuntimeError, AttributeError):
                                pass
                        safe_idx = 0
                else:
                    # Fallback to first button
                    safe_idx = 0

                def set_focus_and_state():
                    for b in btns:
                        try:
                            b.state(["!focus", "!active"])
                        except tk.TclError:
                            pass
                    try:
                        btns[safe_idx].focus_set()
                        try:
                            btns[safe_idx].state(["focus", "active"])
                        except tk.TclError:
                            pass
                    except (IndexError, tk.TclError, AttributeError):
                        # If anything goes wrong, try the first button as
                        # last resort
                        try:
                            if btns:
                                btns[0].focus_set()
                                try:
                                    btns[0].state(["focus", "active"])
                                except tk.TclError:
                                    pass
                        except (IndexError, tk.TclError, AttributeError):
                            pass

                parent.after(10, set_focus_and_state)

        window.bind("<Destroy>", on_destroy, add=True)
    return window, buttons


# File: C:\Data\Personal\Finance_and_Investment\finprog\FinanceManager\StockMan\menu_factory.py ends here
