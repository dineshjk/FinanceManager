# -*- coding: utf-8 -*-
# File: C:\Data\Personal\Finance_and_Investment\finprog\FinanceManager\StockMan\date_utils.py

"""
Date utility functions for the Stock Portfolio Management System.

This module provides functions for working with dates in the context of
financial markets, including working day calculations and date validation.
"""

from datetime import datetime, timedelta, date


def next_working_day(date_obj=None):
    """
    Calculate the next working day (Monday-Friday) after the given date.

    Args:
        date_obj: Can be either a datetime.datetime or datetime.date object.
                 If datetime, only the date portion is used.
                 If None, uses today's date.

    Returns:
        datetime.date: The next working day (excluding weekends).

    Note:
        Weekdays are represented as: Monday=0, Tuesday=1, ..., Sunday=6
        This function skips weekends (Saturday=5, Sunday=6) but does not
        account for holidays.
    """
    # If no date provided, use today
    if date_obj is None:
        d = date.today()
    # Accept either date or datetime; normalize to date
    elif isinstance(date_obj, datetime):
        # If it's a datetime object, extract the date part
        d = date_obj.date()
    elif isinstance(date_obj, date):
        # If it's already a date object, use it directly
        d = date_obj
    else:
        # Fallback: assume it's already a date-like object
        d = date_obj

    next_day = d + timedelta(days=1)
    while next_day.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
        next_day += timedelta(days=1)
    return next_day


def previous_working_day(date_obj=None):
    """
    Calculate the previous working day (Monday-Friday) before the given date.

    Args:
        date_obj: Can be either a datetime.datetime or datetime.date object.
                 If datetime, only the date portion is used.
                 If None, uses today's date.

    Returns:
        datetime.date: The previous working day (excluding weekends).
    """
    # If no date provided, use today
    if date_obj is None:
        d = date.today()
    # Accept either date or datetime; normalize to date
    elif isinstance(date_obj, datetime):
        d = date_obj.date()
    elif isinstance(date_obj, date):
        d = date_obj
    else:
        d = date_obj

    prev_day = d - timedelta(days=1)
    while prev_day.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
        prev_day -= timedelta(days=1)
    return prev_day


def is_working_day(date_obj=None):
    """
    Check if the given date is a working day (Monday-Friday).

    Args:
        date_obj: Can be either a datetime.datetime or datetime.date object.
                 If datetime, only the date portion is used.
                 If None, uses today's date.

    Returns:
        bool: True if the date is a working day, False otherwise.
    """
    # If no date provided, use today
    if date_obj is None:
        d = date.today()
    # Accept either date or datetime; normalize to date
    elif isinstance(date_obj, datetime):
        d = date_obj.date()
    elif isinstance(date_obj, date):
        d = date_obj
    else:
        d = date_obj

    return d.weekday() < 5  # 0-4 are Monday-Friday


def format_date_for_display(date_obj, format_str="%Y-%m-%d"):
    """
    Format a date object for display purposes.

    Args:
        date_obj: Can be either a datetime.datetime or datetime.date object.
        format_str (str): Format string for date display.

    Returns:
        str: Formatted date string.
    """
    if date_obj is None:
        return ""

    # Accept either date or datetime; normalize to date
    if isinstance(date_obj, datetime):
        d = date_obj.date()
    elif isinstance(date_obj, date):
        d = date_obj
    else:
        # Try to parse string dates
        try:
            if isinstance(date_obj, str):
                d = datetime.strptime(date_obj, "%Y-%m-%d").date()
            else:
                return str(date_obj)
        except ValueError:
            return str(date_obj)

    return d.strftime(format_str)


def parse_date_from_string(date_str, format_str="%Y-%m-%d"):
    """
    Parse a date string into a date object.

    Args:
        date_str (str): String representation of the date.
        format_str (str): Format string to parse the date.

    Returns:
        datetime.date: Parsed date object, or None if parsing fails.
    """
    try:
        return datetime.strptime(date_str, format_str).date()
    except (ValueError, TypeError):
        return None


def is_valid_iso_date(date_str: str) -> bool:
    """Return True if date_str is a valid ISO date (YYYY-MM-DD)."""
    if not isinstance(date_str, str):
        return False
    try:
        datetime.strptime(date_str, "%Y-%m-%d").date()
        return True
    except ValueError:
        return False


def normalize_iso_date(value) -> str | None:
    """Normalize a date-like value to an ISO YYYY-MM-DD string.

    Accepts a date, datetime or string. Returns None for invalid values.
    """
    if value is None:
        return None
    # datetime is a subclass of date, so check datetime first
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        try:
            return datetime.strptime(value, "%Y-%m-%d").date().isoformat()
        except ValueError:
            return None
    return None


def validate_iso_date_or_raise(value, field_name: str = "date") -> str:
    """Return normalized ISO date string or raise ValueError with helpful
    message.
    """
    norm = normalize_iso_date(value)
    if norm is None:
        raise ValueError(
            f"{field_name!r} must be YYYY-MM-DD (valid date); got: {value!r}"
        )
    return norm


# File: C:\Data\Personal\Finance_and_Investment\finprog\FinanceManager\StockMan\date_utils.py ends here
