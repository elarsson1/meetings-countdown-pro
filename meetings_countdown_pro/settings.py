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

    # Organization
    internal_domain: str = ""

    # Meeting filters
    include_tentative: bool = False
    include_all_day: bool = False
    back_to_back: str = "countdown_music"  # countdown_music | silent | skip

    # Audio
    sound_file: str = ""  # absolute path to audio file
    sound_duration_override: Optional[float] = None  # seconds, None = auto-detect
    clock_offset: int = 0  # ms, -2000 to +2000
    volume: int = 100  # 0–100
    audio_output_device: str = ""  # empty = system default

    # Calendar selection: {account_name: [calendar_names]} or empty = all
    selected_calendars: dict[str, list[str]] = field(default_factory=dict)

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
        if self.back_to_back not in ("countdown_music", "silent", "skip"):
            self.back_to_back = "countdown_music"
        if self.mode not in ("countdown_music", "silent", "off"):
            self.mode = "countdown_music"
