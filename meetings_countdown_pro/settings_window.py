"""Settings window — 3-tab macOS-style preferences."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSlider,
    QSpinBox,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from meetings_countdown_pro.audio_player import AudioPlayer
from meetings_countdown_pro.settings import Settings


class SettingsWindow(QDialog):
    """4-tab settings dialog: General, Calendars, Audio, Agent."""

    settings_saved = pyqtSignal(Settings)
    test_countdown_requested = pyqtSignal(int)  # duration in seconds

    def __init__(
        self,
        settings: Settings,
        audio_player: AudioPlayer,
        calendars: dict[str, list[dict]],
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._settings = settings
        self._audio = audio_player
        self._calendars = calendars
        self._preview_playing = False

        self.setWindowTitle("Settings")
        self.setWindowFlag(Qt.WindowType.Window)  # Regular window, stays visible on focus loss
        self.setMinimumSize(580, 480)
        self.setMaximumWidth(640)

        self._build_ui()
        self._load_values()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # macOS Preference-pane style: icon + label toolbar buttons, centered
        from PyQt6.QtWidgets import QStackedWidget, QButtonGroup, QToolButton
        from PyQt6.QtGui import QIcon

        toolbar_bar = QWidget()
        toolbar_bar.setObjectName("toolbarBar")
        toolbar_bar.setStyleSheet(
            """
            QWidget#toolbarBar {
                background: palette(window);
                border-bottom: 1px solid palette(mid);
            }
            QToolButton {
                background: transparent;
                border: 1px solid transparent;
                border-radius: 6px;
                padding: 6px 16px 4px 16px;
                font-size: 11px;
                color: palette(text);
                min-width: 64px;
            }
            QToolButton:checked {
                background: rgba(128,128,128,0.25);
                border: 1px solid rgba(128,128,128,0.4);
            }
            QToolButton:hover:!checked {
                background: rgba(128,128,128,0.1);
            }
            """
        )
        toolbar_layout = QHBoxLayout(toolbar_bar)
        toolbar_layout.setContentsMargins(0, 6, 0, 6)
        toolbar_layout.setSpacing(2)
        toolbar_layout.addStretch()

        self._tab_stack = QStackedWidget()
        self._tab_group = QButtonGroup(self)
        self._tab_group.setExclusive(True)

        # Build SVG icons inline for crisp rendering
        def _svg_icon(svg_data: str) -> QIcon:
            from PyQt6.QtSvg import QSvgRenderer
            from PyQt6.QtGui import QPixmap, QPainter
            from PyQt6.QtCore import QByteArray
            renderer = QSvgRenderer(QByteArray(svg_data.encode()))
            pm = QPixmap(32, 32)
            pm.fill(QColor(0, 0, 0, 0))
            painter = QPainter(pm)
            renderer.render(painter)
            painter.end()
            return QIcon(pm)

        gear_svg = '''<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#555" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
        </svg>'''

        calendar_svg = '''<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#555" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>
        </svg>'''

        speaker_svg = '''<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#555" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14"/><path d="M15.54 8.46a5 5 0 0 1 0 7.07"/>
        </svg>'''

        ai_svg = '''<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#555" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M9.5 2A2.5 2.5 0 0 1 12 4.5V5a1 1 0 0 0 1 1h1.5A2.5 2.5 0 0 1 17 8.5V9a1 1 0 0 1-1 1h-1"/><path d="M8 10H7a1 1 0 0 1-1-1V8.5A2.5 2.5 0 0 1 8.5 6H9"/><rect x="6" y="10" width="12" height="10" rx="2"/><circle cx="10" cy="15" r="1" fill="#555"/><circle cx="14" cy="15" r="1" fill="#555"/><path d="M10 18h4"/>
        </svg>'''

        tab_pages = [
            ("General", gear_svg, self._build_general_tab()),
            ("Calendars", calendar_svg, self._build_calendars_tab()),
            ("Audio", speaker_svg, self._build_audio_tab()),
            ("AI Integration", ai_svg, self._build_agent_tab()),
        ]

        for i, (label, svg, page) in enumerate(tab_pages):
            btn = QToolButton()
            btn.setText(label)
            btn.setIcon(_svg_icon(svg))
            btn.setIconSize(QSize(28, 28))
            btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            btn.setCheckable(True)
            btn.setAutoExclusive(True)
            if i == 0:
                btn.setChecked(True)
            self._tab_group.addButton(btn, i)
            toolbar_layout.addWidget(btn)
            self._tab_stack.addWidget(page)

        toolbar_layout.addStretch()

        layout.addWidget(toolbar_bar)
        layout.addWidget(self._tab_stack, 1)

        self._tab_group.idClicked.connect(self._tab_stack.setCurrentIndex)

        # Bottom button bar
        btn_bar = QHBoxLayout()
        btn_bar.setContentsMargins(16, 12, 16, 16)

        # Test buttons
        self._test_btn = QPushButton("\u25b6 Test Countdown")
        self._test_btn.setStyleSheet(
            "QPushButton { background: #f59e0b; color: white; border: none; border-radius: 6px; padding: 6px 18px; font-weight: bold; }"
            "QPushButton:hover { background: #d97706; }"
        )
        self._test_btn.clicked.connect(lambda: self._request_test(None))
        btn_bar.addWidget(self._test_btn)

        self._quick_test_btn = QPushButton("Quick Test (10s)")
        self._quick_test_btn.setStyleSheet(
            "QPushButton { background: white; color: #888; border: 1px solid #ddd; border-radius: 6px; padding: 6px 14px; font-size: 11px; }"
            "QPushButton:hover { background: #f0f0f0; }"
        )
        self._quick_test_btn.clicked.connect(lambda: self._request_test(10))
        btn_bar.addWidget(self._quick_test_btn)

        btn_bar.addStretch()

        self._save_btn = QPushButton("Save")
        self._save_btn.setStyleSheet(
            "QPushButton { background: #0066ff; color: white; border: none; border-radius: 6px; padding: 6px 18px; font-weight: bold; }"
            "QPushButton:hover { background: #0052cc; }"
        )
        self._save_btn.clicked.connect(self._save)
        btn_bar.addWidget(self._save_btn)

        layout.addLayout(btn_bar)

    # ------------------------------------------------------------------
    # General tab
    # ------------------------------------------------------------------

    def _build_general_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        # Row 1: Startup (left) + Organization (right)
        top_row = QHBoxLayout()
        top_row.setSpacing(16)

        group = QGroupBox("Startup")
        gl = QFormLayout(group)
        self._launch_login = QCheckBox("Launch at Login")
        gl.addRow(self._launch_login)
        top_row.addWidget(group, 1)

        group = QGroupBox("Organization")
        gl = QVBoxLayout(group)
        gl.addWidget(QLabel("Internal Email Domain"))
        self._internal_domain = QLineEdit()
        self._internal_domain.setPlaceholderText("example.com")
        gl.addWidget(self._internal_domain)
        top_row.addWidget(group, 1)

        layout.addLayout(top_row)

        # Row 2: Countdown (left) + Meeting Filters (right)
        mid_row = QHBoxLayout()
        mid_row.setSpacing(16)

        # Countdown
        group = QGroupBox("Countdown")
        gl = QVBoxLayout(group)
        gl.setSpacing(6)

        dur_row = QHBoxLayout()
        dur_row.addWidget(QLabel("Countdown Duration"))
        self._duration_spin = QSpinBox()
        self._duration_spin.setRange(10, 300)
        self._duration_spin.setSuffix(" sec")
        self._duration_spin.setMaximumWidth(120)
        dur_row.addWidget(self._duration_spin)
        dur_row.addStretch()
        gl.addLayout(dur_row)

        self._video_only = QCheckBox("Only for video meetings")
        gl.addWidget(self._video_only)

        self._auto_join = QCheckBox("Auto-open link when done")
        gl.addWidget(self._auto_join)

        self._continue_after_join = QCheckBox("Continue after joining")
        gl.addWidget(self._continue_after_join)

        b2b_row = QHBoxLayout()
        b2b_row.addWidget(QLabel("Back-to-Back"))
        self._back_to_back = QComboBox()
        self._back_to_back.addItems(["Default", "Silent", "Skip"])
        b2b_row.addWidget(self._back_to_back)
        b2b_row.addStretch()
        gl.addLayout(b2b_row)

        mid_row.addWidget(group, 1)

        # Meeting Filters
        group = QGroupBox("Meeting Filters")
        gl = QVBoxLayout(group)
        gl.setSpacing(6)
        self._include_tentative = QCheckBox("Include Tentative")
        gl.addWidget(self._include_tentative)
        self._include_free = QCheckBox("Include Free Events")
        gl.addWidget(self._include_free)
        self._include_allday = QCheckBox("Include All-Day Events")
        gl.addWidget(self._include_allday)
        gl.addStretch()
        mid_row.addWidget(group, 1)

        layout.addLayout(mid_row)

        # Working Hours
        group = QGroupBox("Working Hours")
        gl = QFormLayout(group)

        self._wh_enabled = QCheckBox("Only start countdowns during working hours")
        self._wh_enabled.toggled.connect(self._toggle_working_hours)
        gl.addRow(self._wh_enabled)

        # Day toggle buttons (Sun=6, Mon=0, Tue=1, ... Sat=5 in Python weekday())
        day_row = QHBoxLayout()
        day_row.setSpacing(4)
        self._wh_day_buttons: list[QPushButton] = []
        # Display order: Sun, Mon, Tue, Wed, Thu, Fri, Sat
        # Python weekday():  6,   0,   1,   2,   3,   4,   5
        self._wh_day_order = [6, 0, 1, 2, 3, 4, 5]
        day_labels = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
        for label in day_labels:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setFixedSize(42, 26)
            btn.setStyleSheet(self._day_button_style())
            btn.toggled.connect(lambda _: self._update_day_button_styles())
            day_row.addWidget(btn)
            self._wh_day_buttons.append(btn)
        day_row.addStretch()
        self._wh_days_label = QLabel("Days")
        gl.addRow(self._wh_days_label, day_row)

        # Time range inputs
        time_row = QHBoxLayout()
        time_row.setSpacing(6)
        self._wh_start_time = QLineEdit()
        self._wh_start_time.setMaximumWidth(90)
        self._wh_start_time.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._wh_start_time.editingFinished.connect(
            lambda: self._validate_time_input(self._wh_start_time)
        )
        time_row.addWidget(self._wh_start_time)
        self._wh_to_label = QLabel("to")
        time_row.addWidget(self._wh_to_label)
        self._wh_end_time = QLineEdit()
        self._wh_end_time.setMaximumWidth(90)
        self._wh_end_time.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._wh_end_time.editingFinished.connect(
            lambda: self._validate_time_input(self._wh_end_time)
        )
        time_row.addWidget(self._wh_end_time)
        time_row.addStretch()
        self._wh_hours_label = QLabel("Hours")
        gl.addRow(self._wh_hours_label, time_row)

        self._wh_time_error = QLabel("")
        self._wh_time_error.setStyleSheet("color: #e53e3e; font-size: 11px;")
        gl.addRow("", self._wh_time_error)

        layout.addWidget(group)

        layout.addStretch()
        return page

    @staticmethod
    def _day_button_style() -> str:
        return (
            "QPushButton { font-size: 11px; font-weight: 500; border-radius: 13px;"
            "  border: 1px solid #ccc; background: white; color: #999; }"
            "QPushButton:checked { background: #0066ff; border-color: #0066ff; color: white; }"
            "QPushButton:hover:!checked { background: #f0f0f0; color: #666; }"
            "QPushButton:disabled { opacity: 0.5; }"
            "QPushButton:checked:disabled { background: #a0c4ff; border-color: #a0c4ff; color: white; }"
        )

    def _update_day_button_styles(self) -> None:
        for btn in self._wh_day_buttons:
            btn.setStyleSheet(self._day_button_style())

    def _toggle_working_hours(self, enabled: bool) -> None:
        for btn in self._wh_day_buttons:
            btn.setEnabled(enabled)
        self._wh_start_time.setEnabled(enabled)
        self._wh_end_time.setEnabled(enabled)
        self._wh_days_label.setEnabled(enabled)
        self._wh_hours_label.setEnabled(enabled)
        self._wh_to_label.setEnabled(enabled)

    _TIME_INPUT_NORMAL = "QLineEdit { }"
    _TIME_INPUT_ERROR = (
        "QLineEdit { border: 1.5px solid #e53e3e; background: #fff5f5; }"
    )

    def _validate_time_input(self, field: QLineEdit) -> None:
        """Normalize valid time input on focus-out, or show error styling."""
        text = field.text().strip()
        if not text:
            field.setStyleSheet(self._TIME_INPUT_NORMAL)
            self._update_time_error()
            return
        parsed = self._parse_time_to_24h(text)
        if parsed is not None:
            field.setText(self._format_time_12h(parsed))
            field.setStyleSheet(self._TIME_INPUT_NORMAL)
        else:
            field.setStyleSheet(self._TIME_INPUT_ERROR)
        self._update_time_error()

    def _update_time_error(self) -> None:
        """Show or clear the time error label based on current field styles."""
        has_error = (
            self._wh_start_time.styleSheet() == self._TIME_INPUT_ERROR
            or self._wh_end_time.styleSheet() == self._TIME_INPUT_ERROR
        )
        if has_error:
            self._wh_time_error.setText('Use a format like "9:00 AM" or "14:30"')
        else:
            self._wh_time_error.setText("")

    @staticmethod
    def _format_time_12h(time_24h: str) -> str:
        """Convert 'HH:MM' 24h to '9:00 AM' style display."""
        try:
            h, m = map(int, time_24h.split(":"))
            suffix = "AM" if h < 12 else "PM"
            h12 = h % 12 or 12
            return f"{h12}:{m:02d} {suffix}"
        except (ValueError, AttributeError):
            return time_24h

    @staticmethod
    def _parse_time_to_24h(text: str) -> str | None:
        """Parse user time input to 'HH:MM' 24h format.

        Accepts: '9:00 AM', '9:00AM', '9am', '14:30', '2:30 PM', etc.
        Returns None if unparseable.
        """
        import re
        text = text.strip().upper()
        # Try HH:MM with optional AM/PM
        m = re.fullmatch(r"(\d{1,2}):(\d{2})\s*(AM|PM)?", text)
        if m:
            h, mins, period = int(m.group(1)), int(m.group(2)), m.group(3)
            if period == "PM" and h != 12:
                h += 12
            elif period == "AM" and h == 12:
                h = 0
            if 0 <= h <= 23 and 0 <= mins <= 59:
                return f"{h:02d}:{mins:02d}"
            return None
        # Try bare number with AM/PM, e.g. '9AM', '5pm'
        m = re.fullmatch(r"(\d{1,2})\s*(AM|PM)", text)
        if m:
            h, period = int(m.group(1)), m.group(2)
            if period == "PM" and h != 12:
                h += 12
            elif period == "AM" and h == 12:
                h = 0
            if 0 <= h <= 23:
                return f"{h:02d}:00"
            return None
        # Try plain 24h, e.g. '14:30'
        m = re.fullmatch(r"(\d{1,2}):(\d{2})", text)
        if m:
            h, mins = int(m.group(1)), int(m.group(2))
            if 0 <= h <= 23 and 0 <= mins <= 59:
                return f"{h:02d}:{mins:02d}"
        return None

    # ------------------------------------------------------------------
    # Calendars tab
    # ------------------------------------------------------------------

    def _build_calendars_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(12)

        layout.addWidget(QLabel("Select which calendars to monitor for meetings:"))

        self._cal_tree = QTreeWidget()
        self._cal_tree.setHeaderHidden(True)
        self._cal_tree.setRootIsDecorated(True)

        for account, cals in self._calendars.items():
            account_item = QTreeWidgetItem([account])
            account_item.setFlags(account_item.flags() | Qt.ItemFlag.ItemIsAutoTristate | Qt.ItemFlag.ItemIsUserCheckable)
            for cal in cals:
                child = QTreeWidgetItem([cal["name"]])
                child.setFlags(child.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                child.setCheckState(0, Qt.CheckState.Checked)
                child.setData(0, Qt.ItemDataRole.UserRole, cal)
                account_item.addChild(child)
            self._cal_tree.addTopLevelItem(account_item)
            account_item.setExpanded(True)

        layout.addWidget(self._cal_tree, 1)
        return page

    # ------------------------------------------------------------------
    # Audio tab
    # ------------------------------------------------------------------

    def _build_audio_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        # Sound File
        group = QGroupBox("Sound File")
        gl = QFormLayout(group)

        file_row = QHBoxLayout()
        self._file_choose_btn = QPushButton("Choose File...")
        self._file_choose_btn.clicked.connect(self._choose_sound_file)
        file_row.addWidget(self._file_choose_btn)

        self._file_name_label = QLabel("No file selected")
        self._file_name_label.setStyleSheet("color: #666;")
        file_row.addWidget(self._file_name_label, 1)

        self._file_duration_label = QLabel("")
        self._file_duration_label.setStyleSheet("color: #999; font-size: 11px;")
        file_row.addWidget(self._file_duration_label)

        self._preview_btn = QPushButton("\u25b6")
        self._preview_btn.setFixedWidth(32)
        self._preview_btn.clicked.connect(self._toggle_preview)
        file_row.addWidget(self._preview_btn)

        self._clear_btn = QPushButton("\u2715")
        self._clear_btn.setFixedWidth(32)
        self._clear_btn.setStyleSheet("color: #cc3333;")
        self._clear_btn.clicked.connect(self._clear_sound_file)
        file_row.addWidget(self._clear_btn)

        gl.addRow("Countdown Music", file_row)

        dur_row = QHBoxLayout()
        self._duration_override = QSpinBox()
        self._duration_override.setRange(0, 600)
        self._duration_override.setSuffix(" sec")
        self._duration_override.setSpecialValueText("Auto")
        self._duration_override.setMaximumWidth(100)
        dur_row.addWidget(self._duration_override)
        dur_row.addStretch()
        gl.addRow("Duration Override", dur_row)
        layout.addWidget(group)

        # Playback
        group = QGroupBox("Playback")
        gl = QFormLayout(group)

        vol_row = QHBoxLayout()
        vol_row.addWidget(QLabel("\U0001f508"))
        self._volume_slider = QSlider(Qt.Orientation.Horizontal)
        self._volume_slider.setRange(0, 100)
        vol_row.addWidget(self._volume_slider, 1)
        vol_row.addWidget(QLabel("\U0001f50a"))
        self._volume_label = QLabel("100%")
        self._volume_label.setMinimumWidth(40)
        self._volume_slider.valueChanged.connect(
            lambda v: self._volume_label.setText(f"{v}%")
        )
        vol_row.addWidget(self._volume_label)
        gl.addRow("Volume", vol_row)

        self._output_device = QComboBox()
        self._output_device.addItem("System Default", "")
        for dev in AudioPlayer.available_output_devices():
            self._output_device.addItem(dev["name"], dev["id"])
        gl.addRow("Audio Output Device", self._output_device)
        layout.addWidget(group)

        # Timing Calibration
        group = QGroupBox("Timing Calibration")
        gl = QFormLayout(group)
        offset_row = QHBoxLayout()
        self._clock_offset = QSpinBox()
        self._clock_offset.setRange(-2000, 2000)
        self._clock_offset.setSuffix(" ms")
        self._clock_offset.setMaximumWidth(100)
        offset_row.addWidget(self._clock_offset)
        offset_row.addStretch()
        gl.addRow("Clock Offset", offset_row)
        layout.addWidget(group)

        layout.addStretch()
        return page

    # ------------------------------------------------------------------
    # Agent tab
    # ------------------------------------------------------------------

    def _build_agent_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        # Enable toggle
        self._agent_enabled = QCheckBox("Enable AI Integration at countdown start")
        layout.addWidget(self._agent_enabled)

        # Terminal
        group = QGroupBox("Terminal")
        gl = QFormLayout(group)
        self._agent_terminal = QComboBox()
        self._agent_terminal.addItem("Terminal.app", "terminal")
        self._agent_terminal.addItem("iTerm2", "iterm2")
        gl.addRow("Application", self._agent_terminal)
        layout.addWidget(group)

        # Working Directory
        group = QGroupBox("Working Directory")
        gl = QFormLayout(group)
        dir_row = QHBoxLayout()
        self._agent_working_dir = QLineEdit()
        self._agent_working_dir.setPlaceholderText("~/Documents/meeting-notes")
        dir_row.addWidget(self._agent_working_dir, 1)
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_agent_dir)
        dir_row.addWidget(browse_btn)
        gl.addRow(dir_row)
        layout.addWidget(group)

        # Command Template
        group = QGroupBox("Command Template")
        gl = QFormLayout(group)
        self._agent_command = QLineEdit()
        self._agent_command.setPlaceholderText("claude {Prompt}")
        gl.addRow(self._agent_command)
        hint = QLabel("{Prompt} is replaced with the shell-escaped prompt text.")
        hint.setStyleSheet("color: #888; font-size: 11px;")
        gl.addRow(hint)
        layout.addWidget(group)

        # Prompt Template
        group = QGroupBox("Prompt Template")
        gl = QVBoxLayout(group)
        self._agent_prompt = QPlainTextEdit()
        self._agent_prompt.setMaximumHeight(100)
        self._agent_prompt.setPlaceholderText(
            "Please help me prep for this meeting: {MeetingData}"
        )
        gl.addWidget(self._agent_prompt)
        hint = QLabel(
            "{MeetingData} is replaced with a JSON object containing meeting "
            "titles, times, attendees, video links, and calendar info."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #888; font-size: 11px;")
        gl.addWidget(hint)
        layout.addWidget(group)

        layout.addStretch()
        return page

    def _browse_agent_dir(self) -> None:
        current = self._agent_working_dir.text() or "~"
        path = QFileDialog.getExistingDirectory(
            self, "Select Working Directory", os.path.expanduser(current)
        )
        if path:
            # Use ~ shorthand if under home dir
            home = os.path.expanduser("~")
            if path.startswith(home):
                path = "~" + path[len(home):]
            self._agent_working_dir.setText(path)

    # ------------------------------------------------------------------
    # Load / Save
    # ------------------------------------------------------------------

    def _load_values(self) -> None:
        s = self._settings

        # General
        self._launch_login.setChecked(s.launch_at_login)
        self._duration_spin.setValue(s.countdown_duration)
        self._video_only.setChecked(s.video_calls_only)
        self._auto_join.setChecked(s.auto_join)
        self._continue_after_join.setChecked(s.continue_after_join)
        self._internal_domain.setText(s.internal_domain)
        self._include_tentative.setChecked(s.include_tentative)
        self._include_allday.setChecked(s.include_all_day)
        self._include_free.setChecked(s.include_free)

        b2b_map = {"default": 0, "countdown_music": 0, "silent": 1, "skip": 2}
        self._back_to_back.setCurrentIndex(b2b_map.get(s.back_to_back, 0))

        # Working hours
        self._wh_enabled.setChecked(s.working_hours_enabled)
        for i, weekday in enumerate(self._wh_day_order):
            self._wh_day_buttons[i].setChecked(weekday in s.working_hours_days)
        self._wh_start_time.setText(self._format_time_12h(s.working_hours_start))
        self._wh_end_time.setText(self._format_time_12h(s.working_hours_end))
        self._toggle_working_hours(s.working_hours_enabled)

        # Calendars — check/uncheck based on selected_calendars
        if s.selected_calendars:
            for i in range(self._cal_tree.topLevelItemCount()):
                account_item = self._cal_tree.topLevelItem(i)
                account_name = account_item.text(0)
                selected = s.selected_calendars.get(account_name, [])
                for j in range(account_item.childCount()):
                    child = account_item.child(j)
                    cal_name = child.text(0)
                    state = Qt.CheckState.Checked if cal_name in selected else Qt.CheckState.Unchecked
                    child.setCheckState(0, state)

        # Audio
        if s.sound_file:
            self._file_name_label.setText(Path(s.sound_file).name)
        self._duration_override.setValue(int(s.sound_duration_override or 0))
        self._volume_slider.setValue(s.volume)
        self._clock_offset.setValue(s.clock_offset)

        # Output device — if the saved device isn't in the list (disconnected),
        # add a placeholder so _save() preserves the preference rather than
        # silently resetting to System Default.
        found_device = False
        for i in range(self._output_device.count()):
            if self._output_device.itemData(i) == s.audio_output_device:
                self._output_device.setCurrentIndex(i)
                found_device = True
                break
        if not found_device and s.audio_output_device:
            self._output_device.addItem(f"{s.audio_output_device} (disconnected)", s.audio_output_device)
            self._output_device.setCurrentIndex(self._output_device.count() - 1)

        # Agent
        self._agent_enabled.setChecked(s.agent_enabled)
        for i in range(self._agent_terminal.count()):
            if self._agent_terminal.itemData(i) == s.agent_terminal:
                self._agent_terminal.setCurrentIndex(i)
                break
        self._agent_working_dir.setText(s.agent_working_dir)
        self._agent_command.setText(s.agent_command_template)
        self._agent_prompt.setPlainText(s.agent_prompt_template)

    def _save(self) -> None:
        s = self._settings

        # General
        s.launch_at_login = self._launch_login.isChecked()
        s.countdown_duration = self._duration_spin.value()
        s.video_calls_only = self._video_only.isChecked()
        s.auto_join = self._auto_join.isChecked()
        s.continue_after_join = self._continue_after_join.isChecked()
        s.internal_domain = self._internal_domain.text().strip()
        s.include_tentative = self._include_tentative.isChecked()
        s.include_all_day = self._include_allday.isChecked()
        s.include_free = self._include_free.isChecked()

        b2b_map = {0: "default", 1: "silent", 2: "skip"}
        s.back_to_back = b2b_map.get(self._back_to_back.currentIndex(), "default")

        # Working hours
        s.working_hours_enabled = self._wh_enabled.isChecked()
        s.working_hours_days = [
            self._wh_day_order[i]
            for i, btn in enumerate(self._wh_day_buttons)
            if btn.isChecked()
        ]
        s.working_hours_start = self._parse_time_to_24h(self._wh_start_time.text()) or "09:00"
        s.working_hours_end = self._parse_time_to_24h(self._wh_end_time.text()) or "17:00"

        # Calendars
        selected: dict[str, list[str]] = {}
        for i in range(self._cal_tree.topLevelItemCount()):
            account_item = self._cal_tree.topLevelItem(i)
            account_name = account_item.text(0)
            cals = []
            for j in range(account_item.childCount()):
                child = account_item.child(j)
                if child.checkState(0) == Qt.CheckState.Checked:
                    cals.append(child.text(0))
            if cals:
                selected[account_name] = cals
        s.selected_calendars = selected

        # Audio
        s.sound_duration_override = self._duration_override.value() or None
        s.volume = self._volume_slider.value()
        s.clock_offset = self._clock_offset.value()
        s.audio_output_device = self._output_device.currentData() or ""

        # Agent
        s.agent_enabled = self._agent_enabled.isChecked()
        s.agent_terminal = self._agent_terminal.currentData() or "terminal"
        s.agent_working_dir = self._agent_working_dir.text().strip() or "~"
        s.agent_command_template = self._agent_command.text().strip()
        s.agent_prompt_template = self._agent_prompt.toPlainText().strip()

        s.validate()
        s.save()
        self.settings_saved.emit(s)
        self.close()

    # ------------------------------------------------------------------
    # Sound file actions
    # ------------------------------------------------------------------

    def _choose_sound_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Countdown Music",
            "",
            "Audio Files (*.mp3 *.wav *.flac *.aac *.m4a);;All Files (*)",
        )
        if path:
            self._settings.sound_file = path
            self._file_name_label.setText(Path(path).name)
            # Detect duration
            self._audio.set_sound_file(path)
            self._audio.duration_detected.connect(self._on_duration_detected)

    def _on_duration_detected(self, seconds: float) -> None:
        mins = int(seconds) // 60
        secs = int(seconds) % 60
        self._file_duration_label.setText(f"({mins}:{secs:02d})")

    def _clear_sound_file(self) -> None:
        self._settings.sound_file = ""
        self._file_name_label.setText("No file selected")
        self._file_duration_label.setText("")
        self._audio.stop()

    def _toggle_preview(self) -> None:
        if self._preview_playing:
            self._audio.stop()
            self._preview_btn.setText("\u25b6")
            self._preview_playing = False
        else:
            if self._settings.sound_file:
                self._audio.preview(self._settings.sound_file)
                self._preview_btn.setText("\u25a0")
                self._preview_playing = True

    def _request_test(self, duration: Optional[int]) -> None:
        self._save()
        d = duration if duration else self._settings.countdown_duration
        self.test_countdown_requested.emit(d)
