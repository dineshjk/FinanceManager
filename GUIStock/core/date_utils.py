# -*- coding: utf-8 -*-
# File: c:\Users\aumji\source\repos\Finance\FinanceManager\GUIStock\core\date_utils.py

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
