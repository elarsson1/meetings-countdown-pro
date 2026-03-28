"""Audio player — QMediaPlayer wrapper with countdown sync logic."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QUrl, pyqtSignal, QObject
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer

log = logging.getLogger(__name__)


class AudioPlayer(QObject):
    """Manages countdown audio playback with sync to countdown timing."""

    duration_detected = pyqtSignal(float)  # seconds

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._player = QMediaPlayer(self)
        self._audio_output = QAudioOutput(self)
        self._player.setAudioOutput(self._audio_output)

        self._player.mediaStatusChanged.connect(self._on_media_status)
        self._player.errorOccurred.connect(self._on_error)

        self._detected_duration: Optional[float] = None
        self._sound_file: str = ""
        self._play_on_load: bool = False
        self._pending_seek: int = 0
        self._preferred_device_id: str = ""

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def set_sound_file(self, path: str) -> None:
        """Load a new sound file for duration detection."""
        if path == self._sound_file and self._detected_duration is not None:
            return  # Same file already loaded with known duration
        self._sound_file = path
        self._detected_duration = None
        self._play_on_load = False  # Don't auto-play on detection
        if path and Path(path).is_file():
            self._player.setSource(QUrl.fromLocalFile(path))
        else:
            self._player.setSource(QUrl())

    def set_volume(self, percent: int) -> None:
        """Set volume 0–100."""
        self._audio_output.setVolume(max(0.0, min(1.0, percent / 100.0)))

    def set_muted(self, muted: bool) -> None:
        self._audio_output.setMuted(muted)

    @property
    def is_muted(self) -> bool:
        return self._audio_output.isMuted()

    def set_output_device(self, device_id: str) -> None:
        """Set audio output device by ID. Empty string = system default.

        The preference is stored so it can be re-applied when the device
        reconnects. If the device is unavailable at playback time,
        _resolve_output_device() falls back to system default.
        """
        self._preferred_device_id = device_id
        self._apply_output_device()

    def _apply_output_device(self) -> None:
        """Apply the preferred device if available, otherwise system default."""
        from PyQt6.QtMultimedia import QMediaDevices

        volume = self._audio_output.volume()
        muted = self._audio_output.isMuted()

        if self._preferred_device_id:
            for dev in QMediaDevices.audioOutputs():
                if dev.id().data().decode() == self._preferred_device_id:
                    self._audio_output = QAudioOutput(dev, self)
                    log.info("Audio output: %s", dev.description())
                    break
            else:
                log.info("Preferred audio device unavailable, falling back to system default")
                self._audio_output = QAudioOutput(self)
        else:
            self._audio_output = QAudioOutput(self)

        self._audio_output.setVolume(volume)
        self._audio_output.setMuted(muted)
        self._player.setAudioOutput(self._audio_output)

    @staticmethod
    def available_output_devices() -> list[dict[str, str]]:
        """Return list of available audio output devices."""
        from PyQt6.QtMultimedia import QMediaDevices

        devices = []
        for dev in QMediaDevices.audioOutputs():
            devices.append(
                {
                    "id": dev.id().data().decode(),
                    "name": dev.description(),
                }
            )
        return devices

    # ------------------------------------------------------------------
    # Playback
    # ------------------------------------------------------------------

    def start_countdown_playback(
        self,
        countdown_seconds: float,
        duration_override: Optional[float] = None,
    ) -> float:
        """Start audio synced to countdown. Returns delay before audio should start.

        Based on spec sync logic:
        - D > C: seek to D-C, play immediately
        - D == C: play from start
        - D < C: return delay = C-D (caller waits this long before calling play_now)
        """
        if not self._sound_file or not Path(self._sound_file).is_file():
            return 0.0

        duration = duration_override or self._detected_duration

        if not duration or duration <= 0:
            # Duration unknown — play from start, no sync
            self._pending_seek = 0
            self._ensure_source_and_play()
            return 0.0

        if duration >= countdown_seconds:
            # Audio is longer than or equal to countdown — seek into it
            self._pending_seek = int((duration - countdown_seconds) * 1000)
            self._ensure_source_and_play()
            return 0.0
        else:
            # Audio is shorter — delay playback
            self._pending_seek = 0
            delay = countdown_seconds - duration
            return delay

    def _ensure_source_and_play(self) -> None:
        """Set source if needed and play once media is loaded."""
        # Re-resolve audio device in case it was disconnected/reconnected
        self._apply_output_device()
        current_source = self._player.source().toLocalFile()
        if current_source == self._sound_file:
            # Source already loaded — seek and play directly
            if self._pending_seek:
                self._player.setPosition(self._pending_seek)
            else:
                self._player.setPosition(0)
            self._player.play()
        else:
            # Need to load source first — play will start in _on_media_status
            self._play_on_load = True
            self._player.setSource(QUrl.fromLocalFile(self._sound_file))

    def play_now(self) -> None:
        """Start playback from the beginning (used after a delay)."""
        if self._sound_file and Path(self._sound_file).is_file():
            self._pending_seek = 0
            self._ensure_source_and_play()

    def stop(self) -> None:
        self._player.stop()

    @property
    def detected_duration(self) -> Optional[float]:
        return self._detected_duration

    @property
    def is_playing(self) -> bool:
        return self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState

    # ------------------------------------------------------------------
    # Preview (for settings)
    # ------------------------------------------------------------------

    def preview(self, path: str, duration_ms: int = 10000) -> None:
        """Play first N ms of a file for preview in settings."""
        if path and Path(path).is_file():
            self._player.setSource(QUrl.fromLocalFile(path))
            self._player.setPosition(0)
            self._player.play()
            # Stop after duration_ms via a single-shot timer
            from PyQt6.QtCore import QTimer

            QTimer.singleShot(duration_ms, self.stop)

    # ------------------------------------------------------------------
    # Signals
    # ------------------------------------------------------------------

    def _on_media_status(self, status: QMediaPlayer.MediaStatus) -> None:
        if status == QMediaPlayer.MediaStatus.LoadedMedia:
            dur_ms = self._player.duration()
            if dur_ms > 0:
                self._detected_duration = dur_ms / 1000.0
                self.duration_detected.emit(self._detected_duration)
                log.info("Audio duration detected: %.1fs", self._detected_duration)

            # Deferred play after source load
            if self._play_on_load:
                self._play_on_load = False
                if self._pending_seek:
                    self._player.setPosition(self._pending_seek)
                self._player.play()
                log.info("Deferred playback started at position %dms", self._pending_seek)

    def _on_error(self, error: QMediaPlayer.Error, message: str) -> None:
        log.warning("Audio player error: %s — %s", error, message)
