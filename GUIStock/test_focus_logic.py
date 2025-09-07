#!/usr/bin/env python3
"""
Simple test to validate the focus restoration logic without GUI interaction.
"""

import tkinter as tk
import sys
import os

# Add the GUIStock directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_find_next_focusable_widget():
    """Test the find_next_focusable_widget function logic."""

    # Create a test window with buttons
    root = tk.Tk()
    root.withdraw()  # Hide the window for testing

    # Create test buttons
    btn1 = tk.Button(root, text="Button 1")
    btn2 = tk.Button(root, text="Button 2")
    btn3 = tk.Button(root, text="Button 3")

    btn1.pack()
    btn2.pack()
    btn3.pack()

    # Test the focus restoration logic
    def find_next_focusable_widget(start_widget, parent_window):
        """Find the next focusable widget after the given widget."""
        if not start_widget or not parent_window:
            return None

        try:
            # Get all widgets in the parent window that can take focus
            def get_all_focusable_widgets(widget, focusable_list=[]):
                """Recursively find all focusable widgets."""
                focusable_list = []  # Reset for each call
                try:
                    for child in widget.winfo_children():
                        # Check if widget can take focus (buttons, entries, etc.)
                        if hasattr(child, 'focus_set') and child.winfo_viewable():
                            widget_class = child.winfo_class()
                            if widget_class in ['Button', 'Entry', 'Text', 'Listbox',
                                              'Scale', 'Checkbutton', 'Radiobutton']:
                                focusable_list.append(child)
                        # Recursively check children
                        focusable_list.extend(get_all_focusable_widgets(child, []))
                except Exception:
                    pass
                return focusable_list

            focusable_widgets = get_all_focusable_widgets(parent_window)

            if not focusable_widgets:
                return None

            # Find the current widget in the list
            try:
                current_index = focusable_widgets.index(start_widget)
                # Return the next widget, or the first one if at the end
                next_index = (current_index + 1) % len(focusable_widgets)
                return focusable_widgets[next_index]
            except (ValueError, IndexError):
                # If start_widget not found, return the first focusable widget
                return focusable_widgets[0] if focusable_widgets else None

        except Exception:
            return None

    # Test cases
    print("Testing find_next_focusable_widget function...")

    # Test 1: btn1 -> btn2
    next_widget = find_next_focusable_widget(btn1, root)
    print(f"After btn1, next should be btn2: {next_widget == btn2}")

    # Test 2: btn2 -> btn3
    next_widget = find_next_focusable_widget(btn2, root)
    print(f"After btn2, next should be btn3: {next_widget == btn3}")

    # Test 3: btn3 -> btn1 (wraparound)
    next_widget = find_next_focusable_widget(btn3, root)
    print(f"After btn3, next should wrap to btn1: {next_widget == btn1}")

    # Test 4: None input
    next_widget = find_next_focusable_widget(None, root)
    print(f"With None input, should return None: {next_widget is None}")

    root.destroy()
    print("All tests completed!")

if __name__ == "__main__":
    print("Testing focus restoration logic...")
    test_find_next_focusable_widget()
