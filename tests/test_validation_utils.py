import importlib
import sys
from pathlib import Path
import pytest

# Ensure project parent is on sys.path so package imports work
tests_dir = Path(__file__).resolve().parent
project_root = tests_dir.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

validation_utils = importlib.import_module("StockMan.validation_utils")
dialog_utils = importlib.import_module("Shared.dialog_utils")


def test_map_validation_exception_with_validation_error():
    exc = validation_utils.ValidationError("ISIN invalid: must start with IN")
    msg = validation_utils.map_validation_exception(exc)
    assert "ISIN invalid" in msg


def test_show_validation_error_calls_dialog(monkeypatch):
    called = {}

    def fake_show(parent, title, message):
        called["parent"] = parent
        called["title"] = title
        called["message"] = message

    # validation_utils imported show_colorful_error at import-time, so
    # monkeypatch that symbol directly on validation_utils.
    monkeypatch.setattr(validation_utils, "show_colorful_error", fake_show)

    validation_utils.show_validation_error(
        None, validation_utils.ValidationError("Bad date")
    )
    assert called["title"] == "Validation Error"
    assert "Bad date" in called["message"]


def test_validate_required_mapping_raises_for_missing_fields():
    with pytest.raises(validation_utils.ValidationError) as exc_info:
        validation_utils.validate_required_mapping(
            {"cont_no": "CN-1", "company_name": "ABC"},
            ("cont_no", "trd_dt", "company_name"),
        )

    assert "trd_dt" in str(exc_info.value)


def test_validate_trade_import_payload_normalizes_trade_type_and_dates():
    payload = validation_utils.validate_trade_import_payload(
        {
            "cont_no": "CN-1",
            "trd_dt": "2025-01-01",
            "company_name": "ABC LTD",
            "trade_type_trd": "buy",
            "id_stk": "7",
            "qty_trd": "10",
            "exchange_orders": [
                {
                    "ord_no": 1,
                    "ord_dt": "2025-01-01",
                    "trd_no": 1,
                    "qty_eo": 10,
                    "rate_eo": 50.0,
                }
            ],
        }
    )

    assert payload["trade_type_trd"] == "BUY"
    assert payload["settle_dt"] == "2025-01-01"
    assert payload["id_stk"] == 7
    assert payload["qty_trd"] == 10


def test_validate_trade_import_payload_rejects_bad_exchange_order_date():
    with pytest.raises(validation_utils.ValidationError) as exc_info:
        validation_utils.validate_trade_import_payload(
            {
                "cont_no": "CN-1",
                "trd_dt": "2025-01-01",
                "company_name": "ABC LTD",
                "trade_type_trd": "BUY",
                "id_stk": 7,
                "qty_trd": 10,
                "exchange_orders": [
                    {
                        "ord_no": 1,
                        "ord_dt": "2025-02-30",
                        "trd_no": 1,
                        "qty_eo": 10,
                        "rate_eo": 50.0,
                    }
                ],
            }
        )

    assert "exchange_orders[1].ord_dt" in str(exc_info.value)


def test_validate_trade_core_payload_rejects_settlement_before_trade():
    with pytest.raises(validation_utils.ValidationError) as exc_info:
        validation_utils.validate_trade_core_payload(
            {
                "cont_no": "CN-1",
                "trd_dt": "2025-01-02",
                "settle_dt": "2025-01-01",
                "company_name": "ABC LTD",
                "trade_type_trd": "BUY",
                "qty_trd": 10,
                "id_stk": 7,
            },
            require_id_stk=True,
        )

    assert "settle_dt must be on or after trd_dt" in str(exc_info.value)


def test_validate_exchange_order_payload_rejects_negative_trade_number():
    with pytest.raises(validation_utils.ValidationError) as exc_info:
        validation_utils.validate_exchange_order_payload(
            {
                "ord_no": 1,
                "ord_dt": "2025-01-01",
                "trd_no": -1,
                "qty_eo": 10,
                "rate_eo": 50.0,
            },
            order_index=1,
        )

    assert "exchange_orders[1].trd_no" in str(exc_info.value)


def test_validate_order_quantity_progress_rejects_excess_ordered_qty():
    with pytest.raises(validation_utils.ValidationError) as exc_info:
        validation_utils.validate_order_quantity_progress(11, 10)

    assert "Ordered quantity is greater than the traded quantity" in str(
        exc_info.value
    )
