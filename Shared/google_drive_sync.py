# -*- coding: utf-8 -*-
# Shared/google_drive_sync.py

"""
Google Drive Cloud Synchronization Proxy & Adapter.

This module acts as a centralized cross-module facade for Google Drive synchronization
services. It re-exports and adapts synchronization functions from `StockMan.drive_sync`
so that BankMan, the main dashboard, or external scripts can initiate cloud backups
and workbook synchronizations without tight coupling to internal StockMan sub-packages.

Key Responsibilities:
    • Façade Pattern: Provides clean, uniform access to Google Drive upload, download,
      and token authentication capabilities.
    • Background Threading: Supports asynchronous synchronization to prevent UI freezing
      during slow network transfers.
    • Portfolio Workbook Sync: Bridges the automated upload of 'StockMan_Portfolio.xlsx'
      and database snapshot archives to user-configured Google Drive directories.

Key Re-exports & Functions:
    • `sync_to_drive(...)`: Uploads local files/workbooks to Google Drive.
    • `sync_from_drive(...)`: Downloads latest remote backups from Google Drive.
    • `is_drive_available()`: Checks token validity and cloud connectivity.
"""

from StockMan.drive_sync import (
    read_investment_parameters,
    prompt_startup_parameters_dialog,
    update_portfolio_excel,
    get_drive_service,
    upload_portfolio_to_drive,
    download_latest_pick_of_the_day,
    sync_two_way_pipeline,
    get_local_pick_of_the_day,
    run_startup_sequence,
    should_prompt_user_today,
    record_startup_prompt_completed,
    get_current_day_cycle_start,
    PORTFOLIO_EXCEL_PATH,
    DATA_DIR,
    SCOPES,
    STATE_FILE_PATH,
)

__all__ = [
    "read_investment_parameters",
    "prompt_startup_parameters_dialog",
    "update_portfolio_excel",
    "get_drive_service",
    "upload_portfolio_to_drive",
    "download_latest_pick_of_the_day",
    "sync_two_way_pipeline",
    "get_local_pick_of_the_day",
    "run_startup_sequence",
    "should_prompt_user_today",
    "record_startup_prompt_completed",
    "get_current_day_cycle_start",
    "PORTFOLIO_EXCEL_PATH",
    "DATA_DIR",
    "SCOPES",
    "STATE_FILE_PATH",
]
