# -*- coding: utf-8 -*-
# scripts/inspect_legacy_tx.py
from pathlib import Path
import sys
sys.path.insert(0, str(Path('.').resolve()))
from StockMan.trade_from_file import _fetch_source_transactions
import json

LEGACY = r"C:\Data\Personal\Finance_and_Investment\finprog\FinanceManager\data\mystocks_old.db"
rows = _fetch_source_transactions(LEGACY)
print('rows:', len(rows))
if rows:
    print(json.dumps(rows[0], indent=2, default=str))
