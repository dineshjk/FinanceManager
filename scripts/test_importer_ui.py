# -*- coding: utf-8 -*-
# scripts/test_importer_ui.py
"""Programmatic UI test for the importer modal.

Run this from the project root. It opens a hidden root Tk window and calls
`trade_entry_from_file` twice; the second call should focus the existing
modal and not create a second one.

This is intended to be run on the same machine where the GUI is visible.
"""
import sys, os, time
proj_root = os.path.dirname(os.path.dirname(__file__))
if proj_root not in sys.path:
    sys.path.insert(0, proj_root)

import tkinter as tk
from StockMan.trade_from_file import trade_entry_from_file, _importer_open

root = tk.Tk()
root.withdraw()
print('initial _importer_open:', _importer_open)
print('Opening first importer modal...')
trade_entry_from_file(root, auto_close=True, auto_choose=False, dry_run=True)
print('after first call _importer_open:', getattr(sys.modules['StockMan.trade_from_file'], '_importer_open', None))
print('Attempting second importer modal call...')
trade_entry_from_file(root, auto_close=True, auto_choose=False, dry_run=True)
print('after second call _importer_open:', getattr(sys.modules['StockMan.trade_from_file'], '_importer_open', None))

# short sleep so scheduled closes complete
root.update()
time.sleep(0.2)
root.destroy()
print('Done')
