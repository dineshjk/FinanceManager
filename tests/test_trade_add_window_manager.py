# -*- coding: utf-8 -*-
# tests/test_trade_add_window_manager.py
from datetime import date

import pytest

from StockMan import trade_add
from Shared import window_manager


class _FakeEntry:
    def __init__(self, value=""):
        self.value = value

    def get(self):
        return self.value

    def delete(self, _start, _end):
        self.value = ""

    def insert(self, _index, value):
        self.value = str(value)


class _FakeVar:
    def __init__(self, value=None):
        self.value = value

    def set(self, value):
        self.value = value

    def get(self):
        return self.value


class _FakeDateEntry:
    def __init__(self, current_date):
        self.current_date = current_date

    def get_date(self):
        return self.current_date

    def set_date(self, new_date):
        self.current_date = new_date


class _FakeParent:
    def __init__(self):
        self.lift_called = 0
        self.focus_force_called = 0
        self.focus_set_called = 0

    def lift(self):
        self.lift_called += 1

    def focus_force(self):
        self.focus_force_called += 1

    def focus_set(self):
        self.focus_set_called += 1


class _FakeButton:
    def __init__(self):
        self.focus_set_called = 0

    def focus_set(self):
        self.focus_set_called += 1


class _FakeWindow:
    def __init__(self):
        self.protocol_handlers = {}
        self.destroy_bindings = []
        self.exists = True
        self.destroy_called = 0
        self.grab_release_called = 0
        self.master = None

    def protocol(self, name, callback):
        self.protocol_handlers[name] = callback

    def bind(self, name, callback):
        self.destroy_bindings.append((name, callback))

    def winfo_exists(self):
        return self.exists

    def destroy(self):
        self.destroy_called += 1
        self.exists = False

    def grab_release(self):
        self.grab_release_called += 1


@pytest.fixture(autouse=True)
def clear_window_stack():
    window_manager._window_stack.clear()
    yield
    window_manager._window_stack.clear()


def test_validate_required_fields_returns_true_for_complete_payload():
    assert (
        trade_add.validate_required_fields(
            {"cont_no": "ABC/12", "company_name": "Acme"},
            ["cont_no", "company_name"],
        )
        is True
    )


def test_validate_required_fields_reports_missing_data(monkeypatch):
    captured = {}

    def fake_show_validation_error(parent, exc, title):
        captured["parent"] = parent
        captured["message"] = str(exc)
        captured["title"] = title

    monkeypatch.setattr(
        trade_add, "show_validation_error", fake_show_validation_error
    )

    result = trade_add.validate_required_fields(
        {"cont_no": "", "company_name": "Acme"},
        ["cont_no", "company_name"],
        parent_window="parent-window",
    )

    assert result is False
    assert captured == {
        "parent": "parent-window",
        "message": (
            "Required field(s) missing: cont_no. Please complete all "
            "required steps before submitting."
        ),
        "title": "Missing Data",
    }


def test_update_and_calculate_settle_no_extracts_number_from_contract():
    cont_no_entry = _FakeEntry("ABC/42/2025")
    settle_no_entry = _FakeEntry()
    settle_no_var = _FakeVar()

    result = trade_add.update_and_calculate_settle_no(
        cont_no_entry,
        settle_no_entry,
        settle_no_var,
    )

    assert result == 42
    assert settle_no_entry.get() == "42"
    assert settle_no_var.get() == 42


def test_update_settle_date_on_focus_uses_next_working_day(monkeypatch):
    trade_date_entry = _FakeDateEntry(date(2025, 4, 4))
    settle_date_entry = _FakeDateEntry(date(2025, 4, 4))

    monkeypatch.setattr(
        trade_add,
        "next_working_day",
        lambda current_date: date(2025, 4, 7),
    )

    trade_add.update_settle_date_on_focus(trade_date_entry, settle_date_entry)

    assert settle_date_entry.get_date() == date(2025, 4, 7)


def test_safe_close_modal_cleans_stack_and_restores_focus(monkeypatch):
    parent = _FakeParent()
    button = _FakeButton()
    window = _FakeWindow()
    enable_calls = []

    monkeypatch.setattr(
        window_manager,
        "enable_parent",
        lambda parent_arg: enable_calls.append(parent_arg),
    )

    window_manager.push_window(window, parent)

    result = window_manager.safe_close_modal(
        window,
        parent=parent,
        calling_button=button,
    )

    assert result == "break"
    assert window.grab_release_called == 1
    assert window.destroy_called == 1
    assert window_manager.stack_size() == 0
    assert enable_calls == [parent]
    assert parent.lift_called == 1
    assert parent.focus_force_called == 1
    assert button.focus_set_called == 1


def test_push_window_delete_handler_cleans_up_stack(monkeypatch):
    parent = _FakeParent()
    window = _FakeWindow()
    enable_calls = []

    monkeypatch.setattr(
        window_manager,
        "enable_parent",
        lambda parent_arg: enable_calls.append(parent_arg),
    )

    window_manager.push_window(window, parent)
    window.protocol_handlers["WM_DELETE_WINDOW"]()

    assert window_manager.stack_size() == 0
    assert enable_calls == [parent]
    assert window.destroy_called == 1
