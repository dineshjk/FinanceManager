# -*- coding: utf-8 -*-
# File: test_trade_deletion.py

"""
Specific test for the trade deletion functionality to ensure it works correctly
with the modular implementation.
"""

import tkinter as tk
import sys

def test_remove_trade_interface():
    """Test that the remove_trade function can be called correctly."""
    print("🗑️ Testing Trade Deletion Interface...")

    try:
        from business.trade_operations import remove_trade

        # Create a minimal tkinter window for testing
        root = tk.Tk()
        root.title("Trade Deletion Test")
        root.geometry("400x300")

        # Add a test button that calls remove_trade
        test_frame = tk.Frame(root, bg="#f0f0f0")
        test_frame.pack(fill="both", expand=True, padx=20, pady=20)

        title_label = tk.Label(test_frame, text="Trade Deletion Function Test",
                              font=("Arial", 16, "bold"), bg="#f0f0f0")
        title_label.pack(pady=20)

        info_label = tk.Label(test_frame,
                             text="Click the button below to test the trade deletion interface.\n" +
                                  "This will open the trade selection dialog.",
                             font=("Arial", 10), bg="#f0f0f0", justify="center")
        info_label.pack(pady=10)

        test_btn = tk.Button(test_frame, text="🗑️ Test Remove Trade",
                            font=("Arial", 12, "bold"),
                            bg="#dc2626", fg="white",
                            command=lambda: remove_trade(root),
                            width=20, height=2)
        test_btn.pack(pady=20)

        close_btn = tk.Button(test_frame, text="❌ Close Test",
                             font=("Arial", 12), bg="#6b7280", fg="white",
                             command=root.destroy, width=15, height=2)
        close_btn.pack(pady=10)

        # Center the window
        root.update_idletasks()
        x = (root.winfo_screenwidth() // 2) - (200)
        y = (root.winfo_screenheight() // 2) - (150)
        root.geometry(f"400x300+{x}+{y}")

        print("✅ Trade deletion interface test window created successfully")
        print("   Click the 'Test Remove Trade' button to test the functionality")

        # Run the test window
        root.mainloop()

        return True

    except Exception as e:
        print(f"❌ Error testing trade deletion interface: {e}")
        import traceback
        print(traceback.format_exc())
        return False

def test_dialog_functions():
    """Test that all dialog functions work correctly."""
    print("\n🎨 Testing Dialog Functions...")

    try:
        from dialogs import show_colorful_info, show_colorful_error, show_colorful_yesno

        # Create a test window
        root = tk.Tk()
        root.title("Dialog Functions Test")
        root.geometry("500x400")

        test_frame = tk.Frame(root, bg="#f8fafc")
        test_frame.pack(fill="both", expand=True, padx=20, pady=20)

        title_label = tk.Label(test_frame, text="Dialog System Test",
                              font=("Arial", 16, "bold"), bg="#f8fafc")
        title_label.pack(pady=20)

        # Test buttons for each dialog type
        info_btn = tk.Button(test_frame, text="ℹ️ Test Info Dialog",
                            font=("Arial", 11, "bold"), bg="#3b82f6", fg="white",
                            command=lambda: show_colorful_info(root, "Test Info",
                                   "This is a test information dialog.\nIt should display with proper sizing."),
                            width=25, height=2)
        info_btn.pack(pady=5)

        error_btn = tk.Button(test_frame, text="❌ Test Error Dialog",
                             font=("Arial", 11, "bold"), bg="#dc2626", fg="white",
                             command=lambda: show_colorful_error(root, "Test Error",
                                    "This is a test error dialog.\nIt should display with red theme."),
                             width=25, height=2)
        error_btn.pack(pady=5)

        confirm_btn = tk.Button(test_frame, text="❓ Test Confirmation Dialog",
                               font=("Arial", 11, "bold"), bg="#059669", fg="white",
                               command=lambda: test_yesno_dialog(root),
                               width=25, height=2)
        confirm_btn.pack(pady=5)

        close_btn = tk.Button(test_frame, text="❌ Close Test",
                             font=("Arial", 11), bg="#6b7280", fg="white",
                             command=root.destroy, width=20, height=2)
        close_btn.pack(pady=20)

        # Center the window
        root.update_idletasks()
        x = (root.winfo_screenwidth() // 2) - (250)
        y = (root.winfo_screenheight() // 2) - (200)
        root.geometry(f"500x400+{x}+{y}")

        print("✅ Dialog functions test window created successfully")

        # Run the test window
        root.mainloop()

        return True

    except Exception as e:
        print(f"❌ Error testing dialog functions: {e}")
        return False

def test_yesno_dialog(parent):
    """Test the yes/no dialog and show the result."""
    from dialogs import show_colorful_yesno, show_colorful_info

    result = show_colorful_yesno(parent, "Test Confirmation",
                                "Do you want to test the Yes/No dialog?\n\nThis is a sample confirmation message.")

    if result:
        show_colorful_info(parent, "Result", "You clicked 'Yes'! ✅")
    else:
        show_colorful_info(parent, "Result", "You clicked 'No'! ❌")

def main():
    """Main test function."""
    print("🚀 TESTING MODULAR TRADE DELETION IMPLEMENTATION")
    print("=" * 55)

    # Test 1: Dialog functions
    print("Test 1: Dialog Functions")
    test_dialog_functions()

    print("\n" + "=" * 55)

    # Test 2: Trade deletion interface
    print("Test 2: Trade Deletion Interface")
    test_remove_trade_interface()

    print("\n✅ All tests completed!")

if __name__ == "__main__":
    main()
