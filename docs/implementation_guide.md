# Developer Implementation & Architecture Guide

This guide details the technical architecture, database schemas, core computation algorithms, and design choices of the **Universal Finance Manager** codebase.

---

## 📂 Codebase Directory Structure

```text
FinanceManager/
│
├── finance_dashboard.py        # Main Hub Launcher (Tkinter)
├── README.md                   # Project Overview & Quick Start
├── api_key.txt.template        # Instructions template for AI key config
│
├── Shared/                     # Common utilities & UI components
│   ├── globals.py              # App-wide constants, database helper
│   ├── gui_utils.py            # Themes, widgets, and tooltip binders
│   ├── dialog_utils.py         # Standardized popup modals
│   └── window_manager.py       # Modality and focus helper
│
├── StockMan/                   # Stock Portfolio Tracker module
│   ├── stocks.py               # Module menu interface
│   ├── reporting.py            # Core Analytics Dashboard UI & Tab Handlers
│   ├── ai_analyzer.py          # Gemini AI API interface (client initialization)
│   ├── watchlist_menu.py       # Watchlist management UI & AI triggers
│   ├── trade_manager.py        # Transaction ledger UI
│   ├── trade_add.py            # Trade entry logic (Buy, Sell, Splits, Mergers)
│   └── stock_database_setup.py # Database schema initialization script
│
├── BankMan/                    # Bank Tracker module
│   └── banks.py                # Main module entry point & UI
│
├── data/                       # User data directory (Excluded from Git)
│   └── .gitkeep                # Keeps directory folder in Git
│
└── docs/                       # Project documentation suite
    ├── implementation_guide.md # Technical implementation details (This file)
    └── user_guide.md           # End-user operational guide
```

---

## 🗄️ Database Schema (`mystocks.db`)

The stock portfolio tracker maintains its state inside a local SQLite database file `mystocks.db`. Below are the primary tables:

### 1. `stocks`
Tracks the unique counters held or monitored in the portfolio.
- `id_stk` (INTEGER, Primary Key): Unique stock ID.
- `ticker` (TEXT): Stock symbol (e.g., `RELIANCE.NS` for Yahoo Finance).
- `short_name` (TEXT): Display name.
- `is_active` (INTEGER): `1` if currently held, `0` if fully sold out.
- `current_qty` (INTEGER): Running quantity currently held.
- `invested_amt` (REAL): Running total invested capital for current positions.

### 2. `transactions`
Logs all transaction entries (Buys, Splits, Mergers, IPOs, Rights).
- `id_trd` (INTEGER, Primary Key): Unique transaction ID.
- `id_stk` (INTEGER, Foreign Key -> `stocks`): Reference stock.
- `trd_dt` (TEXT): Trade Date (`YYYY-MM-DD`).
- `trade_type_trd` (TEXT): `'BUY'`, `'SELL'`, `'SPLIT'`, `'BONUS'`, etc.
- `qty_trd` (INTEGER): Volume of shares transacted.
- `rate_trd` (REAL): Price per share.
- `amt_trd` (REAL): Net amount of trade (after broker charges and taxes).

### 3. `sell_records`
Maintains the mapping between Sell transactions and their matching Buy lots.
- `id_sell_record` (INTEGER, Primary Key): Record identifier.
- `id_buy_trd` (INTEGER, Foreign Key -> `transactions`): The matching Buy lot transaction.
- `id_sell_trd` (INTEGER, Foreign Key -> `transactions`): The matching Sell transaction.
- `sell_qty` (INTEGER): Quantity of shares matched in this lot.
- `sell_dt` (TEXT): Date of sale.
- `realized_gain_loss` (REAL): Net profit or loss for this transaction lot.

### 4. `watchlist`
Stocks monitored for technical signals or price updates.
- `id_stk` (INTEGER, Primary Key, Foreign Key -> `stocks`): Reference stock.

---

## 🧮 Core Algorithms & Logics

### 1. First-In-First-Out (FIFO) Match Engine
When a sale is recorded, the FIFO match engine allocates the sold quantity against the oldest available Buy transaction lots of the selected stock:
- It queries all Buy transactions for the stock where the quantity has not been fully offset by existing `sell_records`.
- It matches the sold quantity chunk-by-chunk starting from the earliest trade date.
- For each matched chunk, it inserts a record into `sell_records` and computes:
  $$\text{Realized P\&L} = (\text{Sell Price} - \text{Buy Price}) \times \text{Matched Quantity}$$
- If a Buy transaction is deleted, the engine rolls back and runs `rebuild_sell_allocations` to recalculate matches for subsequent lots to avoid data inconsistencies.

### 2. Annualized Rate of Return (XIRR)
Annualized return is calculated individually for each stock using the Newton-Raphson numerical solver to find the internal rate of return for non-periodic cashflows:
- **Cashflow Construction**:
  - All Buy transaction amounts are inputted as **negative** values (outflows).
  - All Sell transaction amounts and Received Dividends are inputted as **positive** values (inflows).
  - If the stock is currently held, a final cashflow is appended on the current date, representing the current market value (Live Price $\times$ Current Qty) as a **positive** value.
- **Solver Equation**:
  The solver finds the rate $r$ such that:
  $$\text{NPV} = \sum_{i=1}^{N} \frac{C_i}{(1 + r)^{\frac{d_i - d_1}{365}}} = 0$$
  where $C_i$ is the cashflow amount on date $d_i$.

### 3. Asynchronous Matplotlib & Data Insertion
To prevent the Tkinter user interface from freezing during database calculations or network API fetches:
- Intensive processes (like loading all historical transaction reports, fetching online corporate actions, and drawing Matplotlib intraday charts) are executed in background threads (`threading.Thread`).
- UI updates, widget configuration changes, and table rows insertions are scheduled back to the Tkinter Main Thread using the safe thread bridge: `pnl_win.after(0, callback)`.

---

## 🤖 Gemini AI Client Configuration

The portfolio advisor modules in `StockMan/watchlist_menu.py` interact with the Gemini API via the helper function `get_api_key` defined in `StockMan/ai_analyzer.py`.

```python
def get_api_key():
    # Resolves project root and checks file 'api_key.txt'
    # Fallback to system environment variable 'GEMINI_API_KEY'
    # Returns key or None (Graceful warning displayed in GUI)
```

The AI tasks invoke the modern `Client` from the `google-genai` library targeting the `gemini-2.5-flash` model, using **Google Search Grounding** to query real-time market news and consensus target research reports:

```python
client = genai.Client(api_key=api_key)
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=prompt,
    config=types.GenerateContentConfig(tools=[{"google_search": {}}]),
)
```
If billing or quota limits are hit, `ai_analyzer.py` catches the API exceptions and gracefully disables the AI widgets to prevent crashes.
