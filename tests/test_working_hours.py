"""Tests for working hours — settings validation and App._is_within_working_hours."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

import pytest

from meetings_countdown_pro.settings import Settings


# ---------------------------------------------------------------------------
# Helper: call _is_within_working_hours without a full App instance
# ---------------------------------------------------------------------------

def _within(meeting_start: datetime, **settings_kw) -> bool:
    """Invoke App._is_within_working_hours via the unbound method."""
    from meetings_countdown_pro.app import App

    s = Settings(**settings_kw)

    class FakeApp:
        _settings = s

    return App._is_within_working_hours(FakeApp(), meeting_start)


def _local_dt(year, month, day, hour, minute=0):
    """Create a timezone-aware local datetime."""
    from datetime import timezone as tz
    import time

    # Use the local timezone
    local_tz = datetime.now().astimezone().tzinfo
    return datetime(year, month, day, hour, minute, tzinfo=local_tz)


# ===================================================================
# Feature disabled (default)
# ===================================================================

class TestDisabled:
    def test_always_allowed_when_disabled(self):
        """When working_hours_enabled=False, any time should pass."""
        # Saturday at 3 AM — would fail if enabled with defaults
        saturday_3am = _local_dt(2026, 4, 4, 3)  # 2026-04-04 is a Saturday
        assert _within(saturday_3am, working_hours_enabled=False) is True

    def test_disabled_is_the_default(self):
        s = Settings()
        assert s.working_hours_enabled is False


# ===================================================================
# Day-of-week filtering
# ===================================================================

class TestDayFiltering:
    def test_weekday_allowed_with_defaults(self):
        # Wednesday at 10 AM
        wed = _local_dt(2026, 4, 1, 10)  # 2026-04-01 is a Wednesday
        assert _within(wed, working_hours_enabled=True) is True

    def test_saturday_blocked_with_defaults(self):
        sat = _local_dt(2026, 4, 4, 10)  # Saturday
        assert _within(sat, working_hours_enabled=True) is False

    def test_sunday_blocked_with_defaults(self):
        sun = _local_dt(2026, 4, 5, 10)  # Sunday
        assert _within(sun, working_hours_enabled=True) is False

    def test_custom_days_include_saturday(self):
        sat = _local_dt(2026, 4, 4, 10)
        # Add Saturday (weekday=5) to allowed days
        assert _within(sat, working_hours_enabled=True,
                       working_hours_days=[0, 1, 2, 3, 4, 5]) is True

    def test_custom_days_exclude_wednesday(self):
        wed = _local_dt(2026, 4, 1, 10)
        # Only Mon, Tue (0, 1)
        assert _within(wed, working_hours_enabled=True,
                       working_hours_days=[0, 1]) is False

    def test_empty_days_blocks_everything(self):
        wed = _local_dt(2026, 4, 1, 10)
        assert _within(wed, working_hours_enabled=True,
                       working_hours_days=[]) is False


# ===================================================================
# Time-of-day filtering
# ===================================================================

class TestTimeFiltering:
    def test_within_default_hours(self):
        # Wednesday at 12:00 noon
        wed_noon = _local_dt(2026, 4, 1, 12)
        assert _within(wed_noon, working_hours_enabled=True) is True

    def test_before_start_blocked(self):
        # Wednesday at 8:59 AM — before 9:00
        wed_early = _local_dt(2026, 4, 1, 8, 59)
        assert _within(wed_early, working_hours_enabled=True) is False

    def test_exactly_at_start_allowed(self):
        # Wednesday at exactly 9:00 AM
        wed_9am = _local_dt(2026, 4, 1, 9, 0)
        assert _within(wed_9am, working_hours_enabled=True) is True

    def test_exactly_at_end_blocked(self):
        # Wednesday at exactly 5:00 PM — end is exclusive
        wed_5pm = _local_dt(2026, 4, 1, 17, 0)
        assert _within(wed_5pm, working_hours_enabled=True) is False

    def test_one_minute_before_end_allowed(self):
        wed = _local_dt(2026, 4, 1, 16, 59)
        assert _within(wed, working_hours_enabled=True) is True

    def test_after_end_blocked(self):
        wed_evening = _local_dt(2026, 4, 1, 20, 0)
        assert _within(wed_evening, working_hours_enabled=True) is False

    def test_custom_early_start(self):
        # Start at 7:00 AM
        wed_730 = _local_dt(2026, 4, 1, 7, 30)
        assert _within(wed_730, working_hours_enabled=True,
                       working_hours_start="07:00") is True

    def test_custom_late_end(self):
        # End at 9:00 PM
        wed_8pm = _local_dt(2026, 4, 1, 20, 0)
        assert _within(wed_8pm, working_hours_enabled=True,
                       working_hours_end="21:00") is True

    def test_half_hour_boundaries(self):
        # Start at 8:30 AM
        wed_825 = _local_dt(2026, 4, 1, 8, 25)
        wed_835 = _local_dt(2026, 4, 1, 8, 35)
        assert _within(wed_825, working_hours_enabled=True,
                       working_hours_start="08:30") is False
        assert _within(wed_835, working_hours_enabled=True,
                       working_hours_start="08:30") is True


# ===================================================================
# Combined day + time filtering
# ===================================================================

class TestCombined:
    def test_right_day_wrong_time(self):
        wed_6am = _local_dt(2026, 4, 1, 6)
        assert _within(wed_6am, working_hours_enabled=True) is False

    def test_wrong_day_right_time(self):
        sat_10am = _local_dt(2026, 4, 4, 10)
        assert _within(sat_10am, working_hours_enabled=True) is False

    def test_right_day_right_time(self):
        wed_10am = _local_dt(2026, 4, 1, 10)
        assert _within(wed_10am, working_hours_enabled=True) is True


# ===================================================================
# Settings validation
# ===================================================================

class TestSettingsValidation:
    def test_default_days(self):
        s = Settings()
        assert s.working_hours_days == [0, 1, 2, 3, 4]  # Mon-Fri

    def test_default_times(self):
        s = Settings()
        assert s.working_hours_start == "09:00"
        assert s.working_hours_end == "17:00"

    def test_invalid_days_stripped(self):
        s = Settings(working_hours_days=[0, 1, 7, -1, 99])
        s.validate()
        assert s.working_hours_days == [0, 1]

    def test_duplicate_days_deduped(self):
        s = Settings(working_hours_days=[0, 0, 1, 1])
        s.validate()
        assert s.working_hours_days == [0, 1]

    def test_invalid_start_time_reset(self):
        s = Settings(working_hours_start="not a time")
        s.validate()
        assert s.working_hours_start == "09:00"

    def test_invalid_end_time_reset(self):
        s = Settings(working_hours_end="25:00")
        s.validate()
        assert s.working_hours_end == "17:00"

    def test_valid_custom_times_preserved(self):
        s = Settings(working_hours_start="07:30", working_hours_end="20:00")
        s.validate()
        assert s.working_hours_start == "07:30"
        assert s.working_hours_end == "20:00"
