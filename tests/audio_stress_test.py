"""
Stress test for QMediaPlayer audio playback — with optional UI contention.

Runs N consecutive play cycles, monitoring for silent failures.
The --ui flag simulates the countdown window's startup work (widget tree,
stylesheets, drop shadows, animations, timers) to reproduce event-loop
contention that causes intermittent silent playback.

Usage:
    python tests/audio_stress_test.py --sound-file path.mp3 [OPTIONS]

Options:
    --cycles        Number of play/stop cycles (default: 50)
    --sound-file    Path to audio file (required)
    --backend       Qt media backend: darwin or ffmpeg (default: don't set, use Qt default)
    --fresh-player  Create new QMediaPlayer + QAudioOutput each cycle
    --ui            Create/destroy a heavyweight window each cycle (simulates countdown)
    --log-level     Logging level: DEBUG, INFO, WARNING (default: INFO)
"""

from __future__ import annotations

import argparse
import os
import sys
import time
import logging

# Parse args early so we can set backend before importing Qt
parser = argparse.ArgumentParser(description="Audio playback stress test")
parser.add_argument("--sound-file", required=True, help="Path to audio file")
parser.add_argument("--cycles", type=int, default=50, help="Number of cycles (default: 50)")
parser.add_argument("--backend", choices=["darwin", "ffmpeg"], default=None,
                    help="Qt media backend (default: Qt's default)")
parser.add_argument("--fresh-player", action="store_true",
                    help="Create new player objects each cycle")
parser.add_argument("--ui", action="store_true",
                    help="Simulate countdown window UI work each cycle")
parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING"], default="INFO",
                    help="Logging level (default: INFO)")
args = parser.parse_args()

if args.backend:
    os.environ["QT_MEDIA_BACKEND"] = args.backend

# Now safe to import Qt
from PyQt6.QtCore import (
    QEasingCurve,
    QPoint,
    QPropertyAnimation,
    QTimer,
    QUrl,
    Qt,
)
from PyQt6.QtGui import QColor, QFont, QPixmap
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtWidgets import (
    QApplication,
    QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

logging.basicConfig(level=getattr(logging, args.log_level),
                    format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Fake countdown window — replicates the expensive UI work the real window
# does during __init__, which all happens synchronously on the main thread
# before the event loop gets a chance to process the LoadedMedia callback.
# ---------------------------------------------------------------------------

class FakeCountdownWindow(QWidget):
    """Simulates the UI construction and animation of CountdownWindow."""

    def __init__(self) -> None:
        super().__init__(None, Qt.WindowType.FramelessWindowHint
                         | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(640, 320)
        self._anims: list[QPropertyAnimation] = []
        self._build_ui()
        self._position_and_show()
        self._start_animations()
        self._start_tick_timer()

    def _build_ui(self) -> None:
        """Replicate the real window's widget tree and stylesheet parsing."""
        # Container with gradient + border-radius (triggers style engine)
        self._container = QWidget(self)
        self._container.setGeometry(0, 0, 640, 320)
        self._container.setObjectName("container")
        self._container.setStyleSheet("""
            QWidget#container {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #0f0f1a, stop:0.5 #1a1a2e, stop:1 #16213e);
                border-radius: 14px;
                border: 1px solid rgba(255,255,255,20);
            }
        """)

        # Drop shadow (expensive compositing)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(60)
        shadow.setOffset(0, 25)
        shadow.setColor(QColor(0, 0, 0, 150))
        self._container.setGraphicsEffect(shadow)

        # Close button
        close_btn = QPushButton(self._container)
        close_btn.setFixedSize(14, 14)
        close_btn.move(14, 12)
        close_btn.setStyleSheet("""
            QPushButton { background: #ff5f57; border: none; border-radius: 7px; }
            QPushButton:hover { background: #e04840; }
        """)

        # Main layout with left (scroll) + right panes
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(24, 32, 24, 16)
        main_layout.setSpacing(20)

        # Left pane — scrollable with multiple styled labels
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical { width: 4px; background: transparent; }
            QScrollBar::handle:vertical {
                background: rgba(255,255,255,38); border-radius: 2px; min-height: 20px;
            }
        """)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 8, 0)
        left_layout.setSpacing(4)

        # Simulate meeting info labels (title, time, attendees)
        for text in [
            "Sprint Planning — Daily Standup",
            "10:00 AM — 10:30 AM",
            "alice@example.com, bob@example.com, carol@example.com",
            "Organizer: dave@example.com",
            "4 attendees — 2 external",
        ]:
            lbl = QLabel(text)
            lbl.setStyleSheet("color: #8888aa; font-size: 13px; background: transparent;")
            lbl.setWordWrap(True)
            left_layout.addWidget(lbl)

        # Join button
        join_btn = QPushButton("Join Meeting")
        join_btn.setFixedHeight(36)
        join_btn.setStyleSheet("""
            QPushButton {
                background: #10b981; color: white; border: none;
                border-radius: 8px; font-weight: 600; font-size: 13px;
            }
            QPushButton:hover { background: #059669; }
        """)
        left_layout.addWidget(join_btn)
        left_layout.addStretch()

        scroll.setWidget(left_widget)
        main_layout.addWidget(scroll, 1)

        # Right pane — countdown display
        right_pane = QWidget()
        right_layout = QVBoxLayout(right_pane)
        right_layout.setContentsMargins(0, 0, 0, 0)

        countdown_label = QLabel("47")
        countdown_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        countdown_label.setFont(QFont("Helvetica Neue", 96, QFont.Weight.Bold))
        countdown_label.setStyleSheet("color: white; background: transparent;")
        right_layout.addWidget(countdown_label)

        status_label = QLabel("Meeting starts in")
        status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_label.setStyleSheet("color: #8888aa; font-size: 13px; background: transparent;")
        right_layout.addWidget(status_label)

        # Mute button
        mute_btn = QPushButton("🔊")
        mute_btn.setFixedSize(32, 32)
        mute_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,10); border: none;
                border-radius: 16px; font-size: 16px;
            }
        """)
        right_layout.addWidget(mute_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        main_layout.addWidget(right_pane, 1)
        self._container.setLayout(main_layout)

        # Opacity effect on the whole window (used for fade-in)
        self._opacity = QGraphicsOpacityEffect(self)
        self._opacity.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity)

    def _position_and_show(self) -> None:
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = geo.right() - 640 - 20
            y = geo.top() + 20
        else:
            x, y = 100, 100
        self._final_pos = (x, y)
        # Start off-screen to the right (for slide-in)
        self.move(x + 660, y)
        self.show()

    def _start_animations(self) -> None:
        """Slide in + fade in, like the real countdown window."""
        # Slide animation
        slide = QPropertyAnimation(self, b"pos")
        slide.setDuration(300)
        slide.setStartValue(self.pos())
        slide.setEndValue(QPoint(*self._final_pos))
        slide.setEasingCurve(QEasingCurve.Type.OutCubic)
        slide.start()
        self._anims.append(slide)

        # Fade animation
        fade = QPropertyAnimation(self._opacity, b"opacity")
        fade.setDuration(300)
        fade.setStartValue(0.0)
        fade.setEndValue(1.0)
        fade.start()
        self._anims.append(fade)

    def _start_tick_timer(self) -> None:
        """1-second tick timer like the real countdown — forces periodic repaints."""
        self._tick_timer = QTimer(self)
        self._tick_timer.setInterval(1000)
        self._tick_timer.timeout.connect(self._tick)
        self._tick_timer.start()
        self._tick_count = 0

    def _tick(self) -> None:
        self._tick_count += 1
        # Force a style recalc + repaint (the real window changes colors at thresholds)
        labels = self.findChildren(QLabel)
        if labels:
            labels[0].setStyleSheet(
                f"color: {'#f59e0b' if self._tick_count % 2 else '#ffffff'}; "
                "font-size: 13px; background: transparent;"
            )

    def teardown(self) -> None:
        """Clean up before destruction."""
        if hasattr(self, '_tick_timer'):
            self._tick_timer.stop()
        for anim in self._anims:
            anim.stop()
        self._anims.clear()
        self.close()
        self.deleteLater()


# ---------------------------------------------------------------------------
# Stress tester
# ---------------------------------------------------------------------------

class AudioStressTester:
    """Exercises the same code path as AudioPlayer._ensure_source_and_play."""

    def __init__(self, sound_file: str, cycles: int, fresh_player: bool, with_ui: bool):
        self.sound_file = sound_file
        self.total_cycles = cycles
        self.fresh_player = fresh_player
        self.with_ui = with_ui
        self.current_cycle = 0
        self.successes = 0
        self.failures = 0
        self.results: list[tuple[int, str, int]] = []  # (cycle, "ok"|"SILENT", position_ms)

        self.player: QMediaPlayer | None = None
        self.audio_output: QAudioOutput | None = None
        self._window: FakeCountdownWindow | None = None
        self._create_player()

        self._play_on_load = False
        self._got_position_change = False

    def _create_player(self) -> None:
        """Create player objects, replicating AudioPlayer.__init__."""
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(1.0)

        self.player.mediaStatusChanged.connect(self._on_status)
        self.player.errorOccurred.connect(self._on_error)
        self.player.positionChanged.connect(self._on_position)
        self.player.playbackStateChanged.connect(self._on_playback_state)

    def _destroy_player(self) -> None:
        """Clean up player objects."""
        if self.player:
            self.player.stop()
            self.player.setSource(QUrl())
            self.player.setAudioOutput(None)
        if self.audio_output:
            self.audio_output.deleteLater()
        if self.player:
            self.player.deleteLater()
        self.player = None
        self.audio_output = None

    def run_next_cycle(self) -> None:
        if self.current_cycle >= self.total_cycles:
            self._cleanup_window()
            self._print_summary()
            QApplication.instance().quit()
            return

        self.current_cycle += 1
        self._got_position_change = False
        self._play_on_load = True

        log.info("=== CYCLE %d/%d ===", self.current_cycle, self.total_cycles)

        if self.fresh_player:
            self._destroy_player()
            self._create_player()

        # Tear down previous window
        self._cleanup_window()

        # Create the heavyweight UI *before* triggering audio — this is what
        # the real app does: CountdownWindow.__init__ builds UI, then calls
        # _start_countdown which triggers audio load+play.
        if self.with_ui:
            self._window = FakeCountdownWindow()

        # Replicate the exact _ensure_source_and_play code path
        self.player.setSource(QUrl())
        self.player.setSource(QUrl.fromLocalFile(self.sound_file))

        # After 3 seconds, check if audio actually played
        QTimer.singleShot(3000, self._check_and_stop)

    def _cleanup_window(self) -> None:
        if self._window:
            self._window.teardown()
            self._window = None

    def _on_status(self, status: QMediaPlayer.MediaStatus) -> None:
        log.debug("  MediaStatus: %s (play_on_load=%s)", status.name, self._play_on_load)
        if status == QMediaPlayer.MediaStatus.LoadedMedia:
            if self._play_on_load:
                self._play_on_load = False
                self.player.setPosition(0)
                self.player.play()
                log.info("  -> play() called")

    def _on_playback_state(self, state: QMediaPlayer.PlaybackState) -> None:
        log.debug("  PlaybackState: %s", state.name)

    def _on_position(self, pos_ms: int) -> None:
        if pos_ms > 0:
            self._got_position_change = True

    def _on_error(self, error: QMediaPlayer.Error, message: str) -> None:
        log.warning("  ERROR: %s — %s", error.name, message)

    def _check_and_stop(self) -> None:
        """After letting it play for 3s, check if position advanced."""
        pos = self.player.position()
        state = self.player.playbackState()
        status = self.player.mediaStatus()

        if self._got_position_change and pos > 100:
            log.info("  RESULT: OK (position=%dms, state=%s)", pos, state.name)
            self.successes += 1
            self.results.append((self.current_cycle, "ok", pos))
        else:
            log.warning(
                "  RESULT: *** SILENT *** (position=%dms, got_pos_change=%s, state=%s, status=%s)",
                pos, self._got_position_change, state.name, status.name,
            )
            self.failures += 1
            self.results.append((self.current_cycle, "SILENT", pos))

        self.player.stop()
        # 500ms pause between cycles
        QTimer.singleShot(500, self.run_next_cycle)

    def _print_summary(self) -> None:
        log.info("=" * 60)
        log.info("STRESS TEST COMPLETE: %d cycles", self.total_cycles)
        log.info("  Backend: %s", os.environ.get("QT_MEDIA_BACKEND", "(default/auto)"))
        log.info("  Fresh player each cycle: %s", self.fresh_player)
        log.info("  UI contention: %s", self.with_ui)
        log.info("  Successes: %d (%.0f%%)", self.successes,
                 100 * self.successes / self.total_cycles if self.total_cycles else 0)
        log.info("  Failures:  %d (%.0f%%)", self.failures,
                 100 * self.failures / self.total_cycles if self.total_cycles else 0)
        if self.failures:
            silent_cycles = [r[0] for r in self.results if r[1] == "SILENT"]
            log.info("  Silent cycles: %s", silent_cycles)
        log.info("=" * 60)


def main() -> None:
    log.info("Qt media backend env: %s", os.environ.get("QT_MEDIA_BACKEND", "(not set)"))
    log.info("Sound file: %s", args.sound_file)
    log.info("Cycles: %d", args.cycles)
    log.info("Fresh player: %s", args.fresh_player)
    log.info("UI contention: %s", args.ui)

    qapp = QApplication(sys.argv[:1])

    tester = AudioStressTester(args.sound_file, args.cycles, args.fresh_player, args.ui)

    # Start the first cycle after the event loop is running
    QTimer.singleShot(100, tester.run_next_cycle)

    qapp.exec()


if __name__ == "__main__":
    main()
