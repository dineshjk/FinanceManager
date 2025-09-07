# -*- coding: utf-8 -*-
# File: c:\Users\aumji\source\repos\Finance\FinanceManager\GUIStock\ui\forms\trade_forms.py

"""
Trade-related form components for the Stock Portfolio Management System.

This module contains form widgets and validation for trade entry, editing,
and deletion operations.
"""

import tkinter as tk
from tkinter import ttk
from datetime import datetime

# Dual import handling for date utilities
try:
    from GUIStock.core.date_utils import next_working_day
except ImportError:
    from core.date_utils import next_working_day

# Dual import handling for business operations
try:
    from GUIStock.business.trade_operations import validate_trade_data, remove_trade
except ImportError:
    from business.trade_operations import validate_trade_data, remove_trade

# Dual import handling for dialogs
try:
    from GUIStock.dialogs.info_dialogs import show_colorful_error
except ImportError:
    from dialogs.info_dialogs import show_colorful_error


class TradeEntryForm:
    """Form widget for entering new trades or editing existing ones."""

    def __init__(self, parent, trade_data=None):
        """
        Initialize the trade entry form.

        Args:
            parent: Parent tkinter widget
            trade_data (dict, optional): Existing trade data for editing
        """
        self.parent = parent
        self.trade_data = trade_data
        self.is_editing = trade_data is not None

        self.frame = ttk.LabelFrame(parent, text="Trade Information",
                                   padding="10")
        self.frame.pack(fill="x", padx=10, pady=5)

        self._create_widgets()
        if self.is_editing:
            self._populate_data()

    def _create_widgets(self):
        """Create the form widgets."""
        # Symbol entry
        ttk.Label(self.frame, text="Symbol:").grid(row=0, column=0,
                                                  sticky="w", pady=2)
        self.symbol_var = tk.StringVar()
        self.symbol_entry = ttk.Entry(self.frame, textvariable=self.symbol_var,
                                     width=15)
        self.symbol_entry.grid(row=0, column=1, sticky="w", padx=(5, 20),
                              pady=2)

        # Quantity entry
        ttk.Label(self.frame, text="Quantity:").grid(row=0, column=2,
                                                    sticky="w", pady=2)
        self.quantity_var = tk.StringVar()
        self.quantity_entry = ttk.Entry(self.frame,
                                       textvariable=self.quantity_var,
                                       width=15)
        self.quantity_entry.grid(row=0, column=3, sticky="w", padx=(5, 0),
                                pady=2)

        # Price entry
        ttk.Label(self.frame, text="Price:").grid(row=1, column=0,
                                                 sticky="w", pady=2)
        self.price_var = tk.StringVar()
        self.price_entry = ttk.Entry(self.frame, textvariable=self.price_var,
                                    width=15)
        self.price_entry.grid(row=1, column=1, sticky="w", padx=(5, 20),
                             pady=2)

        # Date entry
        ttk.Label(self.frame, text="Date (YYYY-MM-DD):").grid(row=1, column=2,
                                                              sticky="w",
                                                              pady=2)
        self.date_var = tk.StringVar()
        self.date_entry = ttk.Entry(self.frame, textvariable=self.date_var,
                                   width=15)
        self.date_entry.grid(row=1, column=3, sticky="w", padx=(5, 0),
                            pady=2)

        # Set default date to next working day
        self.date_var.set(next_working_day().strftime("%Y-%m-%d"))

        # Validation bindings
        self.quantity_entry.bind('<KeyRelease>', self._validate_number)
        self.price_entry.bind('<KeyRelease>', self._validate_number)
        self.date_entry.bind('<KeyRelease>', self._validate_date)

    def _populate_data(self):
        """Populate form with existing trade data."""
        if self.trade_data:
            self.symbol_var.set(self.trade_data.get('symbol', ''))
            self.quantity_var.set(str(self.trade_data.get('quantity', '')))
            self.price_var.set(str(self.trade_data.get('price', '')))
            self.date_var.set(self.trade_data.get('trade_date', ''))

    def _validate_number(self, event):
        """Validate numeric input."""
        widget = event.widget
        value = widget.get()

        if value and not value.replace('.', '').replace('-', '').isdigit():
            # Remove invalid characters
            valid_chars = ''.join(c for c in value if c.isdigit() or c == '.')
            widget.delete(0, tk.END)
            widget.insert(0, valid_chars)

    def _validate_date(self, event):
        """Validate date input format."""
        value = event.widget.get()

        # Allow partial dates during typing
        if len(value) <= 10:
            # Remove invalid characters for date
            valid_chars = ''.join(c for c in value if c.isdigit() or c == '-')
            if valid_chars != value:
                event.widget.delete(0, tk.END)
                event.widget.insert(0, valid_chars)

    def get_data(self):
        """
        Get the form data.

        Returns:
            dict: Form data with keys: symbol, quantity, price, trade_date
        """
        try:
            quantity = float(self.quantity_var.get()) if self.quantity_var.get() else 0
            price = float(self.price_var.get()) if self.price_var.get() else 0
        except ValueError:
            quantity = 0
            price = 0

        return {
            'symbol': self.symbol_var.get().strip().upper(),
            'quantity': quantity,
            'price': price,
            'trade_date': self.date_var.get().strip()
        }

    def validate(self):
        """
        Validate the form data.

        Returns:
            tuple: (is_valid, error_message)
        """
        data = self.get_data()
        return validate_trade_data(data['symbol'], data['quantity'],
                                 data['price'], data['trade_date'])

    def clear(self):
        """Clear all form fields."""
        self.symbol_var.set('')
        self.quantity_var.set('')
        self.price_var.set('')
        self.date_var.set(next_working_day().strftime("%Y-%m-%d"))

    def set_focus(self):
        """Set focus to the first field."""
        self.symbol_entry.focus_set()


class TradeDeleteForm:
    """Form widget for selecting trades to delete."""

    def __init__(self, parent, trades_list):
        """
        Initialize the trade deletion form.

        Args:
            parent: Parent tkinter widget
            trades_list: List of trade records for selection
        """
        self.parent = parent
        self.trades_list = trades_list

        self.frame = ttk.LabelFrame(parent, text="Select Trade to Delete",
                                   padding="10")
        self.frame.pack(fill="both", expand=True, padx=10, pady=5)

        self._create_widgets()

    def _create_widgets(self):
        """Create the selection widgets."""
        # Create treeview for trade selection
        columns = ('ID', 'Symbol', 'Company', 'Quantity', 'Price', 'Date',
                  'Total')
        self.tree = ttk.Treeview(self.frame, columns=columns, show='headings',
                                height=10)

        # Configure column headings and widths
        column_widths = {'ID': 60, 'Symbol': 80, 'Company': 150,
                        'Quantity': 100, 'Price': 100, 'Date': 100,
                        'Total': 120}

        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=column_widths.get(col, 100))

        # Add scrollbar
        scrollbar = ttk.Scrollbar(self.frame, orient="vertical",
                                 command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        # Pack treeview and scrollbar
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Populate with trade data
        self._populate_trades()

        # Bind double-click event
        self.tree.bind('<Double-1>', self._on_double_click)

    def _populate_trades(self):
        """Populate the treeview with trade data."""
        for trade in self.trades_list:
            # Format the data for display
            trade_id, symbol, company, quantity, price, date, total = trade
            formatted_trade = (
                trade_id,
                symbol,
                company[:20] + "..." if len(company) > 20 else company,
                f"{quantity:,.0f}",
                f"₹{price:,.2f}",
                date,
                f"₹{total:,.2f}"
            )
            self.tree.insert('', 'end', values=formatted_trade)

    def _on_double_click(self, event):
        """Handle double-click on trade item."""
        selection = self.tree.selection()
        if selection:
            item = self.tree.item(selection[0])
            trade_id = item['values'][0]
            self.delete_selected_trade(trade_id)

    def delete_selected_trade(self, trade_id):
        """Delete the selected trade."""
        if remove_trade(self.parent, trade_id):
            # Refresh the tree after successful deletion
            self.refresh_trades()

    def refresh_trades(self):
        """Refresh the trades list."""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        # This would need to be implemented to fetch fresh data
        # For now, just clear the tree
        pass

    def get_selected_trade_id(self):
        """
        Get the ID of the currently selected trade.

        Returns:
            int or None: Selected trade ID
        """
        selection = self.tree.selection()
        if selection:
            item = self.tree.item(selection[0])
            return item['values'][0]
        return None
