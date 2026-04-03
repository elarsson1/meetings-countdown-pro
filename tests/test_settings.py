"""Tests for Settings model — validation and persistence."""

from __future__ import annotations

import json

import pytest

from meetings_countdown_pro.settings import Settings


# ===================================================================
# Settings.validate() clamping
# ===================================================================

class TestValidate:
    @pytest.mark.parametrize("field,input_val,expected", [
        ("countdown_duration", 5, 10),
        ("countdown_duration", 500, 300),
        ("countdown_duration", 60, 60),
        ("countdown_duration", 10, 10),
        ("countdown_duration", 300, 300),
        ("clock_offset", -5000, -2000),
        ("clock_offset", 5000, 2000),
        ("clock_offset", 0, 0),
        ("clock_offset", -2000, -2000),
        ("clock_offset", 2000, 2000),
        ("volume", -10, 0),
        ("volume", 200, 100),
        ("volume", 50, 50),
        ("volume", 0, 0),
        ("volume", 100, 100),
    ])
    def test_numeric_clamping(self, field, input_val, expected):
        s = Settings(**{field: input_val})
        s.validate()
        assert getattr(s, field) == expected

    @pytest.mark.parametrize("field,input_val,expected", [
        ("back_to_back", "invalid", "default"),
        ("back_to_back", "silent", "silent"),
        ("back_to_back", "skip", "skip"),
        ("back_to_back", "default", "default"),
        ("back_to_back", "countdown_music", "countdown_music"),
        ("mode", "invalid", "countdown_music"),
        ("mode", "silent", "silent"),
        ("mode", "off", "off"),
        ("agent_terminal", "invalid", "terminal"),
        ("agent_terminal", "iterm2", "iterm2"),
    ])
    def test_enum_clamping(self, field, input_val, expected):
        s = Settings(**{field: input_val})
        s.validate()
        assert getattr(s, field) == expected


# ===================================================================
# Settings save/load round-trip
# ===================================================================

class TestPersistence:
    def test_round_trip_defaults(self, config_dir):
        s = Settings()
        s.save()
        loaded = Settings.load()
        assert loaded.countdown_duration == s.countdown_duration
        assert loaded.mode == s.mode
        assert loaded.volume == s.volume

    def test_round_trip_non_defaults(self, config_dir):
        s = Settings(
            countdown_duration=120,
            video_calls_only=True,
            internal_domain="corp.com",
            mode="silent",
            volume=42,
            clock_offset=-500,
            agent_enabled=True,
            agent_terminal="iterm2",
            continue_after_join=True,
            selected_calendars={"iCloud": ["Work", "Personal"]},
        )
        s.save()
        loaded = Settings.load()
        assert loaded.countdown_duration == 120
        assert loaded.video_calls_only is True
        assert loaded.internal_domain == "corp.com"
        assert loaded.mode == "silent"
        assert loaded.volume == 42
        assert loaded.clock_offset == -500
        assert loaded.agent_enabled is True
        assert loaded.agent_terminal == "iterm2"
        assert loaded.continue_after_join is True
        assert loaded.selected_calendars == {"iCloud": ["Work", "Personal"]}

    def test_load_missing_file(self, config_dir):
        loaded = Settings.load()
        assert loaded.countdown_duration == 60  # default

    def test_load_corrupt_json(self, config_dir):
        (config_dir / "settings.json").write_text("not valid json {{{")
        loaded = Settings.load()
        assert loaded.countdown_duration == 60  # falls back to defaults

    def test_load_ignores_unknown_keys(self, config_dir):
        data = {"countdown_duration": 90, "unknown_future_key": True}
        (config_dir / "settings.json").write_text(json.dumps(data))
        loaded = Settings.load()
        assert loaded.countdown_duration == 90
        assert not hasattr(loaded, "unknown_future_key")

    def test_load_fills_missing_keys(self, config_dir):
        data = {"countdown_duration": 90}
        (config_dir / "settings.json").write_text(json.dumps(data))
        loaded = Settings.load()
        assert loaded.countdown_duration == 90
        assert loaded.volume == 100  # default filled in

    def test_continue_after_join_defaults_false(self):
        s = Settings()
        assert s.continue_after_join is False
