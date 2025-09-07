# -*- coding: utf-8 -*-
"""
Simple direct test for the enhanced add_company window
"""

import tkinter as tk
import sys
import os

# Simple test - directly call the add_company function
def test_add_company_direct():
    """Direct test of add_company function"""
    print("Creating test window...")

    # Create a simple root window
    root = tk.Tk()
    root.title("Direct Test")
    root.geometry("200x100")

    # Import and call add_company directly
    try:
        from dbutils.company_utils import add_company
        print("Successfully imported add_company")

        # Call the function directly
        add_company(root)

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        root.destroy()

if __name__ == "__main__":
    print("🧪 Direct Test of Enhanced Add Company Window")
    print("=" * 50)
    test_add_company_direct()
    print("✅ Test completed")
