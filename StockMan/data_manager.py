import os
import yfinance as yf
import pandas as pd
from datetime import date

# Import central directory path
try:
    from Shared.globals import DATA_DIR
except ImportError:
    from globals import DATA_DIR

FLAG_FILE = os.path.join(DATA_DIR, "last_update.txt")

# Ensure the data directory exists
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)


def should_download_data():
    """Checks if data has already been downloaded today."""
    today_string = str(date.today())

    if not os.path.exists(FLAG_FILE):
        return True

    with open(FLAG_FILE, "r") as file:
        last_update_date = file.read().strip()

    if last_update_date == today_string:
        print("[System] Data already updated today. Skipping download.")
        return False
    else:
        return True


def mark_download_complete():
    """Saves today's date to prevent redundant downloads."""
    today_string = str(date.today())
    with open(FLAG_FILE, "w") as file:
        file.write(today_string)


def download_watchlist_data(watchlist):
    """
    Downloads 6 months of historical data for a list of scrips.
    Expects scrips formatted for Indian markets (e.g., 'HAL.NS').
    """
    if not should_download_data():
        return  # Exit the function if we already have today's data

    print("[System] Commencing data download for watchlist...")

    for scrip in watchlist:
        try:
            # Yahoo Finance uses .NS for NSE and .BO for BSE
            ticker = (
                scrip
                if scrip.endswith(".NS") or scrip.endswith(".BO")
                else f"{scrip}.NS"
            )

            print(f"Fetching 6-month data for {ticker}...")
            # Download 6 months of daily data
            df = yf.download(ticker, period="6mo", progress=False)

            if not df.empty:
                # Save it locally as a CSV for our statistical module to read later
                file_path = os.path.join(DATA_DIR, f"{ticker}_data.csv")
                df.to_csv(file_path)
                print(f"  -> Saved {ticker} successfully.")
            else:
                print(f"  -> Warning: No data found for {ticker}.")

        except Exception as e:
            print(f"  -> Error downloading {ticker}: {e}")

    # Once all downloads are complete, set the circuit breaker
    mark_download_complete()
    print("[System] Watchlist data download complete.")


# --- TESTING ---
# If you run this file directly, it will test the download with two scrips.
if __name__ == "__main__":
    test_list = ["HAL.NS", "BHEL.NS"]
    download_watchlist_data(test_list)
