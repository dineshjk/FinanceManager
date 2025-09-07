#!/usr/bin/env python3
"""
Test the autocomplete functionality in a simplified environment
"""

import tkinter as tk
from tkinter import ttk

def setup_autocomplete(combobox, values_list):
    """Setup simple autocomplete functionality for combobox"""

    # Store original values
    combobox._original_values = values_list
    combobox['values'] = values_list

    def on_key_release(event):
        """Handle key release for autocomplete"""
        print(f"Key released: {event.keysym}")

        # Skip navigation and special keys
        if event.keysym in ['Up', 'Down', 'Left', 'Right', 'Tab',
                           'Return', 'Escape']:
            if event.keysym == 'Escape':
                combobox.set('')
                combobox['values'] = values_list
                print("Cleared field and reset values")
            return

        # Get current text
        current = combobox.get()
        print(f"Current text: '{current}'")

        if not current:
            combobox['values'] = values_list
            print("No text - showing all values")
            return

        # Find matching values (case insensitive)
        matches = [item for item in values_list
                  if item.lower().startswith(current.lower())]

        print(f"Matches found: {matches}")

        # Update dropdown values
        combobox['values'] = matches

        # Auto-complete first match
        if matches:
            # Save current cursor position
            cursor_pos = combobox.index(tk.INSERT)
            print(f"Cursor position: {cursor_pos}")

            # Set the text to first match
            first_match = matches[0]
            combobox.set(first_match)

            # Select the auto-completed part
            combobox.select_range(cursor_pos, len(first_match))
            combobox.icursor(cursor_pos)

            print(f"Auto-completed to: '{first_match}' with selection from {cursor_pos}")

    # Bind the event
    combobox.bind('<KeyRelease>', on_key_release)

def main():
    root = tk.Tk()
    root.title("Autocomplete Test")
    root.geometry("400x200")

    # Sample data
    sectors = ["Banking", "IT", "Auto", "Pharma", "FMCG", "Energy", "Metals", "Telecom"]

    label = tk.Label(root, text="Type to see autocomplete:", font=("Helvetica", 12))
    label.pack(pady=20)

    # Create combobox
    sector_var = tk.StringVar()
    combobox = ttk.Combobox(root, textvariable=sector_var, font=("Helvetica", 14),
                           width=20, values=sectors)
    combobox.pack(pady=10)

    # Setup autocomplete
    setup_autocomplete(combobox, sectors)

    # Focus on combobox
    combobox.focus_set()

    instructions = tk.Label(root,
                           text="Type 'b' for Banking, 'i' for IT, etc.\nESC to clear",
                           font=("Helvetica", 10))
    instructions.pack(pady=10)

    root.mainloop()

if __name__ == "__main__":
    main()
