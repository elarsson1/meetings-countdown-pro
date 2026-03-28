"""Countdown window — the main broadcast-style countdown UI."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    QRect,
    QPoint,
    QSize,
    Qt,
    QTimer,
    QUrl,
    pyqtProperty,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QColor,
    QDesktopServices,
    QFont,
    QIcon,
    QPainter,
    QPainterPath,
    QPixmap,
    QPolygon,
)
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

from meetings_countdown_pro.audio_player import AudioPlayer
from meetings_countdown_pro.favicon_cache import FaviconCache
from meetings_countdown_pro.meeting import Meeting
from meetings_countdown_pro.settings import Settings

ASSETS = Path(__file__).parent / "assets"

# Colors from mockups
COLOR_BG_START = QColor(15, 15, 26)
COLOR_BG_MID = QColor(26, 26, 46)
COLOR_BG_END = QColor(22, 33, 62)
COLOR_TEXT = QColor(255, 255, 255)
COLOR_MUTED_TEXT = QColor(136, 136, 170)
COLOR_DIM_TEXT = QColor(106, 106, 138)
COLOR_INTERNAL_ACCENT = QColor(90, 122, 255)
COLOR_EXTERNAL_ACCENT = QColor(139, 92, 246)
COLOR_JOIN_GREEN = QColor(16, 185, 129)
COLOR_WARNING = QColor(245, 158, 11)
COLOR_CRITICAL = QColor(239, 68, 68)
COLOR_ACTION = QColor(245, 158, 11)

WINDOW_W, WINDOW_H = 640, 320
SCREEN_INSET = 20


class ClapperboardWidget(QWidget):
    """Draws a movie clapperboard/slate graphic with an animated clap."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedSize(110, 90)
        self._clap_angle = -30.0  # Start in the open position
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._anim: Optional[QPropertyAnimation] = None

    def start_animation(self) -> None:
        """Start the clap animation. Call when the widget becomes visible."""
        self._anim = QPropertyAnimation(self, b"clapAngle")
        self._anim.setDuration(600)
        self._anim.setStartValue(-30.0)
        self._anim.setKeyValueAt(0.4, 0.0)
        self._anim.setEndValue(0.0)
        self._anim.setEasingCurve(QEasingCurve.Type.OutBounce)
        self._anim.start()

    @pyqtProperty(float)
    def clapAngle(self) -> float:
        return self._clap_angle

    @clapAngle.setter
    def clapAngle(self, value: float) -> None:
        self._clap_angle = value
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        body_h = 55
        top_h = 22
        body_y = h - body_h
        stripe_w = 14

        # --- Body (slate) ---
        p.setPen(QColor(255, 255, 255))
        p.setBrush(QColor(26, 26, 46))
        body_rect = QRect(5, body_y, w - 10, body_h)
        p.drawRoundedRect(body_rect, 4, 4)

        # Body text
        p.setPen(QColor(136, 136, 170))
        text_font = QFont("Helvetica Neue", 8)
        text_font.setWeight(QFont.Weight.Medium)
        text_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1)
        p.setFont(text_font)
        p.drawText(body_rect, Qt.AlignmentFlag.AlignCenter, "SCENE 1 \u00b7 TAKE 1")

        # --- Top bar (striped, animated) ---
        p.save()
        # Pivot at bottom-left of the top bar
        pivot_x = 8
        pivot_y = body_y + 2
        p.translate(pivot_x, pivot_y)
        p.rotate(self._clap_angle)

        bar_w = w - 16
        bar_rect = QRect(0, -top_h, bar_w, top_h)

        # Clip to rounded rect
        clip_path = QPainterPath()
        clip_path.addRoundedRect(0, -top_h, bar_w, top_h, 3, 3)
        p.setClipPath(clip_path)

        # Draw alternating diagonal stripes
        p.setPen(Qt.PenStyle.NoPen)
        for i in range(-4, bar_w // stripe_w + 6):
            x = i * stripe_w
            if i % 2 == 0:
                p.setBrush(QColor(255, 255, 255))
            else:
                p.setBrush(QColor(26, 26, 46))
            points = [
                (x, -top_h),
                (x + stripe_w, -top_h),
                (x + stripe_w - 8, 0),
                (x - 8, 0),
            ]
            poly = QPolygon([QPoint(int(px), int(py)) for px, py in points])
            p.drawPolygon(poly)

        p.setClipping(False)

        # Hinge dot
        p.setBrush(QColor(100, 100, 100))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(-2, -3, 7, 7)

        p.restore()


class CountdownWindow(QWidget):
    """Frameless floating countdown window."""

    closed = pyqtSignal()

    def __init__(
        self,
        meetings: list[Meeting],
        settings: Settings,
        audio_player: AudioPlayer,
        favicon_cache: FaviconCache,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._meetings = meetings
        self._settings = settings
        self._audio = audio_player
        self._favicons = favicon_cache
        self._target_time = meetings[0].start
        self._is_multi = len(meetings) > 1

        # State
        self._seconds_remaining = 0
        self._phase = "countdown"  # countdown | action | live

        # Window setup
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(WINDOW_W, WINDOW_H)

        self._build_ui()
        self._position_window()
        self._start_countdown()
        self._slide_in()

        # Connect favicon updates
        self._favicons.favicon_ready.connect(self._on_favicon_ready)

        # Request favicons for external domains
        for meeting in meetings:
            _, ext = meeting.classify_attendees(settings.internal_domain)
            for domain in ext:
                self._favicons.fetch(domain)

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        # Main container with rounded corners
        self._container = QWidget(self)
        self._container.setGeometry(0, 0, WINDOW_W, WINDOW_H)
        self._container.setStyleSheet(
            f"""
            QWidget#container {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {COLOR_BG_START.name()},
                    stop:0.5 {COLOR_BG_MID.name()},
                    stop:1 {COLOR_BG_END.name()});
                border-radius: 14px;
                border: 1px solid rgba(255,255,255,20);
            }}
            """
        )
        self._container.setObjectName("container")

        # Drop shadow on the window
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(60)
        shadow.setOffset(0, 25)
        shadow.setColor(QColor(0, 0, 0, 150))
        self._container.setGraphicsEffect(shadow)

        # Close button
        self._close_btn = QPushButton(self._container)
        self._close_btn.setFixedSize(14, 14)
        self._close_btn.move(14, 12)
        self._close_btn.setStyleSheet(
            """
            QPushButton {
                background: #ff5f57;
                border: none;
                border-radius: 7px;
            }
            QPushButton:hover {
                background: #e04840;
            }
            """
        )
        self._close_btn.clicked.connect(self.close)
        self._close_btn.setCursor(Qt.CursorShape.PointingHandCursor)

        # Main layout: left pane + right pane
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(24, 32, 24, 16)
        main_layout.setSpacing(20)

        # Left pane — scrollable meeting info
        self._left_scroll = QScrollArea()
        self._left_scroll.setWidgetResizable(True)
        self._left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._left_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._left_scroll.setStyleSheet(
            """
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                width: 4px;
                background: transparent;
            }
            QScrollBar::handle:vertical {
                background: rgba(255,255,255,38);
                border-radius: 2px;
                min-height: 20px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            """
        )

        left_widget = QWidget()
        left_widget.setStyleSheet("background: transparent;")
        self._left_layout = QVBoxLayout(left_widget)
        self._left_layout.setContentsMargins(0, 0, 8, 0)
        self._left_layout.setSpacing(0)
        self._left_scroll.setWidget(left_widget)
        main_layout.addWidget(self._left_scroll, 1)

        # Right pane — countdown + controls
        right_pane = QWidget()
        right_pane.setFixedWidth(200)
        right_pane.setStyleSheet("background: transparent;")
        self._right_layout = QVBoxLayout(right_pane)
        self._right_layout.setContentsMargins(0, 0, 0, 0)
        self._right_layout.setSpacing(16)
        main_layout.addWidget(right_pane)

        # Countdown number
        self._countdown_label = QLabel("0")
        self._countdown_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont("Helvetica Neue", 96)
        font.setWeight(QFont.Weight.Black)
        self._countdown_label.setFont(font)
        self._countdown_label.setStyleSheet(f"color: {COLOR_TEXT.name()}; background: transparent;")
        self._right_layout.addWidget(self._countdown_label, 1)

        # Action display (hidden initially) — clapperboard + ACTION! text
        self._action_widget = QWidget()
        self._action_widget.setStyleSheet("background: transparent;")
        action_layout = QVBoxLayout(self._action_widget)
        action_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        action_layout.setSpacing(12)

        self._clapperboard = ClapperboardWidget()
        action_layout.addWidget(self._clapperboard, alignment=Qt.AlignmentFlag.AlignCenter)

        self._action_text = QLabel("ACTION!")
        action_font = QFont("Helvetica Neue", 28)
        action_font.setWeight(QFont.Weight.Black)
        self._action_text.setFont(action_font)
        self._action_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._action_text.setStyleSheet(f"color: {COLOR_ACTION.name()}; background: transparent; letter-spacing: 4px;")
        action_layout.addWidget(self._action_text)
        self._action_widget.hide()
        self._right_layout.addWidget(self._action_widget, 1)

        # LIVE display (hidden initially)
        self._live_widget = QWidget()
        self._live_widget.setStyleSheet("background: transparent;")
        live_layout = QVBoxLayout(self._live_widget)
        live_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        live_badge = QWidget()
        live_badge.setFixedSize(160, 52)
        live_badge.setStyleSheet(
            """
            background: rgba(239,68,68,38);
            border: 2px solid #ef4444;
            border-radius: 10px;
            """
        )
        badge_layout = QHBoxLayout(live_badge)
        badge_layout.setSpacing(10)
        badge_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._live_dot = QLabel()
        self._live_dot.setFixedSize(14, 14)
        self._live_dot.setStyleSheet(
            """
            background: #ef4444;
            border-radius: 7px;
            """
        )
        badge_layout.addWidget(self._live_dot)

        live_text = QLabel("LIVE")
        live_font = QFont("Helvetica Neue", 36)
        live_font.setWeight(QFont.Weight.Black)
        live_text.setFont(live_font)
        live_text.setStyleSheet("color: #ef4444; background: transparent; letter-spacing: 6px;")
        badge_layout.addWidget(live_text)

        live_layout.addWidget(live_badge, alignment=Qt.AlignmentFlag.AlignCenter)
        self._live_widget.hide()
        self._right_layout.addWidget(self._live_widget, 1)

        # Join Now button (right side — hidden for multi-meeting)
        self._join_btn = QPushButton("Join Now")
        self._join_btn.setFixedHeight(38)
        self._join_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._join_btn.setStyleSheet(
            """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #10b981, stop:1 #059669);
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
                letter-spacing: 0.5px;
                padding: 0 16px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #34d399, stop:1 #10b981);
            }
            """
        )
        self._right_layout.addWidget(self._join_btn)

        # Wire join button
        video_link = self._meetings[0].video_link if not self._is_multi else None
        if video_link:
            self._join_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(video_link)))
        else:
            self._join_btn.hide()
        if self._is_multi:
            self._join_btn.hide()

        # Mute button
        self._mute_btn = QPushButton()
        self._mute_btn.setFixedSize(28, 28)
        self._mute_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._mute_btn.setStyleSheet(
            """
            QPushButton {
                background: transparent;
                border: none;
                color: #b0b0c8;
                font-size: 18px;
            }
            QPushButton:hover { color: #ddd; }
            """
        )
        self._update_mute_icon()
        self._mute_btn.clicked.connect(self._toggle_mute)
        mute_row = QHBoxLayout()
        mute_row.addStretch()
        mute_row.addWidget(self._mute_btn)
        self._right_layout.addLayout(mute_row)

        # Hide mute in silent mode or no sound file
        show_mute = (
            self._settings.mode == "countdown_music"
            and bool(self._settings.sound_file)
        )
        self._mute_btn.setVisible(show_mute)

        self._container.setLayout(main_layout)

        # Populate left pane
        self._populate_meetings()

    def _populate_meetings(self) -> None:
        """Fill the left pane with meeting details."""
        for i, meeting in enumerate(self._meetings):
            if i > 0:
                # Separator between meetings
                sep = QWidget()
                sep.setFixedHeight(1)
                sep.setStyleSheet("background: rgba(255,255,255,20); margin: 16px 0;")
                self._left_layout.addSpacing(16)
                self._left_layout.addWidget(sep)
                self._left_layout.addSpacing(16)

            # Subject
            subject = QLabel(meeting.title)
            subject.setFont(self._make_font(18, QFont.Weight.Bold))
            subject.setStyleSheet(f"color: {COLOR_TEXT.name()}; background: transparent;")
            subject.setWordWrap(True)
            self._left_layout.addWidget(subject)

            # Time
            time_str = f"{meeting.start.astimezone().strftime('%-I:%M %p')} – {meeting.end.astimezone().strftime('%-I:%M %p')}"
            time_label = QLabel(time_str)
            time_label.setFont(self._make_font(13))
            time_label.setStyleSheet(f"color: {COLOR_MUTED_TEXT.name()}; background: transparent;")
            self._left_layout.addWidget(time_label)
            self._left_layout.addSpacing(2)

            # Attendee summary
            summary = meeting.attendee_summary(self._settings.internal_domain)
            summary_label = QLabel(summary)
            summary_label.setFont(self._make_font(12))
            summary_label.setStyleSheet(f"color: {COLOR_DIM_TEXT.name()}; background: transparent;")
            self._left_layout.addWidget(summary_label)
            self._left_layout.addSpacing(12)

            # Attendees
            if self._settings.internal_domain:
                internal, external = meeting.classify_attendees(self._settings.internal_domain)
                if internal:
                    self._add_section_header("Internal", COLOR_INTERNAL_ACCENT)
                    for att in internal:
                        self._add_attendee(att.effective_name, COLOR_INTERNAL_ACCENT)

                if external:
                    self._add_section_header("External", COLOR_EXTERNAL_ACCENT, top_margin=10)
                    for domain, atts in external.items():
                        self._add_domain_header(domain)
                        for att in atts:
                            self._add_attendee(att.effective_name, COLOR_EXTERNAL_ACCENT, indent=20)
            else:
                # No domain configured — flat list
                if meeting.attendees:
                    self._add_section_header("Attendees", COLOR_MUTED_TEXT)
                    for att in sorted(meeting.attendees, key=lambda a: a.effective_name.lower()):
                        self._add_attendee(att.effective_name, COLOR_MUTED_TEXT)

            # Inline Join button for multi-meeting
            if self._is_multi and meeting.video_link:
                self._left_layout.addSpacing(8)
                link = meeting.video_link
                # Determine label from URL
                if "zoom.us" in link:
                    btn_text = "\u25b6 Join Zoom Meeting"
                elif "meet.google.com" in link:
                    btn_text = "\u25b6 Join Google Meet"
                elif "teams.microsoft.com" in link:
                    btn_text = "\u25b6 Join Teams Meeting"
                else:
                    btn_text = "\u25b6 Join Meeting"
                join_btn = QPushButton(btn_text)
                join_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                join_btn.setStyleSheet(
                    """
                    QPushButton {
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #10b981, stop:1 #059669);
                        color: white;
                        border: none;
                        border-radius: 6px;
                        font-size: 12px;
                        font-weight: bold;
                        padding: 5px 12px;
                    }
                    QPushButton:hover {
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #34d399, stop:1 #10b981);
                    }
                    """
                )
                join_btn.setFixedWidth(180)
                join_btn.clicked.connect(lambda _, url=link: QDesktopServices.openUrl(QUrl(url)))
                self._left_layout.addWidget(join_btn)

        self._left_layout.addStretch()

    def _add_section_header(self, text: str, color: QColor, top_margin: int = 0) -> None:
        if top_margin:
            self._left_layout.addSpacing(top_margin)
        label = QLabel(text.upper())
        font = self._make_font(10, QFont.Weight.Bold)
        label.setFont(font)
        label.setStyleSheet(f"color: {color.name()}; background: transparent; letter-spacing: 1.5px;")
        self._left_layout.addWidget(label)
        self._left_layout.addSpacing(4)

    def _add_attendee(self, name: str, dot_color: QColor, indent: int = 0) -> None:
        row = QHBoxLayout()
        row.setContentsMargins(indent, 0, 0, 0)
        row.setSpacing(6)

        dot = QLabel()
        dot.setFixedSize(4, 4)
        dot.setStyleSheet(
            f"background: {dot_color.name()}; border-radius: 2px; margin-top: 6px;"
        )
        row.addWidget(dot, alignment=Qt.AlignmentFlag.AlignTop)

        label = QLabel(name)
        label.setFont(self._make_font(13))
        label.setStyleSheet("color: #c8c8e0; background: transparent;")
        row.addWidget(label, 1)

        wrapper = QWidget()
        wrapper.setStyleSheet("background: transparent;")
        wrapper.setLayout(row)
        self._left_layout.addWidget(wrapper)

    def _add_domain_header(self, domain: str) -> None:
        self._left_layout.addSpacing(6)
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        # Favicon
        favicon_label = QLabel()
        favicon_label.setFixedSize(14, 14)
        favicon_label.setObjectName(f"favicon_{domain}")
        favicon_label.setStyleSheet(
            "background: #2a2a4a; border-radius: 3px;"
        )
        # Try cached favicon
        pm = self._favicons.get(domain)
        if pm and not pm.isNull():
            favicon_label.setPixmap(pm.scaled(14, 14, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            # Show first letter as placeholder
            favicon_label.setText(domain[0].upper() if domain else "?")
            favicon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            favicon_label.setStyleSheet(
                "background: #2a2a4a; border-radius: 3px; color: #8b5cf6; font-size: 8px; font-weight: bold;"
            )
        row.addWidget(favicon_label)

        # Domain name
        name_label = QLabel(domain)
        name_label.setFont(self._make_font(12, QFont.Weight.DemiBold))
        name_label.setStyleSheet(f"color: #9a8adf; background: transparent;")
        row.addWidget(name_label, 1)

        wrapper = QWidget()
        wrapper.setStyleSheet("background: transparent;")
        wrapper.setLayout(row)
        self._left_layout.addWidget(wrapper)
        self._left_layout.addSpacing(2)

    def _on_favicon_ready(self, domain: str, pixmap: QPixmap) -> None:
        """Update favicon labels when async fetch completes."""
        if pixmap.isNull():
            return
        # Find and update the favicon label
        label = self._container.findChild(QLabel, f"favicon_{domain}")
        if label:
            label.setPixmap(pixmap.scaled(14, 14, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            label.setStyleSheet("background: transparent; border-radius: 3px;")

    # ------------------------------------------------------------------
    # Countdown Logic
    # ------------------------------------------------------------------

    def _start_countdown(self) -> None:
        now = datetime.now(timezone.utc)
        remaining = (self._target_time - now).total_seconds()
        self._seconds_remaining = max(0, int(math.ceil(remaining)))

        self._update_display()

        # Start audio
        if self._settings.mode == "countdown_music" and self._settings.sound_file:
            duration_override = self._settings.sound_duration_override
            delay = self._audio.start_countdown_playback(
                remaining, duration_override
            )
            if delay > 0:
                QTimer.singleShot(int(delay * 1000), self._audio.play_now)

        # Tick timer — fires every second with offset
        offset_ms = max(0, self._settings.clock_offset)
        if offset_ms > 0:
            QTimer.singleShot(offset_ms, self._start_tick_timer)
        else:
            self._start_tick_timer()

    def _start_tick_timer(self) -> None:
        self._tick_timer = QTimer(self)
        self._tick_timer.setInterval(1000)
        self._tick_timer.timeout.connect(self._tick)
        self._tick_timer.start()

    def _tick(self) -> None:
        now = datetime.now(timezone.utc)
        remaining = (self._target_time - now).total_seconds()
        self._seconds_remaining = max(0, int(math.ceil(remaining)))

        if self._seconds_remaining <= 2 and self._phase == "countdown":
            self._enter_action_phase()
        else:
            self._update_display()

    def _update_display(self) -> None:
        s = self._seconds_remaining
        self._countdown_label.setText(str(s))

        # Color transitions
        if s <= 3:
            color = COLOR_CRITICAL.name()
            shadow_color = "rgba(239,68,68,0.5)"
        elif s <= 10:
            color = COLOR_WARNING.name()
            shadow_color = "rgba(245,158,11,0.4)"
        else:
            color = COLOR_TEXT.name()
            shadow_color = "rgba(90,122,255,0.3)"

        self._countdown_label.setStyleSheet(
            f"color: {color}; background: transparent;"
        )

    def _enter_action_phase(self) -> None:
        """Transition to ACTION! clapperboard phase (~2s before meeting start)."""
        self._phase = "action"
        self._tick_timer.stop()
        self._countdown_label.hide()
        self._action_widget.show()
        self._clapperboard.start_animation()

        # Calculate time remaining until meeting start for LIVE transition
        now = datetime.now(timezone.utc)
        remaining_ms = max(0, int((self._target_time - now).total_seconds() * 1000))

        # Schedule auto-join at T=0
        if (
            self._settings.auto_join
            and not self._is_multi
            and self._meetings[0].video_link
        ):
            QTimer.singleShot(remaining_ms, lambda: QDesktopServices.openUrl(QUrl(self._meetings[0].video_link)))

        # Transition to LIVE at T=0 (meeting start)
        QTimer.singleShot(remaining_ms, self._enter_live_phase)

    def _enter_live_phase(self) -> None:
        """Transition to LIVE indicator."""
        self._phase = "live"
        self._action_widget.hide()
        self._live_widget.show()

        # Pulse animation on the LIVE dot
        self._pulse_anim = QGraphicsOpacityEffect(self._live_dot)
        self._live_dot.setGraphicsEffect(self._pulse_anim)
        self._pulse_opacity = QPropertyAnimation(self._pulse_anim, b"opacity")
        self._pulse_opacity.setDuration(1500)
        self._pulse_opacity.setStartValue(1.0)
        self._pulse_opacity.setKeyValueAt(0.5, 0.5)
        self._pulse_opacity.setEndValue(1.0)
        self._pulse_opacity.setLoopCount(-1)
        self._pulse_opacity.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._pulse_opacity.start()

    # ------------------------------------------------------------------
    # Mute
    # ------------------------------------------------------------------

    def _toggle_mute(self) -> None:
        self._audio.set_muted(not self._audio.is_muted)
        self._update_mute_icon()

    def _update_mute_icon(self) -> None:
        icon_file = "speaker_muted.svg" if self._audio.is_muted else "speaker.svg"
        icon_path = ASSETS / icon_file
        if icon_path.exists():
            self._mute_btn.setIcon(QIcon(str(icon_path)))
            self._mute_btn.setIconSize(QSize(18, 18))
        else:
            self._mute_btn.setText("\U0001f507" if self._audio.is_muted else "\U0001f50a")

    # ------------------------------------------------------------------
    # Window positioning & animation
    # ------------------------------------------------------------------

    def _position_window(self) -> None:
        screen = QApplication.primaryScreen()
        if not screen:
            return
        geom = screen.availableGeometry()
        x = geom.right() - WINDOW_W - SCREEN_INSET
        y = geom.top() + SCREEN_INSET
        self._final_pos = (x, y)
        # Start off-screen to the right for slide-in
        self.move(geom.right() + 10, y)

    def _slide_in(self) -> None:
        self._slide_anim = QPropertyAnimation(self, b"pos")
        self._slide_anim.setDuration(300)
        self._slide_anim.setEndValue(self.mapToGlobal(self.pos()).__class__(*self._final_pos) if hasattr(self, '_final_pos') else self.pos())
        self._slide_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        from PyQt6.QtCore import QPoint
        self._slide_anim.setStartValue(self.pos())
        self._slide_anim.setEndValue(QPoint(*self._final_pos))
        self._slide_anim.start()

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event) -> None:
        self._audio.stop()
        if hasattr(self, "_tick_timer"):
            self._tick_timer.stop()
        self.closed.emit()
        super().closeEvent(event)

    @staticmethod
    def _make_font(size: int, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
        f = QFont("Helvetica Neue", size)
        f.setWeight(weight)
        return f
