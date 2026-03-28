"""Main application — menu bar presence, calendar polling, countdown scheduling."""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QAction, QActionGroup, QIcon
from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from meetings_countdown_pro.audio_player import AudioPlayer
from meetings_countdown_pro.calendar_service import CalendarService
from meetings_countdown_pro.countdown_window import CountdownWindow
from meetings_countdown_pro.favicon_cache import FaviconCache
from meetings_countdown_pro.meeting import Attendee, Meeting
from meetings_countdown_pro.notification_state import NotificationState
from meetings_countdown_pro.settings import Settings
from meetings_countdown_pro.settings_window import SettingsWindow

log = logging.getLogger(__name__)

ASSETS = Path(__file__).parent / "assets"
POLL_INTERVAL_MS = 30_000  # 30 seconds
MIN_COUNTDOWN_SECONDS = 5  # Skip countdown if less than this


class App:
    """Core application controller."""

    def __init__(self, qapp: QApplication) -> None:
        self._qapp = qapp
        self._settings = Settings.load()
        self._settings.validate()

        self._calendar = CalendarService()
        self._notified = NotificationState()
        self._notified.prune()

        self._audio = AudioPlayer()
        self._favicons = FaviconCache()

        self._countdown_window: Optional[CountdownWindow] = None
        self._settings_window: Optional[SettingsWindow] = None
        self._next_meeting: Optional[Meeting] = None
        self._trigger_timer: Optional[QTimer] = None

        # Apply initial audio settings
        self._apply_audio_settings()

        self._setup_tray()
        self._setup_polling()

        # Request calendar access
        self._calendar.request_access(self._on_calendar_access)

    # ------------------------------------------------------------------
    # System tray / menu bar
    # ------------------------------------------------------------------

    def _setup_tray(self) -> None:
        icon_path = ASSETS / "menubar_icon.svg"
        icon = QIcon(str(icon_path)) if icon_path.exists() else QIcon()
        self._tray = QSystemTrayIcon(icon, self._qapp)

        self._menu = QMenu()

        # Next meeting header
        self._next_meeting_action = QAction("No more meetings today", self._menu)
        self._next_meeting_action.setEnabled(False)
        self._menu.addAction(self._next_meeting_action)
        self._menu.addSeparator()

        # Mode radio group
        self._mode_group = QActionGroup(self._menu)
        self._mode_group.setExclusive(True)

        mode_labels = [
            ("countdown_music", "Countdown + Music"),
            ("silent", "Countdown (Silent)"),
            ("off", "Off"),
        ]
        self._mode_actions: dict[str, QAction] = {}
        for key, label in mode_labels:
            action = QAction(label, self._menu)
            action.setCheckable(True)
            action.setChecked(key == self._settings.mode)
            action.triggered.connect(lambda checked, k=key: self._set_mode(k))
            self._mode_group.addAction(action)
            self._menu.addAction(action)
            self._mode_actions[key] = action

        self._menu.addSeparator()

        # Settings
        settings_action = QAction("Settings...", self._menu)
        settings_action.triggered.connect(self._open_settings)
        self._menu.addAction(settings_action)

        self._menu.addSeparator()

        # Quit
        quit_action = QAction("Quit Meetings Countdown Pro", self._menu)
        quit_action.triggered.connect(self._qapp.quit)
        self._menu.addAction(quit_action)

        self._tray.setContextMenu(self._menu)
        self._tray.show()

    def _set_mode(self, mode: str) -> None:
        self._settings.mode = mode
        self._mode_actions[mode].setChecked(True)
        self._settings.save()

    def _update_next_meeting_display(self) -> None:
        if not self._calendar.is_authorized:
            self._next_meeting_action.setText(
                "\u26a0 Calendar access required"
            )
            return

        if not self._next_meeting:
            self._next_meeting_action.setText("No more meetings today")
            return

        m = self._next_meeting
        time_str = m.start.astimezone().strftime("%-I:%M %p")
        now = datetime.now(timezone.utc)
        delta = m.start - now
        minutes = int(delta.total_seconds() / 60)

        if minutes < 1:
            relative = "(now)"
        elif minutes < 60:
            relative = f"(in {minutes} min)"
        else:
            hours = minutes // 60
            mins = minutes % 60
            relative = f"(in {hours} hr{' ' + str(mins) + ' min' if mins else ''})"

        # Truncate title if needed
        title = m.title
        max_len = 28
        if len(title) > max_len:
            title = title[: max_len - 1] + "\u2026"

        self._next_meeting_action.setText(f"Next: {time_str} \u2014 {title} {relative}")

    # ------------------------------------------------------------------
    # Calendar polling & scheduling
    # ------------------------------------------------------------------

    def _setup_polling(self) -> None:
        self._poll_timer = QTimer()
        self._poll_timer.setInterval(POLL_INTERVAL_MS)
        self._poll_timer.timeout.connect(self._poll)
        self._poll_timer.start()

    def _on_calendar_access(self, granted: bool) -> None:
        if granted:
            log.info("Calendar access granted")
            self._poll()
        else:
            log.warning("Calendar access denied")
            self._update_next_meeting_display()

    def _poll(self) -> None:
        """Poll for upcoming meetings and schedule the next countdown."""
        if self._settings.mode == "off":
            self._next_meeting = None
            self._update_next_meeting_display()
            return

        meetings = self._calendar.fetch_upcoming(self._settings)
        if not meetings:
            self._next_meeting = None
            self._update_next_meeting_display()
            return

        # Find the next non-notified meeting
        now = datetime.now(timezone.utc)
        eligible: list[Meeting] = []
        for m in meetings:
            if self._notified.is_notified(m.notification_key):
                continue
            if m.start <= now + timedelta(seconds=MIN_COUNTDOWN_SECONDS):
                # Meeting already started or too close — mark as notified, skip
                self._notified.mark_notified(m.notification_key)
                continue
            eligible.append(m)

        if not eligible:
            self._next_meeting = None
            self._update_next_meeting_display()
            return

        # Group simultaneous meetings (same start time)
        primary = eligible[0]
        simultaneous = [m for m in eligible if m.start == primary.start]
        self._next_meeting = primary
        self._update_next_meeting_display()

        # Calculate trigger time
        trigger_time = primary.start - timedelta(seconds=self._settings.countdown_duration)
        delay_ms = int((trigger_time - now).total_seconds() * 1000)

        if delay_ms <= 0:
            # Late start — trigger immediately with reduced countdown
            self._trigger_countdown(simultaneous)
        else:
            # Schedule trigger
            if self._trigger_timer:
                self._trigger_timer.stop()
            self._trigger_timer = QTimer()
            self._trigger_timer.setSingleShot(True)
            self._trigger_timer.timeout.connect(lambda ms=simultaneous: self._trigger_countdown(ms))
            self._trigger_timer.start(delay_ms)

    def _trigger_countdown(self, meetings: list[Meeting]) -> None:
        """Open the countdown window for the given meeting(s)."""
        if self._countdown_window:
            return  # A countdown is already in progress — skip

        # Mark all as notified
        for m in meetings:
            self._notified.mark_notified(m.notification_key)

        # Check back-to-back status
        if self._calendar.is_meeting_in_progress(self._settings):
            b2b = self._settings.back_to_back
            if b2b == "skip":
                log.info("Skipping countdown (back-to-back: skip)")
                return
            elif b2b == "silent":
                # Temporarily override to silent for this countdown
                effective_mode = "silent"
            else:
                effective_mode = self._settings.mode
        else:
            effective_mode = self._settings.mode

        if effective_mode == "off":
            return

        # Create effective settings for this countdown
        countdown_settings = Settings(**{
            f.name: getattr(self._settings, f.name)
            for f in self._settings.__dataclass_fields__.values()
        })
        countdown_settings.mode = effective_mode

        # Audio setup
        if countdown_settings.mode == "countdown_music" and countdown_settings.sound_file:
            self._audio.set_sound_file(countdown_settings.sound_file)
            self._audio.set_volume(countdown_settings.volume)
            if countdown_settings.audio_output_device:
                self._audio.set_output_device(countdown_settings.audio_output_device)
        self._audio.set_muted(False)

        self._countdown_window = CountdownWindow(
            meetings=meetings,
            settings=countdown_settings,
            audio_player=self._audio,
            favicon_cache=self._favicons,
        )
        self._countdown_window.closed.connect(self._on_countdown_closed)
        self._countdown_window.show()

    def _on_countdown_closed(self) -> None:
        self._countdown_window = None
        # Trigger a fresh poll to pick up the next meeting
        self._poll()

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    def _open_settings(self) -> None:
        if self._settings_window and self._settings_window.isVisible():
            self._settings_window.raise_()
            self._settings_window.activateWindow()
            return

        calendars = self._calendar.get_calendars() if self._calendar.is_authorized else {}
        self._settings_window = SettingsWindow(
            settings=self._settings,
            audio_player=self._audio,
            calendars=calendars,
        )
        self._settings_window.settings_saved.connect(self._on_settings_saved)
        self._settings_window.test_countdown_requested.connect(self._run_test_countdown)
        self._settings_window.show()
        self._settings_window.raise_()
        self._settings_window.activateWindow()

    def _on_settings_saved(self, settings: Settings) -> None:
        self._settings = settings
        self._apply_audio_settings()
        self._update_launch_agent()
        # Update mode radio buttons
        for key, action in self._mode_actions.items():
            action.setChecked(key == settings.mode)
        self._poll()

    def _apply_audio_settings(self) -> None:
        if self._settings.sound_file:
            self._audio.set_sound_file(self._settings.sound_file)
        self._audio.set_volume(self._settings.volume)
        if self._settings.audio_output_device:
            self._audio.set_output_device(self._settings.audio_output_device)

    # ------------------------------------------------------------------
    # Test countdown
    # ------------------------------------------------------------------

    def _run_test_countdown(self, duration: int) -> None:
        """Launch a test countdown with mock data."""
        now = datetime.now(timezone.utc)
        target = now + timedelta(seconds=duration)

        mock_meetings = [
            Meeting(
                uid="test-meeting-001",
                title="Q1 Pipeline Review with Acme Corp",
                start=target,
                end=target + timedelta(minutes=30),
                calendar_name="Work",
                attendees=[
                    Attendee(email="alice@example.com", display_name="Alice Chen"),
                    Attendee(email="bob@example.com", display_name="Bob Martinez"),
                    Attendee(email="sarah@example.com", display_name="Sarah Kim"),
                    Attendee(email="carol@acme.com", display_name="Carol White"),
                    Attendee(email="dave@acme.com", display_name="Dave Johnson"),
                    Attendee(email="frank@acme.com", display_name="Frank Lee"),
                    Attendee(email="eve@globex.net", display_name="Eve Parker"),
                    Attendee(email="grace@globex.net", display_name="Grace Nakamura"),
                ],
                url="https://zoom.us/j/1234567890",
            )
        ]

        # Use internal domain "example.com" for test if none configured
        test_settings = Settings(**{
            f.name: getattr(self._settings, f.name)
            for f in self._settings.__dataclass_fields__.values()
        })
        if not test_settings.internal_domain:
            test_settings.internal_domain = "example.com"

        if test_settings.mode == "off":
            test_settings.mode = "countdown_music"

        if self._countdown_window:
            return  # A countdown is already in progress — close it first

        if test_settings.sound_file:
            self._audio.set_sound_file(test_settings.sound_file)
            self._audio.set_volume(test_settings.volume)
        self._audio.set_muted(False)

        self._countdown_window = CountdownWindow(
            meetings=mock_meetings,
            settings=test_settings,
            audio_player=self._audio,
            favicon_cache=self._favicons,
        )
        self._countdown_window.closed.connect(self._on_countdown_closed)
        self._countdown_window.show()

    # ------------------------------------------------------------------
    # Launch agent
    # ------------------------------------------------------------------

    def _update_launch_agent(self) -> None:
        plist_path = Path.home() / "Library/LaunchAgents/com.axeltech.meetingscountdownpro.plist"
        if self._settings.launch_at_login:
            exe = sys.executable
            script = str(Path(__file__).parent.parent / "main.py")
            plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.axeltech.meetingscountdownpro</string>
    <key>ProgramArguments</key>
    <array>
        <string>{exe}</string>
        <string>{script}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>
"""
            plist_path.parent.mkdir(parents=True, exist_ok=True)
            plist_path.write_text(plist_content)
            log.info("Launch agent installed: %s", plist_path)
        else:
            if plist_path.exists():
                plist_path.unlink()
                log.info("Launch agent removed")


def main() -> int:
    """Application entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    qapp = QApplication(sys.argv)
    qapp.setQuitOnLastWindowClosed(False)  # Keep running as menu bar app
    qapp.setApplicationName("Meetings Countdown Pro")

    app = App(qapp)
    return qapp.exec()
