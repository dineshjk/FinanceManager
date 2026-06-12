# -*- coding: utf-8 -*-
# StockMan/scanner.py
import os
import pandas as pd

# Handle both direct execution and package-level execution
from . import data_manager
from Shared.globals import DATA_DIR


def calculate_rsi(data, window=14):
    """
    Calculates the Relative Strength Index (RSI).
    Formula: 100 - (100 / (1 + RS))
    """
    delta = data["Close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def scan_watchlist_for_signals(watchlist):
    """
    Reads local data, calculates technicals, and returns a list of actionable alerts.
    """
    # 1. Ensure we have the latest data before scanning
    data_manager.download_watchlist_data(watchlist)

    alerts = []
    print("\n[System] Scanning data for technical signals...")

    for scrip in watchlist:
        ticker = (
            scrip
            if scrip.endswith(".NS") or scrip.endswith(".BO")
            else f"{scrip}.NS"
        )
        file_path = os.path.join(DATA_DIR, f"{ticker}_data.csv")

        # Skip if data failed to download
        if not os.path.exists(file_path):
            continue

        # 2. Load the data into a Pandas DataFrame
        df = pd.read_csv(file_path)

        # Fix: yfinance sometimes saves 2-level headers, making the first row a string.
        # We force the columns to be numeric, which turns string headers into NaN,
        # and then we drop those NaN rows to ensure pure mathematical data.
        if (
            "Close" in df.columns
            and "Volume" in df.columns
            and "High" in df.columns
            and "Low" in df.columns
        ):
            df["Close"] = pd.to_numeric(df["Close"], errors="coerce")
            df["Volume"] = pd.to_numeric(df["Volume"], errors="coerce")
            df["High"] = pd.to_numeric(df["High"], errors="coerce")
            df["Low"] = pd.to_numeric(df["Low"], errors="coerce")
            df = df.dropna(subset=["Close", "Volume", "High", "Low"])
        else:
            print(
                f"  -> Skipping {ticker}: Missing required price columns in CSV."
            )
            continue

        # We need at least 50 days of data to calculate the 50 SMA
        if df.empty or len(df) < 50:
            print(f"  -> Skipping {ticker}: Not enough data points.")
            continue

        # 3. Calculate Statistical Measures
        df["SMA_20"] = df["Close"].rolling(window=20).mean()
        df["SMA_50"] = df["Close"].rolling(window=50).mean()
        df["RSI"] = calculate_rsi(df)

        # Bollinger Bands (20-day SMA +/- 2 Standard Deviations)
        df["STD_20"] = df["Close"].rolling(window=20).std()
        df["BB_Upper"] = df["SMA_20"] + (df["STD_20"] * 2)
        df["BB_Lower"] = df["SMA_20"] - (df["STD_20"] * 2)

        # Average True Range (ATR) - 14 Day
        high_low = df["High"] - df["Low"]
        high_close = (df["High"] - df["Close"].shift(1)).abs()
        low_close = (df["Low"] - df["Close"].shift(1)).abs()
        df["TR"] = pd.DataFrame(
            {"hl": high_low, "hc": high_close, "lc": low_close}
        ).max(axis=1)
        df["ATR_14"] = df["TR"].rolling(window=14).mean()

        # Volume Weighted Average Price (VWAP) - 20 Day Rolling
        df["Typical_Price"] = (df["High"] + df["Low"] + df["Close"]) / 3
        df["VWAP_20"] = (df["Typical_Price"] * df["Volume"]).rolling(
            window=20
        ).sum() / df["Volume"].rolling(window=20).sum()

        # Get the two most recent days to check for crossovers
        latest = df.iloc[-1]
        previous = df.iloc[-2]

        # --- TRIGGER LOGIC ---

        # Trigger A: RSI is Oversold (below 30)
        if latest["RSI"] < 30:
            alerts.append(
                {
                    "scrip": scrip,
                    "signal": "RSI Oversold",
                    "details": f"RSI has dropped to {round(latest['RSI'], 2)}",
                }
            )

        # Trigger B: Bullish Moving Average Crossover
        if (
            previous["SMA_20"] <= previous["SMA_50"]
            and latest["SMA_20"] > latest["SMA_50"]
        ):
            alerts.append(
                {
                    "scrip": scrip,
                    "signal": "Bullish SMA Crossover",
                    "details": "20-day SMA just crossed above the 50-day SMA.",
                }
            )

        # Trigger C: Volume Spike (Trading at 3x the normal 20-day volume)
        avg_volume = (
            df["Volume"].rolling(window=20).mean().iloc[-2]
        )  # Use yesterday's avg to compare today
        if latest["Volume"] > (avg_volume * 3):
            alerts.append(
                {
                    "scrip": scrip,
                    "signal": "Massive Volume Spike",
                    "details": f"Volume is {round(latest['Volume'] / avg_volume, 1)}x higher than normal.",
                }
            )

        # Trigger D: Bollinger Band Oversold
        # Price drops below the Lower Band, historically indicating a high-probability reversal zone.
        if latest["Close"] < latest["BB_Lower"]:
            alerts.append(
                {
                    "scrip": scrip,
                    "signal": "Bollinger Lower Band Touch",
                    "details": f"Price ({round(latest['Close'], 2)}) dropped below the Lower Band ({round(latest['BB_Lower'], 2)}).",
                }
            )

        # Trigger E: VWAP Breakout
        # Price crosses above the 20-day VWAP, indicating strong volume-backed buying.
        if (
            previous["Close"] <= previous["VWAP_20"]
            and latest["Close"] > latest["VWAP_20"]
        ):
            alerts.append(
                {
                    "scrip": scrip,
                    "signal": "Bullish VWAP Breakout",
                    "details": f"Price crossed above VWAP. (Suggested Stop-Loss: {round(latest['Close'] - latest['ATR_14'], 2)} based on ATR)",
                }
            )

    print("[System] Scan complete.\n")
    return alerts


# --- TESTING ---
if __name__ == "__main__":
    test_list = ["HAL.NS", "BHEL.NS"]
    found_alerts = scan_watchlist_for_signals(test_list)

    if not found_alerts:
        print("No buy signals triggered today for the test watchlist.")
    else:
        for alert in found_alerts:
            print(
                f"ALERT: {alert['scrip']} | {alert['signal']} | {alert['details']}"
            )
