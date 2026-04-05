"""Settings model — load, save, and defaults."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

CONFIG_DIR = Path(os.path.expanduser("~/.config/meetings-countdown-pro"))
SETTINGS_FILE = CONFIG_DIR / "settings.json"


@dataclass
class Settings:
    """All user-configurable settings with spec defaults."""

    # Startup
    launch_at_login: bool = False

    # Countdown
    countdown_duration: int = 60  # seconds, 10–300
    video_calls_only: bool = False
    auto_join: bool = False
    continue_after_join: bool = False

    # Organization
    internal_domain: str = ""

    # Meeting filters
    include_tentative: bool = False
    include_all_day: bool = False
    include_free: bool = False
    back_to_back: str = "default"  # default | silent | skip

    # Audio
    sound_file: str = ""  # absolute path to audio file
    sound_duration_override: Optional[float] = None  # seconds, None = auto-detect
    clock_offset: int = 0  # ms, -2000 to +2000
    volume: int = 100  # 0–100
    audio_output_device: str = ""  # empty = system default

    # Calendar selection: {account_name: [calendar_names]} or empty = all
    selected_calendars: dict[str, list[str]] = field(default_factory=dict)

    # Working hours
    working_hours_enabled: bool = False
    working_hours_days: list[int] = field(default_factory=lambda: [0, 1, 2, 3, 4])  # Mon–Fri (weekday())
    working_hours_start: str = "09:00"  # HH:MM 24h
    working_hours_end: str = "17:00"  # HH:MM 24h

    # AI Agent integration
    agent_enabled: bool = False
    agent_terminal: str = "terminal"  # terminal | iterm2
    agent_working_dir: str = "~"
    agent_command_template: str = "claude {Prompt}"
    agent_prompt_template: str = "Please help me prep for this meeting: {MeetingData}"

    # Runtime mode (not persisted via settings window, controlled from menu bar)
    mode: str = "countdown_music"  # countdown_music | silent | off

    def save(self) -> None:
        """Persist settings to disk."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = asdict(self)
        with open(SETTINGS_FILE, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls) -> Settings:
        """Load settings from disk, falling back to defaults."""
        if not SETTINGS_FILE.exists():
            return cls()
        try:
            with open(SETTINGS_FILE) as f:
                data = json.load(f)
            # Only use known fields, ignore stale keys
            known = {f.name for f in cls.__dataclass_fields__.values()}
            filtered = {k: v for k, v in data.items() if k in known}
            return cls(**filtered)
        except (json.JSONDecodeError, TypeError, KeyError):
            return cls()

    def validate(self) -> None:
        """Clamp values to valid ranges."""
        self.countdown_duration = max(10, min(300, self.countdown_duration))
        self.clock_offset = max(-2000, min(2000, self.clock_offset))
        self.volume = max(0, min(100, self.volume))
        if self.back_to_back not in ("default", "countdown_music", "silent", "skip"):
            self.back_to_back = "default"
        if self.mode not in ("countdown_music", "silent", "off"):
            self.mode = "countdown_music"
        if self.agent_terminal not in ("terminal", "iterm2"):
            self.agent_terminal = "terminal"
        # Working hours: clamp days to valid weekday ints
        self.working_hours_days = sorted(
            set(d for d in self.working_hours_days if isinstance(d, int) and 0 <= d <= 6)
        )
        # Validate time strings (HH:MM, 00:00–23:59)
        import re
        time_re = r"(?:[01]?\d|2[0-3]):[0-5]\d"
        if not re.fullmatch(time_re, self.working_hours_start):
            self.working_hours_start = "09:00"
        if not re.fullmatch(time_re, self.working_hours_end):
            self.working_hours_end = "17:00"
