"""
holiday_manager.py
Sunday, government holiday, and school holiday management for Maharashtra MDM.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

import holidays as holidays_pkg

logger = logging.getLogger(__name__)


class HolidayManager:
    """
    Determines whether a given date is a school working day.

    Non-working days:
        - Sundays
        - Maharashtra government holidays (via `holidays` package)
        - Custom school holidays (loaded from Excel or added manually)
    """

    def __init__(
        self,
        year: int,
        country: str = "IN",
        state: str = "MH",
        school_holidays: Optional[set[date]] = None,
    ) -> None:
        self.year = year
        self._govt: holidays_pkg.HolidayBase = holidays_pkg.country_holidays(
            country, subdiv=state, years=year
        )
        self._school: set[date] = school_holidays or set()

        logger.info(
            "HolidayManager ready | year=%d | govt_holidays=%d | school_holidays=%d",
            year, len(self._govt), len(self._school),
        )

    # ── Core checks ───────────────────────────────────────────────────────────

    def is_sunday(self, d: date) -> bool:
        """Return True if the date falls on a Sunday."""
        return d.weekday() == 6

    def is_holiday(self, d: date) -> bool:
        """Return True if the date is a government or school holiday (excludes Sundays)."""
        return d in self._govt or d in self._school

    def is_working_day(self, d: date) -> bool:
        """Return True only if the date is a school working day."""
        return not self.is_sunday(d) and not self.is_holiday(d)

    def holiday_name(self, d: date) -> Optional[str]:
        """Return the reason a day is non-working, or None if it is a working day."""
        if self.is_sunday(d):
            return "Sunday"
        if d in self._govt:
            return str(self._govt.get(d, "Government Holiday"))
        if d in self._school:
            return "School Holiday"
        return None

    # ── Working day queries ───────────────────────────────────────────────────

    def get_working_days(self, month: int) -> list[date]:
        """Return all working school days for the given month."""
        days: list[date] = []
        current = date(self.year, month, 1)
        while current.month == month:
            if self.is_working_day(current):
                days.append(current)
            current += timedelta(days=1)

        logger.info("Working days %04d-%02d: %d", self.year, month, len(days))
        return days

    def get_non_working_days(self, month: int) -> list[tuple[date, str]]:
        """Return all non-working days with reasons for the given month."""
        result: list[tuple[date, str]] = []
        current = date(self.year, month, 1)
        while current.month == month:
            reason = self.holiday_name(current)
            if reason is not None:
                result.append((current, reason))
            current += timedelta(days=1)
        return result

    # ── School holiday management ─────────────────────────────────────────────

    def add_school_holiday(self, d: date) -> None:
        """Add a single school holiday."""
        self._school.add(d)
        logger.info("School holiday added: %s", d)

    def load_school_holidays(self, holiday_file: Path) -> None:
        """
        Load school holidays from an Excel file.
        Expected column name: Date
        """
        if not holiday_file.exists():
            logger.warning("School holiday file not found: %s — skipping", holiday_file)
            return

        import pandas as pd

        try:
            df = pd.read_excel(str(holiday_file), parse_dates=["Date"])
        except Exception as exc:
            logger.warning("Could not read holiday file %s: %s — skipping", holiday_file, exc)
            return

        if "Date" not in df.columns:
            logger.warning("Holiday file has no 'Date' column — skipping")
            return

        before = len(self._school)
        for val in df["Date"].dropna():
            self._school.add(val.date())

        added = len(self._school) - before
        logger.info("Loaded %d school holidays from %s", added, holiday_file)
