#!/usr/bin/env python3
"""
Demonstration of dynamic attributes vs dictionaries
"""

import tkinter as tk

def demonstrate_dynamic_attributes():
    root = tk.Tk()
    root.withdraw()  # Hide the window

    # Create a button
    button = tk.Button(root, text="Test Button")

    print("=== Before adding custom attributes ===")
    print(f"button.__dict__ keys: {list(button.__dict__.keys())}")

    # Method 1: Dictionary approach
    widget_states = {}
    widget_states["button"] = "active"
    print(f"\nDictionary approach: {widget_states}")

    # Method 2: Dynamic attribute approach
    button.state = "active"
    button.custom_data = {"user_id": 123}
    button.click_count = 0

    print(f"\n=== After adding custom attributes ===")
    print(f"button.state = {button.state}")
    print(f"button.custom_data = {button.custom_data}")
    print(f"button.click_count = {button.click_count}")

    print(f"\nbutton.__dict__ now contains:")
    for key, value in button.__dict__.items():
        if key in ['state', 'custom_data', 'click_count']:
            print(f"  {key}: {value}")

    # Prove they're the same
    print(f"\n=== Proving they're equivalent ===")
    print(f"button.state == button.__dict__['state']: {button.state == button.__dict__['state']}")

    # You can even access via __dict__
    button.__dict__['another_attribute'] = "direct dict access"
    print(f"button.another_attribute = {button.another_attribute}")

    # Check what happens with non-existent attributes
    try:
        print(f"button.nonexistent = {button.nonexistent}")
    except AttributeError as e:
        print(f"Accessing non-existent attribute: {e}")

    root.destroy()

if __name__ == "__main__":
    demonstrate_dynamic_attributes()
