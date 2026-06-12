# -*- coding: utf-8 -*-
# File: C:\Data\Personal\Finance_and_Investment\finprog\FinanceManager\StockMan\validation_utils.py


"""Centralized validation exception mapping and UI helpers.

This module standardizes how validation exceptions are converted into
user-friendly messages and displayed via the project's dialog utilities.
"""

from collections.abc import Iterable, Mapping
from typing import Any, Optional

from Shared.dialog_utils import show_colorful_error
from .date_utils import parse_date_from_string, validate_iso_date_or_raise


class ValidationError(ValueError):
    """Raised when a validation fails in the application code."""


def validate_required_mapping(
    data: Mapping[str, Any], required_fields: Iterable[str]
) -> None:
    """Raise ``ValidationError`` if any required field is missing."""
    missing = []
    for field in required_fields:
        value = data.get(field)
        if value is None or value == "":
            missing.append(field)

    if missing:
        raise ValidationError(
            "Required field(s) missing: "
            f"{', '.join(missing)}. Please complete all required steps "
            "before submitting."
        )


def _as_positive_int(value: Any, field_name: str) -> int:
    try:
        integer_value = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(
            f"{field_name} must be a positive integer."
        ) from exc

    if integer_value <= 0:
        raise ValidationError(f"{field_name} must be a positive integer.")
    return integer_value


def _as_non_negative_int(value: Any, field_name: str) -> int:
    try:
        integer_value = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(
            f"{field_name} must be a non-negative integer."
        ) from exc

    if integer_value < 0:
        raise ValidationError(f"{field_name} must be a non-negative integer.")
    return integer_value


def validate_trade_core_payload(
    trade: Mapping[str, Any], *, require_id_stk: bool = False
) -> dict[str, Any]:
    """Normalize and validate shared trade fields."""
    if not isinstance(trade, Mapping):
        raise ValidationError("Trade payload must be a mapping.")

    normalized = dict(trade)
    required_fields = [
        "cont_no",
        "trd_dt",
        "settle_dt",
        "company_name",
        "trade_type_trd",
        "qty_trd",
    ]
    if require_id_stk:
        required_fields.append("id_stk")
    validate_required_mapping(normalized, required_fields)

    try:
        normalized["trd_dt"] = validate_iso_date_or_raise(
            normalized["trd_dt"], field_name="trd_dt"
        )
        normalized["settle_dt"] = validate_iso_date_or_raise(
            normalized["settle_dt"], field_name="settle_dt"
        )
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc

    trade_date = parse_date_from_string(normalized["trd_dt"])
    settle_date = parse_date_from_string(normalized["settle_dt"])
    if trade_date is None or settle_date is None:
        raise ValidationError("Trade dates must be valid ISO dates.")
    if settle_date < trade_date:
        raise ValidationError("settle_dt must be on or after trd_dt.")

    normalized["qty_trd"] = _as_positive_int(normalized["qty_trd"], "qty_trd")

    trade_type = str(normalized["trade_type_trd"]).upper()
    if trade_type not in {"BUY", "SELL"}:
        raise ValidationError("trade_type_trd must be either 'BUY' or 'SELL'.")
    normalized["trade_type_trd"] = trade_type

    normalized["settle_no"] = _as_non_negative_int(
        normalized.get("settle_no") or 0,
        "settle_no",
    )
    normalized["no_of_trades"] = _as_positive_int(
        normalized.get("no_of_trades") or 1,
        "no_of_trades",
    )
    normalized["sold_qty"] = _as_non_negative_int(
        normalized.get("sold_qty") or 0,
        "sold_qty",
    )

    if require_id_stk:
        try:
            normalized["id_stk"] = int(normalized["id_stk"])
        except (TypeError, ValueError) as exc:
            raise ValidationError("id_stk must be an integer.") from exc
    elif normalized.get("id_stk") not in (None, ""):
        try:
            normalized["id_stk"] = int(normalized["id_stk"])
        except (TypeError, ValueError) as exc:
            raise ValidationError("id_stk must be an integer.") from exc

    return normalized


def validate_exchange_order_payload(
    order: Mapping[str, Any], *, order_index: int = 1
) -> dict[str, Any]:
    """Normalize and validate a single exchange-order payload."""
    if not isinstance(order, Mapping):
        raise ValidationError("Exchange order payload must be a mapping.")

    normalized_order = dict(order)
    validate_required_mapping(
        normalized_order,
        ("ord_no", "ord_dt", "trd_no", "qty_eo", "rate_eo"),
    )
    try:
        normalized_order["ord_dt"] = validate_iso_date_or_raise(
            normalized_order["ord_dt"],
            field_name=f"exchange_orders[{order_index}].ord_dt",
        )
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc

    normalized_order["qty_eo"] = _as_positive_int(
        normalized_order["qty_eo"],
        f"exchange_orders[{order_index}].qty_eo",
    )
    normalized_order["ord_no"] = _as_non_negative_int(
        normalized_order["ord_no"],
        f"exchange_orders[{order_index}].ord_no",
    )
    normalized_order["trd_no"] = _as_non_negative_int(
        normalized_order["trd_no"],
        f"exchange_orders[{order_index}].trd_no",
    )
    return normalized_order


def validate_order_quantity_progress(check_qty: Any, qty_trd: Any) -> None:
    """Ensure accumulated order quantity does not exceed traded quantity."""
    ordered_qty = _as_non_negative_int(check_qty, "check_qty")
    traded_qty = _as_positive_int(qty_trd, "qty_trd")
    if ordered_qty > traded_qty:
        raise ValidationError(
            "Ordered quantity is greater than the traded quantity."
        )


def validate_trade_import_payload(tx: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize and validate a transaction payload for file import."""
    if not isinstance(tx, Mapping):
        raise ValidationError("Transaction payload must be a mapping.")

    tx_payload = dict(tx)
    if not tx_payload.get("settle_dt") and tx_payload.get("trd_dt"):
        tx_payload["settle_dt"] = tx_payload["trd_dt"]

    normalized = validate_trade_core_payload(
        tx_payload,
        require_id_stk=True,
    )

    exchange_orders = normalized.get("exchange_orders") or []
    if not isinstance(exchange_orders, list):
        raise ValidationError("exchange_orders must be a list.")

    normalized_orders = []
    for index, order in enumerate(exchange_orders, start=1):
        normalized_order = validate_exchange_order_payload(
            order,
            order_index=index,
        )
        normalized_orders.append(normalized_order)

    if normalized_orders:
        total_qty = sum(order["qty_eo"] for order in normalized_orders)
        if total_qty != normalized["qty_trd"]:
            raise ValidationError(
                "exchange_orders qty_eo total must match qty_trd."
            )

    normalized["exchange_orders"] = normalized_orders
    normalized["no_of_trades"] = max(
        normalized["no_of_trades"], len(normalized_orders) or 1
    )

    return normalized


def map_validation_exception(exc: Exception) -> str:
    """Return a short user-friendly message for a validation exception.

    Keep messages concise because the dialog will show the title + message.
    """
    if isinstance(exc, ValidationError):
        return str(exc)
    # Default fallback for unexpected exceptions which are not internal
    return "Invalid input. Please check your entries and try again."


def show_validation_error(
    parent: Optional[object],
    exc: Exception,
    title: str = "Validation Error",
) -> None:
    """Show a friendly validation error dialog for exception `exc`.

    This wraps `show_colorful_error` so callers only need to raise or
    forward exceptions and call this helper to present them.
    """
    msg = map_validation_exception(exc)
    show_colorful_error(parent, title, msg)


# File: C:\Data\Personal\Finance_and_Investment\finprog\FinanceManager\StockMan\validation_utils.py ends here
