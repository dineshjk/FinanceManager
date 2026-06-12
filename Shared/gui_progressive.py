# -*- coding: utf-8 -*-
# Shared/gui_progressive.py

"""Utilities for progressive/autocomplete UI elements and test modals.

This module provides a small progressive-selection helper for
`ttk.Combobox` widgets (autocomplete-like behavior) and a lightweight
`test_modal_window` used by the project to sanity-check dialog behavior.

The functions are GUI-focused and intentionally minimal; callers own
form-specific behavior (validation/clearing/etc.).
"""
import tkinter as tk

# from tkinter import ttk
# from .modal_utils import disable_parent, enable_parent
# from .window_manager import push_window, pop_window
# from .globals import logger

# COMBO_VALUES = [
#     "Apple",
#     "Bear",
#     "Cat",
#     "Appropriate",
#     "Chennai",
#     "Cheeta",
#     "Dog",
#     "Elephant",
#     "Fox",
#     "Giraffe",
#     "Horse",
#     "Iguana",
#     "Jaguar",
#     "Kangaroo",
#     "Lion",
#     "Monkey",
#     "Newt",
#     "Owl",
#     "Penguin",
#     "Quail",
#     "Rabbit",
#     "Sheep",
#     "Tiger",
#     "Urial",
#     "Vulture",
#     "Wolf",
#     "Xerus",
#     "Yak",
#     "Zebra",
# ]


def progressive_selection(combobox, values_list):
    """
    Enable progressive search/autocomplete for a ttk.Combobox.
    Args:
        combobox: The ttk.Combobox widget to enhance.
        values_list: The list of string values to use for autocomplete.
    """
    combobox["values"] = values_list
    setattr(combobox, "_ignore_next_event", False)
    setattr(combobox, "_user_typing", False)

    def on_select(_event=None):
        # Only trigger selection if user is not actively typing
        # (placeholder - combobox selection handled by caller)
        return

    def on_key_release(event):
        # Skip if we should ignore this event (but only for specific keys)
        if getattr(combobox, "_ignore_next_event", False):
            setattr(combobox, "_ignore_next_event", False)
            typing_keys = (
                "abcdefghijklmnopqrstuvwxyz"
                "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                "0123456789"
            )
            if event.keysym not in typing_keys and event.keysym != "space":
                return

        nav_keys = ["Up", "Down", "Left", "Right", "Tab", "Return", "Escape"]
        if event.keysym in nav_keys:
            if event.keysym == "Escape":
                combobox.set("")
                combobox["values"] = values_list
                setattr(combobox, "_user_typing", False)
            elif event.keysym in ["Return", "Tab"]:
                # Treat as selection: reset typing, but do not auto-populate
                setattr(combobox, "_user_typing", False)
                return

        if event.keysym in ["BackSpace", "Delete"]:
            current = combobox.get()
            setattr(combobox, "_user_typing", True)
            if not current:
                combobox["values"] = values_list
            else:
                matches = [
                    item
                    for item in values_list
                    if item.lower().startswith(current.lower())
                ]
                combobox["values"] = matches
            return

        current = combobox.get()
        if not current:
            combobox["values"] = values_list
            setattr(combobox, "_user_typing", False)
            return

        setattr(combobox, "_user_typing", True)
        matches = [
            item
            for item in values_list
            if item.lower().startswith(current.lower())
        ]
        combobox["values"] = matches
        # Only auto-complete if user is typing, not on Tab/Return
        if (
            matches
            and len(current) > 0
            and event.keysym not in ["space", "Tab", "Return"]
        ):
            cursor_pos = combobox.index(tk.INSERT)
            if cursor_pos == len(current):
                first_match = matches[0]
                setattr(combobox, "_ignore_next_event", True)
                combobox.set(first_match)
                combobox.select_range(cursor_pos, len(first_match))
                combobox.icursor(cursor_pos)

    def on_dropdown_click(_event=None):
        if not getattr(combobox, "_user_typing", False):
            combobox["values"] = values_list

    def manual_select():
        current = combobox.get().strip()
        setattr(combobox, "_user_typing", False)
        if current in values_list:
            return
        matches = [
            name
            for name in values_list
            if name.lower().startswith(current.lower())
        ]
        if matches:
            combobox.set(matches[0])

    # Expose manual_select so external code can call it if needed
    setattr(combobox, "manual_select", manual_select)

    combobox.bind("<KeyRelease>", on_key_release)
    combobox.bind("<<ComboboxSelected>>", on_select)
    combobox.bind("<Button-1>", on_dropdown_click)


# NOTE: clearing form fields is app-specific; the project modules
# that need this should provide their own clear handlers. Removed
# the generic `clear_all_entries` to avoid undefined variable errors.


# def test_modal_window(parent):
#     """
#     Create a modal window for testing with a combobox field called
#     'Testing Field'.
#     """
#     modal_id = disable_parent(parent)
#     win = tk.Toplevel(parent)
#     win.title("Test Modal Window")
#     win.geometry("350x150")
#     win.transient(parent)
#     win.grab_set()
#     try:
#         push_window(win, parent)
#     except (RuntimeError, AttributeError):
#         pass
#     win.focus_set()
#     win.configure(bg="#f0f8ff")

#     frame = tk.Frame(win, bg="#f0f8ff")
#     frame.pack(fill="both", expand=True, padx=20, pady=20)

#     label = tk.Label(
#         frame, text="Testing Field:", font=("Helvetica", 12), bg="#f0f8ff"
#     )
#     label.grid(row=0, column=0, sticky="w", padx=(0, 10))

#     combo_var = tk.StringVar()
#     combo = ttk.Combobox(
#         frame, textvariable=combo_var, values=COMBO_VALUES, width=20
#     )
#     combo.grid(row=0, column=1, sticky="ew")
#     combo.focus_set()

#     progressive_selection(combo, COMBO_VALUES)

#     def close_modal():
#         try:
#             pop_window()
#         except (RuntimeError, AttributeError):
#             pass
#         try:
#             enable_parent(modal_id)
#         except (RuntimeError, AttributeError):
#             pass
#         try:
#             win.destroy()
#         except tk.TclError:
#             pass

#     close_btn = tk.Button(
#         frame, text="Close", command=close_modal, font=("Helvetica", 11)
#     )
#     close_btn.grid(row=1, column=0, columnspan=2, pady=(20, 0))

#     win.bind("<Escape>", lambda event: close_modal())
#     win.protocol("WM_DELETE_WINDOW", close_modal)
#     parent.wait_window(win)
#     try:
#         if parent.winfo_exists():
#             parent.grab_set()
#     except tk.TclError:
#         logger.debug("parent.grab_set skipped: parent destroyed.")
