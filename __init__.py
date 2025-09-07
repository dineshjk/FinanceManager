# -*- coding: utf-8 -*-
"""
FinanceManager - Stock Portfolio Management System
================================================

A comprehensive Python application for managing stock portfolios with features including:

- Stock transaction recording and tracking
- Company management and corporate actions
- Portfolio performance analysis
- Database-driven data storage
- GUI-based user interface

This package provides a complete solution for individual investors to track
their stock investments, analyze performance, and maintain detailed records
of all trading activities.

Modules:
    GUIStock: Main GUI application package
    Stocks: Core stock data management (if applicable)

Author: Finance Manager Development Team
Version: 1.0.0
"""

__version__ = "1.0.0"
__author__ = "Finance Manager Development Team"
__email__ = "support@financemanager.com"

# Package metadata
__title__ = "FinanceManager"
__description__ = "Stock Portfolio Management System"
__url__ = "https://github.com/financemanager/financemanager"

# Import main subpackages for convenience
try:
    from . import GUIStock
except ImportError:
    # Handle case where GUIStock might not be available
    pass

__all__ = ['GUIStock']
