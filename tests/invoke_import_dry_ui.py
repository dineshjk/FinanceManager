#!/usr/bin/env python3
"""Open a hidden root and call the trade menu Import (dry-run) action.
This simulates a user pressing the Import (dry-run) button.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import tkinter as tk
from StockMan.trade_menu import show_trade_menu_modal

root = tk.Tk()
root.withdraw()
# Show the menu modal; user would click Import (dry-run). We directly call
# the menu routine so code constructs the menu (buttons) and waits on modal.
show_trade_menu_modal(root)
print("Menu modal returned")
root.destroy()
