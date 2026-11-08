# -*- coding: utf-8 -*-
# tests/test_drive_sync.py

"""
Unit tests for StockMan Google Drive integration and startup sequence.
"""

import os
import tempfile
import sqlite3
import pytest
from unittest.mock import MagicMock, patch

import openpyxl

from StockMan import drive_sync


def test_reset_startup_cycle_to_first_run():
    """Verify reset_startup_cycle_to_first_run resets state so should_prompt_user_today returns True."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f_state, \
         tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f_xlsx:
        state_path = f_state.name
        xlsx_path = f_xlsx.name

    try:
        # Simulate having completed startup today
        drive_sync.record_startup_prompt_completed(2000000.0, 50000.0, state_file=state_path)
        assert drive_sync.should_prompt_user_today(state_file=state_path, excel_path=xlsx_path) is False

        # Reset cycle to first run
        drive_sync.reset_startup_cycle_to_first_run(state_file=state_path, excel_path=xlsx_path)
        assert drive_sync.should_prompt_user_today(state_file=state_path, excel_path=xlsx_path) is True
    finally:
        if os.path.exists(state_path):
            os.remove(state_path)
        if os.path.exists(xlsx_path):
            os.remove(xlsx_path)


def test_read_investment_parameters_nonexistent():
    """Verify default values are returned when Excel file does not exist."""
    app, cash = drive_sync.read_investment_parameters("non_existent_file.xlsx")
    assert app == drive_sync.DEFAULT_APPETITE
    assert cash == drive_sync.DEFAULT_CASH


def test_read_investment_parameters_from_excel():
    """Verify parameters are read accurately from Row 1 & Row 2."""
    tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    tmp_path = tmp.name
    tmp.close()

    try:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.cell(1, 1, "Current Appetite")
        ws.cell(1, 2, 2500000.0)
        ws.cell(2, 1, "Cash Available for Investment")
        ws.cell(2, 2, 350000.0)
        wb.save(tmp_path)
        wb.close()

        app, cash = drive_sync.read_investment_parameters(tmp_path)
        assert app == 2500000.0
        assert cash == 350000.0
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_update_portfolio_excel_structure_and_sqlite_data():
    """Verify update_portfolio_excel writes Row 1, Row 2, Row 3 headers, and stock records."""
    db_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_path = db_tmp.name
    db_tmp.close()

    xlsx_tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    xlsx_path = xlsx_tmp.name
    xlsx_tmp.close()

    try:
        # Create a mock stocks table
        conn = sqlite3.connect(db_path)
        try:
            conn.execute("""
                CREATE TABLE stocks (
                    id_stk INTEGER PRIMARY KEY,
                    stk_code TEXT,
                    isin TEXT,
                    company_name TEXT,
                    curr_avg_price REAL,
                    buy_qty INTEGER,
                    sell_qty INTEGER
                )
            """)
            conn.execute("""
                INSERT INTO stocks VALUES
                (1, 'HAL', 'INE066F01012', 'Hindustan Aeronautics Limited', 4850.50, 100, 20),
                (2, 'TCS', 'INE467B01029', 'Tata Consultancy Services', 3500.00, 50, 50)
            """)
            conn.commit()
        finally:
            conn.close()

        # Write to Excel
        drive_sync.update_portfolio_excel(
            excel_path=xlsx_path,
            current_appetite=1800000.0,
            cash_available=150000.0,
            db_path=db_path,
        )

        # Inspect generated workbook
        wb = openpyxl.load_workbook(xlsx_path, data_only=True)
        ws = wb.active

        # Check Row 1 and Row 2
        assert ws.cell(1, 1).value == "Current Appetite"
        assert ws.cell(1, 2).value == 1800000.0
        assert ws.cell(2, 1).value == "Cash Available for Investment"
        assert ws.cell(2, 2).value == 150000.0

        # Check Row 3 Headers
        expected_headers = [
            "id_stk",
            "stk_code",
            "isin",
            "company_name",
            "curr_avg_price",
            "current_qty",
            "curr_investment_amt",
        ]
        actual_headers = [ws.cell(3, c).value for c in range(1, 8)]
        assert actual_headers == expected_headers

        # Check Row 4 (HAL: qty = 100 - 20 = 80, amt = 80 * 4850.50 = 388040.0)
        assert ws.cell(4, 1).value == 1
        assert ws.cell(4, 2).value == "HAL"
        assert ws.cell(4, 3).value == "INE066F01012"
        assert ws.cell(4, 4).value == "Hindustan Aeronautics Limited"
        assert ws.cell(4, 5).value == 4850.50
        assert ws.cell(4, 6).value == 80
        assert ws.cell(4, 7).value == 388040.0

        # Check Row 5 (TCS: qty = 0, amt = 0)
        assert ws.cell(5, 1).value == 2
        assert ws.cell(5, 2).value == "TCS"
        assert ws.cell(5, 6).value == 0
        assert ws.cell(5, 7).value == 0.0

        # Verify Advice_Log sheet exists
        assert "Advice_Log" in wb.sheetnames
        ws_adv = wb["Advice_Log"]
        expected_adv_headers = [
            "Date of Advice",
            "The Advice Given",
            "Execution Status",
            "Execution Date",
            "Notes",
        ]
        assert [ws_adv.cell(1, c).value for c in range(1, 6)] == expected_adv_headers

        wb.close()
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)
        if os.path.exists(xlsx_path):
            os.remove(xlsx_path)


def test_get_local_pick_of_the_day_with_temp_dir():
    """Verify get_local_pick_of_the_day prioritizes latest alias and glob files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = os.path.join(temp_dir, "Pick_of_the_day_20261023.md")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("# 🏆 Pick of the Day Content")

        res = drive_sync.get_local_pick_of_the_day(data_dir=temp_dir)
        assert res is not None
        content, fname, mtime = res
        assert "# 🏆 Pick of the Day Content" in content
        assert fname == "Pick_of_the_day_20261023.md"


def test_upload_portfolio_to_drive_mock():
    """Verify upload_portfolio_to_drive handles folder lookup and file create/update."""
    mock_service = MagicMock()
    mock_files = mock_service.files.return_value

    # 1. Folder search returns Finance folder id 'folder_123'
    mock_files.list.return_value.execute.side_effect = [
        {"files": [{"id": "folder_123", "name": "Finance"}]},  # Folder list
        {"files": [{"id": "file_456", "name": "StockMan_Portfolio.xlsx"}]},  # File list
    ]
    mock_files.update.return_value.execute.return_value = {
        "id": "file_456",
        "name": "StockMan_Portfolio.xlsx",
        "modifiedTime": "2026-10-23T10:00:00Z",
    }

    tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    tmp_path = tmp.name
    tmp.close()

    try:
        res = drive_sync.upload_portfolio_to_drive(mock_service, tmp_path, folder_name="Finance")
        assert res["id"] == "file_456"
        assert res["status"] == "updated"
        assert mock_files.update.called
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_download_latest_pick_of_the_day_raw_markdown_native_media():
    """Verify download_latest_pick_of_the_day downloads raw text/markdown natively with alt=media."""
    mock_service = MagicMock()
    mock_files = mock_service.files.return_value

    # Folder list returns 'folder_123', files list returns Pick_of_the_day markdown file
    raw_markdown = (
        "# 🏆 Pick of the Day Report\n\n"
        "| Rank | Code | Score | Action |\n"
        "| :--- | :--- | :---- | :----- |\n"
        "| 1 | HDFC | 92 | ADD |\n"
    )

    mock_files.list.return_value.execute.side_effect = [
        {"files": [{"id": "folder_123", "name": "Finance"}]},
        {
            "files": [
                {
                    "id": "file_markdown_789",
                    "name": "Pick_of_the_day_20261023.md",
                    "mimeType": "text/markdown",
                    "createdTime": "2026-10-23T08:00:00Z",
                    "modifiedTime": "2026-10-23T08:30:00Z",
                }
            ]
        },
    ]

    with patch("StockMan.drive_sync.MediaIoBaseDownload") as mock_downloader_cls:
        mock_instance = MagicMock()
        # Simulate downloader writing content to stream
        def fake_next_chunk():
            return None, True

        mock_instance.next_chunk.side_effect = fake_next_chunk
        mock_downloader_cls.return_value = mock_instance

        with tempfile.TemporaryDirectory() as temp_dir:
            # Inject fake content into the buffer stream
            def mock_init(fh, req):
                fh.write(raw_markdown.encode("utf-8"))
                return mock_instance

            mock_downloader_cls.side_effect = mock_init

            res = drive_sync.download_latest_pick_of_the_day(
                mock_service, folder_name="Finance", dest_dir=temp_dir
            )
            assert res is not None
            saved_path, md_filename = res
            assert md_filename == "Pick_of_the_day_20261023.md"
            assert os.path.exists(saved_path)

            with open(saved_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Verify markdown table pipes are intact
            assert "| Rank | Code | Score | Action |" in content
            assert "| 1 | HDFC | 92 | ADD |" in content

            # Check standard alias file was also saved as .md
            alias_path = os.path.join(temp_dir, "Pick_of_the_day_latest.md")
            assert os.path.exists(alias_path)
            with open(alias_path, "r", encoding="utf-8") as f_alias:
                assert "| 1 | HDFC | 92 | ADD |" in f_alias.read()


def test_download_google_doc_exports_as_markdown():
    """Verify that Google Docs (application/vnd.google-apps.document) are exported with mimeType=text/markdown."""
    mock_service = MagicMock()
    mock_files = mock_service.files.return_value

    mock_doc_content = (
        "# 🏆 Google Doc Pick of the Day\n\n"
        "| Sector | Weight % |\n"
        "| :----- | :------- |\n"
        "| Defense | 39.50% |\n"
    ).encode("utf-8")

    mock_files.list.return_value.execute.side_effect = [
        {"files": [{"id": "folder_123", "name": "Finance"}]},
        {
            "files": [
                {
                    "id": "doc_pick_999",
                    "name": "Pick_of_the_day_Doc.md",
                    "mimeType": "application/vnd.google-apps.document",
                }
            ]
        },
    ]

    mock_export = mock_files.export_media.return_value
    mock_export.execute.return_value = mock_doc_content

    with tempfile.TemporaryDirectory() as temp_dir:
        res = drive_sync.download_latest_pick_of_the_day(
            mock_service, folder_name="Finance", dest_dir=temp_dir
        )
        assert res is not None
        saved_path, md_name = res
        assert md_name == "Pick_of_the_day_Doc.md"
        assert os.path.exists(saved_path)

        with open(saved_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "| Sector | Weight % |" in content
        assert "| Defense | 39.50% |" in content
        mock_files.export_media.assert_called_with(
            fileId="doc_pick_999", mimeType="text/markdown"
        )


def test_get_current_day_cycle_start():
    """Verify 8:00 AM cycle boundary calculations."""
    from datetime import datetime

    # Scenario A: Exactly at 8:00 AM
    dt_8am = datetime(2026, 10, 24, 8, 0, 0)
    cycle = drive_sync.get_current_day_cycle_start(dt_8am)
    assert cycle == datetime(2026, 10, 24, 8, 0, 0)

    # Scenario B: Afternoon (2:30 PM)
    dt_afternoon = datetime(2026, 10, 24, 14, 30, 0)
    cycle = drive_sync.get_current_day_cycle_start(dt_afternoon)
    assert cycle == datetime(2026, 10, 24, 8, 0, 0)

    # Scenario C: Early Morning (7:59 AM) -> belongs to yesterday's 8:00 AM cycle
    dt_early = datetime(2026, 10, 24, 7, 59, 59)
    cycle = drive_sync.get_current_day_cycle_start(dt_early)
    assert cycle == datetime(2026, 10, 23, 8, 0, 0)


def test_should_prompt_user_today_logic():
    """Verify once-a-day (8:00 AM cycle) prompt check."""
    import json
    from datetime import datetime

    with tempfile.TemporaryDirectory() as temp_dir:
        state_file = os.path.join(temp_dir, "test_state.json")
        fake_excel = os.path.join(temp_dir, "fake.xlsx")

        # 1. No state file, no excel -> should prompt
        now_morning = datetime(2026, 10, 24, 9, 0, 0)
        assert drive_sync.should_prompt_user_today(state_file=state_file, excel_path=fake_excel, now=now_morning) is True

        # 2. Record completion at 9:05 AM on 2026-10-24
        completed_at = datetime(2026, 10, 24, 9, 5, 0)
        drive_sync.record_startup_prompt_completed(
            1800000.0, 150000.0, state_file=state_file, timestamp=completed_at
        )

        # 3. Same day at 2:00 PM -> should NOT prompt
        now_afternoon = datetime(2026, 10, 24, 14, 0, 0)
        assert drive_sync.should_prompt_user_today(state_file=state_file, excel_path=fake_excel, now=now_afternoon) is False

        # 4. Next day before 8:00 AM (e.g. 7:30 AM) -> same cycle -> should NOT prompt
        next_early = datetime(2026, 10, 25, 7, 30, 0)
        assert drive_sync.should_prompt_user_today(state_file=state_file, excel_path=fake_excel, now=next_early) is False

        # 5. Next day after 8:00 AM (e.g. 8:01 AM) -> new cycle -> SHOULD prompt
        next_cycle = datetime(2026, 10, 25, 8, 1, 0)
        assert drive_sync.should_prompt_user_today(state_file=state_file, excel_path=fake_excel, now=next_cycle) is True


def test_fetch_live_cmp_with_ns_suffix():
    """Verify fetch_live_cmp appends .NS for NSE equities and queries yfinance."""
    with patch("StockMan.drive_sync.yf") as mock_yf:
        mock_ticker_instance = MagicMock()
        mock_ticker_instance.fast_info = {"lastPrice": 1250.50}
        mock_yf.Ticker.return_value = mock_ticker_instance

        # Test ticker without suffix
        cmp1 = drive_sync.fetch_live_cmp("INFY")
        mock_yf.Ticker.assert_called_with("INFY.NS")
        assert cmp1 == 1250.50

        # Test ticker with existing .NS suffix
        cmp2 = drive_sync.fetch_live_cmp("TCS.NS")
        mock_yf.Ticker.assert_called_with("TCS.NS")
        assert cmp2 == 1250.50


def test_build_portfolio_dataframe_pnl_calculations():
    """Verify build_portfolio_dataframe computes Unrealized PnL Amount and Percentage accurately."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        conn = sqlite3.connect(db_path)
        try:
            conn.execute("""
                CREATE TABLE stocks (
                    id_stk INTEGER PRIMARY KEY,
                    stk_code TEXT,
                    isin TEXT,
                    company_name TEXT,
                    curr_avg_price REAL,
                    buy_qty INTEGER,
                    sell_qty INTEGER
                )
            """)
            conn.execute("""
                INSERT INTO stocks VALUES
                (1, 'HAL', 'INE066F01012', 'Hindustan Aeronautics Limited', 4000.0, 50, 10),
                (2, 'TCS', 'INE467B01029', 'Tata Consultancy Services', 3000.0, 20, 0),
                (3, 'ZERO_AVG', 'INE000000000', 'Zero Average Scrip', 0.0, 10, 0)
            """)
            conn.commit()
        finally:
            conn.close()

        mock_prices = {
            "HAL": 5000.0,
            "TCS": 2700.0,
            "ZERO_AVG": 100.0,
        }
        with patch("StockMan.drive_sync.fetch_multiple_cmp", return_value=mock_prices):
            df = drive_sync.build_portfolio_dataframe(db_path=db_path)

        assert "CMP" in df.columns
        assert "Unrealized_PnL_Amount" in df.columns
        assert "Unrealized_PnL_Percentage" in df.columns

        row_hal = df[df["stk_code"] == "HAL"].iloc[0]
        assert row_hal["CMP"] == 5000.0
        assert row_hal["Unrealized_PnL_Amount"] == 40000.0
        assert row_hal["Unrealized_PnL_Percentage"] == 25.0

        row_tcs = df[df["stk_code"] == "TCS"].iloc[0]
        assert row_tcs["CMP"] == 2700.0
        assert row_tcs["Unrealized_PnL_Amount"] == -6000.0
        assert row_tcs["Unrealized_PnL_Percentage"] == -10.0

        row_zero = df[df["stk_code"] == "ZERO_AVG"].iloc[0]
        assert row_zero["CMP"] == 100.0
        assert row_zero["Unrealized_PnL_Amount"] == 1000.0
        assert row_zero["Unrealized_PnL_Percentage"] == 0.0

    finally:
        if os.path.exists(db_path):
            os.remove(db_path)


def test_update_portfolio_excel_exports_pnl_columns():
    """Verify update_portfolio_excel writes the three new columns to StockMan_Portfolio.xlsx."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f_db, \
         tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f_xlsx:
        db_path = f_db.name
        xlsx_path = f_xlsx.name

    try:
        conn = sqlite3.connect(db_path)
        try:
            conn.execute("""
                CREATE TABLE stocks (
                    id_stk INTEGER PRIMARY KEY,
                    stk_code TEXT,
                    isin TEXT,
                    company_name TEXT,
                    curr_avg_price REAL,
                    buy_qty INTEGER,
                    sell_qty INTEGER
                )
            """)
            conn.execute("""
                INSERT INTO stocks VALUES
                (1, 'INFY', 'INE009A01021', 'Infosys Ltd', 1500.0, 100, 0)
            """)
            conn.commit()
        finally:
            conn.close()

        with patch("StockMan.drive_sync.fetch_multiple_cmp", return_value={"INFY": 1800.0}):
            out_file = drive_sync.update_portfolio_excel(
                excel_path=xlsx_path,
                current_appetite=1000000.0,
                cash_available=50000.0,
                db_path=db_path,
            )

        assert out_file == xlsx_path
        wb = openpyxl.load_workbook(xlsx_path, data_only=True)
        ws = wb["Portfolio"]

        # Row 3 headers must include CMP, Unrealized_PnL_Amount, Unrealized_PnL_Percentage
        headers = [ws.cell(3, c).value for c in range(1, 11)]
        assert headers == [
            "id_stk",
            "stk_code",
            "isin",
            "company_name",
            "curr_avg_price",
            "current_qty",
            "curr_investment_amt",
            "CMP",
            "Unrealized_PnL_Amount",
            "Unrealized_PnL_Percentage",
        ]

        # Row 4 values
        assert ws.cell(4, 2).value == "INFY"
        assert ws.cell(4, 5).value == 1500.0
        assert ws.cell(4, 6).value == 100
        assert ws.cell(4, 7).value == 150000.0
        assert ws.cell(4, 8).value == 1800.0   # CMP
        assert ws.cell(4, 9).value == 30000.0  # (1800 - 1500) * 100
        assert ws.cell(4, 10).value == 20.0    # ((1800 - 1500) / 1500) * 100

        wb.close()
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)
        if os.path.exists(xlsx_path):
            os.remove(xlsx_path)


def test_upload_portfolio_to_drive_auto_authenticate():
    """Verify upload_portfolio_to_drive calls get_drive_service when service is None."""
    mock_service = MagicMock()
    mock_files = mock_service.files.return_value
    mock_files.list.return_value.execute.side_effect = [
        {"files": [{"id": "folder_123", "name": "Finance"}]},
        {"files": [{"id": "file_auto_789", "name": "StockMan_Portfolio.xlsx"}]},
    ]
    mock_files.update.return_value.execute.return_value = {
        "id": "file_auto_789",
        "name": "StockMan_Portfolio.xlsx",
        "modifiedTime": "2026-11-01T10:00:00Z",
    }

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        with patch("StockMan.drive_sync.get_drive_service", return_value=mock_service) as mock_get_svc:
            res = drive_sync.upload_portfolio_to_drive(service=None, file_path=tmp_path, folder_name="Finance")
            assert mock_get_svc.called
            assert res["id"] == "file_auto_789"
            assert res["status"] == "updated"
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_upload_portfolio_to_drive_creates_new_when_no_existing():
    """Verify upload_portfolio_to_drive creates a new file dynamically if not existing."""
    mock_service = MagicMock()
    mock_files = mock_service.files.return_value
    # 1. Folder exists
    # 2. File not found in folder
    # 3. File not found globally
    mock_files.list.return_value.execute.side_effect = [
        {"files": [{"id": "folder_123", "name": "Finance"}]},
        {"files": []},
        {"files": []},
    ]
    mock_files.create.return_value.execute.return_value = {
        "id": "new_created_file_999",
        "name": "StockMan_Portfolio.xlsx",
        "modifiedTime": "2026-11-01T11:00:00Z",
    }

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        res = drive_sync.upload_portfolio_to_drive(mock_service, file_path=tmp_path, folder_name="Finance")
        assert res["id"] == "new_created_file_999"
        assert res["status"] == "created"
        assert mock_files.create.called
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_download_latest_pick_of_the_day_ranks_by_date_and_time():
    """Verify download_latest_pick_of_the_day dynamically selects the newest dated file."""
    mock_service = MagicMock()
    mock_files = mock_service.files.return_value

    files_list = [
        {
            "id": "file_oct28",
            "name": "Pick_of_the_day_2026-10-28.md",
            "mimeType": "application/vnd.google-apps.document",
            "modifiedTime": "2026-10-28T10:00:00Z",
        },
        {
            "id": "file_nov01_latest",
            "name": "Pick_of_the_day_2026-11-01.md",
            "mimeType": "application/vnd.google-apps.document",
            "modifiedTime": "2026-11-01T07:20:00Z",
        },
        {
            "id": "file_oct30",
            "name": "Pick_of_the_day_2026-10-30.md",
            "mimeType": "application/vnd.google-apps.document",
            "modifiedTime": "2026-10-30T10:00:00Z",
        },
    ]

    # No files in Finance folder, search global returns files_list
    mock_files.list.return_value.execute.side_effect = [
        {"files": [{"id": "folder_123", "name": "Finance"}]},
        {"files": []},         # folder search empty
        {"files": files_list}, # global search
    ]

    mock_export = mock_files.export_media.return_value
    mock_export.execute.return_value = b"# Latest 2026-11-01 Advice Report\n| Stock | Score |\n| HAL | 95 |"

    with tempfile.TemporaryDirectory() as temp_dir:
        res = drive_sync.download_latest_pick_of_the_day(
            service=mock_service,
            folder_name="Finance",
            dest_dir=temp_dir,
            sync_to_workspace_root=False,
        )
        assert res is not None
        saved_alias, md_filename = res
        assert md_filename == "Pick_of_the_day_2026-11-01.md"
        assert os.path.exists(saved_alias)

        # Check export media called for the latest file ID
        mock_files.export_media.assert_called_with(
            fileId="file_nov01_latest", mimeType="text/markdown"
        )

        with open(saved_alias, "r", encoding="utf-8") as f:
            content = f.read()
        assert "Latest 2026-11-01 Advice Report" in content
        assert "| HAL | 95 |" in content


def test_sync_two_way_pipeline_orchestration():
    """Verify sync_two_way_pipeline executes both upload and download seamlessly."""
    mock_service = MagicMock()
    mock_files = mock_service.files.return_value

    # Upload mocks: folder list, file list (found in folder)
    # Download mocks: folder list, file list (found)
    mock_files.list.return_value.execute.side_effect = [
        {"files": [{"id": "folder_fin", "name": "Finance"}]},
        {"files": [{"id": "file_portfolio_111", "name": "StockMan_Portfolio.xlsx"}]},
        {"files": [{"id": "folder_fin", "name": "Finance"}]},
        {
            "files": [
                {
                    "id": "file_pod_222",
                    "name": "Pick_of_the_day_2026-11-01.md",
                    "mimeType": "application/vnd.google-apps.document",
                    "modifiedTime": "2026-11-01T08:00:00Z",
                }
            ]
        },
    ]

    mock_files.update.return_value.execute.return_value = {
        "id": "file_portfolio_111",
        "name": "StockMan_Portfolio.xlsx",
        "modifiedTime": "2026-11-01T12:00:00Z",
    }
    mock_export = mock_files.export_media.return_value
    mock_export.execute.return_value = b"# Pipeline Pick of the Day Report"

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_excel = os.path.join(temp_dir, "StockMan_Portfolio.xlsx")
        # Initialize excel
        drive_sync.update_portfolio_excel(excel_path=temp_excel)

        res = drive_sync.sync_two_way_pipeline(
            service=mock_service,
            excel_path=temp_excel,
            folder_name="Finance",
            dest_dir=temp_dir,
            sync_to_workspace_root=False,
        )

        assert res["success"] is True
        assert res["upload_result"]["id"] == "file_portfolio_111"
        assert res["upload_result"]["status"] == "updated"
        assert res["download_result"][1] == "Pick_of_the_day_2026-11-01.md"
        assert os.path.exists(res["downloaded_file"])


def test_download_latest_pick_of_the_day_prioritizes_higher_version_number():
    """Verify Pick_of_the_day_2026-11-01_v3 is ranked higher than Pick_of_the_day_2026-11-01 even if v1 was touched later."""
    mock_service = MagicMock()
    mock_files = mock_service.files.return_value

    files_list = [
        {
            "id": "file_v1",
            "name": "Pick_of_the_day_2026-11-01.md",
            "mimeType": "application/vnd.google-apps.document",
            "createdTime": "2026-11-01T06:44:41.743Z",
            "modifiedTime": "2026-11-01T07:20:30.635Z",  # touched later
        },
        {
            "id": "file_v3",
            "name": "Pick_of_the_day_2026-11-01_v3.md",
            "mimeType": "application/vnd.google-apps.document",
            "createdTime": "2026-11-01T07:18:09.636Z",  # created later
            "modifiedTime": "2026-11-01T07:18:11.461Z",
        },
    ]

    mock_files.list.return_value.execute.side_effect = [
        {"files": [{"id": "folder_123", "name": "Finance"}]},
        {"files": []},         # folder search empty
        {"files": files_list}, # global search
    ]

    mock_export = mock_files.export_media.return_value
    mock_export.execute.return_value = b"# Version 3 Intelligence Report"

    with tempfile.TemporaryDirectory() as temp_dir:
        res = drive_sync.download_latest_pick_of_the_day(
            service=mock_service,
            folder_name="Finance",
            dest_dir=temp_dir,
            sync_to_workspace_root=False,
        )
        assert res is not None
        saved_alias, md_filename = res
        assert md_filename == "Pick_of_the_day_2026-11-01_v3.md"
        mock_files.export_media.assert_called_with(
            fileId="file_v3", mimeType="text/markdown"
        )


def test_adjust_cash_for_trade_buy():
    """Verify that a BUY trade decreases available cash in the Excel file."""
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp_xlsx, \
         tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
        xlsx_path = tmp_xlsx.name
        db_path = tmp_db.name

    try:
        # 1. Initialize excel with Appetite=1500000, Cash=100000
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Portfolio"
        ws.cell(1, 1, "Current Appetite")
        ws.cell(1, 2, 1500000.0)
        ws.cell(2, 1, "Cash Available for Investment")
        ws.cell(2, 2, 100000.0)
        wb.save(xlsx_path)
        wb.close()

        # 2. Execute BUY trade for net 25,000
        new_cash, app, out_path = drive_sync.adjust_cash_for_trade(
            trade_type="BUY",
            net_amount=25000.0,
            excel_path=xlsx_path,
            db_path=db_path,
            trigger_drive_upload=False,
        )

        assert new_cash == 75000.0
        assert app == 1500000.0

        # 3. Read directly from Excel file on disk to confirm persistence
        read_app, read_cash = drive_sync.read_investment_parameters(xlsx_path)
        assert read_app == 1500000.0
        assert read_cash == 75000.0
    finally:
        for p in (xlsx_path, db_path):
            if os.path.exists(p):
                os.remove(p)


def test_adjust_cash_for_trade_sell():
    """Verify that a SELL trade increases available cash in the Excel file."""
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp_xlsx, \
         tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
        xlsx_path = tmp_xlsx.name
        db_path = tmp_db.name

    try:
        # Initialize with Cash=50,000
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Portfolio"
        ws.cell(1, 1, "Current Appetite")
        ws.cell(1, 2, 1000000.0)
        ws.cell(2, 1, "Cash Available for Investment")
        ws.cell(2, 2, 50000.0)
        wb.save(xlsx_path)
        wb.close()

        # Execute SELL trade for net 40,000
        new_cash, app, out_path = drive_sync.adjust_cash_for_trade(
            trade_type="SELL",
            net_amount=40000.0,
            excel_path=xlsx_path,
            db_path=db_path,
            trigger_drive_upload=False,
        )

        assert new_cash == 90000.0
        assert app == 1000000.0

        read_app, read_cash = drive_sync.read_investment_parameters(xlsx_path)
        assert read_cash == 90000.0
    finally:
        for p in (xlsx_path, db_path):
            if os.path.exists(p):
                os.remove(p)


def test_adjust_cash_for_trades_batch():
    """Verify multiple trades in a batch (e.g. Zerodha) compute correct net cash delta."""
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp_xlsx, \
         tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
        xlsx_path = tmp_xlsx.name
        db_path = tmp_db.name

    try:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Portfolio"
        ws.cell(1, 1, "Current Appetite")
        ws.cell(1, 2, 2000000.0)
        ws.cell(2, 1, "Cash Available for Investment")
        ws.cell(2, 2, 100000.0)
        wb.save(xlsx_path)
        wb.close()

        # Trades: BUY 30,000, BUY 15,000, SELL 60,000 -> net delta: -30k - 15k + 60k = +15,000
        batch = [
            {"trade_type_trd": "BUY", "net_amt_trd": 30000.0},
            {"trade_type_trd": "BUY", "net_amt_trd": 15000.0},
            {"trade_type_trd": "SELL", "net_amt_trd": 60000.0},
        ]
        new_cash, app, _ = drive_sync.adjust_cash_for_trades(
            trades=batch,
            excel_path=xlsx_path,
            db_path=db_path,
            trigger_drive_upload=False,
        )
        assert new_cash == 115000.0
        assert app == 2000000.0

        read_app, read_cash = drive_sync.read_investment_parameters(xlsx_path)
        assert read_cash == 115000.0
    finally:
        for p in (xlsx_path, db_path):
            if os.path.exists(p):
                os.remove(p)


def test_update_available_cash_in_excel_direct():
    """Verify fast in-place cash update function modifies cell (2, 2)."""
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp_xlsx:
        xlsx_path = tmp_xlsx.name

    try:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Portfolio"
        ws.cell(1, 1, "Current Appetite")
        ws.cell(1, 2, 1800000.0)
        ws.cell(2, 1, "Cash Available for Investment")
        ws.cell(2, 2, 50000.0)
        wb.save(xlsx_path)
        wb.close()

        ok = drive_sync.update_available_cash_in_excel(
            new_cash=62500.50,
            excel_path=xlsx_path,
        )
        assert ok is True

        read_app, read_cash = drive_sync.read_investment_parameters(xlsx_path)
        assert read_app == 1800000.0
        assert read_cash == 62500.50
    finally:
        if os.path.exists(xlsx_path):
            os.remove(xlsx_path)


def test_update_portfolio_excel_preserves_existing_values():
    """Verify update_portfolio_excel without arguments preserves existing appetite and cash."""
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp_xlsx, \
         tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
        xlsx_path = tmp_xlsx.name
        db_path = tmp_db.name

    try:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Portfolio"
        ws.cell(1, 1, "Current Appetite")
        ws.cell(1, 2, 2200000.0)
        ws.cell(2, 1, "Cash Available for Investment")
        ws.cell(2, 2, 175000.0)
        wb.save(xlsx_path)
        wb.close()

        # Call with no appetite and cash specified
        drive_sync.update_portfolio_excel(excel_path=xlsx_path, db_path=db_path)

        # Confirm they were NOT overwritten by 1000000 and 50000
        read_app, read_cash = drive_sync.read_investment_parameters(xlsx_path)
        assert read_app == 2200000.0
        assert read_cash == 175000.0
    finally:
        for p in (xlsx_path, db_path):
            if os.path.exists(p):
                os.remove(p)

