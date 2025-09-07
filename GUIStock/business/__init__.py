# -*- coding: utf-8 -*-
"""
Business Logic Package
======================

This package contains business logic and operations for the Stock
Portfolio Management System. It implements core business rules,
calculations, and operations that are independent of the UI layer.

Key Features:
- Trade operations and business rules
- Portfolio calculations and analytics
- Investment performance analysis
- Risk assessment and reporting
- Business rule validation
- Financial calculations

Modules:
    trade_operations: Core trading business logic and operations

Usage:
    # Trade Operations
    from FinanceManager.GUIStock.business import remove_trade
    remove_trade(parent_window)

    # Future modules might include:
    # portfolio_analytics: Portfolio performance calculations
    # risk_management: Risk assessment and management
    # reporting: Business reporting and analytics
"""

# Trade Operations
from .trade_operations import (
    remove_trade,
    remove_trade_by_id,
    get_trade_summary,
    validate_trade_data
)

# Make business operations available at package level
__all__ = [
    'remove_trade',
    'remove_trade_by_id',
    'get_trade_summary',
    'validate_trade_data'
]
