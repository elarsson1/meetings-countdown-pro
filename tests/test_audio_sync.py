"""Tests for compute_audio_sync — pure math, no Qt."""

from __future__ import annotations

import pytest

from meetings_countdown_pro.audio_player import compute_audio_sync


class TestComputeAudioSync:
    def test_audio_longer_than_countdown(self):
        seek_ms, delay = compute_audio_sync(90.0, 60.0)
        assert seek_ms == 30000
        assert delay == 0.0

    def test_audio_equal_to_countdown(self):
        seek_ms, delay = compute_audio_sync(60.0, 60.0)
        assert seek_ms == 0
        assert delay == 0.0

    def test_audio_shorter_than_countdown(self):
        seek_ms, delay = compute_audio_sync(45.0, 60.0)
        assert seek_ms == 0
        assert delay == 15.0

    def test_duration_zero(self):
        seek_ms, delay = compute_audio_sync(0.0, 60.0)
        assert seek_ms == 0
        assert delay == 0.0

    def test_duration_none(self):
        seek_ms, delay = compute_audio_sync(None, 60.0)
        assert seek_ms == 0
        assert delay == 0.0

    def test_duration_negative(self):
        seek_ms, delay = compute_audio_sync(-5.0, 60.0)
        assert seek_ms == 0
        assert delay == 0.0

    def test_late_start_reduced_countdown(self):
        """90s audio, only 30s remaining — seek deep into audio."""
        seek_ms, delay = compute_audio_sync(90.0, 30.0)
        assert seek_ms == 60000
        assert delay == 0.0

    def test_very_short_countdown(self):
        """Audio 60s, countdown 5s — seek to 55s."""
        seek_ms, delay = compute_audio_sync(60.0, 5.0)
        assert seek_ms == 55000
        assert delay == 0.0
