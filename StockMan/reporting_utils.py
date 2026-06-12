from datetime import date, datetime, time
import math
from .date_utils import format_date_for_display


def _financial_year_label(date_str: str) -> str:
    current_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    fy_year = (
        current_date.year if current_date.month >= 4 else current_date.year - 1
    )
    return f"FY {fy_year}-{str(fy_year + 1)[-2:]}"


def _new_portfolio_summary_row() -> dict[str, float]:
    return {
        "inv": 0.0,
        "pnl": 0.0,
        "pat": 0.0,
        "div": 0.0,
        "miss_profit": 0.0,
        "save_loss": 0.0,
    }


def _between_clause(
    column_name: str, start_date, end_date
) -> tuple[str, tuple]:
    if start_date and end_date:
        return f" AND {column_name} BETWEEN ? AND ?", (start_date, end_date)
    return "", ()


def resolve_reporting_period(selected_fy: str):
    is_yearly = selected_fy != "All Years"
    if not is_yearly:
        return False, None, None

    start_year = int(selected_fy.split(" ")[1].split("-")[0])
    return True, f"{start_year}-04-01", f"{start_year + 1}-03-31"


def resolve_optional_date_filters(start_date, end_date):
    if not start_date or not end_date:
        return None, None
    return (
        datetime.strptime(start_date, "%Y-%m-%d"),
        datetime.strptime(end_date, "%Y-%m-%d"),
    )


def build_live_market_snapshot(close_price, fast_info=None):
    def to_float(value) -> float:
        try:
            return float(value or 0.0)
        except (TypeError, ValueError):
            return 0.0

    info = fast_info or {}
    return {
        "price": to_float(close_price),
        "high52": to_float(info.get("yearHigh", 0.0)),
        "low52": to_float(info.get("yearLow", 0.0)),
    }


def fetch_master_ledger_rows(cursor, start_date=None, end_date=None):
    where_clause = (
        "WHERE t.trd_dt BETWEEN ? AND ?" if start_date and end_date else ""
    )
    params = (start_date, end_date) if start_date and end_date else ()
    cursor.execute(
        f"""
        SELECT t.cont_no,
               CASE WHEN s.ticker != '' THEN s.ticker ELSE s.short_name END,
               t.trd_dt,
               t.trade_type_trd,
               t.qty_trd,
               t.wap_unit_trd,
               t.net_amt_trd
        FROM transactions t
        JOIN stocks s ON t.id_stk = s.id_stk
        {where_clause}
        ORDER BY t.trd_dt ASC
        """,
        params,
    )
    return cursor.fetchall()


def fetch_master_dividend_source_rows(cursor, start_date=None, end_date=None):
    where_clause = (
        "WHERE d.credit_dt BETWEEN ? AND ?" if start_date and end_date else ""
    )
    params = (start_date, end_date) if start_date and end_date else ()
    cursor.execute(
        f"""
        SELECT CASE WHEN s.ticker != '' THEN s.ticker ELSE s.short_name END,
               d.id_stk,
               d.record_dt,
               d.credit_dt,
               d.div_type,
               d.entitled_qty,
               d.per_share_amt,
               d.gross_amt,
               d.net_amt,
               d.tds_amt
        FROM dividends d
        JOIN stocks s ON d.id_stk = s.id_stk
        {where_clause}
        """,
        params,
    )
    return cursor.fetchall()


def fetch_master_split_rows(cursor, start_date=None, end_date=None):
    where_clause = (
        "WHERE sp.ex_dt BETWEEN ? AND ?" if start_date and end_date else ""
    )
    params = (start_date, end_date) if start_date and end_date else ()
    cursor.execute(
        f"""
        SELECT CASE WHEN s.ticker != '' THEN s.ticker ELSE s.short_name END,
               sp.ex_dt,
               sp.old_fv,
               sp.new_fv
        FROM splits sp
        JOIN stocks s ON sp.id_stk = s.id_stk
        {where_clause}
        """,
        params,
    )
    return cursor.fetchall()


def fetch_master_bonus_rows(cursor, start_date=None, end_date=None):
    where_clause = (
        "WHERE b.ex_dt BETWEEN ? AND ?" if start_date and end_date else ""
    )
    params = (start_date, end_date) if start_date and end_date else ()
    cursor.execute(
        f"""
        SELECT CASE WHEN s.ticker != '' THEN s.ticker ELSE s.short_name END,
               b.ex_dt,
               b.ratio_old,
               b.ratio_new
        FROM bonus_issues b
        JOIN stocks s ON b.id_stk = s.id_stk
        {where_clause}
        """,
        params,
    )
    return cursor.fetchall()


def fetch_detail_ledger_rows(
    cursor, id_stk: int, start_date=None, end_date=None
):
    where_clause, params = _between_clause("t.trd_dt", start_date, end_date)
    cursor.execute(
        f"""
        SELECT COALESCE(c.settle_dt, t.trd_dt),
               t.trade_type_trd,
               t.qty_trd,
               t.net_amt_trd
        FROM transactions t
        LEFT JOIN contracts c ON t.cont_no = c.cont_no
        WHERE t.id_stk = ?{where_clause}
        ORDER BY COALESCE(c.settle_dt, t.trd_dt) ASC, t.id_trd ASC
        """,
        (id_stk, *params),
    )
    return cursor.fetchall()


def fetch_detail_dividend_source_rows(
    cursor, id_stk: int, start_date=None, end_date=None
):
    where_clause, params = _between_clause("credit_dt", start_date, end_date)
    cursor.execute(
        f"""
        SELECT record_dt,
               credit_dt,
               div_type,
               entitled_qty,
               gross_amt,
               net_amt,
               tds_amt
        FROM dividends
        WHERE id_stk = ?{where_clause}
        """,
        (id_stk, *params),
    )
    return cursor.fetchall()


def fetch_detail_split_rows(
    cursor, id_stk: int, start_date=None, end_date=None
):
    where_clause, params = _between_clause("ex_dt", start_date, end_date)
    cursor.execute(
        f"SELECT ex_dt, old_fv, new_fv FROM splits WHERE id_stk = ?{where_clause}",
        (id_stk, *params),
    )
    return cursor.fetchall()


def fetch_detail_bonus_rows(
    cursor, id_stk: int, start_date=None, end_date=None
):
    where_clause, params = _between_clause("ex_dt", start_date, end_date)
    cursor.execute(
        f"SELECT ex_dt, ratio_old, ratio_new FROM bonus_issues WHERE id_stk = ?{where_clause}",
        (id_stk, *params),
    )
    return cursor.fetchall()


def fetch_realized_detail_rows(
    cursor, id_stk: int, start_date=None, end_date=None
):
    where_clause, params = _between_clause("sell_dt", start_date, end_date)
    cursor.execute(
        f"""
        SELECT buy_value,
               holding_days,
               pnl_amt,
               sell_qty,
               sell_value,
               sell_dt
        FROM sell_records
        WHERE id_stk = ?{where_clause}
        ORDER BY sell_dt, buy_dt
        """,
        (id_stk, *params),
    )
    return cursor.fetchall()


def fetch_tax_summary_records(
    cursor, is_yearly: bool, start_date=None, end_date=None
):
    query = """
        SELECT
            s.company_name,
            s.ticker,
            sr.buy_dt,
            sr.sell_dt,
            sr.sell_qty,
            sr.buy_value,
            sr.sell_value,
            sr.pnl_amt,
            sr.holding_days
        FROM sell_records sr
        JOIN stocks s ON sr.id_stk = s.id_stk
    """
    params = ()
    if is_yearly:
        query += " WHERE sr.sell_dt BETWEEN ? AND ?"
        params = (start_date, end_date)

    query += " ORDER BY sr.sell_dt ASC"
    cursor.execute(query, params)
    return cursor.fetchall()


def fetch_global_sell_records(cursor):
    cursor.execute(
        "SELECT sell_dt, buy_dt, pnl_amt, sell_qty, sell_value, id_stk FROM sell_records"
    )
    return cursor.fetchall()


def fetch_global_buy_transactions(cursor):
    cursor.execute(
        "SELECT trd_dt, net_amt_trd FROM transactions WHERE trade_type_trd = 'BUY'"
    )
    return cursor.fetchall()


def fetch_global_dividends(cursor):
    cursor.execute("SELECT credit_dt, net_amt FROM dividends")
    return cursor.fetchall()


def fetch_global_investment_stats_buys(cursor):
    cursor.execute(
        "SELECT id_trd, trd_dt, net_amt_trd FROM transactions WHERE trade_type_trd = 'BUY'"
    )
    return cursor.fetchall()


def fetch_global_investment_stats_sells(cursor):
    cursor.execute("SELECT sell_id_trd, sell_dt, buy_value FROM sell_records")
    return cursor.fetchall()


def fetch_report_stock_rows(cursor, valid_ids=None):
    if valid_ids:
        placeholders = ",".join("?" * len(valid_ids))
        cursor.execute(
            f"SELECT id_stk, short_name, company_name, ticker, current_qty, rpnl_amt, curr_investment_amt, sector FROM stocks WHERE id_stk IN ({placeholders})",
            valid_ids,
        )
        return cursor.fetchall()

    cursor.execute(
        """SELECT id_stk, short_name, company_name, ticker, current_qty, rpnl_amt, curr_investment_amt, sector
           FROM stocks"""
    )
    return cursor.fetchall()


def fetch_yearly_realized_amount(cursor, id_stk: int, start_date, end_date):
    cursor.execute(
        "SELECT SUM(pnl_amt) FROM sell_records WHERE id_stk = ? AND sell_dt BETWEEN ? AND ?",
        (id_stk, start_date, end_date),
    )
    result = cursor.fetchone()
    return (result[0] if result else 0.0) or 0.0


def fetch_position_cashflow_rows(
    cursor, id_stk: int, start_date=None, end_date=None
):
    where_clause, params = _between_clause("trd_dt", start_date, end_date)
    cursor.execute(
        f"SELECT trd_dt, net_amt_trd FROM transactions WHERE id_stk = ? AND trade_type_trd = 'BUY'{where_clause}",
        (id_stk, *params),
    )
    purchase_rows = cursor.fetchall()
    cursor.execute(
        f"SELECT trd_dt, net_amt_trd FROM transactions WHERE id_stk = ? AND trade_type_trd = 'SELL'{where_clause}",
        (id_stk, *params),
    )
    sell_rows = cursor.fetchall()
    return purchase_rows, sell_rows


def fetch_detail_investment_summary(
    cursor, id_stk: int, start_date=None, end_date=None
):
    if start_date and end_date:
        cursor.execute(
            "SELECT SUM(net_amt_trd) FROM transactions WHERE id_stk = ? AND trade_type_trd = 'BUY' AND trd_dt BETWEEN ? AND ?",
            (id_stk, start_date, end_date),
        )
        total_investment = cursor.fetchone()[0] or 0.0
        cursor.execute(
            "SELECT SUM(buy_value) FROM sell_records WHERE id_stk = ? AND sell_dt BETWEEN ? AND ?",
            (id_stk, start_date, end_date),
        )
        disinvestment_amount = cursor.fetchone()[0] or 0.0
        return total_investment, disinvestment_amount

    cursor.execute(
        "SELECT total_investment_amt, disinvestment_amt FROM stocks WHERE id_stk = ?",
        (id_stk,),
    )
    result = cursor.fetchone()
    if not result:
        return 0.0, 0.0
    return (result[0] or 0.0, result[1] or 0.0)


def fetch_detail_timeline_rows(cursor, id_stk: int):
    cursor.execute(
        """
        SELECT COALESCE(c.settle_dt, t.trd_dt),
               t.trade_type_trd,
               t.qty_trd,
               t.net_amt_trd
        FROM transactions t
        LEFT JOIN contracts c ON t.cont_no = c.cont_no
        WHERE t.id_stk = ?
        ORDER BY COALESCE(c.settle_dt, t.trd_dt) ASC, t.id_trd ASC
        """,
        (id_stk,),
    )
    return cursor.fetchall()


def fetch_holding_bounds(cursor, id_stk: int):
    cursor.execute(
        "SELECT MIN(trd_dt), MAX(trd_dt) FROM transactions WHERE id_stk = ?",
        (id_stk,),
    )
    bounds = cursor.fetchone()
    if not bounds or not bounds[0]:
        return None
    return bounds[0], bounds[1]


def resolve_action_window(
    min_trade_date,
    max_trade_date,
    *,
    current_qty: float,
    filter_start=None,
    filter_end=None,
    now=None,
):
    if not min_trade_date:
        return None

    current_time = now or datetime.now()
    holding_start = datetime.strptime(min_trade_date, "%Y-%m-%d")
    holding_end = (
        current_time
        if current_qty > 0
        else datetime.strptime(max_trade_date, "%Y-%m-%d")
    )

    actual_start = max(filter_start or holding_start, holding_start)
    actual_end = min(filter_end or holding_end, holding_end)
    if actual_start > actual_end:
        return None
    return actual_start, actual_end


def has_corporate_action_history(
    cursor,
    id_stk: int,
    table_names=("splits", "bonus_issues", "merger_events", "demerger_events"),
):
    for table_name in table_names:
        try:
            cursor.execute(
                f"SELECT 1 FROM {table_name} WHERE id_stk = ? LIMIT 1",
                (id_stk,),
            )
            if cursor.fetchone():
                return True
        except Exception:
            continue
    return False


def build_pooled_cost_reality_summary(timeline_rows, *, current_price: float):
    reality_qty = 0.0
    reality_invested = 0.0
    reality_disinvested = 0.0
    reality_realized_pnl = 0.0
    reality_sells = []
    first_buy_date = None

    for event_date, trade_type, qty, amount in timeline_rows:
        if not event_date:
            continue

        if trade_type == "BUY":
            if not first_buy_date:
                first_buy_date = event_date
            reality_qty += qty
            reality_invested += amount
            continue

        if trade_type != "SELL" or reality_qty <= 0:
            continue

        avg_cost = reality_invested / reality_qty
        cost_of_sold = avg_cost * qty
        reality_invested -= cost_of_sold
        reality_qty -= qty
        reality_disinvested += cost_of_sold
        pnl_amount = amount - cost_of_sold
        reality_realized_pnl += pnl_amount

        holding_days = 0
        if first_buy_date:
            try:
                buy_date = datetime.strptime(first_buy_date, "%Y-%m-%d").date()
                sell_date = datetime.strptime(event_date, "%Y-%m-%d").date()
                holding_days = (sell_date - buy_date).days
            except ValueError:
                pass

        reality_sells.append(
            {
                "date": event_date,
                "qty": qty,
                "cost": cost_of_sold,
                "sell_value": amount,
                "pnl": pnl_amount,
                "days": holding_days,
            }
        )

    reality_avg_price = (
        (reality_invested / reality_qty) if reality_qty > 0 else 0.0
    )
    reality_unrealized = (
        ((reality_qty * current_price) - reality_invested)
        if current_price > 0
        else 0.0
    )

    return {
        "qty": reality_qty,
        "invested": reality_invested,
        "disinvested": reality_disinvested,
        "realized_pnl": reality_realized_pnl,
        "unrealized_pnl": reality_unrealized,
        "total_pnl": reality_realized_pnl + reality_unrealized,
        "avg_price": reality_avg_price,
        "sells": reality_sells,
    }


def parse_db_date(date_str) -> date | None:
    if not date_str or date_str == "1900-01-01":
        return None
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return None


def format_db_date(date_str) -> str:
    d = parse_db_date(date_str)
    if d is None:
        return "-"
    return d.strftime("%d-%m-%Y")


def date_diff_days(d1_str, d2) -> int:
    d1 = parse_db_date(d1_str)
    if d1 is None:
        return 9999
    return abs((d1 - d2).days)


def find_match_in_db(action_type: str, yahoo_date_str: str, yahoo_val: float, db_actions: dict) -> str:
    try:
        y_dt = datetime.strptime(yahoo_date_str, "%d-%m-%Y").date()
    except Exception:
        return "Missing in DB"

    if action_type == "Dividend":
        for ex_dt, record_dt, credit_dt, per_share_amt in db_actions.get("dividends", []):
            if per_share_amt is not None and abs(per_share_amt - yahoo_val) < 1e-4:
                diff_ex = date_diff_days(ex_dt, y_dt)
                diff_rec = date_diff_days(record_dt, y_dt)
                diff_cred = date_diff_days(credit_dt, y_dt)
                
                dates_with_diff = []
                if diff_ex <= 15:
                    dates_with_diff.append((diff_ex, f"Ex: {format_db_date(ex_dt)}"))
                if diff_rec <= 15:
                    dates_with_diff.append((diff_rec, f"Rec: {format_db_date(record_dt)}"))
                if diff_cred <= 15:
                    dates_with_diff.append((diff_cred, f"Pay: {format_db_date(credit_dt)}"))
                
                if dates_with_diff:
                    dates_with_diff.sort()
                    best_match_info = dates_with_diff[0][1]
                    return f"Matched ({best_match_info})"
                    
    elif action_type == "Stock Split":
        for ex_dt, record_dt, old_fv, new_fv in db_actions.get("splits", []):
            if old_fv and new_fv:
                db_ratio1 = old_fv / new_fv
                db_ratio2 = new_fv / old_fv
                if abs(db_ratio1 - yahoo_val) < 1e-4 or abs(db_ratio2 - yahoo_val) < 1e-4:
                    diff_ex = date_diff_days(ex_dt, y_dt)
                    diff_rec = date_diff_days(record_dt, y_dt)
                    
                    dates_with_diff = []
                    if diff_ex <= 15:
                        dates_with_diff.append((diff_ex, f"Ex: {format_db_date(ex_dt)}"))
                    if diff_rec <= 15:
                        dates_with_diff.append((diff_rec, f"Rec: {format_db_date(record_dt)}"))
                        
                    if dates_with_diff:
                        dates_with_diff.sort()
                        return f"Matched (Split, {dates_with_diff[0][1]})"

        for ex_dt, record_dt, ratio_old, ratio_new in db_actions.get("bonuses", []):
            if ratio_old:
                eq_ratio1 = (ratio_old + ratio_new) / ratio_old
                eq_ratio2 = ratio_old / (ratio_old + ratio_new)
                if abs(eq_ratio1 - yahoo_val) < 1e-4 or abs(eq_ratio2 - yahoo_val) < 1e-4:
                    diff_ex = date_diff_days(ex_dt, y_dt)
                    diff_rec = date_diff_days(record_dt, y_dt)
                    
                    dates_with_diff = []
                    if diff_ex <= 15:
                        dates_with_diff.append((diff_ex, f"Ex: {format_db_date(ex_dt)}"))
                    if diff_rec <= 15:
                        dates_with_diff.append((diff_rec, f"Rec: {format_db_date(record_dt)}"))
                        
                    if dates_with_diff:
                        dates_with_diff.sort()
                        return f"Matched (Bonus, {dates_with_diff[0][1]})"

    return "Missing in DB"


def fetch_db_corp_actions_for_matching(cursor, id_stk: int) -> dict:
    divs = []
    splits = []
    bonuses = []
    
    try:
        cursor.execute(
            "SELECT ex_dt, record_dt, credit_dt, per_share_amt FROM dividends WHERE id_stk = ?",
            (id_stk,),
        )
        divs = cursor.fetchall()
    except Exception:
        pass
        
    try:
        cursor.execute(
            "SELECT ex_dt, record_dt, old_fv, new_fv FROM splits WHERE id_stk = ?",
            (id_stk,),
        )
        splits = cursor.fetchall()
    except Exception:
        pass
        
    try:
        cursor.execute(
            "SELECT ex_dt, record_dt, ratio_old, ratio_new FROM bonus_issues WHERE id_stk = ?",
            (id_stk,),
        )
        bonuses = cursor.fetchall()
    except Exception:
        pass
        
    return {
        "dividends": divs,
        "splits": splits,
        "bonuses": bonuses,
    }


def build_online_corp_action_rows(
    action_entries,
    db_actions,
    *,
    display_name: str | None = None,
):
    rows = []

    # Check if we are running in the legacy mode (with existing_keys set)
    if not isinstance(db_actions, dict):
        existing_keys = db_actions if db_actions is not None else set()
        updated_keys = set(existing_keys)

        for date_text, dividend_value, split_value in action_entries:
            if dividend_value > 0:
                unique_key = (
                    (date_text, display_name, "Dividend")
                    if display_name is not None
                    else (date_text, "Dividend")
                )
                if unique_key not in updated_keys:
                    updated_keys.add(unique_key)
                    rows.append(
                        (
                            display_name,
                            date_text,
                            "Dividend",
                            f"₹{dividend_value:,.2f}",
                            "Yahoo! Finance",
                        )
                        if display_name is not None
                        else (
                            date_text,
                            "Dividend",
                            f"₹{dividend_value:,.2f}",
                            "Yahoo! Finance",
                        )
                    )

            if split_value > 0:
                unique_key = (
                    (date_text, display_name, "Stock Split")
                    if display_name is not None
                    else (date_text, "Stock Split")
                )
                if unique_key not in updated_keys:
                    updated_keys.add(unique_key)
                    rows.append(
                        (
                            display_name,
                            date_text,
                            "Stock Split",
                            f"Ratio {split_value}",
                            "Yahoo! Finance",
                        )
                        if display_name is not None
                        else (
                            date_text,
                            "Stock Split",
                            f"Ratio {split_value}",
                            "Yahoo! Finance",
                        )
                    )

        return rows, updated_keys

    # New mode: db_actions is a dict of database corporate actions
    for date_text, dividend_value, split_value in action_entries:
        if dividend_value > 0:
            match_status = find_match_in_db("Dividend", date_text, dividend_value, db_actions)
            rows.append(
                (
                    display_name,
                    date_text,
                    "Dividend",
                    f"₹{dividend_value:,.2f}",
                    "Yahoo! Finance",
                    match_status,
                )
                if display_name is not None
                else (
                    date_text,
                    "Dividend",
                    f"₹{dividend_value:,.2f}",
                    "Yahoo! Finance",
                    match_status,
                )
            )

        if split_value > 0:
            match_status = find_match_in_db("Stock Split", date_text, split_value, db_actions)
            rows.append(
                (
                    display_name,
                    date_text,
                    "Stock Split",
                    f"Ratio {split_value}",
                    "Yahoo! Finance",
                    match_status,
                )
                if display_name is not None
                else (
                    date_text,
                    "Stock Split",
                    f"Ratio {split_value}",
                    "Yahoo! Finance",
                    match_status,
                )
            )

    return rows, set()


def build_online_action_entries(action_rows, *, date_formatter):
    return [
        (
            date_formatter(index_value),
            row.get("Dividends", 0),
            row.get("Stock Splits", 0),
        )
        for index_value, row in action_rows
    ]


def build_master_existing_action_keys(corp_records, *, date_formatter):
    return {
        (
            date_formatter(record_date),
            display_name,
            action_type.split(" (")[0],
        )
        for record_date, display_name, action_type, _value, _tds in corp_records
    }


def build_detail_existing_action_keys(corp_records, *, date_formatter):
    return {
        (
            date_formatter(record["date"]),
            record["nature"].split(" (")[0],
        )
        for record in corp_records
    }


def build_detail_ledger_display_rows(ledger_records):
    display_rows = []
    running_balance = 0
    running_investment = 0.0
    running_avg = 0.0

    for settle_date, trade_type, qty, net_amount in ledger_records:
        opening_balance = running_balance

        if trade_type == "BUY":
            debit_credit_text = f"+{qty:,.0f}"
            running_balance += qty
            running_investment += net_amount
        else:
            debit_credit_text = f"-{qty:,.0f}"
            if running_balance > 0:
                running_investment -= qty * running_avg
            running_balance -= qty

        if running_balance <= 0:
            running_balance = 0
            running_investment = 0.0
            running_avg = 0.0
        else:
            running_avg = running_investment / running_balance

        display_rows.append(
            (
                settle_date,
                opening_balance,
                debit_credit_text,
                running_balance,
                running_investment,
                running_avg,
            )
        )

    return display_rows


def build_master_ledger_display_rows(
    ledger_records,
    *,
    date_formatter,
):
    display_rows = []

    for (
        cont_no,
        display_name,
        trade_date,
        trade_type,
        qty,
        wap,
        net_amt,
    ) in ledger_records:
        display_rows.append(
            (
                cont_no if cont_no is not None else "-",
                display_name,
                date_formatter(trade_date),
                trade_type,
                "Credit" if trade_type == "BUY" else "Debit",
                f"{qty:,.0f}",
                f"\u20b9{wap:,.2f}" if wap is not None else "-",
                f"\u20b9{net_amt:,.2f}" if net_amt is not None else "-",
            )
        )

    return display_rows


def build_master_corp_tree_rows(
    corp_records,
    *,
    date_formatter,
):
    return [
        (
            display_name,
            date_formatter(credit_date),
            nature_type,
            nature_value,
            tds_value,
        )
        for credit_date, display_name, nature_type, nature_value, tds_value in corp_records
    ]


def build_master_dividend_tree_rows(master_dividend_data):
    dividend_records = master_dividend_data["dividend_records"]
    summary_row = None

    if dividend_records:
        summary_row = (
            "TOTAL",
            "-",
            f"{master_dividend_data['total_entitled_qty']:,.0f}",
            "-",
            f"₹{master_dividend_data['total_invested_amount']:,.2f}",
            f"₹{master_dividend_data['total_net_amount']:,.2f}",
            "-",
            "-",
        )

    return {
        "summary_row": summary_row,
        "detail_rows": list(dividend_records),
    }


def build_detail_ledger_tree_rows(
    ledger_display_rows,
    *,
    date_formatter,
):
    return [
        (
            date_formatter(settle_date),
            f"{opening_balance:,.0f}",
            debit_credit_text,
            f"{running_balance:,.0f}",
            f"{running_investment:,.2f}",
            f"{running_avg:,.2f}",
        )
        for (
            settle_date,
            opening_balance,
            debit_credit_text,
            running_balance,
            running_investment,
            running_avg,
        ) in ledger_display_rows
    ]


def build_detail_corp_tree_rows(
    corp_records,
    *,
    date_formatter,
):
    return [
        (
            date_formatter(record["date"]),
            record["nature"],
            record["val"],
            record["tds"],
        )
        for record in corp_records
    ]


def build_detail_dividend_tree_rows(detail_dividend_data):
    dividend_records = detail_dividend_data["dividend_records"]
    summary_row = None

    if dividend_records:
        summary_row = (
            "TOTAL",
            f"{detail_dividend_data['total_entitled_qty']:,.0f}",
            f"₹{detail_dividend_data['total_invested_amount']:,.2f}",
            f"₹{detail_dividend_data['total_net_amount']:,.2f}",
            "-",
            "-",
            "-",
        )

    return {
        "summary_row": summary_row,
        "detail_rows": list(dividend_records),
    }


def build_realized_pnl_rows(
    realized_rows,
    *,
    current_price: float,
    capital_gains_tax_rates,
):
    formatted_rows = []

    for (
        buy_value,
        holding_days,
        pnl_amount,
        sell_qty,
        sell_value,
        sell_dt,
    ) in realized_rows:
        sell_date = datetime.strptime(sell_dt, "%Y-%m-%d").date()
        stcg_rate, ltcg_rate = capital_gains_tax_rates(sell_date)
        tax_rate = ltcg_rate if holding_days >= 365 else stcg_rate
        tax_amount = pnl_amount * tax_rate if pnl_amount > 0 else 0.0
        opportunity_delta = None
        if current_price > 0 and sell_qty > 0:
            actual_sell_price = sell_value / sell_qty
            opportunity_delta = (current_price - actual_sell_price) * sell_qty

        formatted_rows.append(
            {
                "cost": buy_value,
                "qty": sell_qty,
                "days": holding_days,
                "pnl": pnl_amount,
                "pat": pnl_amount - tax_amount,
                "opportunity_delta": opportunity_delta,
            }
        )

    return formatted_rows


def build_reality_pnl_rows(reality_sells, *, current_price: float):
    formatted_rows = []
    for reality_sell in reality_sells:
        opportunity_delta = None
        if current_price > 0 and reality_sell["qty"] > 0:
            actual_sell_price = (
                reality_sell["sell_value"] / reality_sell["qty"]
            )
            opportunity_delta = (
                current_price - actual_sell_price
            ) * reality_sell["qty"]

        formatted_rows.append(
            {
                "cost": reality_sell["cost"],
                "qty": reality_sell["qty"],
                "days": reality_sell["days"],
                "pnl": reality_sell["pnl"],
                "opportunity_delta": opportunity_delta,
            }
        )

    return formatted_rows


def build_detail_dividend_display_data(
    dividend_source_rows,
    *,
    display_name: str,
    metric_resolver,
):
    corp_records = []
    dividend_records = []
    total_entitled_qty = 0.0
    total_invested_amount = 0.0
    total_net_amount = 0.0

    for (
        record_dt,
        credit_dt,
        div_type,
        entitled_qty,
        gross_amt,
        net_amt,
        tds_amt,
    ) in dividend_source_rows:
        if credit_dt == "1900-01-01":
            continue

        (
            dividend_return_percent,
            annualized_yield,
            holding_days,
        ) = metric_resolver(
            record_dt,
            credit_dt,
            entitled_qty,
            gross_amt,
        )

        invested_amount = None
        if (
            dividend_return_percent is not None
            and math.isfinite(dividend_return_percent)
            and dividend_return_percent != 0
        ):
            invested_amount = gross_amt * 100.0 / dividend_return_percent

        corp_records.append(
            {
                "date": credit_dt,
                "nature": f"Dividend ({div_type})",
                "val": format_dividend_value_with_yield(
                    net_amt,
                    dividend_return_percent,
                    annualized_yield,
                ),
                "tds": f"₹{tds_amt:,.2f}",
            }
        )

        total_entitled_qty += entitled_qty or 0
        if invested_amount is not None:
            total_invested_amount += invested_amount
        total_net_amount += net_amt or 0.0

        dividend_records.append(
            (
                display_name,
                f"{entitled_qty:,.0f}",
                (
                    f"₹{invested_amount:,.2f}"
                    if invested_amount is not None
                    else "Unavailable"
                ),
                f"₹{net_amt:,.2f}",
                (
                    f"{dividend_return_percent:.2f}%"
                    if dividend_return_percent is not None
                    and math.isfinite(dividend_return_percent)
                    else "Unavailable"
                ),
                (
                    f"{annualized_yield:.2f}%"
                    if annualized_yield is not None
                    and math.isfinite(annualized_yield)
                    else "Unavailable"
                ),
                (
                    f"{holding_days:.1f}"
                    if holding_days is not None and math.isfinite(holding_days)
                    else "Unavailable"
                ),
            )
        )

    return {
        "corp_records": corp_records,
        "dividend_records": dividend_records,
        "total_entitled_qty": total_entitled_qty,
        "total_invested_amount": total_invested_amount,
        "total_net_amount": total_net_amount,
    }


def build_master_dividend_display_data(
    dividend_source_rows,
    *,
    metric_resolver,
):
    corp_records = []
    dividend_records = []
    total_entitled_qty = 0.0
    total_invested_amount = 0.0
    total_net_amount = 0.0

    for (
        display_name,
        dividend_stock_id,
        record_dt,
        credit_dt,
        div_type,
        entitled_qty,
        per_share_amt,
        gross_amt,
        net_amt,
        tds_amt,
    ) in dividend_source_rows:
        if credit_dt == "1900-01-01":
            continue

        dividend_return_percent, annualized_yield = metric_resolver(
            dividend_stock_id,
            record_dt,
            credit_dt,
            entitled_qty,
            gross_amt,
        )

        invested_amount = None
        if (
            dividend_return_percent is not None
            and math.isfinite(dividend_return_percent)
            and dividend_return_percent != 0
        ):
            invested_amount = gross_amt * 100.0 / dividend_return_percent

        corp_records.append(
            (
                credit_dt,
                display_name,
                f"Dividend ({div_type})",
                format_dividend_value_with_yield(
                    net_amt,
                    dividend_return_percent,
                    annualized_yield,
                ),
                f"₹{tds_amt:,.2f}",
            )
        )

        total_entitled_qty += entitled_qty or 0
        if invested_amount is not None:
            total_invested_amount += invested_amount
        total_net_amount += net_amt or 0.0

        dividend_records.append(
            (
                display_name,
                format_db_date(credit_dt),
                f"{entitled_qty:,.0f}",
                f"₹{per_share_amt:,.2f}",
                (
                    f"₹{invested_amount:,.2f}"
                    if invested_amount is not None
                    else "Unavailable"
                ),
                f"₹{net_amt:,.2f}",
                (
                    f"{dividend_return_percent:.2f}%"
                    if dividend_return_percent is not None
                    and math.isfinite(dividend_return_percent)
                    else "Unavailable"
                ),
                (
                    f"{annualized_yield:.2f}%"
                    if annualized_yield is not None
                    and math.isfinite(annualized_yield)
                    else "Unavailable"
                ),
            )
        )

    return {
        "corp_records": corp_records,
        "dividend_records": dividend_records,
        "total_entitled_qty": total_entitled_qty,
        "total_invested_amount": total_invested_amount,
        "total_net_amount": total_net_amount,
    }


def build_master_corp_action_records(
    dividend_corp_records,
    split_rows,
    bonus_rows,
):
    corp_records = list(dividend_corp_records)

    for display_name, ex_dt, old_fv, new_fv in split_rows:
        if ex_dt == "1900-01-01":
            continue
        corp_records.append(
            (
                ex_dt,
                display_name,
                "Stock Split",
                f"Ratio {old_fv}:{new_fv}",
                "-",
            )
        )

    for display_name, ex_dt, ratio_old, ratio_new in bonus_rows:
        if ex_dt == "1900-01-01":
            continue
        corp_records.append(
            (
                ex_dt,
                display_name,
                "Bonus Issue",
                f"Ratio {ratio_new} for {ratio_old}",
                "-",
            )
        )

    corp_records.sort(key=lambda record: record[0])
    return corp_records


def build_detail_corp_action_records(
    dividend_corp_records,
    split_rows,
    bonus_rows,
):
    corp_records = list(dividend_corp_records)

    for ex_dt, old_fv, new_fv in split_rows:
        if ex_dt == "1900-01-01":
            continue
        corp_records.append(
            {
                "date": ex_dt,
                "nature": "Stock Split",
                "val": f"Ratio {old_fv}:{new_fv}",
                "tds": "-",
            }
        )

    for ex_dt, ratio_old, ratio_new in bonus_rows:
        if ex_dt == "1900-01-01":
            continue
        corp_records.append(
            {
                "date": ex_dt,
                "nature": "Bonus Issue",
                "val": f"Ratio {ratio_new} for {ratio_old}",
                "tds": "-",
            }
        )

    corp_records.sort(key=lambda record: record["date"])
    return corp_records


def assemble_detail_tree_data(
    cursor,
    id_stk: int,
    display_name: str,
    current_price: float,
    *,
    start_date=None,
    end_date=None,
    capital_gains_tax_rates,
    dividend_metric_resolver,
):
    # 1. Fetch all raw data
    ledger_rows = fetch_detail_ledger_rows(
        cursor, id_stk, start_date, end_date
    )
    dividend_source_rows = fetch_detail_dividend_source_rows(
        cursor, id_stk, start_date, end_date
    )
    split_rows = fetch_detail_split_rows(cursor, id_stk, start_date, end_date)
    bonus_rows = fetch_detail_bonus_rows(cursor, id_stk, start_date, end_date)
    realized_rows = fetch_realized_detail_rows(
        cursor, id_stk, start_date, end_date
    )
    timeline_rows = fetch_detail_timeline_rows(cursor, id_stk)

    # 2. Build intermediate data structures
    detail_dividend_data = build_detail_dividend_display_data(
        dividend_source_rows,
        display_name=display_name,
        metric_resolver=dividend_metric_resolver,
    )
    corp_records = build_detail_corp_action_records(
        detail_dividend_data["corp_records"], split_rows, bonus_rows
    )
    ledger_display_rows = build_detail_ledger_display_rows(ledger_rows)
    reality_summary = build_pooled_cost_reality_summary(
        timeline_rows, current_price=current_price
    )
    formatted_realized_rows = build_realized_pnl_rows(
        realized_rows,
        current_price=current_price,
        capital_gains_tax_rates=capital_gains_tax_rates,
    )
    reality_pnl_rows = build_reality_pnl_rows(
        reality_summary["sells"], current_price=current_price
    )

    # 3. Build final display-ready tree rows
    ledger_tree_rows = build_detail_ledger_tree_rows(
        ledger_display_rows, date_formatter=lambda d: d
    )
    dividend_tree_rows_data = build_detail_dividend_tree_rows(
        detail_dividend_data
    )
    corp_tree_rows = build_detail_corp_tree_rows(
        corp_records, date_formatter=lambda d: d
    )

    return {
        "ledger_tree_rows": ledger_tree_rows,
        "dividend_tree_rows_data": dividend_tree_rows_data,
        "corp_tree_rows": corp_tree_rows,
        "realized_rows": formatted_realized_rows,
        "reality_pnl_rows": reality_pnl_rows,
        "reality_summary": reality_summary,
    }


def assemble_position_quantity_metrics(cursor, id_stk: int, data: dict):
    cursor.execute(
        "SELECT buy_qty, sell_qty FROM stocks WHERE id_stk = ?", (id_stk,)
    )
    stock_qtys = cursor.fetchone()
    buy_qty = stock_qtys[0] if stock_qtys else 0
    sell_qty = stock_qtys[1] if stock_qtys else 0
    current_qty = data["qty"]
    avg_price = (data["inv_amt"] / current_qty) if current_qty > 0 else 0.0

    return {
        "buy_qty": buy_qty,
        "sell_qty": sell_qty,
        "current_qty": current_qty,
        "avg_price": avg_price,
    }


def fetch_detail_dividend_total(
    cursor, id_stk: int, start_date=None, end_date=None
):
    d_where, d_params = _between_clause("credit_dt", start_date, end_date)
    cursor.execute(
        f"SELECT SUM(net_amt) FROM dividends WHERE id_stk = ? {d_where}",
        (id_stk, *d_params),
    )
    total_divs = cursor.fetchone()[0] or 0.0
    return total_divs


def fetch_and_filter_online_corp_actions(
    ticker: str,
    start_date,
    end_date,
    db_actions: dict,
    *,
    yf_lib,
    pd_lib,
    date_formatter,
):
    if not yf_lib:
        return []  # Silently skip if yfinance is not installed

    if not ticker:
        return []

    tkr = yf_lib.Ticker(ticker)
    actions = tkr.actions

    if actions is None or actions.empty:
        return []

    actions.index = pd_lib.to_datetime(actions.index).tz_localize(None)
    mask = (actions.index >= start_date) & (actions.index <= end_date)
    relevant_actions = actions.loc[mask]

    if relevant_actions.empty:
        return []

    online_rows, _ = build_online_corp_action_rows(
        build_online_action_entries(
            relevant_actions.iterrows(),
            date_formatter=date_formatter,
        ),
        db_actions,
    )
    return online_rows


def compute_current_position_metrics(
    qty: float, invested_amt: float, current_price: float, realized_pnl: float
):
    if qty <= 0:
        return {"unrealized": 0.0, "total": realized_pnl}

    cost = invested_amt
    unrealized = 0.0
    if current_price > 0:
        current_value = qty * current_price
        unrealized = current_value - cost

    return {"unrealized": unrealized, "total": realized_pnl + unrealized}


def compute_portfolio_header_totals(stock_data_cache: dict):
    """
    Aggregate position-level metrics into portfolio totals.

    Returns:
        dict: A dictionary containing total_invested, total_value,
              total_unrealized, and total_realized.
    """
    total_invested = 0.0
    total_value = 0.0
    total_unrealized = 0.0
    total_realized = 0.0

    for _, data in stock_data_cache.items():
        if data.get("qty", 0) > 0:
            cost = data.get("inv_amt", 0.0)
            current_price = data.get("price", 0.0)
            current_value = 0.0
            if current_price > 0:
                current_value = data["qty"] * current_price

            total_invested += cost
            total_value += current_value
            total_unrealized += data.get("unrealized", 0.0)
            total_realized += data.get("realized", 0.0)

    return {
        "total_invested": total_invested,
        "total_value": total_value,
        "total_unrealized": total_unrealized,
        "total_realized": total_realized,
    }


def accumulate_live_position_metrics(
    stock_data_cache: dict, market_data_results: dict
):
    """
    Process live market data and accumulate position-level and portfolio metrics.

    Updates stock_data_cache with market prices, calculates unrealized P&L per position,
    and returns portfolio-wide aggregates.

    Args:
        stock_data_cache: Dict of {id_stk: {qty, inv_amt, realized, ...}}
        market_data_results: Dict of {ticker: {price, high52, low52}}

    Returns:
        dict with keys: total_invested, total_value, total_unrealized, total_realized
    """
    total_invested = 0.0
    total_value = 0.0
    total_unrealized = 0.0
    total_realized = 0.0

    for id_stk, data in stock_data_cache.items():
        ticker = data.get("ticker")
        market_data = market_data_results.get(ticker, {})
        data.update(market_data)

        if data.get("qty", 0) > 0:
            cost = data.get("inv_amt", 0.0)
            current_price = data.get("price", 0.0)
            current_value = 0.0
            if current_price > 0:
                current_value = data["qty"] * current_price
                data["unrealized"] = current_value - cost
                data["total"] = data.get("realized", 0.0) + data["unrealized"]

            total_invested += cost
            total_value += current_value
            total_unrealized += data.get("unrealized", 0.0)
            total_realized += data.get("realized", 0.0)

    return {
        "total_invested": total_invested,
        "total_value": total_value,
        "total_unrealized": total_unrealized,
        "total_realized": total_realized,
    }


def initialize_stock_data_cache(
    cursor, stock_rows, is_yearly, start_date, end_date
):
    """
    Build initial stock data cache and compute grand realized P&L.

    Args:
        cursor: DB cursor for fetching yearly realized amounts.
        stock_rows: List of tuples from fetch_report_stock_rows.
        is_yearly: Whether filtering by financial year.
        start_date: Period start for yearly realized calculations.
        end_date: Period end for yearly realized calculations.

    Returns:
        A tuple containing (stock_data_cache, grand_realized).
    """
    stock_data_cache = {}
    grand_realized = 0.0
    for row in stock_rows:
        (
            id_stk,
            short_name,
            company_name,
            ticker,
            qty,
            rpnl,
            inv_amt,
            sector,
        ) = row
        realized = 0.0
        if is_yearly:
            realized = fetch_yearly_realized_amount(
                cursor,
                id_stk,
                start_date,
                end_date,
            )
        else:
            realized = rpnl or 0.0
        grand_realized += realized

        # Fetch STT specifically for this stock's buy transactions
        cursor.execute("SELECT SUM(stt_trd) FROM transactions WHERE id_stk = ? AND trade_type_trd = 'BUY'", (id_stk,))
        stt_paid = cursor.fetchone()[0] or 0.0

        stock_data_cache[id_stk] = {
            "id_stk": id_stk,
            "short_name": short_name,
            "company_name": company_name,
            "ticker": ticker,
            "qty": qty,
            "realized": realized,
            "inv_amt": inv_amt,
            "stt_paid": stt_paid,  # Store per-stock STT for Ex-STT calculations
            "sector": sector or "Unclassified",
            "unrealized": 0.0,
            "total": realized,
            "price": 0.0,
            "high52": 0.0,
            "low52": 0.0,
            "xirr": None,
        }
    return stock_data_cache, grand_realized


def build_report_value_fragments(label: str, value: float, real_value=None):
    label_padded = f"{label:<30}"
    if real_value is None:
        tag = (
            "negative" if value < 0 else "positive" if value > 0 else "normal"
        )
        return [(f"  {label_padded} {value:16,.2f}\n", tag)]

    value_tag = (
        "negative" if value < 0 else "positive" if value > 0 else "normal"
    )
    real_tag = (
        "negative"
        if real_value < 0
        else "positive" if real_value > 0 else "normal"
    )
    return [
        (f"  {label_padded} ", "normal"),
        (f"{value:16,.2f}", value_tag),
        ("  |  ", "normal"),
        (f"{real_value:16,.2f}\n", real_tag),
    ]


def build_realized_pnl_report_fragments(realized_rows, *, reality_rows=None):
    if not realized_rows:
        return [
            ("  No realized gain/loss details available.\n", "normal"),
        ]

    fragments = [
        ("\nRealized Profit/Loss Breakdown (FIFO):\n", "subheader"),
        (
            f"  {'Cost Amount':>12} {'Qty':>5} {'Days':>6} {'Realized Profit/Loss':>21} {'Est. Post-Tax':>14} {'If Sold Today':>18}\n",
            "normal",
        ),
        (
            f"  {'-'*12} {'-'*5} {'-'*6} {'-'*21} {'-'*14} {'-'*18}\n",
            "normal",
        ),
    ]

    for row in realized_rows:
        fragments.append(
            (
                f"  {row['cost']:12,.2f} {row['qty']:5.0f} {row['days']:6} ",
                "normal",
            )
        )
        fragments.append(
            (
                f"{row['pnl']:15,.2f} ",
                "negative" if row["pnl"] < 0 else "positive",
            )
        )
        fragments.append(
            (
                f"{row['pat']:12,.2f} ",
                "negative" if row["pat"] < 0 else "positive",
            )
        )

        if row["opportunity_delta"] is not None:
            fragments.append(
                (
                    f"{row['opportunity_delta']:18,.2f}\n",
                    "positive" if row["opportunity_delta"] > 0 else "negative",
                )
            )
        else:
            fragments.append((f"{'N/A':>18}\n", "normal"))

    if reality_rows:
        fragments.extend(
            [
                (
                    "\nRealized Profit/Loss Breakdown (Reality - Pooled Cost):\n",
                    "subheader",
                ),
                (
                    f"  {'Cost Amount':>12} {'Qty':>5} {'Days':>6} {'Realized Profit/Loss':>21} {'If Sold Today':>18}\n",
                    "normal",
                ),
                (
                    f"  {'-'*12} {'-'*5} {'-'*6} {'-'*21} {'-'*18}\n",
                    "normal",
                ),
            ]
        )
        for row in reality_rows:
            fragments.append(
                (
                    f"  {row['cost']:12,.2f} {row['qty']:5.0f} {row['days']:6} ",
                    "normal",
                )
            )
            fragments.append(
                (
                    f"{row['pnl']:15,.2f} ",
                    "negative" if row["pnl"] < 0 else "positive",
                )
            )
            if row["opportunity_delta"] is not None:
                fragments.append(
                    (
                        f"{row['opportunity_delta']:18,.2f}\n",
                        (
                            "positive"
                            if row["opportunity_delta"] > 0
                            else "negative"
                        ),
                    )
                )
            else:
                fragments.append((f"{'N/A':>18}\n", "normal"))

    fragments.extend(
        [
            (
                "\n* PAT is an estimation assuming flat Capital Gains rates based on historical transaction dates, without factoring in yearly exemption limits (₹1L/₹1.25L).\n",
                "italic",
            ),
            (
                "* 'If Sold Today' calculates Opportunity Delta: Green = Missed Profit (stock rose after selling). Red = Saved Loss (stock fell after selling).\n",
                "italic",
            ),
        ]
    )
    return fragments


def build_detail_position_overview_fragments(
    *,
    total_investment: float,
    disinvestment_amount: float,
    current_invested_amount: float,
    buy_qty: float,
    sell_qty: float,
    current_qty: float,
    avg_price: float,
    current_price: float,
    reality_summary,
):
    fragments = [
        (
            f"  {'':<26} {'Income Tax (IT)':>16}  |  {'Reality (Pooled)':>16}\n",
            "subheader",
        ),
        (f"  {'-'*30} {'-'*16}  |  {'-'*16}\n", "normal"),
    ]
    fragments.extend(
        build_report_value_fragments(
            "Total Invested Amount:",
            total_investment,
            total_investment,
        )
    )
    fragments.extend(
        build_report_value_fragments(
            "Amount Disinvested:",
            disinvestment_amount,
            reality_summary["disinvested"],
        )
    )
    fragments.extend(
        build_report_value_fragments(
            "Currently Invested Amount:",
            current_invested_amount,
            reality_summary["invested"],
        )
    )
    fragments.append(("\n", "normal"))
    fragments.extend(
        [
            (
                f"  {'Total Bought Quantity:':<30} {buy_qty:16.0f}  |  {buy_qty:16.0f}\n",
                "normal",
            ),
            (
                f"  {'Total Sold Quantity:':<30} {sell_qty:16.0f}  |  {sell_qty:16.0f}\n",
                "normal",
            ),
            (
                f"  {'Current Quantity:':<30} {current_qty:16.0f}  |  {reality_summary['qty']:16.0f}\n",
                "normal",
            ),
        ]
    )

    if current_qty > 0:
        fragments.extend(
            build_report_value_fragments(
                "Average Price per Share:",
                avg_price,
                reality_summary["avg_price"],
            )
        )
        fragments.extend(
            build_report_value_fragments(
                "Current Market Price (CMP):",
                current_price,
                current_price,
            )
        )

    return fragments


def compute_intraday_vwap_analysis(candles):
    vwap_values = []
    cumulative_price_volume = 0.0
    cumulative_volume = 0.0
    latest_close = 0.0

    for high_value, low_value, close_value, volume_value in candles:
        typical_price = (
            float(high_value) + float(low_value) + float(close_value)
        ) / 3.0
        volume = float(volume_value)
        cumulative_price_volume += typical_price * volume
        cumulative_volume += volume
        vwap = (
            cumulative_price_volume / cumulative_volume
            if cumulative_volume > 0
            else float(close_value)
        )
        vwap_values.append(vwap)
        latest_close = float(close_value)

    if not vwap_values:
        return None

    current_vwap = vwap_values[-1]
    trend = "BULLISH 🟢" if latest_close > current_vwap else "BEARISH 🔴"
    delta_pct = (
        ((latest_close - current_vwap) / current_vwap) * 100
        if current_vwap != 0
        else 0.0
    )
    return {
        "vwap_values": vwap_values,
        "current_price": latest_close,
        "current_vwap": current_vwap,
        "trend": trend,
        "delta_pct": delta_pct,
    }


def compute_intraday_price_bounds(
    close_values, vwap_values, *, current_price: float
):
    y_min = min(min(close_values), min(vwap_values))
    y_max = max(max(close_values), max(vwap_values))
    padding = current_price * 0.01
    return y_min - padding, y_max + padding


def resolve_intraday_chart_window(index_values):
    if not index_values:
        return None

    first_value = index_values[0]
    trade_date = (
        first_value.date()
        if hasattr(first_value, "date")
        else datetime.strptime(str(first_value), "%Y-%m-%d").date()
    )
    return (
        datetime.combine(trade_date, time(9, 15)),
        datetime.combine(trade_date, time(15, 30)),
    )


def build_intraday_analysis_lines(
    *,
    current_price: float,
    current_vwap: float,
    trend: str,
    delta_pct: float,
):
    return [
        f"Current Price : ₹{current_price:,.2f}\n",
        f"Intraday VWAP : ₹{current_vwap:,.2f}\n",
        f"Trend Status  : {trend} (Delta: {delta_pct:+.2f}%)\n",
        f"{'-'*60}\n",
        "📈 CHART LEGEND & ANALYSIS GUIDE:\n\n",
        "Solid Line (Price): The actual traded price at each 5-min interval.\n",
        "Dashed Line (VWAP): Volume Weighted Average Price. It calculates the\n",
        "true average price by factoring in trading volume. If the Solid Line\n",
        "is ABOVE the Dashed Line, the market is willing to pay a premium,\n",
        "indicating bullish intraday momentum.\n",
    ]


def build_current_holdings_row(
    holding_data,
    *,
    avg_price: float,
    cost: float,
    stt_paid: float = 0.0,
):
    cost_ex_stt = cost - stt_paid
    avg_price_ex_stt = (cost_ex_stt / holding_data["qty"]) if holding_data["qty"] > 0 else 0.0

    unrealized_pct = (
        (holding_data["unrealized"] / cost * 100) if cost > 0 else 0.0
    )

    unrealized_ex_stt = (holding_data["qty"] * holding_data["price"]) - cost_ex_stt
    unrealized_ex_stt_pct = (unrealized_ex_stt / cost_ex_stt * 100) if cost_ex_stt > 0 else 0.0

    unrealized_text = (
        f"{holding_data['unrealized']:,.2f} ({unrealized_pct:+.2f}%) "
        f"[₹{unrealized_ex_stt:,.2f} ({unrealized_ex_stt_pct:+.2f}%)]"
    )

    row_tag = "neutral"
    if holding_data["unrealized"] > 0:
        row_tag = "profit"
    elif holding_data["unrealized"] < 0:
        row_tag = "loss"

    return {
        "values": (
            holding_data["ticker"],
            holding_data["qty"],
            f"{avg_price:,.2f} (₹{avg_price_ex_stt:,.2f})",
            f"{cost:,.2f} (₹{cost_ex_stt:,.2f})",
            f"{holding_data['price']:,.2f}",
            unrealized_text,
            f"{holding_data['realized']:,.2f}",
        ),
        "tag": row_tag,
    }


def build_current_holdings_header_values(
    *,
    total_invested: float,
    total_value: float,
    total_unrealized: float,
    total_realized: float,
    total_invested_ex_stt: float,
):
    total_unrealized_pct = (
        (total_unrealized / total_invested * 100)
        if total_invested > 0
        else 0.0
    )

    # Calculate Unrealized and its percentage based on Ex-STT cost
    total_unrealized_ex_stt = total_value - total_invested_ex_stt
    total_unrealized_ex_stt_pct = (
        (total_unrealized_ex_stt / total_invested_ex_stt * 100)
        if total_invested_ex_stt > 0
        else 0.0
    )

    return {
        "invested": f"Current Cost Basis: ₹{total_invested:,.2f} (₹{total_invested_ex_stt:,.2f})",
        "value": f"Live Market Value: ₹{total_value:,.2f}",
        "unrealized": (
            f"Unrealized Gain/Loss: ₹{total_unrealized:,.2f} ({total_unrealized_pct:+.2f}%) "
            f"[₹{total_unrealized_ex_stt:,.2f} ({total_unrealized_ex_stt_pct:+.2f}%)]"
        ),
        "unrealized_color": "#27ae60" if total_unrealized >= 0 else "#c0392b",
        "realized": f"Realized Gain/Loss: ₹{total_realized:,.2f}",
    }


def build_summary_tree_rows(summary_agg):
    yearly_rows = []
    totals = {
        "inv": 0.0,
        "pnl": 0.0,
        "pat": 0.0,
        "div": 0.0,
        "miss_profit": 0.0,
        "save_loss": 0.0,
    }

    for fy_label in sorted(summary_agg.keys(), reverse=True):
        row = summary_agg[fy_label]
        total_return = row["pat"] + row["div"]
        yearly_rows.append(
            (
                fy_label,
                f"{row['inv']:,.2f}",
                f"{row['pnl']:,.2f}",
                f"{row['pat']:,.2f}",
                f"{row['div']:,.2f}",
                f"{total_return:,.2f}",
                f"{row['miss_profit']:,.2f}",
                f"{row['save_loss']:,.2f}",
            )
        )
        for key in totals:
            totals[key] += row[key]

    all_years_return = totals["pat"] + totals["div"]
    return {
        "summary_row": (
            "ALL YEARS",
            f"{totals['inv']:,.2f}",
            f"{totals['pnl']:,.2f}",
            f"{totals['pat']:,.2f}",
            f"{totals['div']:,.2f}",
            f"{all_years_return:,.2f}",
            f"{totals['miss_profit']:,.2f}",
            f"{totals['save_loss']:,.2f}",
        ),
        "yearly_rows": yearly_rows,
    }


def build_capital_stats_tree_rows(capital_stats, *, financial_year_sort_key):
    overall_stats = capital_stats["overall"]
    summary_row = (
        "ALL YEARS",
        f"{overall_stats['total_investment']:,.2f}",
        f"{overall_stats['total_disinvestment']:,.2f}",
        f"{overall_stats['max_invested']:,.2f}",
        f"{overall_stats['min_invested']:,.2f}",
        f"{overall_stats['largest_investment']:,.2f}",
        f"{overall_stats['largest_disinvestment']:,.2f}",
    )
    yearly_rows = []
    for fy_label in sorted(
        capital_stats["yearly"], key=financial_year_sort_key, reverse=True
    ):
        stats = capital_stats["yearly"][fy_label]
        yearly_rows.append(
            (
                fy_label,
                f"{stats['total_investment']:,.2f}",
                f"{stats['total_disinvestment']:,.2f}",
                f"{stats['max_invested']:,.2f}",
                f"{stats['min_invested']:,.2f}",
                f"{stats['largest_investment']:,.2f}",
                f"{stats['largest_disinvestment']:,.2f}",
            )
        )
    return {"summary_row": summary_row, "yearly_rows": yearly_rows}


def build_stock_tree_initial_row(
    *,
    display_name: str,
    realized: float,
    is_yearly: bool,
    current_qty: float,
):
    return (
        display_name,
        f"{realized:,.2f}",
        "Fetching..." if not is_yearly and current_qty > 0 else "-",
        f"{realized:,.2f}",
        "Calculating...",
    )


def build_stock_tree_update_row(
    *,
    display_name: str,
    realized: float,
    total: float,
    unrealized: float,
    xirr_rate,
    show_unrealized: bool,
):
    unrealized_text = f"{unrealized:,.2f}" if show_unrealized else "-"
    xirr_text = f"{xirr_rate:.2%}" if xirr_rate is not None else "N/A"
    return (
        display_name,
        f"{realized:,.2f}",
        unrealized_text,
        f"{total:,.2f}",
        xirr_text,
    )


def build_grand_summary_row(
    *,
    grand_realized: float,
    grand_unrealized=None,
):
    total_value = grand_realized + (grand_unrealized or 0.0)
    unrealized_text = (
        f"{grand_unrealized:,.2f}" if grand_unrealized is not None else "-"
    )
    return (
        "🏆 GRAND SUMMARY",
        f"{grand_realized:,.2f}",
        unrealized_text,
        f"{total_value:,.2f}",
        "-",
    )


def build_detail_header_fragments(stock_data, *, is_yearly: bool):
    fragments = [
        (f"{'='*75}\n", "normal"),
        (
            f"Stock: {stock_data['short_name']} ({stock_data['company_name']})\n",
            "header",
        ),
    ]
    if not is_yearly and stock_data["ticker"]:
        fragments.append(
            (
                f"Ticker: {stock_data['ticker']} | Live Price: ₹{stock_data['price']:,.2f}\n",
                "subheader",
            )
        )
        if stock_data["high52"] > 0:
            fragments.append(
                (
                    f"52-Week Range: ₹{stock_data['low52']:,.2f} - ₹{stock_data['high52']:,.2f}\n",
                    "italic",
                )
            )
    fragments.append((f"{'='*75}\n\n", "normal"))
    return fragments


def build_summary_selection_fragments():
    return [
        ("Portfolio Summary\n\n", "header"),
        (
            "Select an individual stock from the list to see detailed transaction history, XIRR calculations, and specific realized/unrealized breakdowns.\n",
            "normal",
        ),
    ]


def build_portfolio_summary(
    sell_rows,
    investment_rows,
    dividend_rows,
    stock_prices,
    capital_gains_tax_rates,
):
    """Build the yearly portfolio summary used by the P&L report.

    This preserves the current reporting behavior: yearly summary rows are
    created from realized sell activity, then investment and dividend totals
    are added only for those already-present financial years.
    """
    summary_agg = {}

    for s_dt, b_dt, pnl, s_qty, s_val, stk_id in sell_rows:
        sell_date = datetime.strptime(s_dt, "%Y-%m-%d").date()
        buy_date = datetime.strptime(b_dt, "%Y-%m-%d").date()
        fy_label = _financial_year_label(s_dt)

        if fy_label not in summary_agg:
            summary_agg[fy_label] = _new_portfolio_summary_row()

        summary_agg[fy_label]["pnl"] += pnl

        stcg_rate, ltcg_rate = capital_gains_tax_rates(sell_date)
        tax_rate = (
            ltcg_rate if (sell_date - buy_date).days >= 365 else stcg_rate
        )
        tax_amt = pnl * tax_rate if pnl > 0 else 0.0
        summary_agg[fy_label]["pat"] += pnl - tax_amt

        live_price = stock_prices.get(stk_id, 0.0)
        if live_price > 0 and s_qty > 0:
            actual_sell_price = s_val / s_qty
            delta = (live_price - actual_sell_price) * s_qty
            if delta > 0:
                summary_agg[fy_label]["miss_profit"] += delta
            else:
                summary_agg[fy_label]["save_loss"] += abs(delta)

    for t_dt, amt in investment_rows:
        fy_label = _financial_year_label(t_dt)
        if fy_label in summary_agg:
            summary_agg[fy_label]["inv"] += amt

    for c_dt, n_amt in dividend_rows:
        if c_dt == "1900-01-01":
            continue
        fy_label = _financial_year_label(c_dt)
        if fy_label in summary_agg:
            summary_agg[fy_label]["div"] += n_amt

    return summary_agg


def get_financial_years(conn):
    """Return financial years present in transactions, newest first."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT DISTINCT CAST(STRFTIME('%Y', trd_dt, '-3 months') AS INTEGER) "
        "AS fy_start_year FROM transactions ORDER BY fy_start_year DESC"
    )
    years = [row[0] for row in cursor.fetchall()]
    return [f"FY {year}-{str(year + 1)[-2:]}" for year in years]


def xnpv(rate, values, dates):
    """Return NPV for irregular cash flows."""
    if rate <= -1.0:
        return float("inf")
    if len(values) != len(dates):
        raise ValueError("values and dates must have the same length")
    if not dates:
        return 0.0

    d0 = dates[0]
    return sum(
        value / ((1 + rate) ** ((current_date - d0).days / 365.0))
        for value, current_date in zip(values, dates)
    )


def xirr(values, dates, guess=0.1):
    """Return IRR for irregular cash flows, or None when it does not converge."""
    guesses = [guess, -0.3, -0.7, -0.9, 0.0, 0.5]

    for current_guess in guesses:
        try:
            rate = current_guess
            for _ in range(100):
                npv = xnpv(rate, values, dates)
                if abs(npv) < 1e-6:
                    return rate

                d0 = dates[0]
                derivative = sum(
                    -value
                    * (current_date - d0).days
                    / 365.0
                    / ((1 + rate) ** ((current_date - d0).days / 365.0 + 1))
                    for value, current_date in zip(values, dates)
                )

                if derivative == 0:
                    break

                rate = rate - npv / derivative
        except (ZeroDivisionError, OverflowError, TypeError):
            continue

    return None


def build_xirr_cashflows(
    purchase_rows,
    sell_rows,
    *,
    current_qty: int = 0,
    current_price: float = 0.0,
    include_live_position: bool = False,
    valuation_date: date | None = None,
):
    """Build dated cashflows for XIRR calculation."""
    flow_dates = []
    flow_amounts = []

    for purchase_date, purchase_amount in purchase_rows:
        flow_dates.append(datetime.strptime(purchase_date, "%Y-%m-%d").date())
        flow_amounts.append(-purchase_amount)

    for sell_date, sell_amount in sell_rows:
        flow_dates.append(datetime.strptime(sell_date, "%Y-%m-%d").date())
        flow_amounts.append(sell_amount)

    if include_live_position and current_qty > 0 and current_price > 0:
        flow_dates.append(valuation_date or date.today())
        flow_amounts.append(current_qty * current_price)

    return flow_amounts, flow_dates


def compute_position_xirr(
    purchase_rows,
    sell_rows,
    *,
    current_qty: int = 0,
    current_price: float = 0.0,
    include_live_position: bool = False,
    valuation_date: date | None = None,
):
    """Compute XIRR for one stock position, returning None when invalid."""
    flow_amounts, flow_dates = build_xirr_cashflows(
        purchase_rows,
        sell_rows,
        current_qty=current_qty,
        current_price=current_price,
        include_live_position=include_live_position,
        valuation_date=valuation_date,
    )

    if not flow_dates:
        return None

    if not any(amount > 0 for amount in flow_amounts):
        return None

    if not any(amount < 0 for amount in flow_amounts):
        return None

    return xirr(flow_amounts, flow_dates)


def format_dividend_value_with_yield(
    displayed_amount: float,
    dividend_return_percent: float | None,
    annualized_yield_percent: float | None,
) -> str:
    """Format dividend amount with simple and annualized return metrics."""
    amount_text = f"₹{displayed_amount:,.2f}"
    return_text = "Return unavailable"
    annualized_text = "Annualized unavailable"

    if dividend_return_percent is not None and math.isfinite(
        dividend_return_percent
    ):
        return_text = f"Ret {dividend_return_percent:.2f}%"

    if annualized_yield_percent is not None and math.isfinite(
        annualized_yield_percent
    ):
        annualized_text = f"Ann {annualized_yield_percent:.2f}% p.a."

    return f"{amount_text} | {return_text} | {annualized_text}"


def build_allocation_tree_rows(stock_data_cache: dict, total_value: float):
    sector_agg = {}
    stock_agg = []

    if total_value <= 0:
        return {"sector_rows": [], "stock_rows": []}

    for _, data in stock_data_cache.items():
        qty = data.get("qty", 0)
        price = data.get("price", 0.0)
        if qty > 0 and price > 0:
            val = qty * price
            sector = data.get("sector", "Unclassified")
            if not sector:
                sector = "Unclassified"

            sector_agg[sector] = sector_agg.get(sector, 0.0) + val

            pct = (val / total_value) * 100
            stock_agg.append(
                {
                    "name": data.get("ticker") or data.get("short_name"),
                    "value": val,
                    "pct": pct,
                }
            )

    sector_rows = [
        (sec, f"₹{val:,.2f}", f"{((val / total_value) * 100):.2f}%")
        for sec, val in sorted(
            sector_agg.items(), key=lambda x: x[1], reverse=True
        )
    ]
    stock_rows = [
        (stk["name"], f"₹{stk['value']:,.2f}", f"{stk['pct']:.2f}%")
        for stk in sorted(stock_agg, key=lambda x: x["value"], reverse=True)
    ]

    return {"sector_rows": sector_rows, "stock_rows": stock_rows}
