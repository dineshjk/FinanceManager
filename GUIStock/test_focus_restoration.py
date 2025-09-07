#!/usr/bin/env python3
"""
Test script to verify focus restoration after modal window closes.
"""

import tkinter as tk
import sys
import os

# Add the GUIStock directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dbutils.company_utils import add_company, update_company

def create_test_window():
    """Create a test window with buttons to test focus restoration."""
    root = tk.Tk()
    root.title("Focus Restoration Test")
    root.geometry("400x300")

    # Create a title
    title = tk.Label(root, text="Focus Restoration Test",
                    font=("Helvetica", 16, "bold"))
    title.pack(pady=20)

    # Create test buttons
    buttons = []

    # Add Company button
    add_btn = tk.Button(root, text="Add Company", width=20,
                       command=lambda: add_company(root, add_btn))
    add_btn.pack(pady=5)
    buttons.append(add_btn)

    # Update Company button
    update_btn = tk.Button(root, text="Update Company", width=20,
                          command=lambda: update_company(root, update_btn))
    update_btn.pack(pady=5)
    buttons.append(update_btn)

    # Dummy button to test focus restoration
    dummy_btn = tk.Button(root, text="Next Button (Should Get Focus)",
                         width=30, command=lambda: print("Next button clicked!"))
    dummy_btn.pack(pady=5)
    buttons.append(dummy_btn)

    # Another dummy button
    final_btn = tk.Button(root, text="Final Button", width=20,
                         command=lambda: print("Final button clicked!"))
    final_btn.pack(pady=5)
    buttons.append(final_btn)

    # Exit button
    exit_btn = tk.Button(root, text="Exit", width=20,
                        command=root.destroy)
    exit_btn.pack(pady=20)

    # Instructions
    instructions = tk.Label(root,
                           text="1. Click 'Add Company' or 'Update Company'\n"
                                "2. Close the modal window (Cancel/Escape/X)\n"
                                "3. Focus should move to the next button\n"
                                "4. Press Enter to verify focus",
                           justify=tk.LEFT)
    instructions.pack(pady=10)

    # Enable navigation between buttons
    def on_key(event):
        if event.keysym == 'Tab':
            # Manual tab navigation for testing
            try:
                current = root.focus_get()
                if current in buttons:
                    current_idx = buttons.index(current)
                    next_idx = (current_idx + 1) % len(buttons)
                    buttons[next_idx].focus_set()
                    return 'break'
            except (ValueError, AttributeError):
                buttons[0].focus_set()
                return 'break'

    root.bind('<Key>', on_key)

    # Set initial focus
    add_btn.focus_set()

    return root

if __name__ == "__main__":
    print("Starting focus restoration test...")
    print("Instructions:")
    print("1. Click on 'Add Company' or 'Update Company'")
    print("2. Close the modal window using Cancel, Escape, or X button")
    print("3. The focus should automatically move to the next button")
    print("4. Press Enter to verify the correct button has focus")

    root = create_test_window()
    root.mainloop()
