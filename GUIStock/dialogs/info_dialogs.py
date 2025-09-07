# -*- coding: utf-8 -*-
# File: c:\Users\aumji\source\repos\Finance\FinanceManager\GUIStock\dialogs\info_dialogs.py

"""
Professional dialog components with dynamic sizing for the Stock Portfolio Management System.

This module provides styled dialog functions for information, error, and
confirmation messages with automatic sizing based on content.
"""

import tkinter as tk
from .sizing import calculate_dialog_size


def show_colorful_info(parent, title, message):
    """Create a colorful info dialog with blue theme and dynamic sizing"""
    dialog = tk.Toplevel(parent)
    dialog.title(title)

    # Calculate optimal size based on content
    width, height = calculate_dialog_size(message, title)
    dialog.geometry(f"{width}x{height}")
    dialog.configure(bg="#e0f2fe")
    dialog.resizable(False, False)
    dialog.transient(parent)
    dialog.grab_set()

    # Center the dialog
    dialog.update_idletasks()
    x = (dialog.winfo_screenwidth() // 2) - (width // 2)
    y = (dialog.winfo_screenheight() // 2) - (height // 2)
    dialog.geometry(f"{width}x{height}+{x}+{y}")

    # Header with icon
    header_frame = tk.Frame(dialog, bg="#3b82f6", height=60)
    header_frame.pack(fill="x")
    header_frame.pack_propagate(False)

    icon_label = tk.Label(header_frame, text="ℹ️", font=("Arial", 24),
                         bg="#3b82f6", fg="white")
    icon_label.pack(side="left", padx=20, pady=15)

    title_label = tk.Label(header_frame, text=title,
                          font=("Arial", 16, "bold"),
                          bg="#3b82f6", fg="white")
    title_label.pack(side="left", pady=15)

    # Message area - dynamic wraplength based on dialog width
    msg_frame = tk.Frame(dialog, bg="#e0f2fe")
    msg_frame.pack(fill="both", expand=True, padx=20, pady=20)

    # Calculate wraplength as 90% of dialog width minus padding
    wraplength = int((width - 60) * 0.9)
    msg_label = tk.Label(msg_frame, text=message, font=("Arial", 11),
                        bg="#e0f2fe", fg="#1e3a8a",
                        wraplength=wraplength, justify="left")
    msg_label.pack(anchor="w")

    # OK button - ensure it's always visible at bottom
    btn_frame = tk.Frame(dialog, bg="#e0f2fe", height=50)
    btn_frame.pack(fill="x", padx=20, pady=(0, 20))
    btn_frame.pack_propagate(False)  # Maintain fixed height for button area

    ok_btn = tk.Button(btn_frame, text="✅ OK", font=("Arial", 14, "bold"),
                      bg="#10b981", fg="white", activebackground="#059669",
                      relief="raised", bd=3, cursor="hand2",
                      width=12, height=2,
                      command=dialog.destroy)
    ok_btn.pack(side="right")

    dialog.focus_set()
    ok_btn.focus_set()
    dialog.bind("<Return>", lambda e: dialog.destroy())
    dialog.bind("<Escape>", lambda e: dialog.destroy())

    dialog.wait_window()


def show_colorful_error(parent, title, message):
    """Create a colorful error dialog with red theme and dynamic sizing"""
    dialog = tk.Toplevel(parent)
    dialog.title(title)

    # Calculate optimal size based on content
    width, height = calculate_dialog_size(message, title)
    dialog.geometry(f"{width}x{height}")
    dialog.configure(bg="#fee2e2")
    dialog.resizable(False, False)
    dialog.transient(parent)
    dialog.grab_set()

    # Center the dialog
    dialog.update_idletasks()
    x = (dialog.winfo_screenwidth() // 2) - (width // 2)
    y = (dialog.winfo_screenheight() // 2) - (height // 2)
    dialog.geometry(f"{width}x{height}+{x}+{y}")

    # Header with icon
    header_frame = tk.Frame(dialog, bg="#dc2626", height=60)
    header_frame.pack(fill="x")
    header_frame.pack_propagate(False)

    icon_label = tk.Label(header_frame, text="❌", font=("Arial", 24),
                         bg="#dc2626", fg="white")
    icon_label.pack(side="left", padx=20, pady=15)

    title_label = tk.Label(header_frame, text=title,
                          font=("Arial", 16, "bold"),
                          bg="#dc2626", fg="white")
    title_label.pack(side="left", pady=15)

    # Message area - dynamic wraplength based on dialog width
    msg_frame = tk.Frame(dialog, bg="#fee2e2")
    msg_frame.pack(fill="both", expand=True, padx=20, pady=20)

    # Calculate wraplength as 90% of dialog width minus padding
    wraplength = int((width - 60) * 0.9)
    msg_label = tk.Label(msg_frame, text=message, font=("Arial", 11),
                        bg="#fee2e2", fg="#991b1b",
                        wraplength=wraplength, justify="left")
    msg_label.pack(anchor="w")

    # OK button
    btn_frame = tk.Frame(dialog, bg="#fee2e2")
    btn_frame.pack(fill="x", padx=20, pady=(0, 20))

    ok_btn = tk.Button(btn_frame, text="❌ OK", font=("Arial", 12, "bold"),
                      bg="#ef4444", fg="white", activebackground="#dc2626",
                      relief="raised", bd=2, cursor="hand2",
                      command=dialog.destroy)
    ok_btn.pack(side="right")

    dialog.focus_set()
    ok_btn.focus_set()
    dialog.bind("<Return>", lambda e: dialog.destroy())
    dialog.bind("<Escape>", lambda e: dialog.destroy())

    dialog.wait_window()


def show_colorful_yesno(parent, title, message):
    """Create a colorful yes/no dialog with green/red theme and dynamic sizing"""
    result = [False]  # Use list to allow modification in nested functions

    dialog = tk.Toplevel(parent)
    dialog.title(title)

    # Calculate optimal size based on content, with larger minimum for buttons
    width, height = calculate_dialog_size(message, title, min_width=450,
                                        min_height=250)
    dialog.geometry(f"{width}x{height}")
    dialog.configure(bg="#f0fdf4")
    dialog.resizable(False, False)
    dialog.transient(parent)
    dialog.grab_set()

    # Center the dialog
    dialog.update_idletasks()
    x = (dialog.winfo_screenwidth() // 2) - (width // 2)
    y = (dialog.winfo_screenheight() // 2) - (height // 2)
    dialog.geometry(f"{width}x{height}+{x}+{y}")

    # Header with icon
    header_frame = tk.Frame(dialog, bg="#059669", height=60)
    header_frame.pack(fill="x")
    header_frame.pack_propagate(False)

    icon_label = tk.Label(header_frame, text="❓", font=("Arial", 24),
                         bg="#059669", fg="white")
    icon_label.pack(side="left", padx=20, pady=15)

    title_label = tk.Label(header_frame, text=title,
                          font=("Arial", 16, "bold"),
                          bg="#059669", fg="white")
    title_label.pack(side="left", pady=15)

    # Message area - dynamic wraplength based on dialog width
    msg_frame = tk.Frame(dialog, bg="#f0fdf4")
    msg_frame.pack(fill="both", expand=True, padx=20, pady=20)

    # Calculate wraplength as 90% of dialog width minus padding
    wraplength = int((width - 60) * 0.9)
    msg_label = tk.Label(msg_frame, text=message, font=("Arial", 11),
                        bg="#f0fdf4", fg="#166534",
                        wraplength=wraplength, justify="left")
    msg_label.pack(anchor="w")

    # Button area - ensure it's always visible at bottom
    btn_frame = tk.Frame(dialog, bg="#f0fdf4", height=50)
    btn_frame.pack(fill="x", padx=20, pady=(0, 20))
    btn_frame.pack_propagate(False)  # Maintain fixed height for button area

    def on_yes():
        result[0] = True
        dialog.destroy()

    def on_no():
        result[0] = False
        dialog.destroy()

    # Larger buttons for better visibility
    no_btn = tk.Button(btn_frame, text="❌ No", font=("Arial", 14, "bold"),
                       bg="#ef4444", fg="white", activebackground="#dc2626",
                       relief="raised", bd=3, cursor="hand2", command=on_no,
                       width=12, height=2)
    no_btn.pack(side="right", padx=(10, 0))

    yes_btn = tk.Button(btn_frame, text="✅ Yes", font=("Arial", 14, "bold"),
                        bg="#10b981", fg="white", activebackground="#059669",
                        relief="raised", bd=3, cursor="hand2", command=on_yes,
                        width=12, height=2)
    yes_btn.pack(side="right")

    dialog.focus_set()
    yes_btn.focus_set()
    dialog.bind("<Return>", lambda e: on_yes())
    dialog.bind("<Escape>", lambda e: on_no())

    dialog.wait_window()
    return result[0]
