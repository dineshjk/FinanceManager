# -*- coding: utf-8 -*-
"""
Configuration Package
====================

This package contains configuration settings, global variables, and
system-wide constants for the GUIStock application.

The configuration system provides:
- Centralized logging configuration
- Application-wide constants and settings
- Global variable management
- System configuration parameters

Modules:
    globals: Global variables, logger, and application constants

Usage:
    from FinanceManager.GUIStock.config import logger, APP_TITLE

    # Use the logger throughout the application
    logger.info("Application started")
    logger.debug("Debug information")
    logger.error("Error occurred")

    # Use application constants
    window.title(APP_TITLE)
"""

# Import and expose commonly used configuration items
from .globals import logger, APP_TITLE

# Make all configuration items available at package level
__all__ = [
    'logger',
    'APP_TITLE'
]
