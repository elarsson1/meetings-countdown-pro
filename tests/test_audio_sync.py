"""Tests for compute_audio_sync and audio correction logic."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from meetings_countdown_pro.audio_player import AudioPlayer, compute_audio_sync


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


class TestAudioCorrectionSignal:
    """Tests for the audio correction mechanism in AudioPlayer."""

    def test_expected_play_time_set_immediate(self, qtbot, tmp_path, monkeypatch):
        """Immediate playback (D >= C) records expected_play_time."""
        fake_file = tmp_path / "audio.mp3"
        fake_file.write_bytes(b"\x00")
        player = AudioPlayer()
        player._sound_file = str(fake_file)
        player._detected_duration = 90.0
        monkeypatch.setattr(player, "_ensure_source_and_play", lambda: None)

        before = time.monotonic()
        player.start_countdown_playback(60.0)
        after = time.monotonic()

        assert player._expected_play_time is not None
        assert before <= player._expected_play_time <= after

    def test_expected_play_time_set_delayed(self, qtbot, tmp_path):
        """Delayed playback (D < C) records expected_play_time = now + delay."""
        fake_file = tmp_path / "audio.mp3"
        fake_file.write_bytes(b"\x00")
        player = AudioPlayer()
        player._sound_file = str(fake_file)
        player._detected_duration = 45.0

        before = time.monotonic()
        delay = player.start_countdown_playback(60.0)
        after = time.monotonic()

        assert delay == pytest.approx(15.0)
        assert player._expected_play_time is not None
        # expected = monotonic() + 15.0, captured between before and after
        assert before + 15.0 <= player._expected_play_time <= after + 15.0

    def test_correction_emitted_on_playing_state(self, qtbot):
        """PlayingState transition emits audio_correction_ready signal."""
        from PyQt6.QtMultimedia import QMediaPlayer

        player = AudioPlayer()
        player._expected_play_time = time.monotonic() - 0.150  # 150ms ago

        with qtbot.waitSignal(player.audio_correction_ready, timeout=1000) as sig:
            player._on_playback_state(QMediaPlayer.PlaybackState.PlayingState)

        assert sig.args[0] == 150  # within rounding

    def test_correction_mod_1000(self, qtbot):
        """Correction wraps at 1000ms boundary."""
        from PyQt6.QtMultimedia import QMediaPlayer

        player = AudioPlayer()
        player._expected_play_time = time.monotonic() - 1.200  # 1200ms ago

        with qtbot.waitSignal(player.audio_correction_ready, timeout=1000) as sig:
            player._on_playback_state(QMediaPlayer.PlaybackState.PlayingState)

        assert sig.args[0] == 200

    def test_no_correction_without_expected_time(self, qtbot):
        """No signal emitted if _expected_play_time is not set (e.g. preview)."""
        from PyQt6.QtMultimedia import QMediaPlayer

        player = AudioPlayer()
        assert player._expected_play_time is None

        callback = MagicMock()
        player.audio_correction_ready.connect(callback)
        player._on_playback_state(QMediaPlayer.PlaybackState.PlayingState)
        callback.assert_not_called()

    def test_correction_cleared_after_emission(self, qtbot):
        """Expected play time is cleared after correction is emitted."""
        from PyQt6.QtMultimedia import QMediaPlayer

        player = AudioPlayer()
        player._expected_play_time = time.monotonic() - 0.050

        with qtbot.waitSignal(player.audio_correction_ready, timeout=1000):
            player._on_playback_state(QMediaPlayer.PlaybackState.PlayingState)

        assert player._expected_play_time is None

    def test_no_sound_file_skips_expected_time(self, qtbot):
        """No expected time set when sound file is missing."""
        player = AudioPlayer()
        player._sound_file = ""

        player.start_countdown_playback(60.0)
        assert player._expected_play_time is None
