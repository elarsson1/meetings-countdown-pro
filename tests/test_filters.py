"""Tests for CalendarService._passes_filters — pure logic, no EventKit."""

from __future__ import annotations

import pytest

from meetings_countdown_pro.calendar_service import CalendarService
from meetings_countdown_pro.settings import Settings
from tests.conftest import make_meeting


def passes(meeting, **settings_overrides) -> bool:
    """Shortcut: call _passes_filters with no self (unused)."""
    s = Settings(**settings_overrides)
    return CalendarService._passes_filters(None, meeting, s)


# ===================================================================
# Always-filtered statuses
# ===================================================================

class TestAlwaysFiltered:
    def test_canceled_always_excluded(self):
        m = make_meeting(status="canceled")
        assert passes(m) is False

    def test_declined_always_excluded(self):
        m = make_meeting(acceptance_status="declined")
        assert passes(m) is False

    def test_normal_meeting_passes(self):
        m = make_meeting()
        assert passes(m) is True


# ===================================================================
# Tentative filter
# ===================================================================

class TestTentativeFilter:
    def test_tentative_acceptance_excluded_by_default(self):
        m = make_meeting(acceptance_status="tentative")
        assert passes(m, include_tentative=False) is False

    def test_tentative_acceptance_included_when_on(self):
        m = make_meeting(acceptance_status="tentative")
        assert passes(m, include_tentative=True) is True

    def test_tentative_availability_excluded_by_default(self):
        m = make_meeting(availability="tentative")
        assert passes(m, include_tentative=False) is False

    def test_tentative_availability_included_when_on(self):
        m = make_meeting(availability="tentative")
        assert passes(m, include_tentative=True) is True


# ===================================================================
# All-day filter
# ===================================================================

class TestAllDayFilter:
    def test_all_day_excluded_by_default(self):
        m = make_meeting(is_all_day=True)
        assert passes(m, include_all_day=False) is False

    def test_all_day_included_when_on(self):
        m = make_meeting(is_all_day=True)
        assert passes(m, include_all_day=True) is True

    def test_non_all_day_passes_regardless(self):
        m = make_meeting(is_all_day=False)
        assert passes(m, include_all_day=False) is True


# ===================================================================
# Free event filter
# ===================================================================

class TestFreeFilter:
    def test_free_excluded_by_default(self):
        m = make_meeting(availability="free")
        assert passes(m, include_free=False) is False

    def test_free_included_when_on(self):
        m = make_meeting(availability="free")
        assert passes(m, include_free=True) is True


# ===================================================================
# Video calls only filter
# ===================================================================

class TestVideoCallsOnly:
    def test_no_link_excluded_when_video_only(self):
        m = make_meeting()  # no video link
        assert passes(m, video_calls_only=True) is False

    def test_with_link_passes_when_video_only(self):
        m = make_meeting(url="https://zoom.us/j/123")
        assert passes(m, video_calls_only=True) is True

    def test_no_link_passes_when_not_video_only(self):
        m = make_meeting()
        assert passes(m, video_calls_only=False) is True


# ===================================================================
# Combinations
# ===================================================================

class TestCombinations:
    def test_tentative_all_day_mixed(self):
        """Tentative + all-day: even with include_tentative=True, all-day filter wins."""
        m = make_meeting(acceptance_status="tentative", is_all_day=True)
        assert passes(m, include_tentative=True, include_all_day=False) is False

    def test_free_with_video_link(self):
        """Free + has video link: include_free=False still filters it out."""
        m = make_meeting(availability="free", url="https://zoom.us/j/123")
        assert passes(m, include_free=False, video_calls_only=True) is False

    def test_all_filters_permissive(self):
        """Everything on: tentative all-day free meeting with link passes."""
        m = make_meeting(
            acceptance_status="tentative",
            is_all_day=True,
            availability="free",
            url="https://zoom.us/j/123",
        )
        assert passes(m, include_tentative=True, include_all_day=True, include_free=True, video_calls_only=True) is True
