# -*- coding: utf-8 -*-
"""
GUIStock - Main GUI Application Package
=======================================

This package contains the main GUI application for the Stock Portfolio
Management System. It provides a user-friendly interface for managing
stock portfolios, recording transactions, and analyzing investment
performance.

Key Features:
- Intuitive GUI interface using Tkinter
- Modal window management system
- Database integration for persistent storage
- Real-time data entry and validation
- Comprehensive reporting capabilities

Subpackages:
    config: Configuration settings and global variables
    dbutils: Database utilities and data access functions
    business: Business logic and operations
    dialogs: Custom dialog components

Main Entry Point:
    MyGUIStock.py: Main application entry point

Usage:
    # Run the application
    python -m FinanceManager.GUIStock.MyGUIStock

    # Or import for programmatic access
    from FinanceManager.GUIStock import main_gui
"""

# Import main application components
from .MyGUIStock import main_gui

# Import key subpackages for convenience
from . import config
from . import dbutils
from . import business

# Make commonly used items available at package level
__all__ = [
    'main_gui',
    'config',
    'dbutils',
    'business'
]
