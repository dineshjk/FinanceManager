# -*- coding: utf-8 -*-
# File: C:\Data\Personal\Finance_and_Investment\finprog\FinanceManager\StockMan\dialog_utils.py

"""
Professional dialog components with dynamic sizing for the Stock Portfolio
Management System.

This module provides styled dialog functions for information, error, and
confirmation messages with automatic sizing based on content.
"""

import tkinter as tk
from tkinter import ttk

from .dialog_sizing import calculate_dialog_size
from .window_manager import push_window, pop_window
from .modal_utils import _safe_call
from .globals import logger


def show_colorful_error(parent, title, message):
    """
    Create a colorful error dialog with red theme and dynamic sizing.
    """
    dialog = tk.Toplevel(parent)
    dialog.title(title)
    width, height = calculate_dialog_size(message, title)
    dialog.geometry(f"{width}x{height}")
    dialog.configure(bg="#fee2e2")
    dialog.resizable(False, False)
    dialog.transient(parent)
    dialog.grab_set()
    # push onto central window stack
    push_window(dialog, parent)
    dialog.update_idletasks()
    x = (dialog.winfo_screenwidth() // 2) - (width // 2)
    y = (dialog.winfo_screenheight() // 2) - (height // 2)
    dialog.geometry(f"{width}x{height}+{x}+{y}")

    header_frame = tk.Frame(dialog, bg="#dc2626", height=60)
    header_frame.pack(fill="x")
    header_frame.pack_propagate(False)
    icon_label = tk.Label(
        header_frame, text="❌", font=("Arial", 24), bg="#dc2626", fg="white"
    )
    icon_label.pack(side="left", padx=20, pady=15)

    title_label = tk.Label(
        header_frame,
        text=title,
        font=("Arial", 16, "bold"),
        bg="#dc2626",
        fg="white",
    )
    title_label.pack(side="left", pady=15)

    msg_frame = tk.Frame(dialog, bg="#fee2e2")
    msg_frame.pack(fill="both", expand=True, padx=20, pady=20)
    wraplength = int((width - 60) * 0.9)
    msg_label = tk.Label(
        msg_frame,
        text=message,
        font=("Arial", 14),
        bg="#fee2e2",
        fg="#991b1b",
        wraplength=wraplength,
        justify="left",
    )
    msg_label.pack(anchor="w")

    btn_frame = tk.Frame(dialog, bg="#fee2e2", height=50)
    btn_frame.pack(fill="x", padx=20, pady=(0, 20))
    btn_frame.pack_propagate(False)

    def close_error():
        pop_window()
        dialog.destroy()

    ok_btn = tk.Button(
        btn_frame,
        text="❌ OK",
        font=("Arial", 14, "bold"),
        bg="#ef4444",
        fg="white",
        activebackground="#dc2626",
        relief="raised",
        bd=3,
        cursor="hand2",
        width=12,
        height=2,
        command=close_error,
    )
    ok_btn.pack(side="right")
    dialog.focus_set()
    ok_btn.focus_set()
    dialog.bind("<Return>", lambda e: close_error())
    dialog.bind("<Escape>", lambda e: close_error())
    # Wait for dialog to close. If caller passed None for parent, fall back
    # to waiting on the dialog itself to avoid AttributeError.
    if parent is None:
        dialog.wait_window()
    else:
        try:
            parent.wait_window(dialog)
        except (RuntimeError, AttributeError, tk.TclError):
            # Fallback to dialog.wait_window if parent is not a valid widget
            dialog.wait_window()
    try:
        if parent is not None and parent.winfo_exists():
            parent.grab_set()
    except tk.TclError:
        logger.debug("parent.grab_set skipped: parent destroyed.")


def show_colorful_info(parent, title, message, on_close=None):
    """
    Create a colorful info dialog with blue theme and dynamic sizing.
    Calls on_close after dialog is destroyed if provided.
    """
    dialog = tk.Toplevel(parent)
    dialog.title(title)
    width, height = calculate_dialog_size(message, title)
    dialog.geometry(f"{width}x{height}")
    dialog.configure(bg="#e0f2fe")
    dialog.resizable(False, False)
    dialog.transient(parent)
    dialog.grab_set()
    try:
        push_window(dialog, parent)
    except (RuntimeError, AttributeError):
        pass
    dialog.update_idletasks()
    x = (dialog.winfo_screenwidth() // 2) - (width // 2)
    y = (dialog.winfo_screenheight() // 2) - (height // 2)
    dialog.geometry(f"{width}x{height}+{x}+{y}")

    header_frame = tk.Frame(dialog, bg="#3b82f6", height=60)
    header_frame.pack(fill="x")
    header_frame.pack_propagate(False)
    tk.Label(
        header_frame, text="ℹ️", font=("Arial", 24), bg="#3b82f6", fg="white"
    ).pack(side="left", padx=20, pady=15)
    tk.Label(
        header_frame,
        text=title,
        font=("Arial", 16, "bold"),
        bg="#3b82f6",
        fg="white",
    ).pack(side="left", pady=15)

    msg_frame = tk.Frame(dialog, bg="#e0f2fe")
    msg_frame.pack(fill="both", expand=True, padx=20, pady=20)
    wraplength = int((width - 60) * 0.9)
    tk.Label(
        msg_frame,
        text=message,
        font=("Arial", 14),
        bg="#e0f2fe",
        fg="#1e3a8a",
        wraplength=wraplength,
        justify="left",
    ).pack(anchor="w")

    btn_frame = tk.Frame(dialog, bg="#e0f2fe", height=50)
    btn_frame.pack(fill="x", padx=20, pady=(0, 20))
    btn_frame.pack_propagate(False)

    # --- Corrected close handler ---
    def close_and_callback():
        try:
            pop_window()
        except (RuntimeError, AttributeError):
            pass
        try:
            dialog.grab_release()  # ✅ release grab cleanly
        except (RuntimeError, tk.TclError):
            pass
        try:
            dialog.destroy()
        except tk.TclError:
            pass
        if on_close:
            _safe_call(on_close)  # ✅ run cleanup after dialog closes

    ok_btn = tk.Button(
        btn_frame,
        text="✅ OK",
        font=("Arial", 14, "bold"),
        bg="#10b981",
        fg="white",
        activebackground="#059669",
        relief="raised",
        bd=3,
        cursor="hand2",
        width=12,
        height=2,
        command=close_and_callback,
    )
    ok_btn.pack(side="right")
    dialog.focus_set()
    ok_btn.focus_set()
    dialog.bind("<Return>", lambda e: close_and_callback())
    dialog.bind("<Escape>", lambda e: close_and_callback())
    # Wait for dialog to close. Support parent being None (some callers pass
    # None when invoked from non-UI code). Use dialog.wait_window as fallback.
    if parent is None:
        dialog.wait_window()
    else:
        try:
            parent.wait_window(dialog)
        except (RuntimeError, AttributeError, tk.TclError):
            dialog.wait_window()
    try:
        if parent is not None and parent.winfo_exists():
            parent.grab_set()
    except tk.TclError:
        logger.debug("parent.grab_set skipped: parent destroyed.")


def show_colorful_yesno(parent, title, message):
    """
    Create a colorful yes/no dialog with green/red theme and dynamic sizing
    """
    result = [False]
    dialog = tk.Toplevel(parent)
    dialog.title(title)
    width, height = calculate_dialog_size(
        message, title, min_width=450, min_height=250
    )
    dialog.geometry(f"{width}x{height}")
    dialog.configure(bg="#f0fdf4")
    dialog.resizable(False, False)
    dialog.transient(parent)
    dialog.grab_set()
    try:
        push_window(dialog, parent)
    except (RuntimeError, AttributeError):
        pass
    dialog.update_idletasks()
    x = (dialog.winfo_screenwidth() // 2) - (width // 2)
    y = (dialog.winfo_screenheight() // 2) - (height // 2)
    dialog.geometry(f"{width}x{height}+{x}+{y}")

    header_frame = tk.Frame(dialog, bg="#059669", height=60)
    header_frame.pack(fill="x")
    header_frame.pack_propagate(False)
    icon_label = tk.Label(
        header_frame, text="❓", font=("Arial", 24), bg="#059669", fg="white"
    )
    icon_label.pack(side="left", padx=20, pady=15)

    title_label = tk.Label(
        header_frame,
        text=title,
        font=("Arial", 16, "bold"),
        bg="#059669",
        fg="white",
    )
    title_label.pack(side="left", pady=15)

    msg_frame = tk.Frame(dialog, bg="#f0fdf4")
    msg_frame.pack(fill="both", expand=True, padx=20, pady=20)
    wraplength = int((width - 60) * 0.9)
    msg_label = tk.Label(
        msg_frame,
        text=message,
        font=("Arial", 14),
        bg="#f0fdf4",
        fg="#166534",
        wraplength=wraplength,
        justify="left",
    )
    msg_label.pack(anchor="w")

    btn_frame = tk.Frame(dialog, bg="#f0fdf4", height=50)
    btn_frame.pack(fill="x", padx=20, pady=(0, 20))
    btn_frame.pack_propagate(False)

    # Blank line before nested function
    def on_yes():
        result[0] = True
        try:
            pop_window()
        except (RuntimeError, AttributeError):
            pass
        try:
            dialog.destroy()
        except tk.TclError:
            pass

    def on_no():
        result[0] = False
        try:
            pop_window()
        except (RuntimeError, AttributeError):
            pass
        try:
            dialog.destroy()
        except tk.TclError:
            pass

    no_btn = tk.Button(
        btn_frame,
        text="❌ No",
        font=("Arial", 14, "bold"),
        bg="#ef4444",
        fg="white",
        activebackground="#dc2626",
        relief="raised",
        bd=3,
        cursor="hand2",
        command=on_no,
        width=12,
        height=2,
    )
    no_btn.pack(side="right", padx=(10, 0))

    yes_btn = tk.Button(
        btn_frame,
        text="✅ Yes",
        font=("Arial", 14, "bold"),
        bg="#10b981",
        fg="white",
        activebackground="#059669",
        relief="raised",
        bd=3,
        cursor="hand2",
        command=on_yes,
        width=12,
        height=2,
    )
    yes_btn.pack(side="right")
    dialog.focus_set()
    yes_btn.focus_set()
    dialog.bind("<Return>", lambda e: on_yes())
    dialog.bind("<Escape>", lambda e: on_no())
    dialog.bind("y", lambda e: on_yes())
    dialog.bind("Y", lambda e: on_yes())
    dialog.bind("n", lambda e: on_no())
    dialog.bind("N", lambda e: on_no())
    # Wait for dialog to close. If caller did not provide a parent, wait on
    # the dialog itself to avoid raising AttributeError on None.
    if parent is None:
        dialog.wait_window()
    else:
        try:
            parent.wait_window(dialog)
        except (RuntimeError, AttributeError, tk.TclError):
            dialog.wait_window()
    try:
        if parent is not None and parent.winfo_exists():
            parent.grab_set()
    except tk.TclError:
        logger.debug("parent.grab_set skipped: parent destroyed.")
    return result[0]


# def apply_dark_entry_theme(window):
#     """Applies a global dark theme to ttk widgets (Combobox, DateEntry) within a given window."""
#     style = ttk.Style(window)
#     if "clam" in style.theme_names():
#         style.theme_use("clam")

#     style.configure(
#         "TCombobox",
#         fieldbackground="black",
#         background="#1e3a8a",
#         foreground="yellow",
#         insertcolor="yellow",
#         bordercolor="black",
#         darkcolor="black",
#         lightcolor="black",
#     )

#     style.map(
#         "TCombobox",
#         fieldbackground=[("readonly", "black"), ("disabled", "black")],
#         foreground=[("readonly", "yellow"), ("disabled", "yellow")],
#         selectbackground=[("readonly", "#8a1e62")],
#         selectforeground=[("readonly", "yellow")],
#     )


# File: C:\Data\Personal\Finance_and_Investment\finprog\FinanceManager\StockMan\dialog_utils.py ends here
