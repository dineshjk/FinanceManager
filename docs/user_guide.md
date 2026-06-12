# User Operations & Help Guide

This guide covers the day-to-day operations of the **Universal Finance Manager** desktop application.

---

## 🚀 Getting Started

When you launch `finance_dashboard.py`, you will see the main hub menu:

1. **Launch StockMan**: Opens the Stock Portfolio Management module.
2. **Launch BankMan**: Opens the Bank Account tracker.
3. **Exit**: Safely closes the application.

---

## 📊 StockMan Dashboard Overview

The StockMan module is divided into 5 main tabs:

### 1. Stock-wise Analysis
- Displays a list of all stocks ever traded on the left pane.
- Selecting a stock dynamically populates its detailed metrics on the right pane:
  - **Stock Performance**: Detailed textual report of realized and unrealized gains.
  - **Holding Ledger**: Chronological transaction history showing opening qty, change, closing qty, and running average cost.
  - **Broker Corporate Actions**: Log of stock splits, bonuses, and dividend payouts recorded in your local database.
  - **Dividend Ledger**: Detailed breakdown of received dividend payouts.
  - **Online Corporate Actions**: Dynamic comparison showing differences between your database records and live data from Yahoo Finance.
  - **Intraday Price Analysis**: Real-time 5-minute price charts with VWAP indicators.

### 2. Portfolio Summary
- Displays multi-year financial summaries grouped by Financial Year (e.g. `FY 24-25`).
- Tracks capital investments, dividend incomes, realized profits, estimated capital gains taxes, and capital inflow/outflow metrics.

### 3. Current Holdings
- Lists all stocks currently in your portfolio.
- Shows live stock prices, market values, unrealized gains, and average buy cost basis.

### 4. Portfolio Allocation
- Shows your asset allocation split by sectors (e.g. Finance, IT, Energy) and individual stock weights as percentage of total portfolio value.

### 5. Portfolio Ledgers
- Provides search and filter tools for your entire historical ledger, corporate actions, and online stock databases.

---

## ✏️ Recording Trade Transactions

To add a new trade:
1. Click **Add Trade** or press **[Alt + T]** in the StockMan menu.
2. Fill out the form fields:
   - **Stock Selection**: Choose a stock or add a new counter.
   - **Trade Type**: Choose `BUY`, `SELL`, `SPLIT`, `BONUS`, `MERGER`, `DEMERGER`, `IPO`, or `RIGHTS`.
   - **Quantity & Price**: Input transaction metrics.
   - **Trade Date**: Enter the date in `DD-MM-YYYY` format.
3. Click **Save** to commit the trade. Sell trades will automatically execute the FIFO allocation matching.

---

## 🔑 Configuring Gemini AI API Key

To activate AI Advice and Technical Signal Insights, you need a free Gemini API Key:

1. Go to [Google AI Studio](https://aistudio.google.com/) and click **Get API Key**.
2. Generate your key.
3. Create a plain text file named `api_key.txt` in the main folder of the project.
4. Paste only your API Key into that file, save, and restart the dashboard.
   *(Example contents of `api_key.txt`: `AIzaSyCnR0NnvD0-zPIBJ3drkZhH1VZGKqUYxIc`)*

---

## 🤖 Using the AI Advice Features

In the **Watchlist & AI** menu:
- **Analyze Technical Signal**: Select a stock in your watchlist, click **Get AI Analysis**, and Gemini will explain the technical chart signal and gather recent grounding news.
- **Scan Buy Opportunities**: Runs a background scanner looking for institutional broker "BUY" ratings from the last 7 days for the stocks in your watchlist.
- **Scan Sell Advice**: Scans your currently profitable portfolio holdings against institutional reports to check if brokers recommend trimming or profit-booking.

---

## 🛠️ Troubleshooting

### 1. "AI Analysis disabled: API access denied or Invalid Key"
- **Reason**: The API key in `api_key.txt` is incorrect, revoked, or has expired.
- **Fix**: Open `api_key.txt`, make sure there are no spaces or extra characters, and verify the key is active in Google AI Studio.

### 2. "yfinance required for live prices"
- **Reason**: The yfinance Python library is missing.
- **Fix**: Open your terminal/command prompt and run:
  ```bash
  pip install yfinance
  ```

### 3. "Legacy Database File Not Found"
- **Reason**: The old database file `mystocks_old.db` is missing from the `data/` folder.
- **Fix**: Place your legacy backup database file in the `data/` directory and rename it to `mystocks_old.db`.
