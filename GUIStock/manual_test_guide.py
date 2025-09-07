#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Manual Testing Guide for FinanceManager Application
==================================================

This script provides a systematic approach to testing the application
menu items and core functionality. Run this to get a testing checklist.
"""

import sys
import os

# Add path for imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def print_testing_checklist():
    """Print a comprehensive testing checklist for manual testing."""

    print("=" * 60)
    print("FINANCEMANAGER APPLICATION - MANUAL TESTING GUIDE")
    print("=" * 60)

    print("\n🔍 PHASE 1: CRITICAL PATH TESTING (Test These First)")
    print("-" * 50)

    critical_tests = [
        ("1. Application Startup", "Launch app - should open without errors"),
        ("2. Add Company", "Menu → Company → Add Company - test form"),
        ("3. Company List", "Menu → Company → Company Menu - view companies"),
        ("4. Add Trade", "Menu → Transactions → Add Trade - test trade entry"),
        ("5. Modal Focus", "Open any dialog - parent should be disabled"),
        ("6. ESC Key", "Press ESC in any dialog - should close properly"),
    ]

    for test_name, description in critical_tests:
        print(f"   ☐ {test_name}: {description}")

    print("\n🔧 PHASE 2: FEATURE TESTING (Test After Phase 1 Passes)")
    print("-" * 50)

    feature_tests = [
        ("Update Company", "Modify existing company data"),
        ("Bulk Entry Company", "Add multiple companies at once"),
        ("Remove Company", "Delete company functionality"),
        ("Transaction Reports", "Various transaction views"),
        ("Database Maintenance", "Backup/restore operations"),
    ]

    for test_name, description in feature_tests:
        print(f"   ☐ {test_name}: {description}")

    print("\n📋 TESTING WORKFLOW:")
    print("-" * 20)
    print("1. Close any running instances first")
    print("2. Start fresh: python -m FinanceManager.GUIStock.MyGUIStock")
    print("3. Test Phase 1 items systematically")
    print("4. If Phase 1 passes, proceed to Phase 2")
    print("5. Report any issues you encounter")

    print("\n🚨 WHAT TO WATCH FOR:")
    print("-" * 25)
    error_signs = [
        "Import errors on startup",
        "Windows that don't disable parent properly",
        "ESC key not working in dialogs",
        "Data not saving to database",
        "Crashes or freezes",
        "Error messages in console"
    ]

    for sign in error_signs:
        print(f"   ⚠️  {sign}")

    print("\n" + "=" * 60)

def test_imports():
    """Test if all critical imports work."""
    print("\n🧪 IMPORT TESTING:")
    print("-" * 20)

    try:
        from FinanceManager.GUIStock.config import logger, APP_TITLE
        print("   ✅ Config imports successful")
    except Exception as e:
        print(f"   ❌ Config imports failed: {e}")
        return False

    try:
        from FinanceManager.GUIStock.dbutils import add_company, add_trade
        print("   ✅ Database utilities imports successful")
    except Exception as e:
        print(f"   ❌ Database utilities imports failed: {e}")
        return False

    try:
        from FinanceManager.GUIStock import MyGUIStock
        print("   ✅ Main application import successful")
    except Exception as e:
        print(f"   ❌ Main application import failed: {e}")
        return False

    print("   ✅ All imports successful - ready for manual testing!")
    return True

if __name__ == "__main__":
    print_testing_checklist()
    test_imports()

    print("\n🚀 READY TO START TESTING!")
    print("Close this script and run: python -m FinanceManager.GUIStock.MyGUIStock")
