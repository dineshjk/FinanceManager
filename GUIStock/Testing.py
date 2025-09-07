import os
import sys
import sqlite3
from datetime import datetime, timedelta

import tkinter as tk
from tkinter import messagebox
from tkcalendar import DateEntry

# Add the root package to the path for IDE compatibility
try:
    # Add FinanceManager package to path for absolute imports
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if BASE_DIR not in sys.path:
        sys.path.insert(0, BASE_DIR)

    # Now use absolute imports
    from FinanceManager.GUIStock.config.globals import DB_PATH, logger
    from FinanceManager.GUIStock.dbutils import (
        add_company, get_all_companies, delete_company
    )
except ImportError as e:
    print(f"Import error: {e}")
    # Fallback to old path-based imports if needed
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DB_PATH = os.path.abspath(os.path.join(BASE_DIR, 'Stocks', 'StockData', 'guimyfolio.db'))

# Future shared values (examples)
APP_TITLE = "Birth Chart"
APP_VERSION = "1.0"
DATA_ENTRY_TITLE = "Data Entry"

def exit_program(win):
    win.destroy()


def enter_data(parent):

    # Prevent duplicate window
    for child in parent.winfo_children(): # CG loop through all children of the parent window
        if isinstance(child, tk.Toplevel) and child.title() == "Data Entry - Child":
            child.lift() # CG bring the existing window to the front. The first one found with this tile will be lifted.
            return

    win = tk.Toplevel(parent)
    win.title("Data Entry - Child")
    win.geometry("520x320")
    win.resizable(False, False)
    win.transient(parent)
    win.grab_set()

    tk.Label(win, text="Data Entry", font=("Helvetica", 16, "bold"),
             bg="navy", fg="white", pady=5).pack(fill="x")

    form_frame = tk.Frame(win, padx=10, pady=10)
    form_frame.pack(fill="both", expand=True)

    entries = {}

    # --- Child Name ---
    tk.Label(form_frame, text="Child Name").grid(row=0, column=0, sticky="w", pady=2)
    child_name_entry = tk.Entry(form_frame, width=38)
    child_name_entry.grid(row=0, column=1, pady=2, sticky="w")
    entries["child_name"] = child_name_entry

    # --- Birth Date ---
    tk.Label(form_frame, text="Birth Date").grid(row=1, column=0, sticky="w", pady=2)
    birth_date_entry = DateEntry(form_frame, date_pattern="yyyy-mm-dd", width=12)
    birth_date_entry.grid(row=1, column=1, pady=2, sticky="w")
    entries["birth_date"] = birth_date_entry

    # win.wait_window(win)









def main_gui():
    root = tk.Tk()  # Create the main window
    root.title(APP_TITLE) # Set the title of the window
    root.geometry("400x300") # Set the size of the window
    root.resizable(False, False)

    title = tk.Label(root, text=APP_TITLE, font=("Helvetica", 16, "bold")) # Create a title label
    title.pack(pady=20) # Add some padding around the title

    btn_specs = [ # Define button specifications
        ("Calendar", lambda: enter_data(root)),
        ("Exit", lambda: exit_program(root))
    ]

    buttons = [] # List to hold button references for navigation

    for label, command in btn_specs: # Create buttons based on specifications
        btn = tk.Button(root, text=label, width=25, font=("Helvetica", 12), activeforeground="red", activebackground="lightblue", command=command)
        btn.pack(pady=5)
        buttons.append(btn)

    enable_button_navigation(root, buttons)  # ✅ Reusable navigation

    root.mainloop()


def enable_button_navigation(window, buttons):
    """
    Enables Up/Down arrow navigation and Enter key activation for a list of Tkinter buttons.
    """
    current_index = [0]  # Mutable to allow inner function modification
    buttons[0].focus_set()

    def on_key(event):
        key = event.keysym
        if key == "Down":
            current_index[0] = (current_index[0] + 1) % len(buttons)
            buttons[current_index[0]].focus_set()
        elif key == "Up":
            current_index[0] = (current_index[0] - 1) % len(buttons)
            buttons[current_index[0]].focus_set()
        elif key == "Return":
            buttons[current_index[0]].invoke()

    window.bind("<Up>", on_key)
    window.bind("<Down>", on_key)
    window.bind("<Return>", on_key)




# Run the GUI
if __name__ == "__main__":
    main_gui()
