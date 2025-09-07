# -*- coding: utf-8 -*-
"""
Test script for the enhanced add_company window
"""

import tkinter as tk
import sys
import os

# Add the GUIStock directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from dbutils.company_utils import add_company
    from config.globals import logger
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running this from the GUIStock directory")
    sys.exit(1)

def test_enhanced_add_company():
    """Test the enhanced add_company window"""
    # Create main window
    root = tk.Tk()
    root.title("Test Enhanced Add Company")
    root.geometry("300x200")
    root.configure(bg="#f0f8ff")

    # Header
    header = tk.Label(root, text="🧪 Test Enhanced Add Company Window",
                     font=("Helvetica", 16, "bold"),
                     bg="#4682b4", fg="white", pady=10)
    header.pack(fill="x", pady=(0, 20))

    # Instructions
    instructions = tk.Label(root,
                           text="Click the button below to test the new\nenhanced add company window with all features:",
                           font=("Helvetica", 12), bg="#f0f8ff", justify="center")
    instructions.pack(pady=10)

    # Features list
    features = tk.Label(root,
                       text="✅ Professional colorful layout\n"
                            "✅ Uppercase conversion (Stock Code & ISIN)\n"
                            "✅ ISIN validation\n"
                            "✅ Progressive search dropdowns\n"
                            "✅ Checkbox widgets\n"
                            "✅ ESC to clear entries\n"
                            "✅ Dynamic sizing",
                       font=("Helvetica", 10), bg="#f0f8ff", justify="left")
    features.pack(pady=10)

    # Test button
    test_btn = tk.Button(root, text="🏢 Open Enhanced Add Company Window",
                        command=lambda: add_company(root),
                        font=("Helvetica", 14, "bold"),
                        bg="#32cd32", fg="white",
                        padx=20, pady=10, cursor="hand2")
    test_btn.pack(pady=20)

    # Exit button
    exit_btn = tk.Button(root, text="❌ Exit Test",
                        command=root.destroy,
                        font=("Helvetica", 12),
                        bg="#dc143c", fg="white",
                        padx=15, pady=5, cursor="hand2")
    exit_btn.pack(pady=10)

    # Center the window
    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - (root.winfo_width() // 2)
    y = (root.winfo_screenheight() // 2) - (root.winfo_height() // 2)
    root.geometry(f"{root.winfo_width()}x{root.winfo_height()}+{x}+{y}")

    # Start the main loop
    root.mainloop()

if __name__ == "__main__":
    print("🚀 Starting Enhanced Add Company Test...")
    print("=" * 50)
    print("Features to test:")
    print("1. Professional multi-column colorful layout")
    print("2. Font size 14 (Helvetica)")
    print("3. Uppercase conversion for Stock Code and ISIN")
    print("4. ISIN validation (12 chars, starts with 'IN')")
    print("5. Progressive search for Sector dropdown")
    print("6. Progressive search for Face Value dropdown")
    print("7. Checkbox widgets for Is Active and Is ETF")
    print("8. ESC key to clear all entries")
    print("9. Dynamic dialog sizing")
    print("10. F1 key for help")
    print("=" * 50)

    try:
        test_enhanced_add_company()
    except KeyboardInterrupt:
        print("\n\n👋 Test cancelled by user")
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
    else:
        print("\n✅ Test completed successfully!")
