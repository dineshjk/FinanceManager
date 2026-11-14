# -*- coding: utf-8 -*-
# scripts/test_importer_ui.py
"""
Graphical Migration Importer Launcher & Workflow Runner.

This script launches the Tkinter graphical user interface for the interactive data migration
and statement importer tool.

Key Responsibilities:
    • GUI Launcher: Spawns the interactive importer window, providing file choosers, progress bars,
      and dry-run validation logs for non-technical users.
    • Subsystem Coordination: Integrates with `Shared.window_manager` to safely run migrations
      within the Universal Finance Manager application window hierarchy.
"""
import sys
import os
import time
proj_root = os.path.dirname(os.path.dirname(__file__))
if proj_root not in sys.path:
    sys.path.insert(0, proj_root)

import tkinter as tk
from StockMan.trade_from_file import trade_entry_from_file

if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    print('Opening first importer modal...')
    trade_entry_from_file(root)
    print('Attempting second importer modal call...')
    trade_entry_from_file(root)
    
    # short sleep so scheduled closes complete
    root.update()
    time.sleep(0.2)
    root.destroy()
    print('Done')
