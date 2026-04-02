"""Shared test fixtures."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from meetings_countdown_pro.meeting import Attendee, Meeting
from meetings_countdown_pro.settings import Settings


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------

def make_meeting(**overrides) -> Meeting:
    """Create a Meeting with sensible defaults. Override any field via kwargs."""
    now = datetime.now(timezone.utc)
    defaults = dict(
        uid="test-uid-001",
        title="Test Meeting",
        start=now + timedelta(seconds=60),
        end=now + timedelta(seconds=3660),
        calendar_name="Work",
        status="confirmed",
        acceptance_status="accepted",
        availability="busy",
    )
    defaults.update(overrides)
    return Meeting(**defaults)


def make_attendee(**overrides) -> Attendee:
    """Create an Attendee with sensible defaults."""
    defaults = dict(email="user@example.com", display_name="Test User", is_organizer=False)
    defaults.update(overrides)
    return Attendee(**defaults)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def config_dir(tmp_path, monkeypatch):
    """Redirect all config I/O to a temp directory."""
    monkeypatch.setattr("meetings_countdown_pro.settings.CONFIG_DIR", tmp_path)
    monkeypatch.setattr("meetings_countdown_pro.settings.SETTINGS_FILE", tmp_path / "settings.json")
    monkeypatch.setattr("meetings_countdown_pro.notification_state.CONFIG_DIR", tmp_path)
    monkeypatch.setattr("meetings_countdown_pro.notification_state.NOTIFIED_FILE", tmp_path / "notified.json")
    return tmp_path


@pytest.fixture
def default_settings():
    return Settings()
