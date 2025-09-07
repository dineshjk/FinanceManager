#!/usr/bin/env python3
"""
Test script to debug combobox progressive search issues
"""
import tkinter as tk
from tkinter import ttk

# Test data similar to company names
test_companies = [
    "Aditya Birla Fashion & Retail Ltd (ABFRL)",
    "Aditya Birla Lifestyle Brands Limited (ADILIF)",
    "Adani Ports and Special Economic Zone Limited (ADANIPORTS)",
    "Avenue Supermarts Limited DMART (DMART)",
    "Bajaj Finance Limited (BAJFINANCE)",
    "Bank of Baroda (BANKBARODA)",
    "Bharat Heavy Electricals Limited (BHEL)"
]

def create_debug_window():
    root = tk.Tk()
    root.title("Combobox Debug Test")
    root.geometry("600x400")

    # Main frame
    frame = tk.Frame(root, padx=20, pady=20)
    frame.pack(fill="both", expand=True)

    # Label
    label = tk.Label(frame, text="Test Progressive Search:", font=("Arial", 12, "bold"))
    label.pack(pady=(0, 10))

    # Create combobox
    company_var = tk.StringVar()
    combo = ttk.Combobox(frame, textvariable=company_var, width=60, font=("Arial", 10))
    combo['values'] = test_companies
    combo.pack(pady=5)

    # Debug info display
    debug_text = tk.Text(frame, height=15, width=80, font=("Courier", 9))
    debug_text.pack(pady=(10, 0), fill="both", expand=True)

    def log_debug(message):
        debug_text.insert(tk.END, f"{message}\n")
        debug_text.see(tk.END)
        root.update_idletasks()

    # Setup progressive search with debugging
    combo._ignore_next_event = False
    combo._user_typing = False

    def on_key_release(event):
        log_debug(f"Key: {event.keysym}, Text: '{combo.get()}', Cursor: {combo.index(tk.INSERT)}, Selection: {combo.selection_get() if combo.selection_present() else 'None'}")

        # Skip if we should ignore this event
        if getattr(combo, '_ignore_next_event', False):
            log_debug("  -> Ignoring event due to flag")
            combo._ignore_next_event = False
            return

        # Skip navigation and special keys
        if event.keysym in ['Up', 'Down', 'Left', 'Right', 'Tab', 'Return', 'Escape']:
            if event.keysym == 'Escape':
                log_debug("  -> Escape pressed - clearing")
                combo.set('')
                combo['values'] = test_companies
                combo._user_typing = False
            return

        # Handle backspace and delete
        if event.keysym in ['BackSpace', 'Delete']:
            current = combo.get()
            log_debug(f"  -> Backspace/Delete - text now: '{current}'")
            combo._user_typing = True
            if not current:
                combo['values'] = test_companies
            else:
                matches = [item for item in test_companies if item.lower().startswith(current.lower())]
                combo['values'] = matches
                log_debug(f"  -> Filtered to {len(matches)} matches")
            return

        # Get current text
        current = combo.get()
        if not current:
            combo['values'] = test_companies
            combo._user_typing = False
            return

        combo._user_typing = True

        # Find matches
        matches = [item for item in test_companies if item.lower().startswith(current.lower())]
        log_debug(f"  -> Found {len(matches)} matches for '{current}'")

        # Update dropdown
        combo['values'] = matches

        # Auto-complete logic
        if matches and len(current) > 0:
            cursor_pos = combo.index(tk.INSERT)
            log_debug(f"  -> Cursor at {cursor_pos}, text length {len(current)}")

            # Only auto-complete if cursor is at end
            if cursor_pos == len(current):
                first_match = matches[0]
                log_debug(f"  -> Auto-completing to '{first_match}'")

                combo._ignore_next_event = True
                combo.set(first_match)
                combo.select_range(cursor_pos, len(first_match))
                combo.icursor(cursor_pos)
                log_debug(f"  -> Selected range {cursor_pos} to {len(first_match)}")

    def on_selection(event):
        log_debug(f"Selection event: '{combo.get()}'")

    def on_focus_out(event):
        log_debug(f"Focus out: '{combo.get()}'")

    # Bind events
    combo.bind('<KeyRelease>', on_key_release)
    combo.bind('<<ComboboxSelected>>', on_selection)
    combo.bind('<FocusOut>', on_focus_out)

    # Clear button
    clear_btn = tk.Button(frame, text="Clear Debug", command=lambda: debug_text.delete(1.0, tk.END))
    clear_btn.pack(pady=(5, 0))

    # Focus on combobox
    combo.focus_set()

    log_debug("Combobox debug test ready. Start typing...")

    return root

if __name__ == "__main__":
    root = create_debug_window()
    root.mainloop()
