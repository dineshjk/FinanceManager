# -*- coding: utf-8 -*-
# StockMan/offers.py


"""Helpers to create/update primary offers and allotments.

These functions validate incoming date fields using the project's
`date_utils` validators and raise `ValidationError` for caller-friendly
handling. They are wrappers around DB operations to centralize
validation and error mapping.
"""

from typing import Optional

from Shared.globals import get_db_connection
from .date_utils import validate_iso_date_or_raise
from .validation_utils import ValidationError
from .trade_utils import compute_avg_price, process_allotment


def add_primary_offer(
    id_stk: int,
    offer_type: str,
    offer_name: str,
    ann_dt: Optional[str] = None,
    record_dt: Optional[str] = None,
    open_dt: Optional[str] = None,
    close_dt: Optional[str] = None,
    allotment_dt: Optional[str] = None,
    listing_dt: Optional[str] = None,
    issue_price: float = 0.0,
    ratio: str = "",
) -> int:
    """Insert a primary_offers row after validating date fields.

    Returns the inserted id_offer.
    """
    try:
        ann_dt = (
            validate_iso_date_or_raise(ann_dt, "ann_dt") if ann_dt else None
        )
        record_dt = (
            validate_iso_date_or_raise(record_dt, "record_dt")
            if record_dt
            else None
        )
        open_dt = (
            validate_iso_date_or_raise(open_dt, "open_dt") if open_dt else None
        )
        close_dt = (
            validate_iso_date_or_raise(close_dt, "close_dt")
            if close_dt
            else None
        )
        allotment_dt = (
            validate_iso_date_or_raise(allotment_dt, "allotment_dt")
            if allotment_dt
            else None
        )
        listing_dt = (
            validate_iso_date_or_raise(listing_dt, "listing_dt")
            if listing_dt
            else None
        )
    except ValueError as ve:
        raise ValidationError(str(ve)) from ve

    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO primary_offers (
                id_stk, offer_type, offer_name, ann_dt, record_dt,
                open_dt, close_dt, allotment_dt, listing_dt, issue_price, ratio
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                id_stk,
                offer_type,
                offer_name,
                ann_dt or "1900-01-01",
                record_dt or "1900-01-01",
                open_dt or "1900-01-01",
                close_dt or "1900-01-01",
                allotment_dt or "1900-01-01",
                listing_dt or "1900-01-01",
                issue_price,
                ratio,
            ),
        )
        conn.commit()
    return int(cur.lastrowid or 0)


def add_offer_allotment(
    id_stk: int,
    id_offer: int,
    exchange: str = "NSE",
    tx_id: Optional[int] = None,
    record_qty: int = 0,
    entitlement_qty: int = 0,
    applied_qty: int = 0,
    allotted_qty: int = 0,
    allotted_amt: float = 0.0,
    status: str = "APPLIED",
    note_allot: str = "",
    allotment_dt: Optional[str] = None,
) -> int:
    """Insert an offer_allotments row. Does minimal validation and returns id_allot."""

    try:
        allotment_dt = (
            validate_iso_date_or_raise(allotment_dt, "allotment_dt")
            if allotment_dt
            else "1900-01-01"
        )
    except ValueError as ve:
        raise ValidationError(str(ve)) from ve

    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO offer_allotments (
                id_stk, id_offer, tx_id, exchange, record_qty, entitlement_qty,
                applied_qty, allotted_qty, allotted_amt, status, note_allot, allotment_dt
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                id_stk,
                id_offer,
                tx_id,
                exchange,
                record_qty,
                entitlement_qty,
                applied_qty,
                allotted_qty,
                allotted_amt,
                status,
                note_allot,
                allotment_dt,
            ),
        )
        # ADD THESE TWO LINES:
        id_allot = cur.lastrowid
        process_allotment(id_allot, cursor=cur)
        conn.commit()
    return int(cur.lastrowid or 0)


def add_ipo(
    id_stk: int,
    offer_name: str,
    ann_dt: Optional[str] = None,
    record_dt: Optional[str] = None,
    open_dt: Optional[str] = None,
    close_dt: Optional[str] = None,
    allotment_dt: Optional[str] = None,
    listing_dt: Optional[str] = None,
    issue_price: float = 0.0,
    ratio: str = "",
) -> int:
    """Convenience wrapper for add_primary_offer with offer_type='IPO'."""
    return add_primary_offer(
        id_stk=id_stk,
        offer_type="IPO",
        offer_name=offer_name,
        ann_dt=ann_dt,
        record_dt=record_dt,
        open_dt=open_dt,
        close_dt=close_dt,
        allotment_dt=allotment_dt,
        listing_dt=listing_dt,
        issue_price=issue_price,
        ratio=ratio,
    )


def add_rights_issue(
    id_stk: int,
    offer_name: str,
    ann_dt: Optional[str] = None,
    record_dt: Optional[str] = None,
    open_dt: Optional[str] = None,
    close_dt: Optional[str] = None,
    allotment_dt: Optional[str] = None,
    listing_dt: Optional[str] = None,
    issue_price: float = 0.0,
    ratio: str = "",
) -> int:
    """Convenience wrapper for add_primary_offer with offer_type='RIGHTS'."""
    return add_primary_offer(
        id_stk=id_stk,
        offer_type="RIGHTS",
        offer_name=offer_name,
        ann_dt=ann_dt,
        record_dt=record_dt,
        open_dt=open_dt,
        close_dt=close_dt,
        allotment_dt=allotment_dt,
        listing_dt=listing_dt,
        issue_price=issue_price,
        ratio=ratio,
    )
