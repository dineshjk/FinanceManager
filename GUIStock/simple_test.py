import tkinter as tk
from dbutils.company_utils import add_company

# Create root window
root = tk.Tk()
root.withdraw()  # Hide the root window

# Call add_company directly - this will open the enhanced window
add_company(root)

# Keep the program running
root.mainloop()
