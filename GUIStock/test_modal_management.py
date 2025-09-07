#!/usr/bin/env python3
"""
Test script for the new centralized modal window management system.

This demonstrates the new disable_parent() and enable_parent() functions.
"""

import tkinter as tk
import sys
import os

# Add the GUIStock directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dbutils.company_utils import disable_parent, enable_parent


def create_simple_modal_test(parent, button_text):
    """Create a simple modal using the new centralized system."""

    # Step 1: Disable parent and get modal ID
    modal_id = disable_parent(parent)
    print(f"✅ Called disable_parent() - Modal ID: {modal_id}")

    # Step 2: Create modal window
    modal = tk.Toplevel(parent)
    modal.title(f"Test Modal - {button_text}")
    modal.geometry("400x250")
    modal.resizable(False, False)
    modal.transient(parent)
    modal.grab_set()

    # Step 3: Add content
    tk.Label(modal, text=f"Test Modal: {button_text}",
            font=("Helvetica", 16, "bold")).pack(pady=20)

    tk.Label(modal, text="This modal uses the new centralized\ndisable_parent() and enable_parent() system!",
            justify=tk.CENTER, font=("Arial", 12)).pack(pady=10)

    tk.Label(modal, text=f"Modal ID: {modal_id}",
            font=("Courier", 10), fg="gray").pack(pady=5)

    # Step 4: Close function
    def close_modal():
        print(f"✅ Closing modal and calling enable_parent({modal_id})")
        modal.destroy()
        enable_parent(modal_id)  # Step 5: Enable parent

    # Step 6: Add buttons
    btn_frame = tk.Frame(modal)
    btn_frame.pack(pady=20)

    tk.Button(btn_frame, text="✅ OK", command=close_modal,
             bg="#4CAF50", fg="white", padx=20, pady=5).pack(side=tk.LEFT, padx=5)

    tk.Button(btn_frame, text="❌ Cancel", command=close_modal,
             bg="#f44336", fg="white", padx=20, pady=5).pack(side=tk.LEFT, padx=5)

    # Step 7: Bind Escape key
    modal.bind("<Escape>", lambda e: close_modal())

    # Step 8: Wait for modal to close
    modal.wait_window()


def create_test_window():
    """Create the main test window."""

    root = tk.Tk()
    root.title("🎯 Centralized Modal Management Test")
    root.geometry("600x400")

    # Title
    title = tk.Label(root, text="🎯 Centralized Modal Management Test",
                    font=("Helvetica", 18, "bold"), fg="#2E7D32")
    title.pack(pady=20)

    # Instructions
    instructions = tk.Text(root, height=6, width=70, wrap=tk.WORD)
    instructions.pack(pady=10)
    instructions.insert(tk.END,
        "NEW SIMPLIFIED SYSTEM:\n"
        "1. Call disable_parent(parent) to disable parent and get modal_id\n"
        "2. Create and show your modal window\n"
        "3. Call enable_parent(modal_id) when closing\n\n"
        "Click any button below to test the new system.\n"
        "Watch how focus automatically moves to the NEXT button!"
    )
    instructions.config(state=tk.DISABLED)

    # Button frame
    button_frame = tk.Frame(root)
    button_frame.pack(pady=30)

    # Create test buttons in sequence
    buttons = []

    btn1 = tk.Button(button_frame, text="1️⃣ First Modal", width=20, height=2,
                     bg="#E3F2FD", font=("Arial", 12, "bold"))
    btn1.pack(pady=5)
    buttons.append(btn1)

    btn2 = tk.Button(button_frame, text="2️⃣ Second Modal", width=20, height=2,
                     bg="#F3E5F5", font=("Arial", 12, "bold"))
    btn2.pack(pady=5)
    buttons.append(btn2)

    btn3 = tk.Button(button_frame, text="3️⃣ Third Modal", width=20, height=2,
                     bg="#E8F5E8", font=("Arial", 12, "bold"))
    btn3.pack(pady=5)
    buttons.append(btn3)

    btn4 = tk.Button(button_frame, text="4️⃣ Next Button", width=20, height=2,
                     bg="#FFF3E0", font=("Arial", 12, "bold"),
                     command=lambda: print("✅ Button 4 clicked - Focus restoration working!"))
    btn4.pack(pady=5)
    buttons.append(btn4)

    btn5 = tk.Button(button_frame, text="5️⃣ Final Button", width=20, height=2,
                     bg="#FFEBEE", font=("Arial", 12, "bold"),
                     command=lambda: print("✅ Button 5 clicked - Focus restoration working!"))
    btn5.pack(pady=5)
    buttons.append(btn5)

    # Set up button commands
    btn1.config(command=lambda: create_simple_modal_test(root, "First Modal"))
    btn2.config(command=lambda: create_simple_modal_test(root, "Second Modal"))
    btn3.config(command=lambda: create_simple_modal_test(root, "Third Modal"))

    # Exit button
    exit_btn = tk.Button(root, text="🚪 Exit", command=root.destroy,
                        bg="#FFCDD2", font=("Arial", 12, "bold"))
    exit_btn.pack(pady=20)

    # Status
    status = tk.Label(root, text="✅ Ready! The new system requires only 2 calls: disable_parent() and enable_parent()",
                     font=("Arial", 11), fg="#1B5E20")
    status.pack(pady=10)

    # Set initial focus
    btn1.focus_set()

    return root


if __name__ == "__main__":
    print("🎯 Testing New Centralized Modal Management System")
    print("\nThe new system simplifies modal windows to just 2 function calls:")
    print("  1. modal_id = disable_parent(parent)")
    print("  2. enable_parent(modal_id)")
    print("\nAll focus restoration is handled automatically!")

    try:
        root = create_test_window()
        root.mainloop()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

    print("\n🎯 Test completed!")
