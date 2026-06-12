# -*- coding: utf-8 -*-
# Shared/gui_utils.py


"""
Shared GUI utilities for Stock Portfolio Management System.
"""

import tkinter as tk
from tkinter import ttk
from datetime import timedelta, datetime

from .globals import UI_THEME

BANK_UI_THEME = {
    "main_bg": "#E0E0E0",  # Light Gray
    "header_bg": "#2E4053",  # Dark Blue-Gray
    "header_fg": "white",
    "label_bg": "#E0E0E0",
    "entry_bg": "white",
    "entry_fg": "black",
    "readonly_bg": "#F0F0F0",
    "button_bg": "#5D6D7E",
    "button_fg": "white",
    "focus_bg": "#F39C12",  # Orange
    "focus_fg": "#17202A",  # Dark Blue
    "hover_bg": "#85929E",  # Grayish Blue
    "hover_fg": "#FDFEFE",  # Almost White
    "error_bg": "#E74C3C",  # Red
    "error_fg": "white",
}

BANK_ADD_UI_THEME = {
    "main_bg": "#83BBF2",
    "header_bg": "#1B4F72",
    "header_fg": "white",
    "label_bg": "#EAECEE",
    "entry_bg": "white",
    "entry_fg": "black",
    "readonly_bg": "#F4F6F7",
    "button_bg": "#2874A6",
    "button_fg": "white",
    "focus_bg": "#F5B041",
    "focus_fg": "#17202A",
    "hover_bg": "#5499C7",
    "hover_fg": "#FDFEFE",
    "error_bg": "#CB4335",
    "error_fg": "white",
    # Aliases required by bind_entry_hover
    "bg_hover": "#5499C7",
    "fg_hover": "#FDFEFE",
    "bg_focus": "#F5B041",
    "fg_focus": "#17202A",
    "bg_error": "#CB4335",
    # --- NEW ADDITIONS FOR banks_add.py ---
    "submit_bg": "#22c55e",  # Green
    "submit_hover_bg": "#2563eb",  # Blue on hover
    "cancel_bg": "#ef4444",  # Red
    "cancel_hover_bg": "#991b1b",  # Darker red on hover
    "help_bg": "#fffaf0",  # Floral white
    "help_header_bg": "#ff7f50",  # Coral
    "help_btn_bg": "#4682b4",  # Steel blue
    "session_bg": "#f8fafc",  # Slate white
    "session_label_fg": "#0b63a7",  # Dark blue
    "session_value_fg": "#0b3d2e",  # Dark green
    "session_alert_fg": "#b91c1c",  # Red alert
    "session_ok_fg": "#064e3b",  # Green success
}

# ---------------------------------------------------------------------------
# Bank Edit – rose / magenta theme
# Companion to BANK_ADD_UI_THEME (blue); distinct warm-rose palette signals
# "edit / update" vs "add / create".
# ---------------------------------------------------------------------------
BANK_EDIT_UI_THEME = {
    "main_bg": "#FCEAEF",  # Very light rose
    "header_bg": "#7B1D4A",  # Dark plum / magenta
    "header_fg": "white",
    "label_bg": "#FCEAEF",
    "entry_bg": "#FFFAFC",  # Near-white with rose tint
    "entry_fg": "#1A000E",  # Very dark plum text
    "readonly_bg": "#FCEAEF",
    "button_bg": "#9B2460",  # Mid rose / magenta
    "button_fg": "white",
    "focus_bg": "#F4D03F",  # Gold focus ring
    "focus_fg": "#17202A",
    "hover_bg": "#B83A6F",  # Lighter rose on hover
    "hover_fg": "#FDFEFE",
    "error_bg": "#C0392B",  # Red error
    "error_fg": "white",
    # Aliases required by bind_entry_hover
    "bg_hover": "#B83A6F",
    "fg_hover": "#FDFEFE",
    "bg_focus": "#F4D03F",
    "fg_focus": "#17202A",
    "bg_error": "#C0392B",
    # Action buttons
    "submit_bg": "#22c55e",  # Green — Save Changes
    "submit_hover_bg": "#2563eb",
    "cancel_bg": "#ef4444",  # Red — Cancel / Close
    "cancel_hover_bg": "#991b1b",
    # Help sub-window
    "help_bg": "#fffaf0",
    "help_header_bg": "#7B1D4A",  # Plum header in help
    "help_btn_bg": "#9B2460",
    # Session viewer
    "session_bg": "#f8fafc",
    "session_label_fg": "#7B1D4A",
    "session_value_fg": "#3A0020",
    "session_alert_fg": "#b91c1c",
    "session_ok_fg": "#064e3b",
}

ACCOUNT_TYPE_ADD_UI_THEME = {
    "main_bg": "#F4ECF7",
    "header_bg": "#5B2C6F",
    "header_fg": "white",
    "label_bg": "#F4ECF7",
    "entry_bg": "white",
    "entry_fg": "black",
    "readonly_bg": "#FDEDEC",
    "button_bg": "#884EA0",
    "button_fg": "white",
    "focus_bg": "#F39C12",
    "focus_fg": "#1B2631",
    "hover_bg": "#A569BD",
    "hover_fg": "#FDFEFE",
    "error_bg": "#C0392B",
    "error_fg": "white",
    # Aliases required by bind_entry_hover
    "bg_hover": "#A569BD",
    "fg_hover": "#FDFEFE",
    "bg_focus": "#F39C12",
    "fg_focus": "#1B2631",
    "bg_error": "#C0392B",
    # --- NEW ADDITIONS FOR budget_head_add.py ---
    "submit_bg": "#22c55e",  # Green
    "submit_hover_bg": "#2563eb",  # Blue on hover
    "cancel_bg": "#ef4444",  # Red
    "cancel_hover_bg": "#991b1b",  # Darker red on hover
    "help_bg": "#fffaf0",
    "help_header_bg": "#ff7f50",
    "help_btn_bg": "#4682b4",
    "session_bg": "#f8fafc",
    "session_label_fg": "#0b63a7",
    "session_value_fg": "#0b3d2e",
    "session_alert_fg": "#b91c1c",
    "session_ok_fg": "#064e3b",
}

ACCOUNTS_ADD_UI_THEME = {
    "main_bg": "#EBF5FB",
    "header_bg": "#1A5276",
    "header_fg": "white",
    "label_bg": "#EBF5FB",
    "entry_bg": "white",
    "entry_fg": "black",
    "readonly_bg": "#F6DDCC",
    "button_bg": "#2471A3",
    "button_fg": "white",
    "focus_bg": "#F8C471",
    "focus_fg": "#17202A",
    "hover_bg": "#5499C7",
    "hover_fg": "#FDFEFE",
    "error_bg": "#BA4A00",
    "error_fg": "white",
    # Aliases required by bind_entry_hover
    "bg_hover": "#5499C7",
    "fg_hover": "#FDFEFE",
    "bg_focus": "#F8C471",
    "fg_focus": "#17202A",
    "bg_error": "#BA4A00",
    "submit_bg": "#22c55e",
    "submit_hover_bg": "#2563eb",
    "cancel_bg": "#ef4444",
    "cancel_hover_bg": "#991b1b",
    "help_bg": "#fffaf0",
    "help_header_bg": "#1a5276",  # Dark Blue used in accounts help
    "help_btn_bg": "#1a5276",
    "session_bg": "#f8fafc",
    "session_label_fg": "#1a5276",
    "session_value_fg": "#1b2631",
    "session_alert_fg": "#b91c1c",
    "session_ok_fg": "#064e3b",
}

# ---------------------------------------------------------------------------
# Accounts Edit – warm coral / terracotta theme
# Companion to ACCOUNTS_ADD_UI_THEME (deep navy #1A5276 / #EBF5FB).
# The warm terra-cotta palette makes "edit" windows immediately
# distinguishable from the cool blue "add" window.
# ---------------------------------------------------------------------------
ACCOUNTS_EDIT_UI_THEME = {
    "main_bg": "#FFF0E6",  # Very light coral / cream
    "header_bg": "#8B3A2A",  # Deep terracotta
    "header_fg": "white",
    "label_bg": "#FFF0E6",
    "entry_bg": "#FFFAF8",  # Near-white with warm tint
    "entry_fg": "#2C1A14",  # Very dark brown text
    "readonly_bg": "#F5D5C5",  # Soft coral for read-only cells
    "button_bg": "#B0412E",  # Mid terracotta
    "button_fg": "white",
    "focus_bg": "#F4D03F",  # Gold focus ring
    "focus_fg": "#17202A",
    "hover_bg": "#D4634A",  # Lighter terracotta on hover
    "hover_fg": "#FDFEFE",
    "error_bg": "#C0392B",
    "error_fg": "white",
    # Aliases required by bind_entry_hover
    "bg_hover": "#D4634A",
    "fg_hover": "#FDFEFE",
    "bg_focus": "#F4D03F",
    "fg_focus": "#17202A",
    "bg_error": "#C0392B",
    "submit_bg": "#22c55e",
    "submit_hover_bg": "#2563eb",
    "cancel_bg": "#ef4444",
    "cancel_hover_bg": "#991b1b",
    "help_bg": "#fffaf0",
    "help_header_bg": "#8B3A2A",
    "help_btn_bg": "#B0412E",
    "session_bg": "#f8fafc",
    "session_label_fg": "#8B3A2A",
    "session_value_fg": "#2C1A14",
    "session_alert_fg": "#b91c1c",
    "session_ok_fg": "#064e3b",
}

CATEGORIES_ADD_UI_THEME = {
    "main_bg": "#E8F8F5",
    "header_bg": "#0E6251",
    "header_fg": "white",
    "label_bg": "#E8F8F5",
    "entry_bg": "white",
    "entry_fg": "black",
    "readonly_bg": "#F4ECF7",
    "button_bg": "#138D75",
    "button_fg": "white",
    "focus_bg": "#F4D03F",
    "focus_fg": "#1B2631",
    "hover_bg": "#16A085",
    "hover_fg": "#FDFEFE",
    "error_bg": "#A93226",
    "error_fg": "white",
    # Aliases required by bind_entry_hover
    "bg_hover": "#16A085",
    "fg_hover": "#FDFEFE",
    "bg_focus": "#F4D03F",
    "fg_focus": "#1B2631",
    "bg_error": "#A93226",
    "submit_bg": "#22c55e",
    "submit_hover_bg": "#2563eb",
}

BANK_TRANSACTION_ADD_UI_THEME = {
    "main_bg": "#FDF2E9",  # Warm peach — distinct from all other dialogs
    "header_bg": "#784212",  # Dark amber/brown
    "header_fg": "white",
    "label_bg": "#FDF2E9",
    "entry_bg": "white",
    "entry_fg": "black",
    "readonly_bg": "#FDEBD0",
    "button_bg": "#A04000",
    "button_fg": "white",
    "focus_bg": "#F39C12",
    "focus_fg": "#1B2631",
    "hover_bg": "#CA6F1E",
    "hover_fg": "#FDFEFE",
    "error_bg": "#C0392B",
    "error_fg": "white",
    # Aliases required by bind_entry_hover
    "bg_hover": "#CA6F1E",
    "fg_hover": "#FDFEFE",
    "bg_focus": "#F39C12",
    "fg_focus": "#1B2631",
    "bg_error": "#C0392B",
    "submit_bg": "#22c55e",
    "submit_hover_bg": "#2563eb",
    "cancel_bg": "#ef4444",
    "cancel_hover_bg": "#991b1b",
    "help_bg": "#fffaf0",
    "help_header_bg": "#2980b9",
    "help_btn_bg": "#34495e",
    "help_tab_bg": "#2E86C1",
    "session_bg": "#f8fafc",
    "session_label_fg": "#2c3e50",
    "session_value_fg": "#0b3d2e",
    "session_alert_fg": "#b91c1c",
    "session_ok_fg": "#064e3b",
}

# ---------------------------------------------------------------------------
# Bank Transaction Edit – deep indigo / lavender theme
# Companion to BANK_TRANSACTION_ADD_UI_THEME (warm amber/peach/brown).
# A cool indigo palette provides maximum contrast with the warm add theme,
# making "edit" windows immediately distinguishable at a glance.
# ---------------------------------------------------------------------------
BANK_TRANSACTION_EDIT_UI_THEME = {
    "main_bg": "#EDF0FF",  # Very light indigo / lavender
    "header_bg": "#2D3A8C",  # Deep indigo — cool contrast to amber add
    "header_fg": "white",
    "label_bg": "#EDF0FF",
    "entry_bg": "#F8F9FF",  # Near-white with blue tint
    "entry_fg": "#0A0A2E",  # Very dark navy text
    "readonly_bg": "#E4E8F9",  # Slightly deeper lavender for read-only
    "button_bg": "#3D52B5",  # Mid indigo
    "button_fg": "white",
    "focus_bg": "#F4D03F",  # Gold focus ring
    "focus_fg": "#17202A",
    "hover_bg": "#5B6FD4",  # Lighter indigo on hover
    "hover_fg": "#FDFEFE",
    "error_bg": "#C0392B",  # Standard red error
    "error_fg": "white",
    # Aliases required by bind_entry_hover
    "bg_hover": "#5B6FD4",
    "fg_hover": "#FDFEFE",
    "bg_focus": "#F4D03F",
    "fg_focus": "#17202A",
    "bg_error": "#C0392B",
    # Action buttons
    "submit_bg": "#22c55e",  # Green — Save Changes
    "submit_hover_bg": "#2563eb",
    "cancel_bg": "#ef4444",  # Red — Cancel / Close
    "cancel_hover_bg": "#991b1b",
    # Help sub-window
    "help_bg": "#fffaf0",
    "help_header_bg": "#2D3A8C",
    "help_btn_bg": "#3D52B5",
    "help_tab_bg": "#2D3A8C",
    # Session viewer
    "session_bg": "#f8fafc",
    "session_label_fg": "#2D3A8C",
    "session_value_fg": "#0A0A2E",
    "session_alert_fg": "#b91c1c",
    "session_ok_fg": "#064e3b",
}

# ---------------------------------------------------------------------------
# PPF Master Add – deep midnight / gold theme
# Distinct from every other dialog: near-black chrome with gold accents,
# entry fields remain yellow-on-black via the global UI_THEME (apply_entry_theme).
# ---------------------------------------------------------------------------
PPF_MASTER_ADD_UI_THEME = {
    "main_bg": "#0D1117",  # Near-black (GitHub dark canvas)
    "header_bg": "#013220",  # Deep forest green
    "header_fg": "#FFD700",  # Gold
    "label_fg": "#FFD700",  # Gold labels inside bands
    "button_bg": "#00704A",  # Forest-green buttons
    "button_fg": "#FFD700",  # Gold button text
    # Band background colours (very dark, distinct hues)
    "band_account": "#0f1923",  # Near-black blue
    "band_holder": "#141d26",  # Slightly lighter dark blue
    "band_dates": "#1a1a2e",  # Deep navy
    "band_status": "#16213e",  # Dark indigo
    "submit_bg": "#22c55e",
    "submit_hover_bg": "#2563eb",
}

# ---------------------------------------------------------------------------
# PPF Transactions Add – deep amethyst / violet theme
# Related to PPF master but visually distinct: dark violet-black chrome with
# gold labels, entry fields stay yellow-on-black via global UI_THEME.
# ---------------------------------------------------------------------------
PPF_TRANS_ADD_UI_THEME = {
    "main_bg": "#0c0018",  # Near-black with violet tint
    "header_bg": "#3b0066",  # Deep amethyst / violet
    "header_fg": "#FFD700",  # Gold
    "label_fg": "#FFD700",  # Gold labels inside bands
    "button_bg": "#6a00b8",  # Amethyst buttons
    "button_fg": "#FFD700",  # Gold button text
    # Band background colours (dark violet palette)
    "band_master": "#130026",  # Very dark violet
    "band_details": "#1a0033",  # Slightly lighter dark violet
    "band_amounts": "#20003d",  # Deep violet with more colour depth
    "submit_bg": "#22c55e",
    "submit_hover_bg": "#2563eb",
}

# ---------------------------------------------------------------------------
# CC Master Add – deep crimson / ruby-red theme
# Credit-card feel: dark-red chrome with gold labels.
# Entry fields remain yellow-on-black via the global UI_THEME.
# ---------------------------------------------------------------------------
CC_MASTER_ADD_UI_THEME = {
    "main_bg": "#FFF0F0",  # Light pinkish-crimson canvas (not black)
    "header_bg": "#7b0000",  # Deep crimson header/title bar
    "header_fg": "#FFD700",  # Gold on dark header
    "label_fg": "#6b0000",  # Dark crimson — readable on light band backgrounds
    "button_bg": "#b91c1c",  # Ruby red buttons
    "button_fg": "#FFD700",  # Gold button text
    # Section band backgrounds — light crimson palette (NOT near-black)
    "band_account": "#FFE8E8",  # Soft pinkish-red
    "band_card": "#FFD6D6",  # Slightly deeper pink
    "band_financial": "#FFC8C8",  # Most saturated light pink
    "submit_bg": "#22c55e",
    "submit_hover_bg": "#2563eb",
    "cancel_bg": "#ef4444",
    "cancel_hover_bg": "#991b1b",
    "help_bg": "#fffaf0",  # Floral white help body
    "help_text_fg": "#2d0000",  # Dark crimson — readable on light help bg
    "help_header_bg": "#800000",
    "help_btn_bg": "#b30000",
    "session_bg": "#fcf9f2",
    "session_label_fg": "#800000",
    "session_value_fg": "#1b2631",
    "session_alert_fg": "#b91c1c",
    "session_ok_fg": "#064e3b",
}

CC_TRANS_ADD_UI_THEME = {
    "main_bg": "#001414",  # Near-black teal canvas
    "header_bg": "#005f5f",  # Deep teal
    "header_fg": "#FFD700",  # Gold
    "label_fg": "#FFD700",  # Gold labels inside bands
    "button_bg": "#007a7a",  # Teal buttons
    "button_fg": "#FFD700",  # Gold button text
    # Band background colours (dark teal palette)
    "band_master": "#001a1a",  # Near-black teal
    "band_details": "#002020",  # Slightly lighter teal
    "band_amounts": "#002a2a",  # Deepest teal
    "submit_bg": "#22c55e",
    "submit_hover_bg": "#2563eb",
}

REWARDS_ADD_UI_THEME = {
    "main_bg": "#2e1065",  # Deep Indigo
    "header_bg": "#1e1b4b",  # Darker Indigo
    "header_fg": "#fde047",  # Gold text for header
    "band1_bg": "#4c1d95",  # Royal Purple
    "band2_bg": "#5b21b6",  # Vibrant Purple
    "footer_bg": "#312e81",  # Indigo footer
    "button_bg": "#6d28d9",  # Purple default buttons
    "button_fg": "white",
    "submit_bg": "#22c55e",  # Green for Save
    "submit_hover_bg": "#2563eb",
    "cancel_bg": "#be123c",  # Red for Esc
    "cancel_hover_bg": "#e11d48",
    "text_fg": "#e0e7ff",  # Light text for labels
    "entry_bg": "#000000",  # Pure Black entry boxes
    "entry_fg": "#fde047",  # Bright Yellow/Gold entry text
}

FD_MASTER_ADD_UI_THEME = {
    "main_bg": "#0a0a2e",  # Near-black navy canvas
    "header_bg": "#1a1a6e",  # Deep navy/indigo
    "header_fg": "#FFD700",  # Gold
    "label_fg": "#FFD700",  # Gold labels inside bands
    "button_bg": "#2828a0",  # Medium indigo buttons
    "button_fg": "#FFD700",  # Gold button text
    # Band background colours (dark navy palette)
    "band_account": "#0d0d38",  # Near-black navy
    "band_fd": "#111145",  # Slightly lighter navy
    "band_dates": "#141452",  # Deeper indigo
    "submit_bg": "#22c55e",
    "submit_hover_bg": "#2563eb",
}

FD_TRANS_ADD_UI_THEME = {
    "main_bg": "#1a0e00",  # Near-black copper canvas
    "header_bg": "#5c3100",  # Deep copper/bronze
    "header_fg": "#FFD700",  # Gold
    "label_fg": "#FFD700",  # Gold labels inside bands
    "button_bg": "#7a4200",  # Copper buttons
    "button_fg": "#FFD700",  # Gold button text
    # Band background colours (dark copper palette)
    "band_master": "#1f1200",  # Near-black copper
    "band_details": "#261600",  # Slightly lighter copper
    "band_amounts": "#2d1a00",  # Deepest copper
    "submit_bg": "#22c55e",
    "submit_hover_bg": "#2563eb",
}

# ---------------------------------------------------------------------------
# Loan Master Add – dark olive / moss-green theme
# Distinct from PPF (forest green) and all others: near-black olive chrome
# with bright-lime accents.  Entry fields remain yellow-on-black (global).
# ---------------------------------------------------------------------------
LOAN_MASTER_ADD_UI_THEME = {
    "main_bg": "#0f1a00",  # Near-black olive canvas
    "header_bg": "#2d4a00",  # Deep olive/moss green
    "header_fg": "#FFD700",  # Gold
    "label_fg": "#FFD700",  # Gold labels inside bands
    "button_bg": "#4a7a00",  # Olive-green buttons
    "button_fg": "#FFD700",  # Gold button text
    # Band background colours (dark olive palette)
    "band_account": "#141f00",  # Near-black olive
    "band_loan": "#1a2800",  # Slightly lighter dark olive
    "band_dates": "#213200",  # Deepest olive-green
    "submit_bg": "#22c55e",
    "submit_hover_bg": "#2563eb",
}

# ---------------------------------------------------------------------------
# Loan Master Edit – bright teal / cyan theme
# Companion to LOAN_MASTER_ADD_UI_THEME (near-black olive / gold).
# A vivid teal palette provides maximum contrast with the dark olive add
# theme, making "edit" windows immediately distinguishable at a glance.
# ---------------------------------------------------------------------------
LOAN_MASTER_EDIT_UI_THEME = {
    "main_bg": "#E6FAFA",  # Very light teal / aqua
    "header_bg": "#0E6B6B",  # Deep teal
    "header_fg": "#FFFFFF",
    "label_bg": "#E6FAFA",
    "label_fg": "#0E6B6B",  # Teal labels in bands
    "entry_bg": "#F0FFFE",
    "entry_fg": "#012525",  # Very dark teal text
    "readonly_bg": "#C5EFEF",
    "button_bg": "#117A7A",
    "button_fg": "white",
    "focus_bg": "#F4D03F",
    "focus_fg": "#17202A",
    "hover_bg": "#1FA8A8",
    "hover_fg": "#FFFFFF",
    "error_bg": "#C0392B",
    "error_fg": "white",
    # Aliases required by bind_entry_hover / apply_entry_theme
    "bg_hover": "#1FA8A8",
    "fg_hover": "#FFFFFF",
    "bg_focus": "#F4D03F",
    "fg_focus": "#17202A",
    "bg_error": "#C0392B",
    # Action buttons
    "submit_bg": "#22c55e",
    "submit_hover_bg": "#2563eb",
    "cancel_bg": "#ef4444",
    "cancel_hover_bg": "#991b1b",
    # Band backgrounds (light teal palette matching dark-olive add bands)
    "band_account": "#D0F5F5",
    "band_loan": "#C5EFEF",
    "band_dates": "#BBEBE8",
}

# ---------------------------------------------------------------------------
# Loan Transactions Add – dark maroon / wine theme
# Distinct from CC (crimson) and all others: near-black maroon canvas with
# rose-pink accents.  Entry fields remain yellow-on-black (global).
# ---------------------------------------------------------------------------
LOAN_TRANS_ADD_UI_THEME = {
    "main_bg": "#1a000a",  # Near-black maroon canvas
    "header_bg": "#5c0020",  # Deep maroon/wine
    "header_fg": "#FFD700",  # Gold
    "label_fg": "#FFD700",  # Gold labels inside bands
    "button_bg": "#8b0030",  # Maroon buttons
    "button_fg": "#FFD700",  # Gold button text
    # Band background colours (dark maroon palette)
    "band_master": "#1f000d",  # Near-black maroon
    "band_details": "#260012",  # Slightly lighter maroon
    "band_amounts": "#2d0016",  # Deepest maroon
    "band_balance": "#340019",  # Extra-deep for principal-due band
    "submit_bg": "#22c55e",
    "submit_hover_bg": "#2563eb",
}


def setup_footer_tooltip(parent_window, bg_color="#f3f4f6", fg_color="#374151"):
    """
    Centralizes the creation of the tooltip string variable and the footer label.

    Args:
        parent_window: The main window (Toplevel or Tk) to attach the footer to.
        bg_color: The background color for the footer label.
        fg_color: The text color for the footer label.

    Returns:
        tooltip_var (tk.StringVar): The variable to be updated by hover events.
    """
    tooltip_var = tk.StringVar()
    tooltip_var.set("Hover over fields for info")

    info_label = tk.Label(
        parent_window,
        textvariable=tooltip_var,
        font=("Helvetica", 16, "italic"),
        bg=bg_color,
        fg=fg_color,
        # bg="#000000",
        # fg="#FFFF00",
        relief="sunken",
        bd=1,
        anchor="w",
        padx=10,
        pady=5,
    )
    # Pack at the absolute bottom, filling the horizontal space
    info_label.pack(side="bottom", fill="x", pady=(5, 0))

    return tooltip_var


def format_hotkey_label(label: str, hotkey: str) -> str:
    """Format button label with hotkey in brackets."""
    idx = label.lower().find(hotkey.lower())
    if idx != -1:
        return label[:idx] + "[" + label[idx] + "]" + label[idx + 1 :]
    else:
        return f"{label} ({hotkey.upper()})"


def bind_tooltip(widget: tk.Widget, tooltip_var: tk.StringVar, text: str):
    """Binds a hover tooltip to update a StringVar."""

    def _show(_ev=None):
        tooltip_var.set(f"💡 Hint: {text}")

    def _hide(_ev=None):
        tooltip_var.set("💡 Hover over fields to view helpful tips here.")

    widget.bind("<FocusIn>", _show, add="+")
    widget.bind("<FocusOut>", _hide, add="+")
    widget.bind("<Enter>", _show, add="+")
    widget.bind("<Leave>", _hide, add="+")


def bind_entry_hover(widget: tk.Widget, theme: dict = UI_THEME):
    """Adds background and foreground color changes on hover and focus to standard widgets."""
    try:
        default_bg = widget.cget("background")
        default_fg = widget.cget("foreground")
    except (tk.TclError, AttributeError):
        return

    hover_bg = theme["bg_hover"]
    hover_fg = theme["fg_hover"]
    focus_bg = theme["bg_focus"]
    focus_fg = theme["fg_focus"]
    error_bg = theme["bg_error"]

    def _on_enter(e):
        try:
            current_bg = str(widget.cget("background"))
            if current_bg != error_bg:
                widget.config(
                    background=hover_bg,
                    readonlybackground=hover_bg,
                    foreground=hover_fg,
                )
        except (tk.TclError, AttributeError):
            pass

    def _on_leave(e):
        try:
            current_bg = str(widget.cget("background"))
            if current_bg != error_bg:
                widget.config(
                    background=default_bg,
                    readonlybackground=default_bg,
                    foreground=default_fg,
                )
        except (tk.TclError, AttributeError):
            pass

    def _on_focus_in(e):
        try:
            widget.config(
                background=focus_bg,
                readonlybackground=focus_bg,
                foreground=focus_fg,
            )
        except (tk.TclError, AttributeError):
            pass

    def _on_focus_out(e):
        try:
            widget.config(
                background=default_bg,
                readonlybackground=default_bg,
                foreground=default_fg,
            )
        except (tk.TclError, AttributeError):
            pass

    widget.bind("<Enter>", _on_enter)
    widget.bind("<Leave>", _on_leave)
    widget.bind("<FocusIn>", _on_focus_in)
    widget.bind("<FocusOut>", _on_focus_out)


def flash_error(widget: tk.Widget, cycles: int = 5, interval_ms: int = 100):
    """Flashes an error message on the widget."""
    bg_normal = UI_THEME["bg_input"]
    bg_error = UI_THEME["bg_error"]

    def blink(w, colors, delay=100, count=0):
        try:
            if count < len(colors):
                w.config(bg=colors[count])
                w.after(delay, blink, w, colors, delay, count + 1)
            else:
                w.config(bg=bg_error)
        except tk.TclError:
            pass

    blink(widget, [bg_error, bg_normal] * 5)


def on_enter_focus_next(event, window, save_btn, cancel_btn):
    """Handles Return key to invoke buttons or move to the next widget."""
    focused_widget = window.focus_get()
    if focused_widget in (save_btn, cancel_btn):
        inv = getattr(focused_widget, "invoke", None)
        try:
            if inv is not None:
                inv()
        except TypeError:
            pass
    elif isinstance(
        focused_widget,
        (tk.Entry, tk.Spinbox, tk.Text, tk.Radiobutton, ttk.Combobox),
    ):
        next_widget = focused_widget.tk_focusNext()
        if next_widget is not None:
            next_widget.focus_set()


def apply_button_animations(button: tk.Button, usual_bg: str, active_bg: str):
    """Applies hover and focus color changes to a Tkinter Button."""
    button.bind("<Enter>", lambda e: button.config(bg=active_bg))
    button.bind("<Leave>", lambda e: button.config(bg=usual_bg))
    button.bind("<FocusIn>", lambda e: button.config(bg=active_bg))
    button.bind("<FocusOut>", lambda e: button.config(bg=usual_bg))


def apply_button_hover(btn, normal_bg, hover_bg):
    """
    Applies standard hover and focus color changes to a Tkinter button.
    Used to DRY up repetitive button bindings across data entry forms.
    """
    btn.bind("<Enter>", lambda e: btn.config(bg=hover_bg))
    btn.bind("<Leave>", lambda e: btn.config(bg=normal_bg))
    btn.bind("<FocusIn>", lambda e: btn.config(bg=hover_bg))
    btn.bind("<FocusOut>", lambda e: btn.config(bg=normal_bg))


def apply_entry_theme(widget: tk.Widget, is_readonly: bool = False) -> None:
    """
    Applies the universal theme to an input widget (Entry, Spinbox, Combobox, DateEntry).
    Strictly follows the UI_THEME defined in globals.py.
    """
    bg_color = UI_THEME["bg_readonly"] if is_readonly else UI_THEME["bg_input"]
    fg_color = UI_THEME["fg_readonly"] if is_readonly else UI_THEME["fg_input"]
    bg_disabled = UI_THEME["bg_disabled"]
    fg_disabled = UI_THEME["fg_disabled"]
    font_style = UI_THEME["font_bold"] if is_readonly else UI_THEME["font_main"]

    hover_bg = UI_THEME["bg_hover"]
    hover_fg = UI_THEME["fg_hover"]
    focus_bg = UI_THEME["bg_focus"]
    focus_fg = UI_THEME["fg_focus"]
    select_bg = UI_THEME["bg_select"]

    w_class = widget.winfo_class()
    type_name = widget.__class__.__name__

    # --- 1. Handle TTK Widgets (Combobox, DateEntry) ---
    if (
        "Combobox" in w_class
        or "DateEntry" in w_class
        or "DateEntry" in type_name
        or "Combobox" in type_name
    ):
        style = ttk.Style()

        if "clam" not in style.theme_use():
            try:
                style.theme_use("clam")
            except tk.TclError:
                pass

        style_name = f"DarkRO.{w_class}" if is_readonly else f"Dark.{w_class}"

        style.configure(
            style_name,
            fieldbackground=bg_color,
            background=bg_color,  # Dropdown arrow button color
            foreground=fg_color,
            arrowcolor=fg_color,
            bordercolor=focus_bg,
            lightcolor=focus_bg,
            darkcolor=focus_bg,
            font=font_style,
        )

        # CRITICAL FIX: "hover" MUST be listed before "focus"
        style.map(
            style_name,
            fieldbackground=[
                ("hover", hover_bg),
                ("focus", focus_bg),
                ("readonly", bg_color),
                ("disabled", bg_disabled),
                ("!focus", bg_color),
            ],
            selectbackground=[
                ("hover", hover_bg),
                ("focus", select_bg),
                ("!focus", bg_color),
            ],
            foreground=[
                ("hover", hover_fg),
                ("focus", focus_fg),
                ("!focus", fg_color),
            ],
            selectforeground=[
                ("hover", hover_fg),
                ("focus", focus_fg),
                ("!focus", fg_color),
            ],
        )

        try:
            widget.configure(style=style_name)
        except (tk.TclError, AttributeError):
            pass

        try:
            widget.configure(font=font_style)
        except (tk.TclError, AttributeError):
            pass

        if "DateEntry" in w_class or "DateEntry" in type_name:
            # CRITICAL FIX: DateEntry text fields often ignore custom style names.
            # We must explicitly map the base "DateEntry" style.
            style.map(
                "DateEntry",
                fieldbackground=[
                    ("readonly", bg_color),
                    ("!focus", bg_color),
                    ("focus", focus_bg),
                ],
                foreground=[
                    ("readonly", fg_color),
                    ("!focus", fg_color),
                    ("focus", focus_fg),
                ],
            )
            try:
                widget.configure(
                    background=focus_bg,
                    foreground=focus_fg,
                    headersbackground=bg_color,
                    headersforeground=fg_color,
                    selectbackground=select_bg,
                    selectforeground=focus_fg,
                )
            except (tk.TclError, AttributeError):
                pass

        return

    # --- 2. Handle Standard TK Widgets (Entry, Spinbox) ---
    try:
        widget.configure(
            bg=bg_color,
            fg=fg_color,
            font=font_style,
            insertbackground=fg_color,
            readonlybackground=bg_color,
            disabledbackground=bg_disabled,
            disabledforeground=fg_disabled,
            relief="flat",
            bd=1,
            highlightthickness=1,
            highlightbackground=focus_bg,
            highlightcolor=focus_bg,
        )
    except (tk.TclError, AttributeError, TypeError):
        pass

    # --- 3. Attach Centralized Hover Bindings ---
    bind_entry_hover(widget)


def create_label_entry_pair(
    parent_frame: tk.Widget,
    row: int,
    col: int,
    label_text: str,
    var: tk.Variable,
    width: int = 25,
    is_required: bool = True,
    widget_type: str = "entry",
    values: list = None,
    label_color: str = "#2f4f4f",  # Matches the original label_color
    req_color: str = "#dc143c",  # Matches the original required_color
) -> tk.Widget:
    """
    Centrally constructs a standard Label + Widget pair.
    The label blends with the parent's background, while the input widget
    automatically receives the global UI_THEME styling and hover/focus logic.
    """
    # Automatically inherit the background color from the parent frame
    bg_color = parent_frame.cget("bg")

    req_text = " *" if is_required else ""
    fg_color = req_color if is_required else label_color

    # 1. Create the Label (Preserving original UI look)
    label = tk.Label(
        parent_frame,
        text=f"{label_text}{req_text}",
        font=("Helvetica", 14, "bold"),
        fg=fg_color,
        bg=bg_color,
        anchor="w",
    )
    label.grid(row=row, column=col * 2, sticky="nw", padx=(10, 5), pady=8)

    # 2. Create the Widget
    if widget_type == "entry":
        widget = tk.Entry(parent_frame, textvariable=var, width=width)
    elif widget_type == "combobox":
        widget = ttk.Combobox(
            parent_frame,
            textvariable=var,
            width=width - 3,
            values=values or [],
        )
    elif widget_type == "checkbox":
        widget = tk.Checkbutton(
            parent_frame,
            variable=var,
            text="Yes",
            font=("Helvetica", 14),
            bg=bg_color,
            activebackground=bg_color,
        )
    else:
        widget = tk.Entry(parent_frame, textvariable=var, width=width)

    # 3. Apply central theming to INPUTS ONLY (Skip checkbox to keep it clean)
    if widget_type in ("entry", "combobox"):
        apply_entry_theme(widget)

    widget.grid(row=row, column=col * 2 + 1, sticky="nw", padx=(5, 10), pady=8)
    return widget


def bind_date_spin(date_widget, callback=None) -> None:
    """Binds Up/Down arrow keys to increment/decrement a DateEntry date.

    Accepts an optional callback function that runs after the date is
    modified.
    """
    def _spin(event, delta):
        try:
            current_date = date_widget.get_date()
            if current_date:
                date_widget.set_date(current_date + timedelta(days=delta))
                if callback:
                    callback()
        except Exception:
            pass
        return "break"  # Prevents default Tkinter cursor movement

    date_widget.bind("<Up>", lambda e: _spin(e, 1))
    date_widget.bind("<Down>", lambda e: _spin(e, -1))


def universal_tree_sort(tree: ttk.Treeview, col: str, reverse: bool) -> None:
    """A generic sorter that handles Strings, Currency, Percentages, and various date formats."""
    # Find all items to sort, ignoring summary rows
    data_list = [
        (tree.set(child, col), child)
        for child in tree.get_children("")
        if "summary" not in tree.item(child, "tags") and child != "SUMMARY"
    ]

    def convert_type(val_tuple):
        val = str(val_tuple[0]).strip()
        # Handle empty/loading states
        if val in ("N/A", "-", "", "TBD", "Fetching...", "Calculating...", "—"):
            return float("-inf") if reverse else float("inf")

        # Strip currency and formatting
        clean_val = (
            val.split("(")[0]
            .replace(",", "")
            .replace("₹", "")
            .replace("%", "")
            .strip()
        )

        # Check for date formats (length between 8 and 10 with 2 separators)
        if 8 <= len(clean_val) <= 10 and (
            clean_val.count("-") == 2 or clean_val.count("/") == 2
        ):
            for fmt in ("%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
                try:
                    return datetime.strptime(clean_val, fmt).timestamp()
                except ValueError:
                    continue

        # Try numeric, fallback to string
        try:
            return float(clean_val)
        except ValueError:
            return val.lower()

    data_list.sort(key=convert_type, reverse=reverse)

    for index, (val, child) in enumerate(data_list):
        tree.move(child, "", index)

        # Keep alternating colors (oddrow/evenrow or odd/even tags) consistent after sorting
        current_tags = list(tree.item(child, "tags") or [])
        if "oddrow" in current_tags or "evenrow" in current_tags:
            filtered_tags = [t for t in current_tags if t not in ("oddrow", "evenrow")]
            new_tag = "evenrow" if index % 2 == 0 else "oddrow"
            tree.item(child, tags=filtered_tags + [new_tag])
        elif "odd" in current_tags or "even" in current_tags:
            filtered_tags = [t for t in current_tags if t not in ("odd", "even")]
            new_tag = "even" if index % 2 == 0 else "odd"
            tree.item(child, tags=filtered_tags + [new_tag])

    tree.heading(
        col,
        command=lambda _col=col: universal_tree_sort(tree, _col, not reverse),
    )
