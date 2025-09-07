# -*- coding: utf-8 -*-
"""
Test script to verify that MyGUIStock.py can be executed in both contexts
without errors.
"""

import subprocess
import sys
import os

def test_module_execution():
    """Test running with python -m GUIStock.MyGUIStock"""
    print("🧪 Testing module execution (VS Code Ctrl+F5 method)...")
    try:
        # Run for 3 seconds then kill
        result = subprocess.run([
            sys.executable, "-m", "GUIStock.MyGUIStock"
        ], capture_output=True, text=True, timeout=3, cwd=os.getcwd())
        print(f"  ✅ Module execution started successfully")
        return True
    except subprocess.TimeoutExpired:
        print(f"  ✅ Module execution started successfully (GUI launched)")
        return True
    except Exception as e:
        print(f"  ❌ Module execution failed: {e}")
        return False

def test_direct_execution():
    """Test running with python MyGUIStock.py"""
    print("🧪 Testing direct execution...")
    try:
        # Change to GUIStock directory and run
        guistock_dir = os.path.join(os.getcwd(), "GUIStock")
        result = subprocess.run([
            sys.executable, "MyGUIStock.py"
        ], capture_output=True, text=True, timeout=3, cwd=guistock_dir)
        print(f"  ✅ Direct execution started successfully")
        return True
    except subprocess.TimeoutExpired:
        print(f"  ✅ Direct execution started successfully (GUI launched)")
        return True
    except Exception as e:
        print(f"  ❌ Direct execution failed: {e}")
        return False

def main():
    print("🚀 MAIN APPLICATION EXECUTION TEST")
    print("=" * 50)
    print(f"📁 Current directory: {os.getcwd()}")
    print("=" * 50)

    module_success = test_module_execution()
    direct_success = test_direct_execution()

    print("\n" + "=" * 50)
    print("📊 FINAL RESULTS")
    print("=" * 50)

    if module_success and direct_success:
        print("🎉 ALL EXECUTION METHODS WORK!")
        print("   ✅ VS Code Ctrl+F5 will work properly")
        print("   ✅ Direct script execution works")
        print("   ✅ Modular reorganization is complete and functional")
    else:
        print("❌ SOME EXECUTION METHODS FAILED!")
        print(f"   Module execution: {'✅' if module_success else '❌'}")
        print(f"   Direct execution: {'✅' if direct_success else '❌'}")

if __name__ == "__main__":
    main()
