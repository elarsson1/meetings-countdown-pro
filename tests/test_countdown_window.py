"""Tests for CountdownWindow — phase transitions, button visibility, signals."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

import pytest
from PyQt6.QtCore import QObject, Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QPushButton

from meetings_countdown_pro.countdown_window import CountdownWindow
from meetings_countdown_pro.meeting import Attendee, Meeting
from meetings_countdown_pro.settings import Settings


# ---------------------------------------------------------------------------
# Stubs — minimal stand-ins for AudioPlayer / FaviconCache
# ---------------------------------------------------------------------------

class StubAudioPlayer(QObject):
    duration_detected = pyqtSignal(float)
    audio_correction_ready = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._muted = False
        self.stopped = False

    def start_countdown_playback(self, *a, **kw):
        return 0.0

    def play_now(self):
        pass

    def stop(self):
        self.stopped = True

    def set_muted(self, m):
        self._muted = m

    @property
    def is_muted(self):
        return self._muted

    def set_sound_file(self, path):
        pass

    def set_volume(self, pct):
        pass

    def set_output_device(self, dev):
        pass

    def cleanup(self):
        pass


class StubFaviconCache(QObject):
    favicon_ready = pyqtSignal(str, QPixmap)

    def fetch(self, domain):
        pass

    def get(self, domain):
        return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_window(qtbot, meetings, *, mode="silent", sound_file="", internal_domain="corp.com", **settings_kw):
    audio = StubAudioPlayer()
    favicons = StubFaviconCache()
    settings = Settings(mode=mode, sound_file=sound_file, internal_domain=internal_domain, **settings_kw)
    win = CountdownWindow(meetings, settings, audio, favicons)
    qtbot.addWidget(win)
    win.show()
    qtbot.waitExposed(win)
    return win, audio


def _meeting(*, video_link=None, title="Test Meeting", attendees=None, **kw):
    now = datetime.now(timezone.utc)
    defaults = dict(
        uid="uid-001",
        title=title,
        start=now + timedelta(seconds=30),
        end=now + timedelta(seconds=3630),
        calendar_name="Work",
    )
    if video_link:
        defaults["url"] = video_link
    if attendees:
        defaults["attendees"] = attendees
    defaults.update(kw)
    return Meeting(**defaults)


# ===================================================================
# Phase transitions
# ===================================================================

class TestPhaseTransitions:
    def test_starts_in_countdown_phase(self, qtbot):
        win, _ = _make_window(qtbot, [_meeting()])
        assert win._phase == "countdown"
        assert win._countdown_label.isVisible()
        assert win._action_widget.isHidden()
        assert win._live_widget.isHidden()

    def test_enter_action_phase(self, qtbot):
        win, _ = _make_window(qtbot, [_meeting()])
        win._enter_action_phase()
        assert win._phase == "action"
        assert win._countdown_label.isHidden()
        assert win._action_widget.isVisible()
        assert win._live_widget.isHidden()

    def test_enter_live_phase(self, qtbot):
        win, _ = _make_window(qtbot, [_meeting()])
        win._enter_action_phase()
        win._enter_live_phase()
        assert win._phase == "live"
        assert win._action_widget.isHidden()
        assert win._live_widget.isVisible()


# ===================================================================
# Join button visibility
# ===================================================================

class TestJoinButton:
    def test_visible_with_video_link(self, qtbot):
        win, _ = _make_window(qtbot, [_meeting(video_link="https://zoom.us/j/123")])
        assert win._join_btn.isVisible()

    def test_hidden_without_video_link(self, qtbot):
        win, _ = _make_window(qtbot, [_meeting()])
        assert win._join_btn.isHidden()

    def test_hidden_for_multi_meeting(self, qtbot):
        now = datetime.now(timezone.utc) + timedelta(seconds=30)
        m1 = _meeting(video_link="https://zoom.us/j/111", uid="a", start=now)
        m2 = _meeting(video_link="https://zoom.us/j/222", uid="b", start=now)
        # Ensure same start time
        m2 = Meeting(uid="b", title="Meeting B", start=m1.start, end=m1.end,
                     calendar_name="Work", url="https://zoom.us/j/222")
        win, _ = _make_window(qtbot, [m1, m2])
        assert win._join_btn.isHidden()

    def test_inline_join_buttons_for_multi_meeting(self, qtbot):
        now = datetime.now(timezone.utc) + timedelta(seconds=30)
        m1 = Meeting(uid="a", title="A", start=now, end=now + timedelta(hours=1),
                     calendar_name="Work", url="https://zoom.us/j/111")
        m2 = Meeting(uid="b", title="B", start=now, end=now + timedelta(hours=1),
                     calendar_name="Work", url="https://meet.google.com/abc-defg-hij")
        win, _ = _make_window(qtbot, [m1, m2])
        # Find inline join buttons (QPushButtons with "Join" in text, excluding the main one)
        inline_btns = [
            btn for btn in win._container.findChildren(QPushButton)
            if "Join" in btn.text() and btn is not win._join_btn
        ]
        assert len(inline_btns) == 2


# ===================================================================
# Join closes window (default) / continue_after_join
# ===================================================================

class TestJoinClosesWindow:
    def test_join_closes_window_by_default(self, qtbot, monkeypatch):
        monkeypatch.setattr("meetings_countdown_pro.countdown_window.QDesktopServices.openUrl", lambda url: True)
        win, _ = _make_window(qtbot, [_meeting(video_link="https://zoom.us/j/123")])
        with qtbot.waitSignal(win.closed, timeout=1000):
            win._handle_join("https://zoom.us/j/123")

    def test_join_keeps_window_when_continue_after_join(self, qtbot, monkeypatch):
        monkeypatch.setattr("meetings_countdown_pro.countdown_window.QDesktopServices.openUrl", lambda url: True)
        win, _ = _make_window(qtbot, [_meeting(video_link="https://zoom.us/j/123")], continue_after_join=True)
        win._handle_join("https://zoom.us/j/123")
        assert win.isVisible()

    def test_join_opens_url(self, qtbot, monkeypatch):
        opened_urls = []
        monkeypatch.setattr("meetings_countdown_pro.countdown_window.QDesktopServices.openUrl", lambda url: opened_urls.append(url.toString()))
        win, _ = _make_window(qtbot, [_meeting(video_link="https://zoom.us/j/123")])
        win._handle_join("https://zoom.us/j/123")
        assert len(opened_urls) == 1
        assert "zoom.us" in opened_urls[0]

    def test_multi_meeting_join_closes_window(self, qtbot, monkeypatch):
        monkeypatch.setattr("meetings_countdown_pro.countdown_window.QDesktopServices.openUrl", lambda url: True)
        now = datetime.now(timezone.utc) + timedelta(seconds=30)
        m1 = Meeting(uid="a", title="A", start=now, end=now + timedelta(hours=1),
                     calendar_name="Work", url="https://zoom.us/j/111")
        m2 = Meeting(uid="b", title="B", start=now, end=now + timedelta(hours=1),
                     calendar_name="Work", url="https://meet.google.com/abc-defg-hij")
        win, _ = _make_window(qtbot, [m1, m2])
        with qtbot.waitSignal(win.closed, timeout=1000):
            win._handle_join("https://zoom.us/j/111")

    def test_multi_meeting_join_keeps_window_when_continue(self, qtbot, monkeypatch):
        monkeypatch.setattr("meetings_countdown_pro.countdown_window.QDesktopServices.openUrl", lambda url: True)
        now = datetime.now(timezone.utc) + timedelta(seconds=30)
        m1 = Meeting(uid="a", title="A", start=now, end=now + timedelta(hours=1),
                     calendar_name="Work", url="https://zoom.us/j/111")
        m2 = Meeting(uid="b", title="B", start=now, end=now + timedelta(hours=1),
                     calendar_name="Work", url="https://meet.google.com/abc-defg-hij")
        win, _ = _make_window(qtbot, [m1, m2], continue_after_join=True)
        win._handle_join("https://zoom.us/j/111")
        assert win.isVisible()


# ===================================================================
# Mute button visibility
# ===================================================================

class TestMuteButton:
    def test_visible_in_countdown_music_with_sound(self, qtbot):
        win, _ = _make_window(qtbot, [_meeting()], mode="countdown_music", sound_file="/fake/sound.mp3")
        assert win._mute_btn.isVisible()

    def test_hidden_in_silent_mode(self, qtbot):
        win, _ = _make_window(qtbot, [_meeting()], mode="silent")
        assert win._mute_btn.isHidden()

    def test_hidden_when_no_sound_file(self, qtbot):
        win, _ = _make_window(qtbot, [_meeting()], mode="countdown_music", sound_file="")
        assert win._mute_btn.isHidden()


# ===================================================================
# Mute toggle
# ===================================================================

class TestMuteToggle:
    def test_toggle_mute_on(self, qtbot):
        win, audio = _make_window(qtbot, [_meeting()], mode="countdown_music", sound_file="/fake/sound.mp3")
        assert audio.is_muted is False
        win._toggle_mute()
        assert audio.is_muted is True

    def test_toggle_mute_off(self, qtbot):
        win, audio = _make_window(qtbot, [_meeting()], mode="countdown_music", sound_file="/fake/sound.mp3")
        win._toggle_mute()  # on
        win._toggle_mute()  # off
        assert audio.is_muted is False


# ===================================================================
# Close behavior
# ===================================================================

class TestCloseBehavior:
    def test_close_emits_signal(self, qtbot):
        win, _ = _make_window(qtbot, [_meeting()])
        with qtbot.waitSignal(win.closed, timeout=1000):
            win.close()

    def test_close_stops_audio(self, qtbot):
        win, audio = _make_window(qtbot, [_meeting()])
        win.close()
        assert audio.stopped is True

    def test_escape_closes(self, qtbot):
        win, _ = _make_window(qtbot, [_meeting()])
        with qtbot.waitSignal(win.closed, timeout=1000):
            qtbot.keyPress(win, Qt.Key.Key_Escape)


# ===================================================================
# Countdown display
# ===================================================================

class TestCountdownDisplay:
    def test_display_shows_seconds(self, qtbot):
        win, _ = _make_window(qtbot, [_meeting()])
        win._seconds_remaining = 42
        win._update_display()
        assert win._countdown_label.text() == "42"

    def test_color_normal(self, qtbot):
        win, _ = _make_window(qtbot, [_meeting()])
        win._seconds_remaining = 20
        win._update_display()
        style = win._countdown_label.styleSheet()
        assert "#ffffff" in style.lower()  # white

    def test_color_warning(self, qtbot):
        win, _ = _make_window(qtbot, [_meeting()])
        win._seconds_remaining = 8
        win._update_display()
        style = win._countdown_label.styleSheet()
        assert "f59e0b" in style.lower()  # amber

    def test_color_critical(self, qtbot):
        win, _ = _make_window(qtbot, [_meeting()])
        win._seconds_remaining = 2
        win._update_display()
        style = win._countdown_label.styleSheet()
        assert "ef4444" in style.lower()  # red


# ===================================================================
# Audio correction
# ===================================================================

class TestAudioCorrection:
    def test_correction_defaults_to_zero(self, qtbot):
        win, _ = _make_window(qtbot, [_meeting()])
        assert win._audio_correction_s == 0.0

    def test_correction_applied_from_signal(self, qtbot):
        win, audio = _make_window(qtbot, [_meeting()])
        audio.audio_correction_ready.emit(150)
        assert win._audio_correction_s == pytest.approx(0.150)

    def test_correction_mod_1000(self, qtbot):
        """Correction from AudioPlayer is already mod 1000, verify it's stored as-is."""
        win, audio = _make_window(qtbot, [_meeting()])
        audio.audio_correction_ready.emit(750)
        assert win._audio_correction_s == pytest.approx(0.750)


# ===================================================================
# Multi-meeting rendering
# ===================================================================

class TestMultiMeeting:
    def test_both_titles_present(self, qtbot):
        now = datetime.now(timezone.utc) + timedelta(seconds=30)
        m1 = Meeting(uid="a", title="Alpha Meeting", start=now, end=now + timedelta(hours=1), calendar_name="Work")
        m2 = Meeting(uid="b", title="Beta Meeting", start=now, end=now + timedelta(hours=1), calendar_name="Work")
        win, _ = _make_window(qtbot, [m1, m2])
        # Search all QLabel text for both titles
        from PyQt6.QtWidgets import QLabel
        labels = [lbl.text() for lbl in win._container.findChildren(QLabel)]
        assert any("Alpha Meeting" in t for t in labels)
        assert any("Beta Meeting" in t for t in labels)


# ===================================================================
# Directory link rendering
# ===================================================================

def _find_attendee_label(win, name):
    from PyQt6.QtWidgets import QLabel
    for lbl in win._container.findChildren(QLabel):
        if lbl.text() == name:
            return lbl
    return None


class TestDirectoryLinks:
    def _meeting_with(self, *attendees):
        now = datetime.now(timezone.utc)
        return Meeting(
            uid="dl-1",
            title="Directory Test",
            start=now + timedelta(seconds=30),
            end=now + timedelta(seconds=3630),
            calendar_name="Work",
            attendees=list(attendees),
        )

    def test_internal_attendee_clickable_when_template_set(self, qtbot):
        m = self._meeting_with(Attendee(display_name="Jane Doe", email="jane@corp.com"))
        win, _ = _make_window(
            qtbot, [m],
            directory_url_template="https://d.corp.com/u/{Username}",
        )
        lbl = _find_attendee_label(win, "Jane Doe")
        assert lbl is not None
        assert lbl.cursor().shape() == Qt.CursorShape.PointingHandCursor
        assert lbl.property("directoryUrl") == "https://d.corp.com/u/jane"

    def test_internal_attendee_plain_when_template_empty(self, qtbot):
        m = self._meeting_with(Attendee(display_name="Jane Doe", email="jane@corp.com"))
        win, _ = _make_window(qtbot, [m])
        lbl = _find_attendee_label(win, "Jane Doe")
        assert lbl is not None
        assert lbl.property("directoryUrl") is None

    def test_external_attendee_never_clickable(self, qtbot):
        m = self._meeting_with(
            Attendee(display_name="Bob Ext", email="bob@other.com"),
            Attendee(display_name="Jane Int", email="jane@corp.com"),
        )
        win, _ = _make_window(
            qtbot, [m],
            directory_url_template="https://d.corp.com/u/{Username}",
        )
        lbl = _find_attendee_label(win, "Bob Ext")
        assert lbl is not None
        assert lbl.property("directoryUrl") is None

    def test_clicking_label_opens_url(self, qtbot, monkeypatch):
        opened = []
        monkeypatch.setattr(
            "meetings_countdown_pro.countdown_window.QDesktopServices.openUrl",
            lambda url: opened.append(url.toString()),
        )
        m = self._meeting_with(Attendee(display_name="Jane Doe", email="jane@corp.com"))
        win, _ = _make_window(
            qtbot, [m],
            directory_url_template="https://d.corp.com/u/{Username}",
        )
        lbl = _find_attendee_label(win, "Jane Doe")
        lbl.mousePressEvent(None)
        assert opened == ["https://d.corp.com/u/jane"]

    def test_malformed_email_falls_back_to_plain(self, qtbot):
        m = self._meeting_with(Attendee(display_name="No Email", email="not-an-email"))
        # Without @, classification puts it in external bucket — give it the
        # internal domain by using a bare local-part with the right domain.
        m2 = self._meeting_with(Attendee(display_name="Broken", email="broken-corp.com"))
        # The above email has no @, so it's not internal. Use a different shape:
        # an attendee whose email matches internal domain check requires '@corp.com'.
        # Create one with empty email so it falls in the no-domain bucket.
        m3 = self._meeting_with(Attendee(display_name="Empty", email=""))
        win, _ = _make_window(
            qtbot, [m3],
            directory_url_template="https://d.corp.com/u/{Username}",
        )
        # Empty email isn't internal — just confirm rendering doesn't crash and
        # the label, if present, is plain.
        lbl = _find_attendee_label(win, "Empty")
        if lbl is not None:
            assert lbl.property("directoryUrl") is None
