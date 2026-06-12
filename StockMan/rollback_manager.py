# -*- coding: utf-8 -*-
# File: FinanceManager/StockMan/rollback_manager.py

"""
Centralized housekeeping engine for the StockMan application.
Safely manages cascading deletions and rollbacks for trades and corporate actions
to maintain strict database and accounting integrity.
"""

import sqlite3
from typing import Tuple

from Shared.globals import get_db_connection, logger
from .trade_utils import (
    compute_avg_price,
    enforce_no_oversell_for_stock,
    revert_sell_allocation,
)


def execute_safe_rollback(db_logic_func, *args) -> Tuple[bool, str]:
    """
    A universal wrapper that executes deletion logic within a strict database transaction.
    If any step of the deletion fails, the entire transaction is rolled back.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Begin a strict transaction
            cursor.execute("BEGIN TRANSACTION;")

            # Execute the specific deletion logic passed to this wrapper
            db_logic_func(cursor, *args)

            # If no exceptions were raised, commit the deletion
            conn.commit()
            return True, "Rollback completed successfully."

    except sqlite3.Error as e:
        logger.error(f"Rollback failed. Transaction aborted. Details: {e}")
        return False, f"Database error during rollback: {e}"
    except Exception as e:
        logger.error(f"Unexpected error during rollback: {e}")
        return False, str(e)


# =============================================================================
# 1. TRADE ROLLBACK LOGIC
# =============================================================================


def _logic_delete_trade(cursor: sqlite3.Cursor, trans_id: int):
    """
    The internal logic for completely reversing a specific trade.
    DO NOT call this directly; use delete_trade() instead.
    """
    # 1. Fetch the trade details before we delete them
    cursor.execute(
        "SELECT id_stk, cont_no, trade_type_trd FROM transactions WHERE id_trd = ?",
        (trans_id,),
    )
    trade = cursor.fetchone()
    if not trade:
        raise ValueError(f"Transaction ID {trans_id} does not exist.")

    id_stk, cont_no, trade_type = trade

    # 2. If it is a SELL trade, revert its sell allocations
    if trade_type.upper() == "SELL":
        revert_sell_allocation(
            trans_id,
            cursor=cursor,
            poke=False,
            raise_on_error=True,
        )

    # 3. Handle IPO allotments — capture id_offer before deleting the link
    cursor.execute(
        "SELECT id_offer FROM offer_allotments WHERE tx_id = ?", (trans_id,)
    )
    allot_row = cursor.fetchone()
    id_offer = allot_row[0] if allot_row else None
    cursor.execute("DELETE FROM offer_allotments WHERE tx_id = ?", (trans_id,))

    # 4. Delete exchange orders for this trade
    cursor.execute("DELETE FROM exchange_orders WHERE id_trd = ?", (trans_id,))

    # 5. Delete the transaction itself
    cursor.execute("DELETE FROM transactions WHERE id_trd = ?", (trans_id,))

    # Clean up orphaned primary offer
    if id_offer is not None:
        cursor.execute(
            "SELECT COUNT(*) FROM offer_allotments WHERE id_offer = ?",
            (id_offer,),
        )
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                "DELETE FROM primary_offers WHERE id_offer = ?", (id_offer,)
            )

    # 6. Check contract status
    cursor.execute(
        "SELECT COUNT(*) FROM transactions WHERE cont_no = ?", (cont_no,)
    )
    remaining_trades = cursor.fetchone()[0]

    if remaining_trades == 0:
        cursor.execute("DELETE FROM contracts WHERE cont_no = ?", (cont_no,))
        cursor.execute(
            "DELETE FROM computed_bank WHERE cont_no = ?", (cont_no,)
        )
    else:
        # Update contract aggregates
        cursor.execute(
            """
            UPDATE contracts
            SET
                brok_cont = (SELECT SUM(brok_lot_trd) FROM transactions WHERE cont_no = ?),
                etc_cont = (SELECT SUM(etc_trd) FROM transactions WHERE cont_no = ?),
                sebi_cont = (SELECT SUM(sebi_trd) FROM transactions WHERE cont_no = ?),
                gst_cont = (SELECT SUM(gst_trd) FROM transactions WHERE cont_no = ?),
                stamp_cont = (SELECT SUM(stamp_trd) FROM transactions WHERE cont_no = ?),
                stt_cont = (SELECT SUM(stt_trd) FROM transactions WHERE cont_no = ?),
                igst_cont = (SELECT SUM(igst_trd) FROM transactions WHERE cont_no = ?),
                net_amt_cont = (SELECT SUM(net_amt_trd) FROM transactions WHERE cont_no = ?),
                sell_chrg_cont = (SELECT SUM(sell_chrg_trd) FROM transactions WHERE cont_no = ?),
                etc_cont_applicable = (
                    SELECT SUM(etc_trd_applicable) FROM transactions WHERE cont_no = ?
                ),
                gst_cont_applicable = (
                    SELECT SUM(gst_trd_applicable) FROM transactions WHERE cont_no = ?
                ),
                stt_cont_applicable = (
                    SELECT SUM(stt_trd_applicable) FROM transactions WHERE cont_no = ?
                ),
                net_amt_cont_applicable = (
                    SELECT SUM(net_amt_trd_applicable) FROM transactions WHERE cont_no = ?
                ),
                no_of_trades = ?
            WHERE cont_no = ?
            """,
            (
                cont_no,
                cont_no,
                cont_no,
                cont_no,
                cont_no,
                cont_no,
                cont_no,
                cont_no,
                cont_no,
                cont_no,
                cont_no,
                cont_no,
                cont_no,
                remaining_trades,
                cont_no,
            ),
        )

        # Recalculate computed_bank
        cursor.execute(
            "DELETE FROM computed_bank WHERE cont_no = ?", (cont_no,)
        )
        cursor.execute(
            """
            SELECT
                SUM(CASE
                    WHEN trade_type_trd = 'BUY' THEN net_amt_trd
                    WHEN trade_type_trd = 'SELL' THEN -net_amt_trd
                    ELSE 0
                END),
                SUM(CASE
                    WHEN trade_type_trd = 'BUY' THEN net_amt_trd_applicable
                    WHEN trade_type_trd = 'SELL' THEN -net_amt_trd_applicable
                    ELSE 0
                END),
                (SELECT settle_dt FROM contracts WHERE cont_no = ?)
            FROM transactions
            WHERE cont_no = ? AND net_amt_trd IS NOT NULL
            """,
            (cont_no, cont_no),
        )
        comp_bt_row = cursor.fetchone()
        final_comp_bt_value = (
            comp_bt_row[0]
            if comp_bt_row and comp_bt_row[0] is not None
            else 0.0
        )
        final_comp_bt_app_value = (
            comp_bt_row[1]
            if comp_bt_row and comp_bt_row[1] is not None
            else 0.0
        )
        settle_dt_for_bank = (
            comp_bt_row[2]
            if comp_bt_row and comp_bt_row[2] is not None
            else "1900-01-01"
        )

        if final_comp_bt_value != 0:
            comp_bt_type = "DEBIT" if final_comp_bt_value > 0 else "CREDIT"
            comp_bt_amt = abs(round(final_comp_bt_value, 2))
            comp_bt_app_amt = abs(round(final_comp_bt_app_value, 2))
            comp_bt_desc = "Buying" if comp_bt_type == "DEBIT" else "Selling"
            cursor.execute(
                """
                INSERT INTO computed_bank
                (cont_no, comp_bt_dt, comp_bt_type, comp_bt_amt,
                 comp_bt_amt_applicable, comp_bt_desc)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    cont_no,
                    settle_dt_for_bank,
                    comp_bt_type,
                    comp_bt_amt,
                    comp_bt_app_amt,
                    comp_bt_desc,
                ),
            )

    # 7. Enforce no over-sell before commit (raises ValueError if violated)
    enforce_no_oversell_for_stock(cursor, id_stk)

    return id_stk


def delete_trade(trans_id: int) -> Tuple[bool, str]:
    """
    Public function to safely delete a trade and reverse all its accounting effects.
    """
    id_stk = None

    def logic_wrapper(cursor):
        nonlocal id_stk
        id_stk = _logic_delete_trade(cursor, trans_id)

    # Execute the transaction
    success, message = execute_safe_rollback(logic_wrapper)

    # If successful, recompute the average price for the affected stock
    if success and id_stk is not None:
        compute_avg_price(id_stk)

    return success, message


# =============================================================================
# 2. CORPORATE ACTION ROLLBACK LOGIC (To be implemented next)
# =============================================================================


def _logic_delete_bonus(cursor: sqlite3.Cursor, act_id: int):
    """
    Internal logic for completely reversing a Bonus Issue.
    DO NOT call this directly; use delete_bonus() instead.
    """
    # 1. Fetch the stock ID before deletion to recompute average price later
    cursor.execute("SELECT id_stk FROM corp_acts WHERE id_act = ?", (act_id,))
    result = cursor.fetchone()
    if not result:
        raise ValueError(f"Corporate Action ID {act_id} does not exist.")
    id_stk = result[0]

    # Reconstruct the exact contract number generated by bonus_entry.py
    cont_no = f"BONUS_{act_id}"

    # 2. Delete the zero-cost allotted shares from the transactions table
    cursor.execute("DELETE FROM transactions WHERE cont_no = ?", (cont_no,))

    # 3. Delete the zero-cost contract note
    cursor.execute("DELETE FROM contracts WHERE cont_no = ?", (cont_no,))

    # 4. Delete the corporate action record itself
    cursor.execute("DELETE FROM corp_acts WHERE id_act = ?", (act_id,))

    # 5. Return the stock ID so the wrapper can trigger a recalculation
    return id_stk


def delete_bonus(act_id: int) -> Tuple[bool, str]:
    """
    Public function to safely delete a Bonus Issue and reverse all its accounting effects.
    """
    id_stk = None

    def logic_wrapper(cursor):
        nonlocal id_stk
        id_stk = _logic_delete_bonus(cursor, act_id)

    # Execute the transaction within the safety wrapper
    success, message = execute_safe_rollback(logic_wrapper)

    # If successful, recompute the average price for the affected stock
    if success and id_stk is not None:
        compute_avg_price(id_stk)

    return success, message


def _logic_delete_split(cursor: sqlite3.Cursor, act_id: int):
    """
    Internal logic for completely reversing a Stock Split.
    DO NOT call this directly; use delete_split() instead.
    """
    # 1. Fetch the stock ID before deletion to recompute average price later
    cursor.execute("SELECT id_stk FROM corp_acts WHERE id_act = ?", (act_id,))
    result = cursor.fetchone()
    if not result:
        raise ValueError(f"Corporate Action ID {act_id} does not exist.")
    id_stk = result[0]

    # Reconstruct the exact contract number generated by split_entry.py
    cont_no = f"SPLIT_{act_id}"

    # 2. Delete the split adjustments (both the removal of old shares and
    # the addition of new shares) from the transactions table
    cursor.execute("DELETE FROM transactions WHERE cont_no = ?", (cont_no,))

    # 3. Delete the zero-cost contract note
    cursor.execute("DELETE FROM contracts WHERE cont_no = ?", (cont_no,))

    # 4. Delete the corporate action record itself
    cursor.execute("DELETE FROM corp_acts WHERE id_act = ?", (act_id,))

    # 5. Return the stock ID so the wrapper can trigger a recalculation
    return id_stk


def delete_split(act_id: int) -> Tuple[bool, str]:
    """
    Public function to safely delete a Stock Split and reverse all its accounting effects.
    """
    id_stk = None

    def logic_wrapper(cursor):
        nonlocal id_stk
        id_stk = _logic_delete_split(cursor, act_id)

    # Execute the transaction within the safety wrapper
    success, message = execute_safe_rollback(logic_wrapper)

    # If successful, recompute the average price for the affected stock
    if success and id_stk is not None:
        compute_avg_price(id_stk)

    return success, message


def _logic_delete_merger(cursor: sqlite3.Cursor, act_id: int):
    """
    Internal logic for completely reversing a Corporate Merger.
    DO NOT call this directly; use delete_merger() instead.
    """
    # 1. Fetch the Target Stock ID from the corporate action record
    cursor.execute("SELECT id_stk FROM corp_acts WHERE id_act = ?", (act_id,))
    result = cursor.fetchone()
    if not result:
        raise ValueError(f"Corporate Action ID {act_id} does not exist.")
    target_id = result[0]

    # 2. Safely find all related contract numbers (Deduction, Allotment, Fractional Cash)
    # We fetch all Merger contracts and use Python to exactly match the ID
    # to prevent deleting MRG_DED_11 when looking for MRG_DED_1.
    cursor.execute("SELECT cont_no FROM contracts WHERE cont_no LIKE 'MRG_%'")
    all_mrg_conts = [row[0] for row in cursor.fetchall()]

    target_conts = []
    for c in all_mrg_conts:
        parts = c.split("_")
        # This safely matches "MRG_DED_1" or "MRG_ALT_1_0"
        if len(parts) >= 3 and parts[2] == str(act_id):
            target_conts.append(c)

    acquirer_ids = []
    if target_conts:
        # Create a dynamic list of SQL placeholders (?, ?, ?) based on how many contracts we found
        placeholders = ",".join("?" * len(target_conts))

        # 3. Fetch any Acquirer Stock IDs from the BUY transactions before deleting
        cursor.execute(
            f"""
            SELECT DISTINCT id_stk FROM transactions
            WHERE cont_no IN ({placeholders}) AND trade_type_trd = 'BUY'
        """,
            target_conts,
        )
        acquirer_ids = [row[0] for row in cursor.fetchall()]

        # 4. Delete the associated transactions and contracts
        cursor.execute(
            f"DELETE FROM transactions WHERE cont_no IN ({placeholders})",
            target_conts,
        )
        cursor.execute(
            f"DELETE FROM contracts WHERE cont_no IN ({placeholders})",
            target_conts,
        )

    # 5. Delete the corporate action record itself
    cursor.execute("DELETE FROM corp_acts WHERE id_act = ?", (act_id,))

    # 6. Return all affected stock IDs (Target + Acquirer) so the wrapper can recalculate them
    affected_stocks = set([target_id] + acquirer_ids)
    return affected_stocks


def delete_merger(act_id: int) -> Tuple[bool, str]:
    """
    Public function to safely delete a Corporate Merger and reverse all its accounting effects.
    """
    affected_stocks = set()

    def logic_wrapper(cursor):
        nonlocal affected_stocks
        affected_stocks = _logic_delete_merger(cursor, act_id)

    # Execute the transaction within the safety wrapper
    success, message = execute_safe_rollback(logic_wrapper)

    # If successful, recompute the average price for ALL involved stocks
    if success and affected_stocks:
        for stk_id in affected_stocks:
            compute_avg_price(stk_id)

    return success, message


def _logic_delete_demerger(cursor: sqlite3.Cursor, act_id: int):
    """
    Internal logic for completely reversing a Corporate Demerger.
    DO NOT call this directly; use delete_demerger() instead.
    """
    # 1. Fetch the Parent Stock ID from the corporate action record
    cursor.execute("SELECT id_stk FROM corp_acts WHERE id_act = ?", (act_id,))
    result = cursor.fetchone()
    if not result:
        raise ValueError(f"Corporate Action ID {act_id} does not exist.")
    parent_id = result[0]

    # 2. Safely find all related contract numbers (Parent Deduction and Child Allotments)
    # We fetch all Demerger contracts and use Python to exactly match the ID
    # to prevent accidentally deleting DEM_ALT_11_0 when looking for DEM_ALT_1_0.
    cursor.execute("SELECT cont_no FROM contracts WHERE cont_no LIKE 'DEM_%'")
    all_dem_conts = [row[0] for row in cursor.fetchall()]

    target_conts = []
    for c in all_dem_conts:
        parts = c.split("_")
        # This safely matches "DEM_DED_1" or "DEM_ALT_1_0"
        if len(parts) >= 3 and parts[2] == str(act_id):
            target_conts.append(c)

    child_ids = []
    if target_conts:
        # Create a dynamic list of SQL placeholders (?, ?, ?)
        placeholders = ",".join("?" * len(target_conts))

        # 3. Fetch any Child Stock IDs from the BUY transactions before deleting
        cursor.execute(
            f"""
            SELECT DISTINCT id_stk FROM transactions
            WHERE cont_no IN ({placeholders}) AND trade_type_trd = 'BUY'
        """,
            target_conts,
        )
        child_ids = [row[0] for row in cursor.fetchall()]

        # 4. Delete the associated transactions and contracts
        cursor.execute(
            f"DELETE FROM transactions WHERE cont_no IN ({placeholders})",
            target_conts,
        )
        cursor.execute(
            f"DELETE FROM contracts WHERE cont_no IN ({placeholders})",
            target_conts,
        )

    # 5. Delete the corporate action record itself
    cursor.execute("DELETE FROM corp_acts WHERE id_act = ?", (act_id,))

    # 6. Return all affected stock IDs (Parent + Children) so the wrapper can recalculate them
    affected_stocks = set([parent_id] + child_ids)
    return affected_stocks


def delete_demerger(act_id: int) -> Tuple[bool, str]:
    """
    Public function to safely delete a Corporate Demerger and reverse all its accounting effects.
    """
    affected_stocks = set()

    def logic_wrapper(cursor):
        nonlocal affected_stocks
        affected_stocks = _logic_delete_demerger(cursor, act_id)

    # Execute the transaction within the safety wrapper
    success, message = execute_safe_rollback(logic_wrapper)

    # If successful, recompute the average price for ALL involved stocks
    if success and affected_stocks:
        for stk_id in affected_stocks:
            compute_avg_price(stk_id)

    return success, message
