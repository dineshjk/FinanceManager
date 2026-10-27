# -*- coding: utf-8 -*-
# Shared/google_drive_sync.py

"""
Google Drive integration alias module for Universal Finance Manager.
Re-exports functionality from StockMan.drive_sync.
"""

from StockMan.drive_sync import (
    read_investment_parameters,
    prompt_startup_parameters_dialog,
    update_portfolio_excel,
    get_drive_service,
    upload_portfolio_to_drive,
    download_latest_pick_of_the_day,
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
