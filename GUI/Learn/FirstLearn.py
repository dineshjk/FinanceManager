import tkinter as tk

# Create the main window
root = tk.Tk()
root.title("My First GUI")
root.geometry("300x150")  # width x height

# Add a label
label = tk.Label(root, text="Hello, GUI World!")
label.pack(pady=20)

# Run the application
root.mainloop()
