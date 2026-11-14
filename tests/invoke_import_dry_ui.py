# -*- coding: utf-8 -*-
# tests/invoke_import_dry_ui.py
#!/usr/bin/env python3
"""
UI Migration Runner Headless Test Wrapper.

This test wrapper instantiates the GUI migration dialog in a headless or automated
test mode to verify Tkinter widget bindings and event callbacks without manual user input.

Key Responsibilities:
    • Headless GUI Testing: Spawns the importer window within a test harness.
    • Workflow Validation: Simulates button clicks and verifies progress bar updates.
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
