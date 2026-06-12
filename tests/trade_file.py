# -*- coding: utf-8 -*-
"""Import helper: read legacy DB rows and import them into the current DB.

This module provides three small pieces used by the importer command:

- _fetch_source_transactions(src_path): read-only SELECTs against a legacy
    SQLite file and returns a list of transaction dictionaries. Each dict
    contains an ``exchange_orders`` list of dicts.
- import_transaction(conn, tx): execute the exact SQL sequence used by the
    interactive add flow (contracts -> transactions -> exchange_orders).
    It captures ``id_trd`` via ``cursor.lastrowid`` and commits after the
    full sequence.
- trade_entry_from_file(parent, src_db_path): a minimal modal UI that walks
    the rows and prompts the user to Add or Skip each transaction.

All write operations set PRAGMA foreign_keys = ON before executing and
commit only after the entire sequence succeeds.
"""

from __future__ import annotations

import sqlite3
import typing as _t
import tkinter as tk
from tkinter import ttk
import os

from Shared.globals import STOCK_DB_PATH, get_db_connection, logger
from .dialog_utils import show_colorful_info, show_colorful_error
from .window_manager import push_window, pop_window
from .modal_utils import disable_parent, enable_parent
from tkinter import filedialog

# Guard to prevent multiple importer modals being opened concurrently
_importer_open = False


def _fetch_source_transactions(src_path: str) -> _t.List[_t.Dict[str, _t.Any]]:
    """Return transactions (with nested exchange_orders) from ``src_path``.

    The function performs only SELECT queries and will not modify the DB.
    It returns a list of dictionaries ready for the import core.
    """
    # flake8: noqa
    # type: ignore
    rows: _t.List[_t.Dict[str, _t.Any]] = []
    conn = None
    try:
        # Resolve src_path if it does not exist: try module dir, DB dir, cwd

        candidates = [src_path]
        # module directory
        module_dir = os.path.dirname(os.path.abspath(__file__))
        candidates.append(os.path.join(module_dir, src_path))
        # directory where current DB resides
        try:
            db_dir = os.path.dirname(os.path.abspath(STOCK_DB_PATH))
            candidates.append(os.path.join(db_dir, src_path))
        except (OSError, TypeError, NameError):
            pass
        # current working directory
        candidates.append(os.path.join(os.getcwd(), src_path))

        chosen = None
        for c in candidates:
            try:
                if os.path.exists(c):
                    chosen = c
                    break
            except OSError:
                continue
        if chosen is None:
            logger.error(
                "Source DB not found; looked for %s (candidates: %s)",
                src_path,
                candidates,
            )
            return rows

        logger.info("Using source DB for import: %s", chosen)
        conn = sqlite3.connect(chosen)
        cur = conn.cursor()

        cur.execute(
            (
                "SELECT id_trd, cont_no, trd_dt, company_name, "
                "trade_type_trd, id_stk, qty_trd, wap_unit_trd, "
                "brok_unit_trd, net_amt_trd "
                "FROM transactions "
                "ORDER BY trd_dt, id_trd"
            )
        )

        for (
            id_trd,
            cont_no,
            trd_dt,
            company_name,
            trade_type_trd,
            id_stk,
            qty_trd,
            wap_unit_trd,
            brok_unit_trd,
            net_amt_trd,
        ) in cur.fetchall():

            cur.execute(
                (
                    "SELECT ord_no, ord_dt, trd_no, qty_eo, rate_eo, "
                    "brok_unit_eo, net_rate_eo, net_total_eo "
                    "FROM exchange_orders WHERE id_trd = ? "
                    "ORDER BY ord_dt, ord_no"
                ),
                (id_trd,),
            )

            eos = [
                {
                    "ord_no": r[0],
                    "ord_dt": r[1],
                    "trd_no": r[2],
                    "qty_eo": r[3],
                    "rate_eo": r[4],
                    "brok_unit_eo": r[5],
                    "net_rate_eo": r[6],
                    "net_total_eo": r[7],
                }
                for r in cur.fetchall()
            ]

            rows.append(
                {
                    "src_id_trd": id_trd,
                    "cont_no": cont_no,
                    "trd_dt": trd_dt,
                    "company_name": company_name,
                    "trade_type_trd": trade_type_trd,
                    "id_stk": id_stk,
                    "qty_trd": qty_trd,
                    "wap_unit_trd": wap_unit_trd,
                    "brok_unit_trd": brok_unit_trd,
                    "net_amt_trd": net_amt_trd,
                    "exchange_orders": eos,
                }
            )

    except sqlite3.Error as exc:
        logger.exception("Error reading source DB %s: %s", src_path, exc)
    finally:
        if conn:
            try:
                conn.close()
            except (sqlite3.Error, OSError):
                # best-effort close; nothing we can do if it fails
                pass

    return rows


def stream_source_transactions(
    src_path: str,
) -> _t.Iterator[_t.Dict[str, _t.Any]]:
    """Yield transactions (with nested exchange_orders) from ``src_path``.

    This is a memory-friendly generator variant of ``_fetch_source_transactions``
    that yields one transaction dict at a time. It performs only SELECTs and
    does not modify the source DB.
    """
    conn = None
    try:
        # Reuse the same resolution logic as _fetch_source_transactions
        candidates = [src_path]
        module_dir = os.path.dirname(os.path.abspath(__file__))
        candidates.append(os.path.join(module_dir, src_path))
        try:
            db_dir = os.path.dirname(os.path.abspath(STOCK_DB_PATH))
            candidates.append(os.path.join(db_dir, src_path))
        except (OSError, TypeError, NameError):
            pass
        candidates.append(os.path.join(os.getcwd(), src_path))

        chosen = None
        for c in candidates:
            try:
                if os.path.exists(c):
                    chosen = c
                    break
            except OSError:
                continue
        if chosen is None:
            logger.error(
                "Source DB not found; looked for %s (candidates: %s)",
                src_path,
                candidates,
            )
            return

        conn = sqlite3.connect(chosen)
        cur = conn.cursor()
        cur.execute(
            (
                "SELECT id_trd, cont_no, trd_dt, company_name, "
                "trade_type_trd, id_stk, qty_trd, wap_unit_trd, "
                "brok_unit_trd, net_amt_trd "
                "FROM transactions "
                "ORDER BY trd_dt, id_trd"
            )
        )

        for (
            id_trd,
            cont_no,
            trd_dt,
            company_name,
            trade_type_trd,
            id_stk,
            qty_trd,
            wap_unit_trd,
            brok_unit_trd,
            net_amt_trd,
        ) in cur:

            cur.execute(
                (
                    "SELECT ord_no, ord_dt, trd_no, qty_eo, rate_eo, "
                    "brok_unit_eo, net_rate_eo, net_total_eo "
                    "FROM exchange_orders WHERE id_trd = ? "
                    "ORDER BY ord_dt, ord_no"
                ),
                (id_trd,),
            )

            eos = [
                {
                    "ord_no": r[0],
                    "ord_dt": r[1],
                    "trd_no": r[2],
                    "qty_eo": r[3],
                    "rate_eo": r[4],
                    "brok_unit_eo": r[5],
                    "net_rate_eo": r[6],
                    "net_total_eo": r[7],
                }
                for r in cur.fetchall()
            ]

            # Also attempt to fetch the contract row matching cont_no from
            # the source DB so the importer can carry over contract fields
            # when available.
            contract = None
            try:
                cur.execute(
                    (
                        "SELECT cont_no, trd_dt, settle_no, settle_dt, "
                        "no_of_trades FROM contracts WHERE cont_no = ?"
                    ),
                    (cont_no,),
                )
                r = cur.fetchone()
                if r is not None:
                    contract = {
                        "cont_no": r[0],
                        "trd_dt": r[1],
                        "settle_no": r[2],
                        "settle_dt": r[3],
                        "no_of_trades": r[4],
                    }
            except sqlite3.Error:
                # best-effort: if contract lookup fails, continue without it
                contract = None

            yield {
                "src_id_trd": id_trd,
                "cont_no": cont_no,
                "trd_dt": trd_dt,
                "company_name": company_name,
                "trade_type_trd": trade_type_trd,
                "id_stk": id_stk,
                "qty_trd": qty_trd,
                "wap_unit_trd": wap_unit_trd,
                "brok_unit_trd": brok_unit_trd,
                "net_amt_trd": net_amt_trd,
                "exchange_orders": eos,
                "contract": contract,
            }

    except sqlite3.Error as exc:
        logger.exception("Error reading source DB %s: %s", src_path, exc)
    finally:
        if conn:
            try:
                conn.close()
            except (sqlite3.Error, OSError):
                pass


def import_transaction_from_legacy(
    conn: sqlite3.Connection,
    tx: _t.Dict[str, _t.Any],
) -> bool:
    """Import a transaction dict where ``tx`` may include a source `contract`.

    This function prefers contract-level fields from ``tx['contract']`` when
    present and otherwise falls back to the original `import_transaction`
    behavior. It delegates exchange_order/aggregate logic to the same code
    path as the interactive import to preserve invariants.
    """
    # If there is no contract payload, defer to the original function which
    # inserts/ignores contracts using minimal fields.
    contract = tx.get("contract")
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA foreign_keys = ON")

        if contract:
            # Insert or ignore contract using the fuller set of fields found
            # in the legacy DB contract row.
            cur.execute(
                (
                    "INSERT OR IGNORE INTO contracts"
                    " (cont_no, trd_dt, settle_no, settle_dt, no_of_trades)"
                    " VALUES (?, ?, ?, ?, ?)"
                ),
                (
                    contract.get("cont_no"),
                    contract.get("trd_dt", tx.get("trd_dt")),
                    contract.get("settle_no", tx.get("settle_no", 0)),
                    contract.get("settle_dt", tx.get("settle_dt", tx.get("trd_dt"))),
                    contract.get("no_of_trades", tx.get("no_of_trades", 1)),
                ),
            )
        else:
            # Minimal contract insert (same as import_transaction)
            cur.execute(
                (
                    "INSERT OR IGNORE INTO contracts"
                    " (cont_no, trd_dt, settle_no, settle_dt, no_of_trades)"
                    " VALUES (?, ?, ?, ?, ?)"
                ),
                (
                    tx.get("cont_no"),
                    tx.get("trd_dt"),
                    tx.get("settle_no", 0),
                    tx.get("settle_dt", tx.get("trd_dt")),
                    tx.get("no_of_trades", 1),
                ),
            )

        # Reuse the rest of the import logic by constructing a tx-like dict
        # that the core import code understands. The original `import_transaction`
        # already handles transactions/exchange_orders & aggregates.
        return import_transaction(conn, tx)

    except sqlite3.Error:
        try:
            conn.rollback()
        except sqlite3.Error:
            pass
        return False


def perform_import_from_legacy(
    src_path: str,
    *,
    dry_run: bool = False,
    tx_processor: (
        _t.Callable[[sqlite3.Connection, _t.Dict[str, _t.Any]], bool] | None
    ) = None,
) -> tuple[int, int]:
    """Import transactions from ``src_path`` into the live DB.

    Args:
        src_path: path to legacy DB file.
        dry_run: if True, run inside a transaction and roll back at the end.
        tx_processor: optional callable(conn, tx) -> bool. If not provided,
            the module-level ``import_transaction`` is used.

    Returns a tuple (imported_count, failed_count).
    """
    if tx_processor is None:
        tx_processor = import_transaction_from_legacy

    imported = 0
    failed = 0

    # Use the streaming reader so we only hold one tx at a time
    gen = stream_source_transactions(src_path)
    try:
        with get_db_connection() as conn:
            if dry_run:
                try:
                    conn.execute("BEGIN")
                except sqlite3.Error:
                    pass
            for tx in gen:
                ok = tx_processor(conn, tx)
                if ok:
                    imported += 1
                else:
                    failed += 1
            if dry_run:
                try:
                    conn.rollback()
                except sqlite3.Error:
                    pass
    except sqlite3.Error:
        logger.exception("perform_import_from_legacy: DB error")

    return imported, failed


def import_transaction(
    conn: sqlite3.Connection,
    tx: _t.Dict[str, _t.Any],
) -> bool:
    """Import a single transaction dict into the current DB.

    The SQL sequence mirrors the interactive add flow exactly:
     1. Insert into ``contracts`` (cont_no, trd_dt, settle_no,
         settle_dt, no_of_trades)
     2. Lookup/insert/update ``transactions`` and capture ``id_trd`` using
         ``cursor.lastrowid`` when an INSERT is performed.
     3. Insert or update ``exchange_orders`` rows referencing the
         obtained id_trd.

    Returns True on success, False on failure.
    """
    try:
        cur = conn.cursor()
        # Ensure FKs are enforced
        cur.execute("PRAGMA foreign_keys = ON")

        # 1) contracts insert (use minimal fields)
        cur.execute(
            (
                "INSERT OR IGNORE INTO contracts"
                " (cont_no, trd_dt, settle_no, settle_dt, no_of_trades)"
                " VALUES (?, ?, ?, ?, ?)"
            ),
            (
                tx.get("cont_no"),
                tx.get("trd_dt"),
                tx.get("settle_no", 0),
                tx.get("settle_dt", tx.get("trd_dt")),
                tx.get("no_of_trades", 1),
            ),
        )

        # 2) transactions: check for existing
        cur.execute(
            (
                "SELECT id_trd FROM transactions"
                " WHERE cont_no = ? AND company_name = ? AND id_stk = ?"
            ),
            (tx.get("cont_no"), tx.get("company_name"), tx.get("id_stk")),
        )
        found = cur.fetchone()
        if found:
            id_trd = found[0]
            cur.execute(
                (
                    "UPDATE transactions"
                    " SET trd_dt = ?, trade_type_trd = ?, qty_trd = ?,"
                    " wap_unit_trd = ?, brok_unit_trd = ?,"
                    " price_lot_trd = ?, net_amt_trd = ?"
                    " WHERE id_trd = ?"
                ),
                (
                    tx.get("trd_dt"),
                    tx.get("trade_type_trd"),
                    tx.get("qty_trd"),
                    tx.get("wap_unit_trd"),
                    tx.get("brok_unit_trd"),
                    # price_lot_trd absent? use wap_unit_trd
                    tx.get("price_lot_trd", tx.get("wap_unit_trd")),
                    tx.get("net_amt_trd"),
                    id_trd,
                ),
            )
            # price_lot_trd may not exist in source; default to wap_unit_trd
        else:
            cur.execute(
                (
                    "INSERT INTO transactions"
                    " (cont_no, trd_dt, company_name, trade_type_trd, id_stk, "
                    "qty_trd, wap_unit_trd, brok_unit_trd, price_lot_trd, "
                    "net_amt_trd, sold_qty)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
                ),
                (
                    tx.get("cont_no"),
                    tx.get("trd_dt"),
                    tx.get("company_name"),
                    tx.get("trade_type_trd"),
                    tx.get("id_stk"),
                    tx.get("qty_trd"),
                    tx.get("wap_unit_trd"),
                    tx.get("brok_unit_trd"),
                    tx.get("price_lot_trd", tx.get("wap_unit_trd")),
                    tx.get("net_amt_trd"),
                    tx.get("sold_qty", 0),
                ),
            )
            id_trd = cur.lastrowid

        # 3) exchange_orders: update existing by ord_no/ord_dt else insert
        for eo in tx.get("exchange_orders", []):
            # Try update first (mirrors interactive behavior)
            cur.execute(
                (
                    "UPDATE exchange_orders"
                    " SET id_trd = ?, trd_no = ?, qty_eo = ?, rate_eo = ?,"
                    " brok_unit_eo = ?, net_rate_eo = ?, net_total_eo = ?"
                    " WHERE ord_no = ? AND ord_dt = ?"
                ),
                (
                    id_trd,
                    eo.get("trd_no"),
                    eo.get("qty_eo"),
                    eo.get("rate_eo"),
                    eo.get("brok_unit_eo"),
                    eo.get("net_rate_eo"),
                    eo.get("net_total_eo"),
                    eo.get("ord_no"),
                    eo.get("ord_dt"),
                ),
            )
            if cur.rowcount == 0:
                cur.execute(
                    (
                        "INSERT INTO exchange_orders"
                        " (id_trd, ord_no, ord_dt, trd_no, qty_eo, rate_eo,"
                        " brok_unit_eo, net_rate_eo, net_total_eo)"
                        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
                    ),
                    (
                        id_trd,
                        eo.get("ord_no"),
                        eo.get("ord_dt"),
                        eo.get("trd_no"),
                        eo.get("qty_eo"),
                        eo.get("rate_eo"),
                        eo.get("brok_unit_eo"),
                        eo.get("net_rate_eo"),
                        eo.get("net_total_eo"),
                    ),
                )

            # After exchange_orders are inserted/updated, compute transaction-
            # level aggregates from exchange_orders to ensure fields like
            # qty_trd, wap_unit_trd, brok_unit_trd, brok_lot_trd and
            # net_amt_trd are set.
            try:
                cur.execute(
                    (
                        "SELECT "
                        "COALESCE(SUM(qty_eo), 0), "
                        "COALESCE(SUM(net_total_eo), 0.0), "
                        "CASE WHEN COALESCE(SUM(qty_eo),0)=0 THEN 0 "
                        "ELSE (SUM(qty_eo*rate_eo)*1.0)/SUM(qty_eo) END, "
                        "COALESCE(SUM(brok_unit_eo*qty_eo), 0.0) "
                        "FROM exchange_orders WHERE id_trd = ?"
                    ),
                    (id_trd,),
                )
                agg = cur.fetchone()
                if agg:
                    sum_qty = agg[0] or 0
                    sum_net = agg[1] or 0.0
                    eo_wap = agg[2] or 0.0
                    brok_lot = agg[3] or 0.0
                    brok_unit = (brok_lot / sum_qty) if sum_qty else 0.0
                    # price_lot_trd: prefer existing tx value, else use net
                    # total
                    price_lot = tx.get("price_lot_trd")
                    if price_lot is None:
                        price_lot = sum_net
                    # Update transaction row with computed aggregates
                    cur.execute(
                        (
                            "UPDATE transactions"
                            " SET qty_trd = ?, wap_unit_trd = ?,"
                            " brok_unit_trd = ?, brok_lot_trd = ?,"
                            " price_lot_trd = ?, net_amt_trd = ?"
                            " WHERE id_trd = ?"
                        ),
                        (
                            sum_qty,
                            eo_wap,
                            brok_unit,
                            brok_lot,
                            price_lot,
                            sum_net,
                            id_trd,
                        ),
                    )
            except sqlite3.Error:
                # Best-effort; don't let aggregate calculation break the import
                pass

        # Commit after full sequence
        conn.commit()
        return True

    except sqlite3.Error as exc:
        logger.exception("Failed to import transaction: %s", exc)
        try:
            conn.rollback()
        except sqlite3.Error:
            # rollback best-effort; nothing more to do
            pass
        return False

    def import_transaction_from_legacy(
        conn: sqlite3.Connection,
        tx: _t.Dict[str, _t.Any],
    ) -> bool:
        """Import a transaction dict where ``tx`` may include a source `contract`.

        This function prefers contract-level fields from ``tx['contract']`` when
        present and otherwise falls back to the original `import_transaction`
        behavior. It delegates exchange_order/aggregate logic to the same code
        path as the interactive import to preserve invariants.
        """
        # If there is no contract payload, defer to the original function which
        # inserts/ignores contracts using minimal fields.
        contract = tx.get("contract")
        try:
            cur = conn.cursor()
            cur.execute("PRAGMA foreign_keys = ON")

            if contract:
                # Insert or ignore contract using the fuller set of fields found
                # in the legacy DB contract row.
                cur.execute(
                    (
                        "INSERT OR IGNORE INTO contracts"
                        " (cont_no, trd_dt, settle_no, settle_dt, no_of_trades)"
                        " VALUES (?, ?, ?, ?, ?)"
                    ),
                    (
                        contract.get("cont_no"),
                        contract.get("trd_dt", tx.get("trd_dt")),
                        contract.get("settle_no", tx.get("settle_no", 0)),
                        contract.get(
                            "settle_dt", tx.get("settle_dt", tx.get("trd_dt"))
                        ),
                        contract.get("no_of_trades", tx.get("no_of_trades", 1)),
                    ),
                )
            else:
                # Minimal contract insert (same as import_transaction)
                cur.execute(
                    (
                        "INSERT OR IGNORE INTO contracts"
                        " (cont_no, trd_dt, settle_no, settle_dt, no_of_trades)"
                        " VALUES (?, ?, ?, ?, ?)"
                    ),
                    (
                        tx.get("cont_no"),
                        tx.get("trd_dt"),
                        tx.get("settle_no", 0),
                        tx.get("settle_dt", tx.get("trd_dt")),
                        tx.get("no_of_trades", 1),
                    ),
                )

            # Reuse the rest of the import logic by constructing a tx-like dict
            # that the core import code understands. The original `import_transaction`
            # already handles transactions/exchange_orders & aggregates.
            return import_transaction(conn, tx)

        except sqlite3.Error:
            try:
                conn.rollback()
            except sqlite3.Error:
                pass
            return False


def trade_entry_from_file(
    parent: tk.Widget,
    src_db_path: str = "mystocks_old.db",
    auto_close: bool = False,
    auto_choose: bool = False,
    dry_run: bool | None = None,
) -> None:
    """Walk rows in the source DB and prompt the user to Add or Skip each.

    This is intentionally minimal: it shows a small modal with summary data
    for the current transaction and three buttons: Add, Skip, Quit.
    """
    # Keep the selected source path in a mutable container
    selected_src = {"path": src_db_path}
    # module-level open flag will be mutated via globals() to avoid 'global'
    # statements which trigger some linters; use globals()['_importer_open']
    # when assigning.
    rows: _t.List[_t.Dict[str, _t.Any]] = []
    idx = 0

    # simple in-memory buffer so early debug_append calls are safe
    _debug_messages: _t.List[str] = []

    # disk-backed debug log so we can capture messages from a headless run
    module_dir = os.path.dirname(os.path.abspath(__file__))
    debug_log_dir = os.path.join(module_dir, "log")
    debug_log_file = os.path.join(debug_log_dir, "importer_debug.log")
    try:
        os.makedirs(debug_log_dir, exist_ok=True)
    except OSError:
        pass

    def _append_to_disk(msg: str) -> None:
        try:
            with open(debug_log_file, "a", encoding="utf-8") as f:
                f.write(msg + "\n")
        except OSError:
            # best-effort; ignore disk errors
            pass

    def debug_append(msg: str) -> None:
        """Best-effort debug sink used before the on-screen overlay exists.

        It logs to the module logger and accumulates messages in a list.
        After the debug overlay is created we replace this with a UI-aware
        implementation and flush the buffer into the text widget.
        """
        try:
            logger.debug(msg)
        except (AttributeError, TypeError):
            pass
        try:
            _debug_messages.append(msg)
        except (AttributeError, TypeError):
            # Nothing we can do if the list append fails
            pass
        try:
            _append_to_disk(msg)
        except OSError:
            pass

    def show_row(i: int):
        tx = rows[i]
        # Simple text summary
        summary = (
            f"Company: {tx.get('company_name')}\n"
            f"Cont No: {tx.get('cont_no')}  Trd Dt: {tx.get('trd_dt')}\n"
            f"Type: {tx.get('trade_type_trd')}  EOs: "
            f"{len(tx.get('exchange_orders', []))}"
        )
        lbl_var.set(summary)

    def on_add():
        nonlocal idx
        # Guard against repeated clicks or empty rows
        if not rows or idx >= len(rows):
            debug_append("on_add: no more rows to process; closing modal")
            try:
                _close_modal()
            except (RuntimeError, AttributeError):
                pass
            return

        # Disable buttons to avoid re-entrant clicks while processing
        try:
            btn_add.state(["disabled"])
            btn_skip.state(["disabled"])
        except (tk.TclError, RuntimeError, AttributeError):
            pass

        tx = rows[idx]
        with get_db_connection() as conn:
            ok = import_transaction(conn, tx)
        if ok:
            show_colorful_info(
                win,
                "Imported",
                "Transaction imported successfully.",
            )
        else:
            show_colorful_error(
                win,
                "Import Failed",
                "Failed to import transaction. See logs.",
            )
        idx += 1
        if idx >= len(rows):
            # Close modal cleanly
            _close_modal()
            return
        # Re-enable buttons and show next row
        try:
            if win.winfo_exists():
                btn_add.state(["!disabled"])
                btn_skip.state(["!disabled"])
        except (tk.TclError, RuntimeError, AttributeError):
            pass
        show_row(idx)

    def on_skip():
        nonlocal idx
        idx += 1
        if idx >= len(rows):
            _close_modal()
            return
        show_row(idx)

    # Create a unified close handler so we always pop/enable/destroy once
    modal_id = disable_parent(parent)
    logger.debug("importer: disable_parent returned modal_id=%s", modal_id)
    debug_append(f"disable_parent -> {modal_id}")

    def _close_modal() -> None:
        # Clear module-level open flag so another importer can be opened later
        try:
            globals()["_importer_open"] = False
        except (RuntimeError, NameError):
            pass
        # Re-enable any Import buttons on the parent menu if present
        try:
            parent_btns = getattr(parent, "_menu_buttons", None)
            if parent_btns:
                for b in parent_btns:
                    try:
                        text = b.cget("text")
                        if "Import" in text:
                            b.state(["!disabled"])
                    except (tk.TclError, AttributeError):
                        pass
        except (AttributeError, RuntimeError):
            pass
        try:
            logger.debug("importer: popping window from stack")
            debug_append("pop_window called")
            pop_window()
        except (RuntimeError, AttributeError):
            pass
        try:
            enable_parent(modal_id)
        except (RuntimeError, AttributeError):
            pass
        try:
            win.destroy()
        except (RuntimeError, tk.TclError, AttributeError):
            pass

    def on_quit():
        _close_modal()

    # Prevent opening multiple importer modals (fast-path guard)
    from .window_manager import current_window

    try:
        if globals().get("_importer_open", False):
            # There is an active importer modal in this process; focus it
            # and return
            try:
                cw = current_window()
                if cw is not None:
                    cw.deiconify()
                    cw.lift()
                    cw.focus_set()
            except (RuntimeError, AttributeError):
                pass
            logger.info("importer: modal already open")
            debug_append("importer: modal already open")
            return
    except (RuntimeError, AttributeError):
        # Best-effort guard; fall through to create a new modal if check fails
        pass

    win = tk.Toplevel(parent)
    # Standard modal setup: transient + grab + focus
    try:
        from .modal_utils import setup_modal_window

        # type: ignore[arg-type]
        setup_modal_window(
            win,
            parent,
            title="Import Transactions from file",
            geometry="520x220",
        )
    except (ImportError, AttributeError, TypeError):
        # best-effort: fall back to manual setup
        try:
            # Only call transient when parent is a Toplevel (window-like)
            if isinstance(parent, tk.Toplevel):
                win.transient(parent)
            win.grab_set()
            win.focus_set()
        except (tk.TclError, RuntimeError, AttributeError):
            pass
    # mark importer as open to prevent re-entrancy
    try:
        _importer_open = True
    except (RuntimeError, NameError):
        pass
    push_window(win, parent)
    try:
        win.grab_set()
        win.focus_force()
    except (tk.TclError, RuntimeError, AttributeError):
        pass
    # ensure small and non-resizable if setup_modal_window failed
    try:
        win.resizable(False, False)
    except (tk.TclError, RuntimeError, AttributeError):
        pass
    try:
        win.deiconify()
        win.lift()
        win.focus_force()
    except (tk.TclError, RuntimeError):
        pass
    # Ensure close via titlebar or ESC calls our close handler
    # Use direct handler for window close and an explicit escape function
    win.protocol("WM_DELETE_WINDOW", _close_modal)

    def _on_escape(_event: tk.Event) -> None:
        _close_modal()

    win.bind("<Escape>", _on_escape)

    # --- Debug overlay (non-modal, opt-in) ---
    debug_enabled = os.environ.get("STOCKMAN_IMPORTER_DEBUG") == "1"
    dbg_win = None
    if debug_enabled:
        dbg_win = tk.Toplevel(win)
        dbg_win.title("Importer Debug")
        dbg_win.geometry("480x160")
        try:
            dbg_win.attributes("-topmost", True)
        except (tk.TclError, RuntimeError, AttributeError):
            pass
        dbg_win.transient(win)
        dbg_text = tk.Text(dbg_win, height=8, wrap="word")
        dbg_text.pack(fill=tk.BOTH, expand=True)
        dbg_text.configure(state="disabled")

        def _overlay_debug_append(msg: str) -> None:
            try:
                logger.debug(msg)
            except (AttributeError, TypeError):
                pass
            try:
                if dbg_text.winfo_exists():
                    dbg_text.configure(state="normal")
                    dbg_text.insert(tk.END, msg + "\n")
                    dbg_text.see(tk.END)
                    dbg_text.configure(state="disabled")
            except tk.TclError:
                # Ignore UI errors in the overlay
                pass
            try:
                _append_to_disk(msg)
            except OSError:
                pass

        for _m in _debug_messages:
            _overlay_debug_append(_m)
        _debug_messages.clear()
        debug_append = _overlay_debug_append
    else:

        def _disk_only_append(msg: str) -> None:
            try:
                logger.debug(msg)
            except (AttributeError, TypeError):
                pass
            try:
                _append_to_disk(msg)
            except OSError:
                pass

        debug_append = _disk_only_append

    def _close_debug_overlay() -> None:
        if dbg_win is None:
            return
        try:
            if dbg_win.winfo_exists():
                dbg_win.destroy()
        except tk.TclError:
            pass

    frm = ttk.Frame(win, padding=12)
    frm.pack(fill=tk.BOTH, expand=True)

    # File info and choose button
    file_frame = ttk.Frame(frm)
    file_frame.pack(fill=tk.X, pady=(0, 8))
    file_var = tk.StringVar(value=f"Source: {selected_src['path']}")
    file_lbl = ttk.Label(file_frame, textvariable=file_var)
    file_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def choose_file():
        # Release grab so the OS file dialog can be interacted with
        try:
            logger.debug("importer: releasing grab before filedialog")
            debug_append("releasing grab before filedialog")
            win.grab_release()
        except (tk.TclError, RuntimeError):
            pass
        # Compute initialdir: prefer current DB dir, then module dir, then cwd
        try:
            db_dir = os.path.dirname(os.path.abspath(STOCK_DB_PATH))
            if os.path.isdir(db_dir):
                initialdir = db_dir
            else:
                initialdir = os.path.dirname(os.path.abspath(__file__))
        except (OSError, AttributeError):
            try:
                initialdir = os.path.dirname(os.path.abspath(__file__))
            except (OSError, AttributeError):
                initialdir = os.getcwd()

        logger.debug("importer: opening file dialog (parent=%s)", win)
        logger.debug("importer: file dialog initialdir=%s", initialdir)
        debug_append(f"opening file dialog initialdir={initialdir}")
        path = filedialog.askopenfilename(
            parent=win,
            title="Select source DB",
            initialdir=initialdir,
            filetypes=[("SQLite DB", "*.db;*.sqlite;*"), ("All files", "*")],
        )
        try:
            logger.debug("importer: re-acquiring grab after filedialog")
            debug_append("re-acquiring grab after filedialog")
            win.grab_set()
        except (tk.TclError, RuntimeError):
            pass
        if path:
            logger.info("importer: user chose source DB: %s", path)
            debug_append(f"user chose source DB: {path}")
            selected_src["path"] = path
            file_var.set(f"Source: {selected_src['path']}")
            load_rows()

    choose_btn = ttk.Button(file_frame, text="Choose File...", command=choose_file)
    choose_btn.pack(side=tk.RIGHT)

    lbl_var = tk.StringVar()
    lbl = ttk.Label(frm, textvariable=lbl_var, justify=tk.LEFT)
    lbl.pack(fill=tk.BOTH, expand=True)

    btn_frm = ttk.Frame(frm)
    btn_frm.pack(fill=tk.X, pady=(8, 0))

    btn_add = ttk.Button(btn_frm, text="Add", command=on_add)
    btn_add.pack(side=tk.LEFT, padx=(0, 6))
    btn_skip = ttk.Button(btn_frm, text="Skip", command=on_skip)
    btn_skip.pack(side=tk.LEFT, padx=(0, 6))
    # Preview (dry-run all) and Commit All (perform all imports at once)

    def on_preview_all():
        # Run a dry-run across all rows and report counts
        imported = 0
        failed = 0
        try:
            debug_append("preview: starting dry-run transaction")
            with get_db_connection() as conn:
                try:
                    conn.execute("BEGIN")
                except sqlite3.Error:
                    # some sqlite wrappers may already be in a transaction
                    pass
                for tx in rows:
                    ok = import_transaction(conn, tx)
                    if ok:
                        imported += 1
                    else:
                        failed += 1
                try:
                    conn.rollback()
                except sqlite3.Error:
                    pass
        except sqlite3.Error:
            logger.exception("Preview (dry-run) failed")
        show_colorful_info(
            win,
            "Preview complete",
            f"Would import: {imported}  Would fail: {failed}",
        )

    def on_commit_all():
        # Confirm and then run import for all rows
        from .dialog_utils import show_colorful_yesno

        if not show_colorful_yesno(
            win,
            "Confirm import",
            "Commit all imports to the database?\nThis will persist changes.",
        ):
            return
        try:
            debug_append("commit_all: disabling buttons and starting import")
            btn_add.state(["disabled"])
            btn_skip.state(["disabled"])
            btn_preview.state(["disabled"])
            btn_commit.state(["disabled"])
        except (tk.TclError, RuntimeError, AttributeError):
            pass
        imported = 0
        failed = 0
        try:
            with get_db_connection() as conn:
                for tx in rows:
                    ok = import_transaction(conn, tx)
                    if ok:
                        imported += 1
                    else:
                        failed += 1
        except sqlite3.Error:
            logger.exception("Commit-all import failed")
        finally:
            # Always re-enable parent menu import buttons if present
            try:
                parent_btns = getattr(parent, "_menu_buttons", None)
                if parent_btns:
                    for b in parent_btns:
                        try:
                            text = b.cget("text")
                            if "Import" in text:
                                b.state(["!disabled"])
                        except (tk.TclError, AttributeError):
                            pass
            except (AttributeError, RuntimeError):
                pass
        show_colorful_info(
            win,
            "Import complete",
            f"Imported: {imported}  Failed: {failed}",
        )
        # Close modal after commit
        _close_modal()

    btn_preview = ttk.Button(btn_frm, text="Preview All", command=on_preview_all)
    btn_preview.pack(side=tk.LEFT, padx=(0, 6))
    btn_commit = ttk.Button(btn_frm, text="Commit All", command=on_commit_all)
    btn_commit.pack(side=tk.LEFT, padx=(0, 6))
    btn_quit = ttk.Button(btn_frm, text="Quit", command=on_quit)
    btn_quit.pack(side=tk.RIGHT)

    def load_rows():
        nonlocal rows, idx
        logger.debug("importer: loading rows from %s", selected_src["path"])
        debug_append(f"loading rows from {selected_src['path']}")
        rows = _fetch_source_transactions(selected_src["path"])
        if not rows:
            lbl_var.set("No transactions found in source DB.")
            # Widgets may have been destroyed if modal closed rapidly; guard.
            try:
                if win.winfo_exists():
                    btn_add.state(["!disabled"])
                    btn_skip.state(["!disabled"])
            except (tk.TclError, RuntimeError, AttributeError):
                pass
            return
        idx = 0
        try:
            if win.winfo_exists():
                btn_add.state(["!disabled"])
                btn_skip.state(["!disabled"])
        except (tk.TclError, RuntimeError):
            logger.debug("importer: widgets not available to enable")
        show_row(idx)

    # Initial load attempt
    logger.debug("importer: initial load_rows call")
    debug_append("initial load_rows call")
    load_rows()

    # If caller requested a programmatic dry-run (no UI interactions), run it
    if dry_run is True:
        # Run all rows through import in a rollback transaction
        # and report counts
        imported = 0
        failed = 0
        try:
            with get_db_connection() as conn:
                conn.execute("BEGIN")
                for tx in rows:
                    ok = import_transaction(conn, tx)
                    if ok:
                        imported += 1
                    else:
                        failed += 1
                conn.rollback()
        except sqlite3.Error:
            logger.exception("Dry-run failed")
        show_colorful_info(
            parent,
            "Dry-run complete",
            f"Would import: {imported}  Would fail: {failed}",
        )
        _close_debug_overlay()
        _close_modal()
        return

    # If running in auto_close (test) mode, schedule closing the modal
    # shortly after the initial load so we can exercise logging without
    # needing UI interaction.
    if auto_close:
        try:
            debug_append("auto_close: scheduling modal close in 400ms")
            win.after(400, _close_modal)
        except (tk.TclError, RuntimeError):
            pass
    # If requested, programmatically invoke the chooser (useful for tests)
    if auto_choose:
        try:
            # schedule a short delay so the window is visible and ready
            win.after(50, choose_file)
        except (tk.TclError, RuntimeError):
            pass

    # Block until window is closed so this behaves like a modal
    try:
        logger.debug("importer: entering wait_window for %s", win)
        debug_append("entering wait_window")
        parent.wait_window(win)
        try:
            if parent.winfo_exists():
                parent.grab_set()
        except tk.TclError:
            logger.debug("parent.grab_set skipped: parent destroyed.")
            logger.debug("importer: wait_window returned for %s", win)
        debug_append("wait_window returned")
    except (tk.TclError, RuntimeError):
        logger.exception("importer: wait_window failed")
        debug_append("wait_window failed")

    # Initial load attempt
    load_rows()
    _close_debug_overlay()


__all__ = [
    "_fetch_source_transactions",
    "import_transaction",
    "trade_entry_from_file",
]
