# -*- coding: utf-8 -*-
# File: c:\Users\aumji\source\repos\Finance\FinanceManager\GUIStock\dbutils\company_utils.py


import sqlite3
import time
import tkinter as tk
from tkinter import messagebox
from typing import Tuple, List, Optional
import threading

# Import using new package structure
from FinanceManager.GUIStock.config import logger
from FinanceManager.GUIStock.config.globals import get_db_connection

# Import centralized modal management
from FinanceManager.GUIStock.dbutils.modal_management import disable_parent, enable_parent


# =====================================================
# CENTRALIZED MODAL WINDOW MANAGEMENT SYSTEM
# =====================================================


# --- GUI Bulk Entry Company ---


# --- GUI Bulk Entry Company ---
def bulk_entry_company(parent: tk.Tk) -> None:
    """GUI version: Bulk insert company data into the stocks table with progress UI."""
    # Tuple stock_code, company_name, short_name, isin, face_value, sector, is_active, is_etf, tick
    company_data = [
        ("ABFRL", "Aditya Birla Fashion & Retail Ltd", "Adi Birla Fashion", "INE647O01011", 10.0, "Consumer Durables", 1,0, 0.01),
        ("ADILIF", "Aditya Birla Lifestyle Brands Limited", "Adi Birla Lifestyle", "INE14LE01019", 10.0, "Retail", 1,0, 0.01),
        ("ADANIPORTS", "Adani Ports and Special Economic Zone Limited", "Adani Ports", "INE742F01042", 2.0, "Port & Port services", 1, 0, 0.1),
        ("DMART", "Avenue Supermarts Limited DMART", "Dmart", "INE192R01011", 10.0, "Consumer Durables", 1, 0, 0.1),
        ("BAJFINANCE", "Bajaj Finance Limited", "Bajaj Fin", "INE296A01024", 2.0, "Non Banking Financial Company (NBFC)", 1, 0, 0.5),
        ("BANKBARODA", "Bank of Baroda", "BoB", "INE028A01039", 2.0, "Banking", 1, 0, 0.01),
        ("BHEL", "Bharat Heavy Electricals Limited", "BHEL", "INE257A01026", 2.0, "Heavy Electrical Equipment", 1, 0, 0.01),
        ("COALINDIA", "Coal India Limited", "Coal India", "INE522F01014", 10.0, "Coal", 1, 0, 0.05),
        ("DEEPAKNTR", "Deepak Nitrite Limited", "Deepak Nitrite", "INE288B01029", 2.0, "Chemicals", 1, 0, 0.1),
        ("DIXTEC", "Dixon Technologies (India) Limited", "Dixon Tech", "INE935N01020", 2.0, "Consumer Durables", 1, 0, 1),
        ("ETERNAL(ZOMATO)", "Eternal Limited", "Zomato", "INE758T01015", 1.0, "E-Commerce/App based Aggregator", 1, 0, 0.01),
        ("GRWRHITECH", "Garware Hi-Tech Films Limited", "Garware Hi-Tech Films", "INE291A01017", 10.0, "Plastics", 1, 0, 0.1),
        ("HCLTECH", "HCL Technologies Limited", "HCL Tech", "INE860A01027", 2.0, "Software and Consultancy", 1, 0, 0.1),
        ("HAL", "Hindustan Aeronautics Limited", "HAL", "INE066F01012", 5.0, "Aerospace", 1, 0, 0.1),
        ("HDFC", "HDFC Bank Limited", "HDFC Bank", "INE040A01034", 1.0, "Banking", 1, 0, 0.1),
        ("HYUNDAI", "Hyundai Motor India Limited", "Hyundai Motor India", "INE0V6F01027", 10.0, "Automobile", 1, 0, 0.1),
        ("ICIBAN", "ICICI Bank Limited", "ICICI Bank", "INE090A01021", 2.0, "Banking", 1, 0, 0.1),
        ("BSE500IETF", "ICICI Prudential BSE 500 ETF", "IPru BSE 500 ETF", "INF109KC1V59", 1.0, "Finance ETF", 1, 1, 0.01),
        ("GOLDIETF", "ICICI Prudential Gold ETF", "IPru Gold ETF", "INF109KC1NT3", 1.0, "Gold ETF", 1, 1, 0.01),
        ("ISEC", "ICICI Securities Limited", "ISecure", "INE763G01038", 5.0, "Finance", 1, 0, 0.1),
        ("IOC", "Indian Oil Corporation Limited", "IOC", "INE242A01010", 10.0, "Refineries/Oil-Gas", 1, 0, 0.01),
        ("IREDA", "Indian Renewable Energy Development Agency Ltd", "IREDA", "INE202E01016", 10.0, "Finance", 1, 0, 0.01),
        ("INFY", "Infosys Ltd", "Infosys", "INE009A01021", 5.0, "IT", 1, 0, 0.1),
        ("IRB", "IRB Infrastructure Developers Limited", "IRB", "INE821I01022", 1.0, "Infrastructure", 1, 0, 0.01),
        ("ITC", "ITC Limited", "ITC", "INE154A01025", 1.0, "FMCG", 1, 0, 0.05),
        ("JUSTDIAL", "Just Dial Limited", "Just Dial", "INE599M01018", 10.0, "E-Commerce/App based Aggregator", 1, 0, 0.05),
        ("KOTAKBANK", "Kotak Mahindra Bank Ltd", "Kotak Mahindra Bank", "INE237A01028", 5.0, "Banking", 1, 0,0.1),
        ("KPIGREEN", "KPI Green Energy Limited", "KPI Green Energy", "INE542W01017", 5.0, "Power", 1, 0, 0.05),
        ("KPEL", "K.P. Energy Limited", "K.P. Energy", "INE127T01021", 5.0, "Power", 1, 0, 0.05),
        ("KSOLVES", "Ksolves India Limited", "Ksolves India", "INE0D6I01023", 5.0, "IT", 1, 0, 0.1),
        ("LT", "Larsen & Toubro Limited", "L & T", "INE018A01030", 2.0, "Infrastructure", 1, 0, 0.1),
        ("NDTV", "New Delhi Television Limited", "NDTV", "INE155G01029", 4.0, "Media", 1, 0, 0.01),
        ("NIFTYBEES", "Nippon ETF Nifty 50 Bees", "Nippon ETF Nif50 Bees", "INF204KB14I2", 1.0, "ETF", 1, 1, 0.01),
        ("ONGC", "Oil And Natural Gas Corporation", "ONGC", "INE213A01029", 5.0, "Refineries/Oil-Gas", 1, 0, 0.01),
        ("TATAPOWER", "Tata Power Company Limited", "Tata Power", "INE245A01021", 1.0, "Power/Generation/Distribution", 1, 0, 0.05),
        ("TATASTEEL", "Tata Steel Limited", "Tata Steel", "INE081A01020", 1.0, "Steel", 1, 0, 0.01),
        ("TECHM", "Tech Mahindra Limited", "Tech Mahindra", "INE669C01036", 5.0, "IT", 1, 0, 0.1),
        ("UNIONBANK", "Union Bank Of India", "Union Bank", "INE692A01016", 10.0, "Banking", 1, 0, 0.01),
        ("WAAREE", "Waaree Energies Limited", "Waaree Energies", "INE377N01017", 10.0, "Capital Goods", 1, 0, 0.1),
        ("WIPRO", "Wipro Ltd", "Wipro", "INE075A01022", 2.0, "IT", 1, 0,0.01),
    ]

    win = tk.Toplevel(parent)
    win.title("Bulk Entry Company")
    win.geometry("500x200")
    win.resizable(False, False)
    win.transient(parent)
    win.grab_set()

    status_label = tk.Label(win, text="Starting bulk entry...", font=("Helvetica", 12))
    status_label.pack(pady=20)
    progress = tk.DoubleVar(value=0)
    progress_bar = tk.Scale(win, variable=progress, from_=0, to=len(company_data), orient="horizontal", length=400, showvalue=0, state="disabled")
    progress_bar.pack(pady=10)

    def do_bulk_entry():

        added_count = 0
        skipped_count = 0
        logger.info("Starting bulk entry of companies. Total: %d", len(company_data))
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                for idx, (code, name, short, isin, fv, sector, active, isetf, tick) in enumerate(company_data, 1):
                    logger.debug("Processing company #%d: %s (%s)", idx, name, code)
                    cur.execute("SELECT 1 FROM stocks WHERE stk_code = ? OR isin = ?", (code, isin))
                    if cur.fetchone():
                        skipped_count += 1
                        msg = f"⚠️ Skipping {name}: already exists."
                        logger.info("Skipped company: %s (%s), already exists.", name, code)
                    else:
                        cur.execute("""
                            INSERT INTO stocks (stk_code, company_name, short_name, isin, face_value, sector, is_active, is_etf, tick)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (code, name, short, isin, fv, sector, active, isetf, tick))
                        added_count += 1
                        msg = f"✅ Added {name}."
                        logger.info("Added company: %s (%s)", name, code)
                    win.after(0, status_label.config, {"text": f"{msg}\n{added_count} added, {skipped_count} skipped."})
                    win.after(0, progress.set, idx)
                    time.sleep(0.05)
                conn.commit()
                logger.info("Bulk entry complete. Added: %d, Skipped: %d", added_count, skipped_count)
        except Exception as e:
            logger.error("Error during bulk entry: %s", e, exc_info=True)
            win.after(0, status_label.config, {"text": f"❌ Error: {e}"})
        finally:
            win.after(500, lambda: (win.grab_release(), win.destroy()))
            parent.after(600, lambda: messagebox.showinfo("Bulk Entry Complete", f"Added: {added_count}\nSkipped: {skipped_count}", parent=parent))

    threading.Thread(target=do_bulk_entry, daemon=True).start()




def add_company_db(
    stk_code: str,
    isin: str,
    company_name: str,
    short_name: str = '',
    sector: str = '',
    face_value: float = 10.0,
    tick: float = 0.01,
    is_active: int = 1,
    is_etf: int = 0
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
                    stk_code, isin, company_name, short_name, sector, face_value, tick, is_active, is_etf
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    stk_code, isin, company_name, short_name, sector, face_value, tick, is_active, is_etf
                )
            )
            conn.commit()
        logger.info("Added company: %s (%s)", company_name, stk_code)
        return True, f"Company '{company_name}' added successfully."
    except sqlite3.IntegrityError as e:
        logger.warning("Integrity error adding company: %s (%s): %s", company_name, stk_code, e)
        return False, f"Integrity error: {e}"
    except Exception as e:
        logger.error("Error adding company: %s (%s): %s", company_name, stk_code, e, exc_info=True)
        return False, f"Error: {e}"



def add_company(parent: 'tk.Tk', calling_button: tk.Widget = None) -> None:
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
    # Use centralized modal window management
    modal_id = disable_parent(parent, calling_button=calling_button)

    from tkinter import ttk
    import re

    # Dual import handling for dialogs
    try:
        from GUIStock.dialogs import show_colorful_info, show_colorful_error
        from GUIStock.dialogs.sizing import calculate_dialog_size
    except ImportError:
        from dialogs import show_colorful_info, show_colorful_error
        from dialogs.sizing import calculate_dialog_size

    # Calculate dynamic window size
    message_text = "Add New Company\nPlease fill in all required fields\nStock Code, ISIN, Company Name, Short Name, Sector, Face Value, Is Active, Is ETF"
    base_width, base_height = calculate_dialog_size(
        message_text,
        title="Add New Company"
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

    header_label = tk.Label(header_frame, text="🏢 Add New Company",
                           font=("Helvetica", 18, "bold"),
                           fg="white", bg=header_color, pady=10)
    header_label.pack()

    subtitle_label = tk.Label(main_frame, text="Please fill in all required fields marked with *",
                             font=("Helvetica", 12, "italic"),
                             fg=label_color, bg=bg_color)
    subtitle_label.pack(pady=(0, 15))

    # Form fields container - Simple 2 columns layout (NO CANVAS)
    form_frame = tk.Frame(main_frame, bg=bg_color)
    form_frame.pack(fill="both", expand=True, padx=10, pady=10)

    # Configure grid weights for proper resizing
    form_frame.grid_columnconfigure(1, weight=1)
    form_frame.grid_columnconfigure(3, weight=1)    # Variables for form fields
    stk_code_var = tk.StringVar()
    isin_var = tk.StringVar()
    company_name_var = tk.StringVar()
    short_name_var = tk.StringVar()
    sector_var = tk.StringVar()
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
            cursor.execute("SELECT DISTINCT sector FROM stocks WHERE sector != '' ORDER BY sector")
            existing_sectors = [row[0] for row in cursor.fetchall()]
            # Get unique face values
            cursor.execute("SELECT DISTINCT face_value FROM stocks ORDER BY face_value")
            existing_face_values = [str(row[0]) for row in cursor.fetchall()]
            cursor.close()
    except Exception as e:
        logger.warning(f"Could not fetch existing data: {e}")

    # Add common sectors if not in database
    common_sectors = ["Banking", "IT", "Pharma", "Auto", "FMCG", "Energy", "Metals",
                     "Telecom", "Media", "Realty", "Capital Goods", "Consumer Durables"]
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

    def create_label_entry_pair(parent_frame, row, col, label_text, var, width=25,
                               is_required=True, widget_type="entry", values=None):
        """Helper function to create consistent label-entry pairs"""
        # Required asterisk
        req_text = " *" if is_required else ""

        # Label directly in grid
        label = tk.Label(parent_frame, text=f"{label_text}{req_text}",
                        font=("Helvetica", 14, "bold"),
                        fg=required_color if is_required else label_color,
                        bg=bg_color, anchor="w")
        label.grid(row=row, column=col*2, sticky="nw", padx=(10, 5), pady=8)

        # Widget directly in grid
        if widget_type == "entry":
            widget = tk.Entry(parent_frame, textvariable=var, width=width,
                            font=("Helvetica", 14), bg=entry_bg, relief="solid", bd=1)
        elif widget_type == "combobox":
            widget = ttk.Combobox(parent_frame, textvariable=var, width=width-3,
                                font=("Helvetica", 14), values=values or [])
        elif widget_type == "checkbox":
            widget = tk.Checkbutton(parent_frame, variable=var,
                                  font=("Helvetica", 14), bg=bg_color,
                                  activebackground=bg_color, text="Yes")

        widget.grid(row=row, column=col*2+1, sticky="nw", padx=(5, 10), pady=8)
        return widget

    # Row 0: Stock Code and ISIN
    stk_code_entry = create_label_entry_pair(form_frame, 0, 0, "Stock Code",
                                           stk_code_var, width=15, is_required=True)
    isin_entry = create_label_entry_pair(form_frame, 0, 1, "ISIN",
                                       isin_var, width=15, is_required=True)

    # Row 1: Company Name and Short Name
    company_entry = create_label_entry_pair(form_frame, 1, 0, "Company Name",
                                          company_name_var, width=30, is_required=True)
    short_name_entry = create_label_entry_pair(form_frame, 1, 1, "Short Name",
                                             short_name_var, width=20, is_required=True)

    # Row 2: Sector and Face Value (with progressive search)
    sector_combo = create_label_entry_pair(form_frame, 2, 0, "Sector", sector_var,
                                         width=25, is_required=False,
                                         widget_type="combobox", values=existing_sectors)
    face_value_combo = create_label_entry_pair(form_frame, 2, 1, "Face Value", face_value_var,
                                             width=15, is_required=False,
                                             widget_type="combobox", values=existing_face_values)

    # Row 3: Tick Size and spacer
    tick_entry = create_label_entry_pair(form_frame, 3, 0, "Tick Size", tick_var,
                                       width=15, is_required=False)

    # Row 4: Checkboxes for Is Active and Is ETF
    is_active_check = create_label_entry_pair(form_frame, 4, 0, "Is Active", is_active_var,
                                            is_required=False, widget_type="checkbox")
    is_etf_check = create_label_entry_pair(form_frame, 4, 1, "Is ETF", is_etf_var,
                                         is_required=False, widget_type="checkbox")

    # Store entries for easy access
    entries.update({
        'stk_code': stk_code_entry,
        'isin': isin_entry,
        'company_name': company_entry,
        'short_name': short_name_entry,
        'sector': sector_combo,
        'face_value': face_value_combo,
        'tick': tick_entry,
        'is_active': is_active_check,
        'is_etf': is_etf_check
    })

    # Set default values
    face_value_var.set("10.0")
    tick_var.set("0.01")

    # Focus on first field
    stk_code_entry.focus_set()

    # Validation and transformation functions
    def validate_and_transform_stock_code(event=None):
        """Convert stock code to uppercase"""
        current = stk_code_var.get()
        stk_code_var.set(current.upper())

    def validate_and_transform_isin(event=None):
        """Convert ISIN to uppercase and validate format"""
        current = isin_var.get().upper()
        # Remove any non-alphanumeric characters except those needed
        current = re.sub(r'[^A-Z0-9]', '', current)
        # Limit to 12 characters
        if len(current) > 12:
            current = current[:12]
        isin_var.set(current)

        # Validate format
        if len(current) == 12:
            if not current.startswith('IN'):
                isin_entry.configure(bg="#ffcccc")  # Light red for invalid
                return False
            else:
                isin_entry.configure(bg=entry_bg)  # Reset to normal
                return True
        elif len(current) > 0:
            isin_entry.configure(bg="#fff8dc")  # Light yellow for incomplete
            return False
        else:
            isin_entry.configure(bg=entry_bg)
            return False

    def setup_progressive_search(combobox, values_list):
        """Setup simple autocomplete functionality for combobox"""

        # Store original values and state
        combobox._original_values = values_list
        combobox['values'] = values_list
        combobox._ignore_next_event = False
        combobox._user_typing = False

        def on_key_release(event):
            """Handle key release for autocomplete with improved logic"""
            # Skip if we should ignore this event
            if getattr(combobox, '_ignore_next_event', False):
                combobox._ignore_next_event = False
                return

            # Skip navigation and special keys
            if event.keysym in ['Up', 'Down', 'Left', 'Right', 'Tab',
                               'Return', 'Escape']:
                if event.keysym == 'Escape':
                    combobox.set('')
                    combobox['values'] = values_list
                    combobox._user_typing = False
                return

            # Handle backspace and delete - don't auto-complete
            if event.keysym in ['BackSpace', 'Delete']:
                current = combobox.get()
                combobox._user_typing = True
                if not current:
                    combobox['values'] = values_list
                else:
                    # Just filter, don't auto-complete
                    matches = [item for item in values_list
                              if item.lower().startswith(current.lower())]
                    combobox['values'] = matches
                return

            # Get current text
            current = combobox.get()
            if not current:
                combobox['values'] = values_list
                combobox._user_typing = False
                return

            # Mark that user is actively typing
            combobox._user_typing = True

            # Find matching values (case insensitive)
            matches = [item for item in values_list
                      if item.lower().startswith(current.lower())]

            # Update dropdown values
            combobox['values'] = matches

            # Only auto-complete if we have matches and cursor is at end
            if matches and len(current) > 0:
                cursor_pos = combobox.index(tk.INSERT)

                # Only auto-complete if cursor is at the end (user typing forward)
                if cursor_pos == len(current):
                    first_match = matches[0]

                    # Set ignore flag to prevent recursive triggering
                    combobox._ignore_next_event = True
                    combobox.set(first_match)

                    # Select the auto-completed part
                    combobox.select_range(cursor_pos, len(first_match))
                    combobox.icursor(cursor_pos)

        # Bind the event
        combobox.bind('<KeyRelease>', on_key_release)

    def clear_all_entries(event=None):
        """Clear all entry fields when ESC is pressed"""
        for var in [stk_code_var, isin_var, company_name_var, short_name_var,
                   sector_var, face_value_var, tick_var]:
            var.set('')
        is_active_var.set(True)
        is_etf_var.set(False)
        face_value_var.set("10.0")
        tick_var.set("0.01")
        stk_code_entry.focus_set()

    # Bind validation events
    stk_code_var.trace_add('write', lambda *args: validate_and_transform_stock_code())
    isin_var.trace_add('write', lambda *args: validate_and_transform_isin())

    # Setup progressive search for comboboxes
    setup_progressive_search(sector_combo, existing_sectors)
    setup_progressive_search(face_value_combo, existing_face_values)

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
        elif not isin.startswith('IN'):
            errors.append("ISIN must start with 'IN'")
        elif not re.match(r'^IN[A-Z0-9]{10}$', isin):
            errors.append("ISIN must be 'IN' followed by 10 alphanumeric characters")

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
            error_msg = "Please fix the following errors:\n\n" + "\n".join(f"• {error}" for error in errors)
            show_colorful_error(ac, "Validation Error", error_msg)
            return

        # Prepare data for submission
        try:
            data = {
                'stk_code': stk_code_var.get().strip().upper(),
                'isin': isin_var.get().strip().upper(),
                'company_name': company_name_var.get().strip(),
                'short_name': short_name_var.get().strip(),
                'sector': sector_var.get().strip(),
                'face_value': float(face_value_var.get() or "10.0"),
                'tick': float(tick_var.get() or "0.01"),
                'is_active': 1 if is_active_var.get() else 0,
                'is_etf': 1 if is_etf_var.get() else 0
            }

            # Call backend DB function
            success, message = add_company_db(
                data['stk_code'], data['isin'], data['company_name'],
                data['short_name'], data['sector'], data['face_value'],
                data['tick'], data['is_active'], data['is_etf']
            )

            if success:
                show_colorful_info(ac, "Success", f"✅ {message}")
                enable_parent(modal_id)
                ac.destroy()
            else:
                show_colorful_error(ac, "Database Error", f"❌ {message}")

        except Exception as e:
            show_colorful_error(ac, "Error", f"An unexpected error occurred:\n{str(e)}")

    # Button frame at bottom
    button_frame = tk.Frame(main_frame, bg=bg_color, pady=15)
    button_frame.pack(fill="x", side="bottom")

    # Stylish buttons with proper sizing
    submit_btn = tk.Button(button_frame, text="💾 Add Company",
                          command=on_submit, font=("Helvetica", 14, "bold"),
                          bg="#32cd32", fg="white", relief="raised", bd=2,
                          padx=25, pady=8, cursor="hand2")
    submit_btn.pack(side="right", padx=(10, 20))

    clear_btn = tk.Button(button_frame, text="🔄 Clear All",
                         command=clear_all_entries, font=("Helvetica", 14),
                         bg="#ffa500", fg="white", relief="raised", bd=2,
                         padx=25, pady=8, cursor="hand2")
    clear_btn.pack(side="right", padx=10)

    cancel_btn = tk.Button(button_frame, text="❌ Cancel",
                          command=lambda: (enable_parent(modal_id), ac.destroy()),
                          font=("Helvetica", 14),
                          bg="#dc143c", fg="white", relief="raised", bd=2,
                          padx=25, pady=8, cursor="hand2")
    cancel_btn.pack(side="right", padx=10)

    # Help text
    help_frame = tk.Frame(button_frame, bg=bg_color)
    help_frame.pack(side="left", padx=20)

    help_text = tk.Label(help_frame,
                        text="💡 Tips: ESC to clear all • Progressive search in dropdowns • ISIN auto-uppercase",
                        font=("Helvetica", 10, "italic"), fg=label_color, bg=bg_color)
    help_text.pack()

    # Keyboard bindings
    ac.bind('<Return>', lambda event: on_submit())
    ac.bind('<Escape>', clear_all_entries)
    ac.bind('<F1>', lambda e: show_colorful_info("Help",
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
        "• ESC: Clear all fields\n"
        "• F1: Show this help", ac))

    # Handle window close (X button)
    def on_close():
        enable_parent(modal_id)
        ac.destroy()

    ac.protocol("WM_DELETE_WINDOW", on_close)

    # Make window modal and wait
    ac.wait_window(ac)


def update_company(parent: tk.Tk, calling_button: tk.Widget = None) -> None:
    """
    Update company information with progressive search dropdown for company selection.

    Creates a window with:
    1. Progressive search dropdown to select a company
    2. Form displaying all company fields for editing
    3. Submit button to update the database

    Args:
        parent (tk.Tk): The parent window to which the modal is attached.
        calling_button (tk.Widget): The button that called this function (for focus restoration).

    Side Effects:
        - Displays a modal window for company selection and editing
        - Updates company data in the database
        - Returns to the company menu after successful update
        - Restores focus to the next button after the calling button
    """
    # Use centralized modal window management
    modal_id = disable_parent(parent, calling_button=calling_button)

    # Create update window
    update_win = tk.Toplevel(parent)
    update_win.title("Update Company")
    update_win.geometry("800x700")
    update_win.resizable(False, False)
    update_win.configure(bg="#f0f8ff")
    update_win.transient(parent)
    update_win.grab_set()

    # Header
    header_frame = tk.Frame(update_win, bg="#1e3a8a", relief="raised", bd=3)
    header_frame.pack(fill="x", padx=5, pady=5)

    title_label = tk.Label(header_frame, text="📝 UPDATE COMPANY 📝",
                          font=("Comic Sans MS", 18, "bold"),
                          bg="#1e3a8a", fg="#ffd700", pady=8)
    title_label.pack()

    # Main content frame
    main_frame = tk.Frame(update_win, bg="#f0f8ff", padx=20, pady=20)
    main_frame.pack(fill="both", expand=True)

    # Company selection frame
    selection_frame = tk.LabelFrame(main_frame, text="Select Company to Update",
                                   font=("Arial", 12, "bold"),
                                   bg="#e0f2fe", fg="#1e293b",
                                   relief="groove", bd=2, padx=10, pady=10)
    selection_frame.pack(fill="x", pady=(0, 20))

    # Get all companies from database
    companies = []
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id_stk, stk_code, company_name, short_name, isin,
                       face_value, sector, is_active, is_etf, tick
                FROM stocks
                ORDER BY company_name ASC
            """)
            companies = cursor.fetchall()
    except Exception as e:
        messagebox.showerror("Database Error", f"Failed to fetch companies: {str(e)}")
        enable_parent(modal_id)
        update_win.destroy()
        return

    if not companies:
        messagebox.showinfo("No Companies", "No companies found in database.")
        enable_parent(modal_id)
        update_win.destroy()
        return

    # Progressive search dropdown
    tk.Label(selection_frame, text="Search Company:",
             font=("Arial", 10, "bold"), bg="#e0f2fe").pack(anchor="w")

    from tkinter import ttk

    company_var = tk.StringVar()
    company_dropdown = ttk.Combobox(selection_frame, textvariable=company_var,
                                   width=70, font=("Arial", 10))

    # Populate dropdown with company names
    company_names = [f"{comp[2]} ({comp[1]})" for comp in companies]
    company_dropdown['values'] = company_names
    company_dropdown.pack(pady=5)

    # Dictionary to map display names to company data
    company_map = {f"{comp[2]} ({comp[1]})": comp for comp in companies}

    # Form fields frame (initially hidden)
    form_frame = tk.LabelFrame(main_frame, text="Company Details",
                              font=("Arial", 12, "bold"),
                              bg="#fef3c7", fg="#1e293b",
                              relief="groove", bd=2, padx=15, pady=15)

    # Form variables
    form_vars = {}
    form_entries = {}

    def create_form_fields():
        """Create form fields for company data editing."""
        # Clear existing widgets
        for widget in form_frame.winfo_children():
            widget.destroy()

        fields = [
            ("Stock Code", "stk_code", 1),
            ("Company Name", "company_name", 2),
            ("Short Name", "short_name", 3),
            ("ISIN", "isin", 4),
            ("Face Value", "face_value", 5),
            ("Sector", "sector", 6),
            ("Tick Size", "tick", 9)
        ]

        # Create form variables
        for label, field, idx in fields:
            form_vars[field] = tk.StringVar()

        # Boolean fields
        form_vars["is_active"] = tk.BooleanVar()
        form_vars["is_etf"] = tk.BooleanVar()

        # Create form layout
        row = 0
        for label, field, idx in fields:
            tk.Label(form_frame, text=f"{label}:",
                    font=("Arial", 10, "bold"),
                    bg="#fef3c7", anchor="w").grid(row=row, column=0,
                                                  sticky="w", padx=5, pady=5)

            if field == "sector":
                # Dropdown for sector
                sector_dropdown = ttk.Combobox(form_frame, textvariable=form_vars[field],
                                             width=40, font=("Arial", 10))
                sectors = ["Banking", "IT", "Automobile", "Pharmaceuticals",
                          "Chemicals", "Finance", "Retail", "Infrastructure",
                          "Consumer Durables", "Oil & Gas", "Metals", "Textiles",
                          "Telecommunications", "Power", "Real Estate", "Others"]
                sector_dropdown['values'] = sectors
                sector_dropdown.grid(row=row, column=1, sticky="w", padx=5, pady=5)
                form_entries[field] = sector_dropdown
            else:
                entry = tk.Entry(form_frame, textvariable=form_vars[field],
                               width=45, font=("Arial", 10))
                entry.grid(row=row, column=1, sticky="w", padx=5, pady=5)
                form_entries[field] = entry
            row += 1

        # Boolean checkboxes
        tk.Label(form_frame, text="Status:",
                font=("Arial", 10, "bold"),
                bg="#fef3c7", anchor="w").grid(row=row, column=0,
                                              sticky="w", padx=5, pady=5)

        checkbox_frame = tk.Frame(form_frame, bg="#fef3c7")
        checkbox_frame.grid(row=row, column=1, sticky="w", padx=5, pady=5)

        active_check = tk.Checkbutton(checkbox_frame, text="Active",
                                     variable=form_vars["is_active"],
                                     bg="#fef3c7", font=("Arial", 10))
        active_check.pack(side="left", padx=(0, 20))

        etf_check = tk.Checkbutton(checkbox_frame, text="ETF",
                                  variable=form_vars["is_etf"],
                                  bg="#fef3c7", font=("Arial", 10))
        etf_check.pack(side="left")

        form_entries["is_active"] = active_check
        form_entries["is_etf"] = etf_check

    def on_company_select(event=None):
        """Handle company selection from dropdown."""
        selected_name = company_var.get().strip()
        print(f"DEBUG: on_company_select called with: '{selected_name}'")
        print(f"DEBUG: Available companies: {list(company_map.keys())[:3]}...")  # Show first 3

        # Check exact match first
        if selected_name in company_map:
            print(f"DEBUG: Exact match found for '{selected_name}'")
            company_data = company_map[selected_name]
        else:
            # Try to find partial match (in case of autocomplete issues)
            matches = [name for name in company_map.keys()
                      if name.lower().startswith(selected_name.lower())]
            if matches:
                print(f"DEBUG: Partial match found: '{matches[0]}' for '{selected_name}'")
                selected_name = matches[0]
                company_var.set(selected_name)  # Update the display
                company_data = company_map[selected_name]
            else:
                print(f"DEBUG: No match found for '{selected_name}'")
                return

        print(f"DEBUG: Selected company data: {company_data[1]} - {company_data[2]}")

        # Show form frame
        form_frame.pack(fill="both", expand=True, pady=(20, 0))

        # Create form if not exists
        if not form_vars:
            create_form_fields()

        # Populate form with selected company data
        form_vars["stk_code"].set(company_data[1])
        form_vars["company_name"].set(company_data[2])
        form_vars["short_name"].set(company_data[3])
        form_vars["isin"].set(company_data[4])
        form_vars["face_value"].set(str(company_data[5]))
        form_vars["sector"].set(company_data[6] if company_data[6] else "")
        form_vars["is_active"].set(bool(company_data[7]))
        form_vars["is_etf"].set(bool(company_data[8]))
        form_vars["tick"].set(str(company_data[9]))

        # Store selected company ID for update
        update_win.selected_company_id = company_data[0]
        print(f"DEBUG: Stored company ID: {update_win.selected_company_id}")

    def on_submit():
        """Handle form submission to update company data."""
        print("DEBUG: Submit clicked")

        # First try to trigger manual selection if no company is selected yet
        if not hasattr(update_win, 'selected_company_id'):
            print("DEBUG: No company selected yet - trying manual selection")
            manual_select_company()

        print(f"DEBUG: Has selected_company_id: {hasattr(update_win, 'selected_company_id')}")
        if hasattr(update_win, 'selected_company_id'):
            print(f"DEBUG: Selected company ID: {update_win.selected_company_id}")

        if not hasattr(update_win, 'selected_company_id'):
            messagebox.showerror("Error", "Please select a company to update.")
            return

        # Validate required fields
        required_fields = ['stk_code', 'company_name', 'short_name', 'isin']
        for field in required_fields:
            if not form_vars[field].get().strip():
                messagebox.showerror("Validation Error",
                                   f"{field.replace('_', ' ').title()} is required.")
                return

        # Validate face value and tick as numbers
        try:
            face_value = float(form_vars["face_value"].get())
            tick = float(form_vars["tick"].get())
        except ValueError:
            messagebox.showerror("Validation Error",
                               "Face Value and Tick Size must be valid numbers.")
            return

        # Validate ISIN format
        isin = form_vars["isin"].get().strip()
        if len(isin) != 12 or not isin.startswith("IN"):
            messagebox.showerror("Validation Error",
                               "ISIN must be 12 characters long and start with 'IN'.")
            return

        # Update company in database
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()

                # Check for duplicate stock code/ISIN (excluding current company)
                cursor.execute("""
                    SELECT COUNT(*) FROM stocks
                    WHERE (stk_code = ? OR isin = ?) AND id_stk != ?
                """, (form_vars["stk_code"].get().strip(), isin,
                      update_win.selected_company_id))

                if cursor.fetchone()[0] > 0:
                    messagebox.showerror("Duplicate Error",
                                       "Stock Code or ISIN already exists for another company.")
                    return

                # Update the company
                cursor.execute("""
                    UPDATE stocks SET
                        stk_code = ?, company_name = ?, short_name = ?, isin = ?,
                        face_value = ?, sector = ?, is_active = ?, is_etf = ?, tick = ?
                    WHERE id_stk = ?
                """, (
                    form_vars["stk_code"].get().strip(),
                    form_vars["company_name"].get().strip(),
                    form_vars["short_name"].get().strip(),
                    isin,
                    face_value,
                    form_vars["sector"].get().strip(),
                    1 if form_vars["is_active"].get() else 0,
                    1 if form_vars["is_etf"].get() else 0,
                    tick,
                    update_win.selected_company_id
                ))

                conn.commit()

                messagebox.showinfo("Success",
                                  f"Company '{form_vars['company_name'].get()}' updated successfully!")

                cleanup_and_close()

        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to update company: {str(e)}")

    # Track if focus restoration has been handled
    focus_restored = False

    def cleanup_and_close():
        """Clean up and close the window with proper focus restoration."""
        nonlocal focus_restored
        if not focus_restored:
            print("DEBUG: cleanup_and_close - performing focus restoration")
            focus_restored = True
            # Use centralized modal window management BEFORE destroying window
            enable_parent(modal_id)
            update_win.destroy()
        else:
            print("DEBUG: cleanup_and_close - focus already restored, just destroying window")
            update_win.destroy()

    # Bind company selection event
    company_dropdown.bind('<<ComboboxSelected>>', on_company_select)

    # Enable progressive search with improved debugging
    company_dropdown._ignore_next_event = False
    company_dropdown._user_typing = False

    def on_key_release(event):
        """Handle key release for autocomplete with debugging"""
        print(f"DEBUG: Key released: {event.keysym}, Current text: '{company_dropdown.get()}', Cursor pos: {company_dropdown.index(tk.INSERT)}")

        # Skip if we should ignore this event (but only for specific keys)
        if getattr(company_dropdown, '_ignore_next_event', False):
            print("DEBUG: Ignoring event due to flag")
            company_dropdown._ignore_next_event = False
            # Never ignore Enter key - it should always trigger manual selection
            if event.keysym == 'Return':
                print("DEBUG: Enter key - processing despite flag")
                # Continue processing the Enter key
            # Only ignore if it's not a regular typing key or Enter
            elif event.keysym not in ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm',
                                     'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z',
                                     'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M',
                                     'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z',
                                     '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'space']:
                print("DEBUG: Non-typing key - really ignoring")
                return
            else:
                print("DEBUG: Typing key - processing despite flag")

        # Skip navigation and special keys
        if event.keysym in ['Up', 'Down', 'Left', 'Right', 'Tab', 'Return', 'Escape']:
            if event.keysym == 'Escape':
                print("DEBUG: Escape pressed - clearing dropdown")
                company_dropdown.set('')
                company_dropdown['values'] = company_names
                company_dropdown._user_typing = False
            elif event.keysym == 'Return':
                # Manual selection trigger on Enter
                print("DEBUG: Enter pressed - triggering manual selection")
                manual_select_company()
            return

        # Handle backspace and delete - don't auto-complete
        if event.keysym in ['BackSpace', 'Delete']:
            current = company_dropdown.get()
            print(f"DEBUG: Backspace/Delete - text now: '{current}'")
            company_dropdown._user_typing = True
            if not current:
                company_dropdown['values'] = company_names
            else:
                # Just filter, don't auto-complete
                matches = [item for item in company_names
                          if item.lower().startswith(current.lower())]
                company_dropdown['values'] = matches
                print(f"DEBUG: Filtered to {len(matches)} matches")
            return

        # Get current text
        current = company_dropdown.get()
        print(f"DEBUG: Processing normal key, current text: '{current}'")

        if not current:
            company_dropdown['values'] = company_names
            company_dropdown._user_typing = False
            return

        # Mark that user is actively typing
        company_dropdown._user_typing = True

        # Find matching values (case insensitive) - maintain original order
        matches = [item for item in company_names
                  if item.lower().startswith(current.lower())]

        print(f"DEBUG: Found {len(matches)} matches for '{current}'")
        if matches:
            print(f"DEBUG: First few matches: {matches[:3]}")
        else:
            print("DEBUG: No matches found")

        # Update dropdown values
        company_dropdown['values'] = matches

        # Only auto-complete if we have matches and user typed a real character
        if matches and len(current) > 0 and event.keysym not in ['space']:
            cursor_pos = company_dropdown.index(tk.INSERT)
            print(f"DEBUG: Cursor at position {cursor_pos}, text length {len(current)}")

            # Auto-complete on EVERY character as long as cursor is at the end
            if cursor_pos == len(current):
                # Use the first match from the filtered list
                first_match = matches[0]
                print(f"DEBUG: Auto-completing to '{first_match}' (from {len(matches)} filtered matches)")

                # Set ignore flag to prevent recursive triggering - but only for next non-typing event
                company_dropdown._ignore_next_event = True
                company_dropdown.set(first_match)

                # Select the auto-completed part
                company_dropdown.select_range(cursor_pos, len(first_match))
                company_dropdown.icursor(cursor_pos)
                print(f"DEBUG: Selected range {cursor_pos} to {len(first_match)}")
            else:
                print("DEBUG: Not auto-completing - cursor not at end")
        else:
            print(f"DEBUG: Not auto-completing - matches: {len(matches) if matches else 0}, current: '{current}', keysym: {event.keysym}")

    def on_combobox_select(event):
        """Handle explicit combobox selection - only when user manually selects"""
        selected = company_dropdown.get()
        print(f"DEBUG: Combobox selection event - selected: '{selected}'")
        # Only trigger selection if user is not actively typing (manual selection)
        if not company_dropdown._user_typing:
            print("DEBUG: Manual selection detected - triggering form display")
            on_company_select()
        else:
            print("DEBUG: User is typing - not triggering selection yet")

    def on_focus_out(event):
        """Handle when combobox loses focus - don't auto-trigger selection"""
        current = company_dropdown.get()
        print(f"DEBUG: Focus out - current text: '{current}'")
        # Don't auto-trigger selection on focus out - let user explicitly select
        print("DEBUG: Focus out - not auto-triggering selection")

    def on_dropdown_click(event):
        """Handle dropdown button click to ensure all values are shown"""
        print("DEBUG: Dropdown button clicked - resetting to show all companies")
        if not company_dropdown._user_typing:
            company_dropdown['values'] = company_names

    def manual_select_company():
        """Manually trigger company selection when user presses Enter or clicks Update"""
        current = company_dropdown.get().strip()
        print(f"DEBUG: Manual selection triggered with text: '{current}'")
        company_dropdown._user_typing = False  # Mark as no longer typing
        if current in company_names:
            print("DEBUG: Valid selection - triggering company selection")
            on_company_select()
        else:
            # Try partial match
            matches = [name for name in company_names
                      if name.lower().startswith(current.lower())]
            if matches:
                print(f"DEBUG: Using partial match: '{matches[0]}'")
                company_dropdown.set(matches[0])
                on_company_select()
            else:
                print("DEBUG: No valid company match found")

    company_dropdown.bind('<KeyRelease>', on_key_release)
    company_dropdown.bind('<<ComboboxSelected>>', on_combobox_select)
    company_dropdown.bind('<FocusOut>', on_focus_out)
    company_dropdown.bind('<Button-1>', on_dropdown_click)  # Handle dropdown button clicks

    # Buttons frame
    btn_frame = tk.Frame(main_frame, bg="#f0f8ff")
    btn_frame.pack(fill="x", pady=(20, 0))

    # Submit button (initially disabled)
    submit_btn = tk.Button(btn_frame, text="🔄 Update Company",
                          font=("Arial", 12, "bold"),
                          bg="#22c55e", fg="white",
                          activebackground="#16a34a",
                          relief="raised", bd=3, cursor="hand2",
                          width=20, command=on_submit)
    submit_btn.pack(side="right", padx=(10, 0))

    # Cancel button
    cancel_btn = tk.Button(btn_frame, text="❌ Cancel",
                          font=("Arial", 12, "bold"),
                          bg="#ef4444", fg="white",
                          activebackground="#dc2626",
                          relief="raised", bd=3, cursor="hand2",
                          width=15, command=cleanup_and_close)
    cancel_btn.pack(side="right")

    # Set initial focus
    company_dropdown.focus_set()

    # Handle window close (X button)
    update_win.protocol("WM_DELETE_WINDOW", cleanup_and_close)

    # Bind Escape key to cancel
    update_win.bind("<Escape>", lambda e: cleanup_and_close())

    # Wait for window to close
    update_win.wait_window()

    # Use centralized modal window management only if not already done
    if not focus_restored:
        print("DEBUG: Final focus restoration - window closed without explicit restoration")
        enable_parent(modal_id)
    else:
        print("DEBUG: Focus already restored in cleanup_and_close - skipping final restoration")