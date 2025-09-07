# -*- coding: utf-8 -*-
"""
Test script to verify the new import structure works correctly.
"""

# === Path Setup for IDE Compatibility ===
import sys
import os

# Add FinanceManager root to Python path if not already there
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# === End Path Setup ===

# Test the new import structure
try:
    print("Testing new import structure...")

    # Test config imports
    from FinanceManager.GUIStock.config import logger, APP_TITLE
    print(f"✓ Config imports successful")
    print(f"  APP_TITLE: {APP_TITLE}")

    # Test dbutils imports
    from FinanceManager.GUIStock.dbutils import (
        disable_parent, enable_parent,
        add_company, create_database
    )
    print(f"✓ DBUtils imports successful")

    # Test business imports
    from FinanceManager.GUIStock.business import remove_trade
    print(f"✓ Business imports successful")

    # Test dialogs imports
    from FinanceManager.GUIStock.dialogs import show_colorful_info
    print(f"✓ Dialogs imports successful")

    print("\n🎉 All imports successful! New package structure is working.")

except ImportError as e:
    print(f"❌ Import failed: {e}")
    import traceback
    traceback.print_exc()
