# -*- coding: utf-8 -*-
# C:\Users\aumji\source\repos\Finance\FinanceManager\GUIStock\config\globals.py

from contextlib import contextmanager
import logging
import os




# Database path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.abspath(os.path.join(BASE_DIR, '..', 'Stocks', 'StockData', 'myfolio.db'))
LOG_PATH = os.path.join(BASE_DIR, 'logs', 'stock_portfolio.log')
from typing import Generator

APP_TITLE = "Stock Portfolio Management"
APP_VERSION = "1.0"

# Utility function for consistent DB connection and access to globals
import sqlite3


class ValidationError(Exception):
    """Custom exception for validation errors."""



ETCN = 0.00003313 # Tested numbers 0.0000307, 0.0000331, 0.0000332, 0.00003315
ETCB = 0.000035 # Tested numbers 0.0000307
BROK = 0.0022  # Brokerage rate
GST = 0.18  # GST rate
SEBI = 0.000001  # SEBI charges rate
STT = 0.000862 # Tried (High) 0.001 0.000863


# Database Connection Management
@contextmanager
def get_db_connection() -> Generator[sqlite3.Connection, None, None]:
    """Context manager for database connections."""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        yield conn
    except sqlite3.Error as e:
        logger.error("Database error: %s", e, exc_info=True)
        raise
    finally:
        if conn:
            conn.close()

# Configure logging
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename=LOG_PATH
)
logger = logging.getLogger('GUIStock')


