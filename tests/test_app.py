"""Tests for App controller — polling, scheduling, back-to-back, dedup."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional
from unittest.mock import patch

import pytest
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

from meetings_countdown_pro.meeting import Attendee, Meeting
from meetings_countdown_pro.settings import Settings
from tests.conftest import make_meeting


# ---------------------------------------------------------------------------
# Mock CalendarService
# ---------------------------------------------------------------------------

class MockCalendarService:
    def __init__(self, meetings=None, authorized=True, in_progress=False):
        self._meetings = meetings or []
        self._authorized = authorized
        self._in_progress = in_progress

    @property
    def is_authorized(self):
        return self._authorized

    def request_access(self, callback):
        callback(self._authorized)

    def fetch_upcoming(self, settings):
        return list(self._meetings)

    def is_meeting_in_progress(self, settings):
        return self._in_progress

    def get_calendars(self):
        return {"Test": [{"name": "Work", "uid": "1", "color": (66, 133, 244)}]}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_app(qtbot, config_dir, monkeypatch):
    """Factory that creates an App with a MockCalendarService.

    Returns a callable: mock_app(meetings=[], authorized=True, in_progress=False, **settings_kw)
    """
    def _factory(meetings=None, authorized=True, in_progress=False, **settings_kw):
        mock_cal = MockCalendarService(meetings=meetings or [], authorized=authorized, in_progress=in_progress)

        # Patch CalendarService constructor
        monkeypatch.setattr(
            "meetings_countdown_pro.app.CalendarService",
            lambda: mock_cal,
        )

        # Patch AudioPlayer to avoid real media pipeline
        from tests.test_countdown_window import StubAudioPlayer
        monkeypatch.setattr(
            "meetings_countdown_pro.app.AudioPlayer",
            StubAudioPlayer,
        )

        # Patch FaviconCache
        from tests.test_countdown_window import StubFaviconCache
        monkeypatch.setattr(
            "meetings_countdown_pro.app.FaviconCache",
            StubFaviconCache,
        )

        # Write initial settings
        s = Settings(**settings_kw)
        s.save()

        from meetings_countdown_pro.app import App
        qapp = QApplication.instance()
        app = App(qapp)

        # Process deferred events (e.g., QTimer.singleShot(0) from _on_calendar_access)
        qapp.processEvents()

        return app, mock_cal

    return _factory


def _future_meeting(seconds_ahead=120, **kw):
    """Create a meeting starting `seconds_ahead` from now."""
    now = datetime.now(timezone.utc)
    defaults = dict(
        uid="uid-001",
        title="Upcoming Meeting",
        start=now + timedelta(seconds=seconds_ahead),
        end=now + timedelta(seconds=seconds_ahead + 3600),
        calendar_name="Work",
        status="confirmed",
        acceptance_status="accepted",
        availability="busy",
    )
    defaults.update(kw)
    return Meeting(**defaults)


# ===================================================================
# Menu structure
# ===================================================================

class TestMenu:
    def test_about_action_exists(self, mock_app):
        app, _ = mock_app()
        actions = [a.text() for a in app._menu.actions()]
        assert "About Meetings Countdown Pro" in actions

    def test_about_action_between_settings_and_quit(self, mock_app):
        app, _ = mock_app()
        actions = [a.text() for a in app._menu.actions() if a.text()]
        # Settings, About, Quit should be the last three non-separator items
        assert "Settings..." in actions
        assert "About Meetings Countdown Pro" in actions
        assert "Quit Meetings Countdown Pro" in actions
        si = actions.index("Settings...")
        ai = actions.index("About Meetings Countdown Pro")
        qi = actions.index("Quit Meetings Countdown Pro")
        assert si < ai < qi


# ===================================================================
# Polling & scheduling
# ===================================================================

class TestPolling:
    def test_poll_with_meetings_sets_next(self, mock_app):
        m = _future_meeting(120)
        app, _ = mock_app(meetings=[m])
        assert app._next_meeting is not None
        assert app._next_meeting.uid == "uid-001"

    def test_poll_with_no_meetings(self, mock_app):
        app, _ = mock_app(meetings=[])
        assert app._next_meeting is None

    def test_poll_mode_off_still_shows_next_meeting(self, mock_app):
        m = _future_meeting(120)
        app, cal = mock_app(meetings=[m], mode="off")
        # Mode off should still populate next meeting for display
        assert app._next_meeting is not None
        assert app._next_meeting.uid == "uid-001"

    def test_poll_mode_off_shows_next_meeting_display(self, mock_app):
        m = _future_meeting(120)
        app, _ = mock_app(meetings=[m], mode="off")
        assert "Next:" in app._next_meeting_action.text()

    def test_poll_mode_off_no_trigger_timer(self, mock_app):
        m = _future_meeting(120)
        app, _ = mock_app(meetings=[m], mode="off")
        # No countdown should be scheduled when mode is off
        assert app._trigger_timer is None or not app._trigger_timer.isActive()

    def test_poll_timer_interval(self, mock_app):
        app, _ = mock_app()
        assert app._poll_timer.interval() == 30_000

    def test_trigger_timer_scheduled(self, mock_app):
        m = _future_meeting(120)
        app, _ = mock_app(meetings=[m])
        assert app._trigger_timer is not None
        assert app._trigger_timer.isActive()


# ===================================================================
# Next meeting display
# ===================================================================

class TestNextMeetingDisplay:
    def test_no_meetings_text(self, mock_app):
        app, _ = mock_app(meetings=[])
        assert "No more meetings today" in app._next_meeting_action.text()

    def test_calendar_not_authorized(self, mock_app):
        app, _ = mock_app(authorized=False)
        assert "\u26a0" in app._next_meeting_action.text()

    def test_title_truncation(self, mock_app):
        m = _future_meeting(120, title="A" * 40)
        app, _ = mock_app(meetings=[m])
        text = app._next_meeting_action.text()
        assert "\u2026" in text  # ellipsis present

    def test_meeting_shows_time(self, mock_app):
        m = _future_meeting(120)
        app, _ = mock_app(meetings=[m])
        text = app._next_meeting_action.text()
        assert "Next:" in text

    def test_mode_off_still_shows_meeting(self, mock_app):
        m = _future_meeting(120, title="Standup")
        app, _ = mock_app(meetings=[m], mode="off")
        text = app._next_meeting_action.text()
        assert "Next:" in text
        assert "Standup" in text


# ===================================================================
# Dedup / notification state
# ===================================================================

class TestDedup:
    def test_notified_meeting_skipped(self, mock_app):
        m = _future_meeting(120)
        app, _ = mock_app(meetings=[m])
        # First poll picks it up
        assert app._next_meeting is not None

        # Mark as notified, then re-poll
        app._notified.mark_notified(m.notification_key)
        app._poll()
        assert app._next_meeting is None

    def test_meeting_too_close_auto_notified(self, mock_app):
        m = _future_meeting(3)  # Less than MIN_COUNTDOWN_SECONDS (5)
        app, _ = mock_app(meetings=[m])
        # Should be auto-notified and skipped
        assert app._notified.is_notified(m.notification_key) is True
        assert app._next_meeting is None


# ===================================================================
# Simultaneous meetings
# ===================================================================

class TestSimultaneous:
    def test_same_start_grouped(self, mock_app):
        now = datetime.now(timezone.utc) + timedelta(seconds=120)
        m1 = Meeting(uid="a", title="Alpha", start=now, end=now + timedelta(hours=1),
                     calendar_name="Work", status="confirmed", acceptance_status="accepted", availability="busy")
        m2 = Meeting(uid="b", title="Beta", start=now, end=now + timedelta(hours=1),
                     calendar_name="Work", status="confirmed", acceptance_status="accepted", availability="busy")
        m3 = Meeting(uid="c", title="Gamma", start=now + timedelta(minutes=30),
                     end=now + timedelta(hours=2),
                     calendar_name="Work", status="confirmed", acceptance_status="accepted", availability="busy")
        app, _ = mock_app(meetings=[m1, m2, m3])
        # Primary should be the first one
        assert app._next_meeting.uid == "a"


# ===================================================================
# Back-to-back handling
# ===================================================================

class TestBackToBack:
    def test_skip_mode(self, mock_app):
        m = _future_meeting(3)  # triggers immediately via late start path
        # Actually, we need the meeting within countdown range to test _trigger_countdown
        # Let's directly test _trigger_countdown
        app, cal = mock_app(in_progress=True, back_to_back="skip")
        m = _future_meeting(120)
        app._notified = app._notified  # ensure clean
        app._trigger_countdown([m])
        assert app._countdown_window is None  # skipped
        assert app._notified.is_notified(m.notification_key)  # but still marked

    def test_silent_mode(self, mock_app):
        app, cal = mock_app(in_progress=True, back_to_back="silent", mode="countdown_music")
        m = _future_meeting(120, url="https://zoom.us/j/123")
        app._trigger_countdown([m])
        assert app._countdown_window is not None
        # The effective mode should be silent
        assert app._countdown_window._settings.mode == "silent"
        app._countdown_window.close()

    def test_default_mode(self, mock_app):
        app, cal = mock_app(in_progress=True, back_to_back="default", mode="countdown_music")
        m = _future_meeting(120, url="https://zoom.us/j/123")
        app._trigger_countdown([m])
        assert app._countdown_window is not None
        assert app._countdown_window._settings.mode == "countdown_music"
        app._countdown_window.close()

    def test_no_meeting_in_progress_uses_current_mode(self, mock_app):
        app, cal = mock_app(in_progress=False, back_to_back="skip", mode="countdown_music")
        m = _future_meeting(120)
        app._trigger_countdown([m])
        assert app._countdown_window is not None
        assert app._countdown_window._settings.mode == "countdown_music"
        app._countdown_window.close()


# ===================================================================
# One countdown at a time
# ===================================================================

class TestOneAtATime:
    def test_second_trigger_skipped(self, mock_app):
        app, _ = mock_app()
        m1 = _future_meeting(120, uid="a")
        m2 = _future_meeting(120, uid="b")

        app._trigger_countdown([m1])
        assert app._countdown_window is not None
        first_window = app._countdown_window

        app._trigger_countdown([m2])
        assert app._countdown_window is first_window  # same window, not replaced
        app._countdown_window.close()


# ===================================================================
# Mode & agent toggle
# ===================================================================

class TestModeToggle:
    def test_set_mode_saves(self, mock_app):
        app, _ = mock_app(mode="countdown_music")
        app._set_mode("silent")
        assert app._settings.mode == "silent"
        # Verify persisted
        loaded = Settings.load()
        assert loaded.mode == "silent"

    def test_toggle_agent_saves(self, mock_app):
        app, _ = mock_app(agent_enabled=False)
        app._toggle_agent(True)
        assert app._settings.agent_enabled is True
        loaded = Settings.load()
        assert loaded.agent_enabled is True


# ===================================================================
# Countdown close triggers re-poll
# ===================================================================

class TestCountdownClose:
    def test_close_clears_window_and_repolls(self, mock_app):
        app, _ = mock_app()
        m = _future_meeting(120)
        app._trigger_countdown([m])
        assert app._countdown_window is not None

        app._countdown_window.close()
        assert app._countdown_window is None
