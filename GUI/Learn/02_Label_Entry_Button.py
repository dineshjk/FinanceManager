# -*- coding: utf-8 -*-

import tkinter as tk  # CG tkinter is the built-in GUI library in Python for creating desktop applications.

# CG This function runs when the button is clicked or Enter is pressed.
def show_greeting():
    name = entry.get()  # CG .get() method retrieves the text from the Entry widget.
    if name:
        # CG Updates the label_result with a personalized greeting.
        label_result.config(text=f"Hello, {name}!")
    else:
        # CG Shows an alternate message if the input is empty.
        label_result.config(text="Please enter your name.")

# CG Create the main application window.
root = tk.Tk()  # CG tk.Tk() creates the main window of the application.
root.title("Name Greeter")  # CG Sets the title text shown in the window’s title bar.
root.geometry("350x200")  # CG Sets the window size to 350 pixels wide and 200 pixels tall.

# Prompt Label
label_prompt = tk.Label(root, text="Enter your name:")  # CG A Label widget to prompt user input.
label_prompt.pack(pady=5)  # CG Adds the label to the window with 5 pixels of vertical padding.

# Entry box
# CG tk.Entry is a class (like a constructor) from the tkinter module — it creates a text input field.
# CG entry is just a variable name, it can be anything.
# CG width=30 sets the width of the entry box to 30 characters.
entry = tk.Entry(root, width=30)
entry.pack(pady=5)  # CG Adds the entry box to the window and makes it visible.
# CG pady=5 adds vertical padding of 5 pixels around the entry box for better spacing.
# CG pack() is a method that organizes widgets in blocks before placing them in the parent widget.

# CG Bind the Enter key to call the same function as the button click.
# CG <Return> is the event for the Enter key. The lambda passes the event but ignores it in the function call.
entry.bind("<Return>", lambda event: show_greeting())

# Button
button = tk.Button(root, text="Greet Me", command=show_greeting)  # CG Button that triggers show_greeting() when clicked.
button.pack(pady=10)  # CG Adds the button to the window with padding.

# Output label
label_result = tk.Label(root, text="")  # CG This label is initially empty and will be updated after user input.
label_result.pack(pady=10)  # CG Displays the result message.

# Run the GUI loop
root.mainloop()  # CG Starts the Tkinter event loop which waits for user interaction.
