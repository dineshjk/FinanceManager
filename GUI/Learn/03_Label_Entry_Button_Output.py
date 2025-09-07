# -*- coding: utf-8 -*-

# File: 03_Label_Entry_Button_Output.py

import tkinter as tk

def greet_user():
    name = entry.get()
    if name.strip():
        message.set(f"Hello, {name}!")
    else:
        message.set("Please enter your name.")

# Create main window
root = tk.Tk()
root.title("Greeting App")

# Create widgets
label = tk.Label(root, text="Enter your name:")
entry = tk.Entry(root)
button = tk.Button(root, text="Greet", command=greet_user)
message = tk.StringVar()
output = tk.Label(root, textvariable=message, fg="blue")

# Arrange widgets using grid
label.grid(row=0, column=0, padx=10, pady=5, sticky="e")
entry.grid(row=0, column=1, padx=10, pady=5)
button.grid(row=1, column=0, columnspan=2, pady=5)
output.grid(row=2, column=0, columnspan=2, pady=5)

# Run the main loop
root.mainloop()
