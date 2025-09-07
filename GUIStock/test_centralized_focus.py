#!/usr/bin/env python3
"""
Comprehensive test of the centralized focus restoration system.

This demonstrates how the centralized focus restoration works across
multiple modal windows and different scenarios.
"""

import tkinter as tk
import sys
import os

# Add the GUIStock directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dbutils.focus_utils import restore_focus_to_next_button, ModalWindowManager
from dbutils.company_utils import add_company, update_company


def create_demo_modal(parent, calling_button, modal_title="Demo Modal"):
    """Create a simple demo modal window using centralized focus restoration."""

    # Create modal window
    modal = tk.Toplevel(parent)
    modal.title(modal_title)
    modal.geometry("300x200")
    modal.resizable(False, False)
    modal.transient(parent)
    modal.grab_set()

    # Disable parent for true modality
    parent.attributes('-disabled', True)

    # Add content
    tk.Label(modal, text=f"{modal_title}",
            font=("Helvetica", 14, "bold")).pack(pady=20)

    tk.Label(modal, text="This modal uses centralized\nfocus restoration!",
            justify=tk.CENTER).pack(pady=10)

    # Buttons
    btn_frame = tk.Frame(modal)
    btn_frame.pack(pady=20)

    def close_modal():
        modal.destroy()
        # Use centralized focus restoration
        restore_focus_to_next_button(parent, calling_button)

    tk.Button(btn_frame, text="✅ OK", command=close_modal,
             bg="#4CAF50", fg="white", padx=20).pack(side=tk.LEFT, padx=5)

    tk.Button(btn_frame, text="❌ Cancel", command=close_modal,
             bg="#f44336", fg="white", padx=20).pack(side=tk.LEFT, padx=5)

    # Bind Escape key
    modal.bind("<Escape>", lambda e: close_modal())

    # Wait for modal to close
    modal.wait_window()


def create_context_manager_demo(parent, calling_button):
    """Demonstrate the ModalWindowManager context manager."""

    with ModalWindowManager(parent, calling_button) as modal_mgr:
        modal_mgr.setup_window("Context Manager Demo", "350x250")
        modal_mgr.add_escape_binding(modal_mgr.window.destroy)

        # Add content
        tk.Label(modal_mgr.window,
                text="Context Manager Demo",
                font=("Helvetica", 14, "bold")).pack(pady=20)

        tk.Label(modal_mgr.window,
                text="This modal uses the ModalWindowManager\ncontext manager for automatic\nfocus restoration!",
                justify=tk.CENTER).pack(pady=10)

        # Button
        tk.Button(modal_mgr.window, text="🔄 Close",
                 command=modal_mgr.window.destroy,
                 bg="#2196F3", fg="white", padx=30).pack(pady=20)

        # Wait for modal to close (focus restored automatically by context manager)
        modal_mgr.window.wait_window()


def create_main_test_window():
    """Create the main test window with multiple buttons."""

    root = tk.Tk()
    root.title("🎯 Centralized Focus Restoration Test")
    root.geometry("600x500")

    # Title
    title = tk.Label(root, text="🎯 Centralized Focus Restoration Test",
                    font=("Helvetica", 18, "bold"), fg="#2E7D32")
    title.pack(pady=20)

    # Instructions
    instructions = tk.Text(root, height=8, width=70, wrap=tk.WORD)
    instructions.pack(pady=10)
    instructions.insert(tk.END,
        "INSTRUCTIONS:\n"
        "1. Click any button below to open a modal window\n"
        "2. Close the modal (OK, Cancel, Escape, or X button)\n"
        "3. Notice that focus automatically moves to the NEXT button\n"
        "4. Press Enter to verify the correct button has focus\n\n"
        "TEST SCENARIOS:\n"
        "• Simple Modal: Basic demo using centralized restoration\n"
        "• Context Manager: Uses ModalWindowManager class\n"
        "• Add Company: Real function with centralized restoration\n"
        "• Update Company: Real function with centralized restoration\n"
    )
    instructions.config(state=tk.DISABLED)

    # Button frame
    button_frame = tk.Frame(root)
    button_frame.pack(pady=20)

    # Create test buttons
    buttons = []

    # Row 1: Demo modals
    row1 = tk.Frame(button_frame)
    row1.pack(pady=5)

    btn1 = tk.Button(row1, text="1️⃣ Simple Modal", width=20, height=2,
                     bg="#E3F2FD", font=("Arial", 10, "bold"))
    btn1.pack(side=tk.LEFT, padx=5)
    buttons.append(btn1)

    btn2 = tk.Button(row1, text="2️⃣ Context Manager", width=20, height=2,
                     bg="#F3E5F5", font=("Arial", 10, "bold"))
    btn2.pack(side=tk.LEFT, padx=5)
    buttons.append(btn2)

    # Row 2: Real functions
    row2 = tk.Frame(button_frame)
    row2.pack(pady=5)

    btn3 = tk.Button(row2, text="3️⃣ Add Company", width=20, height=2,
                     bg="#E8F5E8", font=("Arial", 10, "bold"))
    btn3.pack(side=tk.LEFT, padx=5)
    buttons.append(btn3)

    btn4 = tk.Button(row2, text="4️⃣ Update Company", width=20, height=2,
                     bg="#FFF3E0", font=("Arial", 10, "bold"))
    btn4.pack(side=tk.LEFT, padx=5)
    buttons.append(btn4)

    # Row 3: Navigation buttons
    row3 = tk.Frame(button_frame)
    row3.pack(pady=15)

    btn5 = tk.Button(row3, text="5️⃣ Next Button", width=20, height=2,
                     bg="#FFEBEE", font=("Arial", 10, "bold"),
                     command=lambda: print("✅ Button 5 clicked - Focus restoration working!"))
    btn5.pack(side=tk.LEFT, padx=5)
    buttons.append(btn5)

    btn6 = tk.Button(row3, text="6️⃣ Final Button", width=20, height=2,
                     bg="#F1F8E9", font=("Arial", 10, "bold"),
                     command=lambda: print("✅ Button 6 clicked - Focus restoration working!"))
    btn6.pack(side=tk.LEFT, padx=5)
    buttons.append(btn6)

    # Set up button commands after creation (so they can reference each other)
    btn1.config(command=lambda: create_demo_modal(root, btn1, "Simple Modal Demo"))
    btn2.config(command=lambda: create_context_manager_demo(root, btn2))
    btn3.config(command=lambda: add_company(root, btn3))
    btn4.config(command=lambda: update_company(root, btn4))

    # Exit button
    exit_btn = tk.Button(root, text="🚪 Exit Test", command=root.destroy,
                        bg="#FFCDD2", font=("Arial", 12, "bold"),
                        width=15, height=2)
    exit_btn.pack(pady=20)

    # Status label
    status = tk.Label(root, text="✅ Ready! Click any button to test focus restoration.",
                     font=("Arial", 11), fg="#1B5E20")
    status.pack(pady=10)

    # Enable keyboard navigation
    def on_tab(event):
        """Handle Tab navigation between buttons."""
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

    root.bind('<Tab>', on_tab)

    # Set initial focus
    btn1.focus_set()

    return root


if __name__ == "__main__":
    print("🎯 Starting Centralized Focus Restoration Test...")
    print("\nThis test demonstrates:")
    print("  ✅ Centralized focus restoration utilities")
    print("  ✅ Automatic next button focusing")
    print("  ✅ ModalWindowManager context manager")
    print("  ✅ Integration with real company functions")
    print("\nWatch how focus moves to the next button after closing modals!")

    try:
        root = create_main_test_window()
        root.mainloop()
    except Exception as e:
        print(f"❌ Error running test: {e}")
        import traceback
        traceback.print_exc()

    print("\n🎯 Test completed!")
