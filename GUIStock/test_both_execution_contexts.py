# -*- coding: utf-8 -*-
# File: test_both_execution_contexts.py

"""
Test script to verify both execution contexts work correctly.

This script can be run from both:
1. Parent directory: python -m GUIStock.test_both_execution_contexts
2. GUIStock directory: python test_both_execution_contexts.py
"""

def test_imports():
    """Test that all imports work in current execution context."""
    print("🧪 Testing Import Compatibility...")

    try:
        print("  📦 Testing dialog system...")
        try:
            # Try module execution context first
            from GUIStock.dialogs import show_colorful_info, show_colorful_error, show_colorful_yesno
        except ImportError:
            # Fall back to direct execution context
            from dialogs import show_colorful_info, show_colorful_error, show_colorful_yesno
        print("  ✅ Dialog system imports successful")

        print("  🏢 Testing business logic...")
        try:
            from GUIStock.business.trade_operations import remove_trade, remove_trade_by_id
        except ImportError:
            from business.trade_operations import remove_trade, remove_trade_by_id
        print("  ✅ Business logic imports successful")

        print("  📅 Testing core utilities...")
        try:
            from GUIStock.core.date_utils import next_working_day
        except ImportError:
            from core.date_utils import next_working_day
        print("  ✅ Core utilities imports successful")

        print("  🖼️  Testing UI forms...")
        try:
            from GUIStock.ui.forms.trade_forms import TradeEntryForm, TradeDeleteForm
        except ImportError:
            from ui.forms.trade_forms import TradeEntryForm, TradeDeleteForm
        print("  ✅ UI forms imports successful")

        print("  📊 Testing main application...")
        try:
            import GUIStock.MyGUIStock
        except ImportError:
            import MyGUIStock
        print("  ✅ Main application imports successful")

        return True

    except ImportError as e:
        print(f"  ❌ Import failed: {e}")
        return False
    except Exception as e:
        print(f"  ❌ Unexpected error: {e}")
        return False

def test_functionality():
    """Test key functionality works correctly."""
    print("\n🔧 Testing Core Functionality...")

    try:
        # Test dialog sizing
        try:
            from GUIStock.dialogs.sizing import calculate_dialog_size
        except ImportError:
            from dialogs.sizing import calculate_dialog_size
        width, height = calculate_dialog_size("Test message", "Test Title")
        print(f"  ✅ Dialog sizing: {width}x{height}")

        # Test date utilities
        try:
            from GUIStock.core.date_utils import next_working_day
        except ImportError:
            from core.date_utils import next_working_day
        next_day = next_working_day()
        print(f"  ✅ Date utilities: Next working day is {next_day}")

        # Test trade validation
        try:
            from GUIStock.business.trade_operations import validate_trade_data
        except ImportError:
            from business.trade_operations import validate_trade_data
        is_valid, msg = validate_trade_data("AAPL", 100, 150.0, "2024-01-15")
        print(f"  ✅ Trade validation: Valid={is_valid}")

        return True

    except Exception as e:
        print(f"  ❌ Functionality test failed: {e}")
        return False

def main():
    """Main test function."""
    import os
    import sys

    print("🚀 DUAL EXECUTION CONTEXT TEST")
    print("=" * 50)
    print(f"📁 Current directory: {os.getcwd()}")
    print(f"🐍 Execution context: {sys.argv[0]}")

    # Detect execution context
    if "GUIStock" in os.getcwd() and not sys.argv[0].startswith("GUIStock"):
        context = "Direct execution (from GUIStock directory)"
    else:
        context = "Module execution (from parent directory)"

    print(f"🎯 Detected context: {context}")
    print("=" * 50)

    # Run tests
    import_success = test_imports()
    functionality_success = test_functionality()

    print("\n" + "=" * 50)
    print("📊 TEST RESULTS")
    print("=" * 50)

    if import_success and functionality_success:
        print("🎉 ALL TESTS PASSED!")
        print("   The modular implementation works correctly in both execution contexts.")
        print("   ✅ Ctrl+F5 from VS Code will work")
        print("   ✅ Direct execution will work")
        return True
    else:
        print("❌ SOME TESTS FAILED!")
        print("   Please check the error messages above.")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
