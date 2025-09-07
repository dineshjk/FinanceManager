# -*- coding: utf-8 -*-
"""
Database Utilities Package
==========================

This package provides comprehensive database utilities and data access
functions for the Stock Portfolio Management System. It handles all
database operations including CRUD operations, data validation,
and business logic implementation.

Key Features:
- Modal window management system with centralized focus handling
- Company data management (add, update, bulk operations)
- Transaction recording and management
- Database initialization and maintenance
- Corporate action processing
- Data validation and integrity checks

Modules:
    modal_management: Centralized modal window and focus management
    company_utils: Company-related database operations
    transaction_utils: Stock transaction management
    initial_tasks: Database setup and initialization
    maintenance_utils: Database maintenance and cleanup operations
    corp_action_utils: Corporate action processing
    focus_utils: Focus management utilities (legacy)

Usage:
    # Modal Management
    from FinanceManager.GUIStock.dbutils import disable_parent, enable_parent
    modal_id = disable_parent(parent_window)
    # ... show modal ...
    enable_parent(modal_id)

    # Company Operations
    from FinanceManager.GUIStock.dbutils import add_company, update_company
    add_company(parent_window)

    # Transaction Operations
    from FinanceManager.GUIStock.dbutils import add_trade
    add_trade(parent_window)

    # Database Setup
    from FinanceManager.GUIStock.dbutils import create_database
    create_database()
"""

# Modal Management System
from .modal_management import (
    disable_parent,
    enable_parent,
    ModalWindowManager,
    setup_modal_window,
    add_escape_binding
)

# Company Management Operations
from .company_utils import (
    add_company,
    update_company,
    bulk_entry_company
)

# Transaction Management Operations
from .transaction_utils import add_trade

# Database Initialization
from .initial_tasks import create_database

# Make commonly used functions available at package level
__all__ = [
    # Modal Management
    'disable_parent',
    'enable_parent',
    'ModalWindowManager',
    'setup_modal_window',
    'add_escape_binding',

    # Company Operations
    'add_company',
    'update_company',
    'bulk_entry_company',

    # Transaction Operations
    'add_trade',

    # Database Operations
    'create_database'
]
