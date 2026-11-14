# -*- coding: utf-8 -*-
# scripts/inspect_legacy_tx.py
"""
Low-Level Legacy Transaction Inspector & Schema Debugger.

This diagnostic tool dumps and inspects raw transaction records, polymorphic keys, and
legacy field formats directly from legacy database files.

Key Responsibilities:
    • Schema Diagnostics: Inspects raw SQLite table structures and dumps sample records
      for debugging migration parsers.
    • Polymorphic Key Analysis: Validates legacy reference ID patterns to guide mapping logic.
"""

from pathlib import Path
import sys
sys.path.insert(0, str(Path('.').resolve()))
from tests.trade_file import _fetch_source_transactions
import json

LEGACY = r"C:\Data\Personal\Finance_and_Investment\finprog\FinanceManager\data\mystocks_old.db"
rows = _fetch_source_transactions(LEGACY)
print('rows:', len(rows))
if rows:
    print(json.dumps(rows[0], indent=2, default=str))
