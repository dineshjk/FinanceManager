# -*- coding: utf-8 -*-
# File: C:\Data\Personal\Finance_and_Investment\finprog\FinanceManager\StockMan\company_update.py

"""Update company modal window.

This module shows the Update Company dialog and ensures it registers with
the central window stack (push_window / pop_window). It provides a unified
close handler to avoid double-pop/destroy races.
"""

import re
import sqlite3
import tkinter as tk
from tkinter import ttk
from typing import Optional, Union

from Shared.dialog_utils import show_colorful_info, show_colorful_error
from .validation_utils import ValidationError, show_validation_error
from Shared.gui_progressive import progressive_selection
from Shared.globals import get_db_connection, logger
from Shared.window_manager import push_window, pop_window, safe_close_modal
from Shared.modal_utils import disable_parent, enable_parent
from Shared.gui_utils import (
    apply_entry_theme,
    bind_tooltip,
    setup_footer_tooltip,
    apply_button_animations,
)


def update_company(
    parent: Union[tk.Tk, tk.Toplevel],
    calling_button: Optional[tk.Widget] = None,
) -> None:
    """Show the Update Company modal and handle update flow."""
    # --- Colors ---
    bg_color = "#f0f8ff"
    header_color = "#4682b4"
    label_color = "#2f4f4f"
    entry_bg = "#ffffff"
    required_color = "#dc143c"

    # Create modal and register
    modal_id = disable_parent(parent, calling_button=calling_button)
    uc = tk.Toplevel(parent)
    uc.title("\U0001f4dd Update Company")
    uc.geometry("1050x700")
    uc.resizable(True, True)
    uc.minsize(800, 600)
    uc.transient(parent)
    uc.grab_set()
    uc.focus_set()
    uc.configure(bg=bg_color)
    push_window(uc, parent)

    # Main layout
    main_frame = tk.Frame(uc, bg=bg_color)
    main_frame.pack(fill="both", expand=True, padx=20, pady=15)

    header_frame = tk.Frame(main_frame, bg=header_color, relief="raised", bd=2)
    header_frame.pack(fill="x", pady=(0, 20))
    header_label = tk.Label(
        header_frame,
        text="\U0001f4dd Update Company",
        font=("Helvetica", 18, "bold"),
        fg="white",
        bg=header_color,
        pady=10,
    )
    header_label.pack()
    subtitle_label = tk.Label(
        main_frame,
        text=(
            "Select a company to update. Edit details and "
            "click Update."  # wrapped for line length
        ),
        font=("Helvetica", 12, "italic"),
        fg=label_color,
        bg=bg_color,
    )
    subtitle_label.pack(pady=(0, 15))

    # Selection
    selection_frame = tk.Frame(main_frame, bg=bg_color)
    selection_frame.pack(fill="x", pady=(0, 20))
    tk.Label(
        selection_frame,
        text="Select Company:",
        font=("Helvetica", 13, "bold"),
        fg=label_color,
        bg=bg_color,
    ).pack(side="left", padx=(10, 5))
    company_var = tk.StringVar()
    company_combo = ttk.Combobox(
        selection_frame,
        textvariable=company_var,
        width=50,
        font=("Helvetica", 13),
    )
    company_combo.pack(side="left", padx=(0, 10))
    apply_entry_theme(company_combo)

    # Load companies
    company_map = {}
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT stk_code, company_name, isin, short_name, ticker, sector, "  # <-- added ticker
                "face_value, tick, is_active, is_etf FROM stocks "
                "ORDER BY company_name ASC"
            )
            companies = cursor.fetchall()
            for row in companies:
                display = f"{row[1]} ({row[0]})"
                company_map[display] = row
            company_combo["values"] = list(company_map.keys())
    except (sqlite3.Error, RuntimeError) as e:
        logger.warning("Could not fetch companies: %s", e)
        show_colorful_error(
            uc,
            "Database Error",
            f"Could not fetch companies: {e}",
        )

    progressive_selection(company_combo, list(company_map.keys()))
    uc.after(100, company_combo.focus_set)

    # Form (hidden until selection)
    form_frame = tk.Frame(main_frame, bg=bg_color)
    form_frame.pack(fill="both", expand=True, padx=10, pady=10)
    form_frame.pack_forget()

    # Vars
    stk_code_var = tk.StringVar()
    isin_var = tk.StringVar()
    company_name_var = tk.StringVar()
    short_name_var = tk.StringVar()
    sector_var = tk.StringVar()
    ticker_var = tk.StringVar()  # <-- NEW FIELD
    face_value_var = tk.StringVar()
    tick_var = tk.StringVar()
    is_active_var = tk.BooleanVar()
    is_etf_var = tk.BooleanVar()

    def create_label_entry_pair(
        parent_frame,
        row,
        col,
        label_text,
        var,
        width=25,
        is_required=True,
        widget_type="entry",
        values=None,
    ):
        req_text = " *" if is_required else ""
        label = tk.Label(
            parent_frame,
            text=f"{label_text}{req_text}",
            font=("Helvetica", 14, "bold"),
            fg=required_color if is_required else label_color,
            bg=bg_color,
            anchor="w",
        )
        label.grid(row=row, column=col * 2, sticky="nw", padx=(10, 5), pady=8)
        if widget_type == "entry":
            widget = tk.Entry(
                parent_frame,
                textvariable=var,
                width=width,
                font=("Helvetica", 14),
                bg=entry_bg,
                relief="solid",
                bd=1,
            )
        elif widget_type == "combobox":
            widget = ttk.Combobox(
                parent_frame,
                textvariable=var,
                width=width - 3,
                font=("Helvetica", 14),
                values=values or [],
            )
        elif widget_type == "checkbox":
            widget = tk.Checkbutton(
                parent_frame,
                variable=var,
                font=("Helvetica", 14),
                bg=bg_color,
                activebackground=bg_color,
                text="Yes",
            )
        else:
            widget = tk.Entry(
                parent_frame,
                textvariable=var,
                width=width,
                font=("Helvetica", 14),
                bg=entry_bg,
                relief="solid",
                bd=1,
            )
        widget.grid(
            row=row,
            column=col * 2 + 1,
            sticky="nw",
            padx=(5, 10),
            pady=8,
        )

        # Apply central theme strictly to input boxes, leaving labels untouched
        if widget_type in ("entry", "combobox"):
            apply_entry_theme(widget)
            # Force pitch-black background on standard entries to match combobox styling perfectly
            if widget_type == "entry":
                try:
                    widget.config(bg="black", readonlybackground="black")
                except tk.TclError:
                    pass

        return widget

    # Build form
    entries = {}

    def build_form():
        entries["stk_code"] = create_label_entry_pair(
            form_frame,
            0,
            0,
            "Stock Code",
            stk_code_var,
            width=15,
            is_required=True,
        )
        entries["isin"] = create_label_entry_pair(
            form_frame, 0, 1, "ISIN", isin_var, width=15, is_required=True
        )
        entries["company_name"] = create_label_entry_pair(
            form_frame,
            1,
            0,
            "Company Name",
            company_name_var,
            width=30,
            is_required=True,
        )
        entries["short_name"] = create_label_entry_pair(
            form_frame,
            1,
            1,
            "Short Name",
            short_name_var,
            width=20,
            is_required=True,
        )
        entries["sector"] = create_label_entry_pair(
            form_frame,
            2,
            0,
            "Sector",
            sector_var,
            width=25,
            is_required=False,
            widget_type="combobox",
            values=[],
        )
        entries["face_value"] = create_label_entry_pair(
            form_frame,
            2,
            1,
            "Face Value",
            face_value_var,
            width=15,
            is_required=False,
            widget_type="combobox",
            values=[],
        )
        entries["tick"] = create_label_entry_pair(
            form_frame,
            3,
            0,
            "Tick Size",
            tick_var,
            width=15,
            is_required=False,
        )
        entries["ticker"] = create_label_entry_pair(  # <-- NEW FIELD
            form_frame,
            3,
            1,
            "Ticker (e.g. INFY.NS)",
            ticker_var,
            width=20,
            is_required=False,
        )
        entries["is_active"] = create_label_entry_pair(
            form_frame,
            4,
            0,
            "Is Active",
            is_active_var,
            is_required=False,
            widget_type="checkbox",
        )
        entries["is_etf"] = create_label_entry_pair(
            form_frame,
            4,
            1,
            "Is ETF",
            is_etf_var,
            is_required=False,
            widget_type="checkbox",
        )

    # Fetch sector and face_value lists from DB, then augment
    # with common values
    sector_values = []
    face_value_values = []
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT DISTINCT sector FROM stocks "
                "WHERE sector != '' ORDER BY sector"
            )
            sector_values = [row[0] for row in cursor.fetchall()]
            cursor.execute(
                "SELECT DISTINCT face_value FROM stocks ORDER BY face_value"
            )
            face_value_values = [str(row[0]) for row in cursor.fetchall()]
    except (sqlite3.Error, RuntimeError) as e:
        logger.warning("Could not fetch sector/face values: %s", e)

    # Add common values if not present
    for s in [
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
    ]:
        if s not in sector_values:
            sector_values.append(s)
    for fv in ["1.0", "2.0", "5.0", "10.0", "100.0"]:
        if fv not in face_value_values:
            face_value_values.append(fv)
    face_value_values.sort(key=float)

    build_form()
    # Assign values to the comboboxes we just created
    try:
        if "sector" in entries and isinstance(entries["sector"], ttk.Combobox):
            entries["sector"]["values"] = sector_values
        if "face_value" in entries and isinstance(
            entries["face_value"], ttk.Combobox
        ):
            entries["face_value"]["values"] = face_value_values
    except (RuntimeError, tk.TclError, AttributeError):
        # non-fatal: continue without blocking the dialog
        pass
    # Wire progressive selection to the combobox widgets
    try:
        progressive_selection(entries.get("sector"), sector_values)
        progressive_selection(entries.get("face_value"), face_value_values)
    except (RuntimeError, AttributeError):
        # progressive selection is optional; don't block dialog on failure
        pass

    # --- Tooltip Setup ---
    # Initialize the centralized footer tooltip on the main window 'uc'
    tooltip_var = setup_footer_tooltip(
        uc, bg_color=bg_color, fg_color="#1e3a8a"
    )

    bind_tooltip(company_combo, tooltip_var, "Select a company to update.")
    bind_tooltip(
        entries["stk_code"],
        tooltip_var,
        "Update the stock code (min 2 characters).",
    )
    bind_tooltip(
        entries["isin"],
        tooltip_var,
        "Update ISIN (12 characters starting with 'IN').",
    )
    bind_tooltip(
        entries["company_name"], tooltip_var, "Update the full company name."
    )
    bind_tooltip(
        entries["short_name"],
        tooltip_var,
        "Update the short name or abbreviation.",
    )
    bind_tooltip(entries["sector"], tooltip_var, "Update the sector.")
    bind_tooltip(entries["face_value"], tooltip_var, "Update the face value.")
    bind_tooltip(
        entries["tick"],
        tooltip_var,
        "Update the minimum price movement (tick size).",
    )
    bind_tooltip(
        entries["ticker"],
        tooltip_var,
        "Update the exchange ticker symbol (e.g., INFY.NS).",
    )
    bind_tooltip(
        entries["is_active"],
        tooltip_var,
        "Check if the company is currently active.",
    )
    bind_tooltip(
        entries["is_etf"], tooltip_var, "Check if this asset is an ETF."
    )

    form_frame.pack_forget()

    # ISIN validation/transform (same behavior as add_company)
    def validate_and_transform_isin():
        """Convert ISIN to uppercase, strip invalid chars, and limit to 12.
        Also update the entry background to reflect validation state.
        """
        current = isin_var.get().upper()
        current = re.sub(r"[^A-Z0-9]", "", current)
        if len(current) > 12:
            current = current[:12]
        isin_var.set(current)

        isin_entry_widget = entries.get("isin")
        if not isin_entry_widget:
            return False

        # Dynamically fetch the safe dark theme background established by our engine
        try:
            safe_bg = isin_entry_widget.cget("readonlybackground")
        except tk.TclError:
            safe_bg = "black"

        if len(current) == 12:
            if not current.startswith("IN"):
                # Dark theme error state (Crimson Red with white text)
                isin_entry_widget.config(bg="#dc2626", fg="white")
                return False
            else:
                # Valid state (Restored to dark theme)
                isin_entry_widget.config(bg=safe_bg, fg="yellow")
                return True
        elif len(current) > 0:
            # Dark theme incomplete state (Amber with white text)
            isin_entry_widget.config(bg="#b45309", fg="white")
            return False
        else:
            # Empty state (Restored to dark theme)
            isin_entry_widget.config(bg=safe_bg, fg="yellow")
            return False

    # Bind ISIN trace so changes get normalized/validated as user types
    def _on_isin_trace(*_args):
        validate_and_transform_isin()

    isin_var.trace_add("write", _on_isin_trace)

    # Validation/transform for stock code - convert to uppercase as user types
    def validate_and_transform_stock_code():
        """Convert stock code to uppercase while typing."""
        current = stk_code_var.get()
        stk_code_var.set(current.upper())

    def _on_stk_trace(*_args):
        validate_and_transform_stock_code()

    stk_code_var.trace_add("write", _on_stk_trace)

    def validate_and_transform_ticker():
        """Convert ticker to uppercase while typing."""
        current = ticker_var.get()
        ticker_var.set(current.upper())

    def _on_ticker_trace(*_args):
        validate_and_transform_ticker()

    ticker_var.trace_add("write", _on_ticker_trace)

    def on_company_select(_event=None):
        name = company_var.get().strip()
        if name not in company_map:
            show_colorful_error(
                uc,
                "Selection Error",
                "Please select a valid company.",
            )
            return
        row = company_map[name]
        stk_code_var.set(row[0])
        company_name_var.set(row[1])
        isin_var.set(row[2])
        short_name_var.set(row[3])
        ticker_var.set(row[4] or "")  # <-- NEW FIELD (index 4)
        sector_var.set(row[5] or "")  # <-- SHIFTED to 5
        face_value_var.set(str(row[6]))  # <-- SHIFTED to 6
        tick_var.set(str(row[7]))  # <-- SHIFTED to 7
        is_active_var.set(bool(row[8]))  # <-- SHIFTED to 8
        is_etf_var.set(bool(row[9]))  # <-- SHIFTED to 9
        form_frame.pack(fill="both", expand=True, padx=10, pady=10)
        uc.after(100, entries["stk_code"].focus_set)
        company_combo.unbind("<Return>")
        uc.bind("<Return>", lambda event: on_update())

    company_combo.bind("<<ComboboxSelected>>", on_company_select)
    company_combo.bind("<Return>", on_company_select)

    def validate_form():
        errors = []
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

    def on_update():
        errors = validate_form()
        if errors:
            bullet_lines = "\n".join(f"\u2022 {error}" for error in errors)
            error_msg = "Please fix the following errors:\n\n" + bullet_lines
            show_colorful_error(
                uc,
                "Validation Error",
                error_msg,
            )
            return
        name = company_var.get().strip()
        if name not in company_map:
            show_colorful_error(
                uc,
                "Selection Error",
                "Please select a valid company.",
            )
            return
        row = company_map[name]
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    (
                        "SELECT COUNT(*) FROM stocks WHERE (stk_code = ? OR "
                        "isin = ?) AND stk_code != ?"
                    ),
                    (
                        stk_code_var.get().strip(),
                        isin_var.get().strip(),
                        row[0],
                    ),
                )
                if cursor.fetchone()[0] > 0:
                    show_colorful_error(
                        uc,
                        "Duplicate Error",
                        (
                            "Stock Code or ISIN already exists for "
                            "another company."
                        ),
                    )
                    return
                cursor.execute(
                    """
                    UPDATE stocks SET
                        stk_code = ?,
                        company_name = ?,
                        isin = ?,
                        short_name = ?,
                        ticker = ?,      -- <-- NEW FIELD
                        sector = ?,
                        face_value = ?,
                        tick = ?,
                        is_active = ?,
                        is_etf = ?
                    WHERE stk_code = ?
                """,
                    (
                        stk_code_var.get().strip(),
                        company_name_var.get().strip(),
                        isin_var.get().strip(),
                        short_name_var.get().strip(),
                        ticker_var.get().strip().upper(),  # <-- NEW FIELD
                        sector_var.get().strip(),
                        float(face_value_var.get() or "10.0"),
                        float(tick_var.get() or "0.01"),
                        1 if is_active_var.get() else 0,
                        1 if is_etf_var.get() else 0,
                        row[0],
                    ),
                )
                conn.commit()
            show_colorful_info(
                uc,
                "Success",
                f"\u2705 Company '{company_name_var.get()}' updated "
                "successfully.",
            )
            safe_close_modal(uc, parent, calling_button)
        except sqlite3.IntegrityError as e:
            # Map integrity constraint violations to a validation error
            show_validation_error(uc, ValidationError(f"Integrity error: {e}"))
            return
        except (sqlite3.Error, RuntimeError) as e:
            show_colorful_error(
                uc,
                "Database Error",
                f"Failed to update company: {e}",
            )

    # Buttons
    button_frame = tk.Frame(main_frame, bg=bg_color, pady=15)
    button_frame.pack(fill="x", side="bottom")
    update_btn = tk.Button(
        button_frame,
        text="\U0001f504 Update Data",
        command=on_update,
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
    update_btn.pack(side="right", padx=(10, 20))
    apply_button_animations(update_btn, "#22c55e", "#2563eb")

    def close_uc(event=None):
        return safe_close_modal(uc, parent, calling_button)

    cancel_btn = tk.Button(
        button_frame,
        text="\u274c Cancel",
        command=close_uc,
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

    uc.bind("<Escape>", close_uc)
    uc.protocol("WM_DELETE_WINDOW", close_uc)
    parent.wait_window(uc)
    try:
        if parent.winfo_exists():
            parent.grab_set()
    except tk.TclError:
        logger.debug("parent.grab_set skipped: parent destroyed.")


# File: C:\Data\Personal\Finance_and_Investment\finprog\FinanceManager\StockMan\company_update.py ends here
