# -*- coding: utf-8 -*-
# StockMan/company_add.py

"""company_add.py

Provides the Add Company modal dialog used by the StockMan GUI.
Contains helpers to render the form, validate input, and persist a
company record to the application's SQLite database. The dialog is
modal and uses the project's dialog utilities for user feedback.
"""

import re
import sqlite3
import tkinter as tk
from tkinter import ttk
from typing import Optional, Tuple, Union

# Project-specific imports (assume these are available in the project)
from Shared.dialog_utils import (
    show_colorful_info,
    show_colorful_error,
    show_colorful_yesno,
)
from Shared.dialog_sizing import calculate_dialog_size
from Shared.globals import get_db_connection, logger
from Shared.window_manager import push_window, pop_window, safe_close_modal
from Shared.gui_progressive import progressive_selection
from Shared.gui_utils import (
    create_label_entry_pair,
    bind_tooltip,
    setup_footer_tooltip,
    apply_button_animations,
)

from Shared.globals import logger
from .validation_utils import ValidationError, show_validation_error


def add_company_db(
    stk_code: str,
    isin: str,
    company_name: str,
    short_name: str = "",
    ticker: str = "",  # <-- NEW FIELD
    sector: str = "",
    face_value: float = 10.0,
    tick: float = 0.01,
    is_active: int = 1,
    is_etf: int = 0,
) -> Tuple[bool, str]:
    """
    Adds a company to the stocks table.
    Returns (True, 'Success message') or (False, 'Error message').
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO stocks (
                    stk_code, isin, company_name, short_name, ticker, sector,
                    face_value, tick, is_active, is_etf
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    stk_code,
                    isin,
                    company_name,
                    short_name,
                    ticker,  # <-- NEW FIELD
                    sector,
                    face_value,
                    tick,
                    is_active,
                    is_etf,
                ),
            )
            conn.commit()
        logger.info("Added company: %s (%s)", company_name, stk_code)
        return True, f"Company '{company_name}' added successfully."
    except sqlite3.IntegrityError as e:
        # Raise a ValidationError so callers can map to UI-friendly messages
        logger.warning(
            "Integrity error adding company: %s (%s): %s",
            company_name,
            stk_code,
            e,
        )
        raise ValidationError(f"Integrity error: {e}") from e
    except sqlite3.Error as e:
        # Catch SQLite-specific errors and report them
        logger.error(
            "Database error adding company: %s (%s): %s",
            company_name,
            stk_code,
            e,
            exc_info=True,
        )
        raise


def add_company(
    parent: Union[tk.Tk, tk.Toplevel],
    calling_button: Optional[tk.Widget] = None,
) -> None:
    """
    Enhanced GUI form for adding a company to the stocks table.

    Features:
    - Professional colorful multi-column layout
    - Uppercase conversion for stock code and ISIN
    - ISIN validation (12 chars, starts with 'IN')
    - Progressive search for Sector and Face Value dropdowns
    - Checkbox widgets for boolean fields
    - ESC key to clear entries
    - Dynamic dialog sizing
    """
    # Calculate dynamic window size
    message_text = (
        "Add New Company\n"
        "Please fill in all required fields\n"
        "Stock Code, ISIN, Company Name, Short Name, "
        "Sector, Face Value, Is Active, Is ETF"
    )
    base_width, base_height = calculate_dialog_size(
        message_text, title="Add New Company"
    )

    # Adjust for multi-column layout and additional features
    window_width = max(850, base_width + 200)
    window_height = max(650, base_height + 150)

    # Create enhanced modal window
    ac = tk.Toplevel(parent)
    ac.title("🏢 Add New Company")
    ac.geometry(f"{window_width}x{window_height}")
    ac.resizable(True, True)
    ac.minsize(800, 600)
    ac.transient(parent)
    ac.grab_set()
    ac.focus_set()
    push_window(ac, parent)

    # Configure colors and styling
    bg_color = "#f0f8ff"  # Alice blue
    header_color = "#4682b4"  # Steel blue
    label_color = "#2f4f4f"  # Dark slate gray
    entry_bg = "#ffffff"
    required_color = "#dc143c"  # Crimson

    ac.configure(bg=bg_color)

    # Create main container with padding - NO SCROLLING
    main_frame = tk.Frame(ac, bg=bg_color)
    main_frame.pack(fill="both", expand=True, padx=20, pady=15)

    # Header section
    header_frame = tk.Frame(main_frame, bg=header_color, relief="raised", bd=2)
    header_frame.pack(fill="x", pady=(0, 20))

    header_label = tk.Label(
        header_frame,
        text="🏢 Add New Company",
        font=("Helvetica", 18, "bold"),
        fg="white",
        bg=header_color,
        pady=10,
    )
    header_label.pack()

    subtitle_label = tk.Label(
        main_frame,
        text="Please fill in all required fields " "marked with *",
        font=("Helvetica", 12, "italic"),
        fg=label_color,
        bg=bg_color,
    )
    subtitle_label.pack(pady=(0, 15))

    # Form fields container - Simple 2 columns layout (NO CANVAS)
    form_frame = tk.Frame(main_frame, bg=bg_color)
    form_frame.pack(fill="both", expand=True, padx=10, pady=10)

    # Configure grid weights for proper resizing
    form_frame.grid_columnconfigure(1, weight=1)
    form_frame.grid_columnconfigure(3, weight=1)  # Variables for form fields
    stk_code_var = tk.StringVar()
    isin_var = tk.StringVar()
    company_name_var = tk.StringVar()
    short_name_var = tk.StringVar()
    sector_var = tk.StringVar()
    ticker_var = tk.StringVar()  # <-- NEW FIELD
    face_value_var = tk.StringVar()
    tick_var = tk.StringVar()
    is_active_var = tk.BooleanVar(value=True)
    is_etf_var = tk.BooleanVar(value=False)

    # Fetch existing data from database for dropdowns
    existing_sectors = []
    existing_face_values = []

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Get unique sectors
            cursor.execute(
                "SELECT DISTINCT sector FROM stocks "
                "WHERE sector != '' ORDER BY sector"
            )
            existing_sectors = [row[0] for row in cursor.fetchall()]
            # Get unique face values
            cursor.execute(
                "SELECT DISTINCT face_value FROM stocks ORDER BY face_value"
            )
            existing_face_values = [str(row[0]) for row in cursor.fetchall()]
            cursor.close()
    except sqlite3.Error as e:
        logger.warning("Could not fetch existing data: %s", e)

    # Add common sectors if not in database
    common_sectors = [
        "Banking",
        "IT",
        "Pharma",
        "Auto",
        "FMCG",
        "Energy",
        "Metals",
        "Telecom",
        "Media",
        "Realty",
        "Capital Goods",
        "Consumer Durables",
    ]
    for sector in common_sectors:
        if sector not in existing_sectors:
            existing_sectors.append(sector)

    # Add common face values if not in database
    common_face_values = ["1.0", "2.0", "5.0", "10.0", "100.0"]
    for fv in common_face_values:
        if fv not in existing_face_values:
            existing_face_values.append(fv)

    existing_face_values.sort(key=float)

    entries = {}  # Store all widgets for easy access

    # Row 0: Stock Code and ISIN
    stk_code_entry = create_label_entry_pair(
        form_frame,
        0,
        0,
        "Stock Code",
        stk_code_var,
        width=15,
        is_required=True,
    )
    isin_entry = create_label_entry_pair(
        form_frame, 0, 1, "ISIN", isin_var, width=15, is_required=True
    )

    # Row 1: Company Name and Short Name
    company_entry = create_label_entry_pair(
        form_frame,
        1,
        0,
        "Company Name",
        company_name_var,
        width=30,
        is_required=True,
    )
    short_name_entry = create_label_entry_pair(
        form_frame,
        1,
        1,
        "Short Name",
        short_name_var,
        width=20,
        is_required=True,
    )

    # Row 2: Sector and Face Value (with progressive search)
    sector_combo = create_label_entry_pair(
        form_frame,
        2,
        0,
        "Sector",
        sector_var,
        width=25,
        is_required=False,
        widget_type="combobox",
        values=existing_sectors,
    )
    face_value_combo = create_label_entry_pair(
        form_frame,
        2,
        1,
        "Face Value",
        face_value_var,
        width=15,
        is_required=False,
        widget_type="combobox",
        values=existing_face_values,
    )

    # Row 3: Tick Size and Ticker
    tick_entry = create_label_entry_pair(
        form_frame, 3, 0, "Tick Size", tick_var, width=15, is_required=False
    )
    ticker_entry = create_label_entry_pair(
        form_frame,
        3,
        1,
        "Ticker (e.g. INFY.NS)",
        ticker_var,
        width=20,
        is_required=False,
    )

    # Row 4: Checkboxes for Is Active and Is ETF
    is_active_check = create_label_entry_pair(
        form_frame,
        4,
        0,
        "Is Active",
        is_active_var,
        is_required=False,
        widget_type="checkbox",
    )
    is_etf_check = create_label_entry_pair(
        form_frame,
        4,
        1,
        "Is ETF",
        is_etf_var,
        is_required=False,
        widget_type="checkbox",
    )

    # Store entries for easy access
    entries.update(
        {
            "stk_code": stk_code_entry,
            "isin": isin_entry,
            "company_name": company_entry,
            "short_name": short_name_entry,
            "ticker": ticker_entry,  # <-- NEW FIELD
            "sector": sector_combo,
            "face_value": face_value_combo,
            "tick": tick_entry,
            "is_active": is_active_check,
            "is_etf": is_etf_check,
        }
    )

    # Set default values
    face_value_var.set("10.0")
    tick_var.set("0.01")

    # --- Tooltip Setup ---
    # Initialize the centralized footer tooltip on the main window 'ac'
    tooltip_var = setup_footer_tooltip(
        ac, bg_color=bg_color, fg_color="#1e3a8a"
    )

    bind_tooltip(
        entries["stk_code"],
        tooltip_var,
        "Enter a unique stock code (min 2 characters).",
    )
    bind_tooltip(
        entries["isin"],
        tooltip_var,
        "Enter exactly 12 characters starting with 'IN'.",
    )
    bind_tooltip(
        entries["company_name"],
        tooltip_var,
        "Enter the full name of the company.",
    )
    bind_tooltip(
        entries["short_name"],
        tooltip_var,
        "Enter a short name or abbreviation.",
    )
    bind_tooltip(
        entries["ticker"],
        tooltip_var,
        "Enter the exchange ticker symbol (e.g., INFY.NS).",
    )
    bind_tooltip(
        entries["sector"], tooltip_var, "Select a sector or type a new one."
    )
    bind_tooltip(
        entries["face_value"], tooltip_var, "Select or enter the face value."
    )
    bind_tooltip(
        entries["tick"],
        tooltip_var,
        "Enter the minimum price movement (tick size).",
    )
    bind_tooltip(
        entries["is_active"],
        tooltip_var,
        "Check if the company is currently active.",
    )
    bind_tooltip(
        entries["is_etf"], tooltip_var, "Check if this asset is an ETF."
    )

    # Force window to front and set focus to first field
    # after window is visible
    ac.lift()
    ac.attributes("-topmost", True)
    ac.after(
        100,
        lambda: (
            ac.focus_force(),
            stk_code_entry.focus_set(),
            ac.attributes("-topmost", False),
        ),
    )

    # Validation and transformation functions
    def validate_and_transform_stock_code(_event=None):
        """Convert stock code to uppercase"""
        current = stk_code_var.get()
        stk_code_var.set(current.upper())

    def validate_and_transform_isin(_event=None):
        """Convert ISIN to uppercase and validate format"""
        current = isin_var.get().upper()
        # Remove any non-alphanumeric characters except those needed
        current = re.sub(r"[^A-Z0-9]", "", current)
        # Limit to 12 characters
        if len(current) > 12:
            current = current[:12]
        isin_var.set(current)

        # Validate format
        if len(current) == 12:
            if not current.startswith("IN"):
                isin_entry["bg"] = "#ffcccc"  # Light red for invalid
                return False
            else:
                isin_entry["bg"] = entry_bg  # Reset to normal
                return True
        elif len(current) > 0:
            isin_entry["bg"] = "#fff8dc"  # Light yellow for incomplete
            return False
        else:
            isin_entry["bg"] = entry_bg
            return False

    def validate_and_transform_ticker(_event=None):
        """Convert ticker to uppercase"""
        current = ticker_var.get()
        ticker_var.set(current.upper())

    def clear_all_entries(_event=None):
        """Clear all entry fields when ESC is pressed"""
        for var in [
            stk_code_var,
            isin_var,
            company_name_var,
            short_name_var,
            ticker_var,  # <-- NEW FIELD
            sector_var,
            face_value_var,
            tick_var,
        ]:
            var.set("")
        is_active_var.set(True)
        is_etf_var.set(False)
        face_value_var.set("10.0")
        tick_var.set("0.01")
        stk_code_entry.focus_set()

    # Bind validation events
    stk_code_var.trace_add(
        "write", lambda *args: validate_and_transform_stock_code()
    )
    isin_var.trace_add("write", lambda *args: validate_and_transform_isin())
    ticker_var.trace_add(
        "write", lambda *args: validate_and_transform_ticker()
    )

    # Setup progressive search for comboboxes
    progressive_selection(sector_combo, existing_sectors)
    progressive_selection(face_value_combo, existing_face_values)

    # Validation function
    def validate_form():
        """Validate all form fields"""
        errors = []

        # Required fields validation
        if not stk_code_var.get().strip():
            errors.append("Stock Code is required")
        elif len(stk_code_var.get().strip()) < 2:
            errors.append("Stock Code must be at least 2 characters")

        isin = isin_var.get().strip()
        if not isin:
            errors.append("ISIN is required")
        elif len(isin) != 12:
            errors.append("ISIN must be exactly 12 characters")
        elif not isin.startswith("IN"):
            errors.append("ISIN must start with 'IN'")
        elif not re.match(r"^IN[A-Z0-9]{10}$", isin):
            errors.append(
                "ISIN must be 'IN' followed by 10 alphanumeric characters"
            )

        if not company_name_var.get().strip():
            errors.append("Company Name is required")
        elif len(company_name_var.get().strip()) < 3:
            errors.append("Company Name must be at least 3 characters")

        if not short_name_var.get().strip():
            errors.append("Short Name is required")
        elif len(short_name_var.get().strip()) < 2:
            errors.append("Short Name must be at least 2 characters")

        # Numeric fields validation
        try:
            face_value = float(face_value_var.get() or "10.0")
            if face_value <= 0:
                errors.append("Face Value must be greater than 0")
        except ValueError:
            errors.append("Face Value must be a valid number")

        try:
            tick = float(tick_var.get() or "0.01")
            if tick <= 0:
                errors.append("Tick Size must be greater than 0")
        except ValueError:
            errors.append("Tick Size must be a valid number")

        return errors

    def on_submit():
        """Handle form submission"""
        errors = validate_form()
        if errors:
            error_msg = "Please fix the following errors:\n\n" + "\n".join(
                f"• {error}" for error in errors
            )
            show_colorful_error(ac, "Validation Error", error_msg)
            return

        # Prepare data for submission
        try:
            data = {
                "stk_code": stk_code_var.get().strip().upper(),
                "isin": isin_var.get().strip().upper(),
                "company_name": company_name_var.get().strip(),
                "short_name": short_name_var.get().strip(),
                "ticker": ticker_var.get().strip().upper(),  # <-- NEW FIELD
                "sector": sector_var.get().strip(),
                "face_value": float(face_value_var.get() or "10.0"),
                "tick": float(tick_var.get() or "0.01"),
                "is_active": 1 if is_active_var.get() else 0,
                "is_etf": 1 if is_etf_var.get() else 0,
            }

            # Call backend DB function
            success, message = add_company_db(
                data["stk_code"],
                data["isin"],
                data["company_name"],
                data["short_name"],
                data["ticker"],  # <-- NEW FIELD
                data["sector"],
                data["face_value"],
                data["tick"],
                data["is_active"],
                data["is_etf"],
            )

            if success:
                # Maintain a list of added companies
                # Avoid assigning attributes directly on a Tk object (Pylance
                # will warn). Use setattr/getattr to manage a session list of
                # added companies safely.
                if not hasattr(parent, "company_added_list"):
                    setattr(parent, "company_added_list", [])
                lst = getattr(parent, "company_added_list")
                lst.append(data["company_name"])

                yes = show_colorful_yesno(
                    ac,
                    "Success",
                    f"✅ {message}\n\nWould you like to add another company?",
                )
                if yes:
                    safe_close_modal(ac, parent, calling_button)
                    add_company(parent)
                else:
                    safe_close_modal(ac, parent, calling_button)
            else:
                show_colorful_error(ac, "Database Error", f"❌ {message}")

        except sqlite3.Error as e:
            # Database errors while inserting/updating
            logger.exception("Database error while adding company: %s", e)
            show_colorful_error(
                ac,
                "Database Error",
                f"An unexpected database error occurred:\n{e}",
            )
        except ValidationError as e:
            # Show friendly validation error mapped centrally
            show_validation_error(ac, e)
        except ValueError as e:
            # Conversion errors from float(...) calls etc.
            show_colorful_error(ac, "Validation Error", f"Invalid input: {e}")
        except Exception as e:  # noqa: E722 pylint: disable=broad-except
            # Intentionally broad fallback to protect the GUI from unexpected
            # errors raised during form submission. This is a deliberate UI
            # protection: the error is logged (with traceback) and a friendly
            # message is shown to the user. Keep this narrow and explicit.
            logger.exception("Unexpected error in add_company", exc_info=True)
            show_colorful_error(
                ac,
                "Error",
                f"An unexpected error occurred:\n{str(e)}",
            )

    # Button frame at bottom
    button_frame = tk.Frame(main_frame, bg=bg_color, pady=15)
    button_frame.pack(fill="x", side="bottom")

    # Stylish buttons with proper sizing
    submit_btn = tk.Button(
        button_frame,
        text="💾 Add Company",
        command=on_submit,
        font=("Helvetica", 14, "bold"),
        bg="#22c55e",
        fg="white",
        activebackground="#16a34a",
        activeforeground="white",
        relief="raised",
        bd=2,
        padx=25,
        pady=8,
        cursor="hand2",
    )
    submit_btn.pack(side="right", padx=(10, 20))
    apply_button_animations(submit_btn, "#22c55e", "#2563eb")

    clear_btn = tk.Button(
        button_frame,
        text="🔄 Clear All",
        command=clear_all_entries,
        font=("Helvetica", 14),
        bg="#ffa500",
        fg="white",
        relief="raised",
        bd=2,
        padx=25,
        pady=8,
        cursor="hand2",
    )
    clear_btn.pack(side="right", padx=10)

    cancel_btn = tk.Button(
        button_frame,
        text="❌ Cancel",
        command=lambda: safe_close_modal(ac, parent, calling_button),
        font=("Helvetica", 14),
        bg="#dc143c",
        fg="white",
        relief="raised",
        bd=2,
        padx=25,
        pady=8,
        cursor="hand2",
    )
    cancel_btn.pack(side="right", padx=10)

    # Help text
    help_frame = tk.Frame(button_frame, bg=bg_color)
    help_frame.pack(side="left", padx=20)

    help_text = tk.Label(
        help_frame,
        text=(
            "💡 Tips:\n"
            "• F1 for Help\n"
            "• F2 to see companies added in the session\n"
            "• ESC to close window"
        ),
        font=("Helvetica", 14, "bold"),
        fg="#1e3a8a",  # A blue shade for highlight
        bg=bg_color,
        justify="left",
        anchor="w",
        padx=8,
        pady=8,
    )
    help_text.pack(pady=(0, 30), anchor="nw")

    # Keyboard bindings
    ac.bind("<Return>", lambda event: on_submit())
    ac.bind(
        "<Escape>", lambda event: safe_close_modal(ac, parent, calling_button)
    )

    # Help text for F1 key
    help_text_content = (
        "🏢 Add Company Help\n\n"
        "Required Fields:\n"
        "• Stock Code: 2+ characters (auto-uppercase)\n"
        "• ISIN: 12 characters starting with 'IN' (auto-uppercase)\n"
        "• Company Name: 3+ characters\n"
        "• Short Name: 2+ characters\n\n"
        "Optional Fields:\n"
        "• Sector: Use dropdown or type new\n"
        "• Face Value: Default 10.0\n"
        "• Tick Size: Default 0.01\n"
        "• Is Active: Default Yes\n"
        "• Is ETF: Default No\n\n"
        "Keyboard Shortcuts:\n"
        "• Enter: Submit form\n"
        "• ESC: Close window\n"
        "• F1: Show this help"
    )

    def _show_help(_e=None):
        show_colorful_info(ac, "Help", help_text_content)

    ac.bind("<F1>", _show_help)

    # F2: Show companies added in current session
    def show_session_companies(_event=None):
        # Use getattr to obtain the per-parent session list (avoids Pylance
        # warnings about dynamic attributes on Tk objects)
        companies = getattr(parent, "company_added_list", [])
        if not companies:
            msg = "You have not yet added any company in the current session."
        else:
            bullet_lines = [f"• {name}" for name in companies]
            msg = "Companies added in this session:\n\n" + "\n".join(
                bullet_lines
            )
        show_colorful_info(ac, "Current Session Companies", msg)

    ac.bind("<F2>", show_session_companies)

    # Handle window close (X button)
    ac.protocol(
        "WM_DELETE_WINDOW",
        lambda: safe_close_modal(ac, parent, calling_button),
    )
    # Make window modal and wait
    parent.wait_window(ac)
    parent.grab_set()
