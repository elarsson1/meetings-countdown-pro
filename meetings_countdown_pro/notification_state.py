"""Notification state — tracks which meetings have already triggered a countdown."""

from __future__ import annotations

import json
import time
from pathlib import Path

from meetings_countdown_pro.settings import CONFIG_DIR

NOTIFIED_FILE = CONFIG_DIR / "notified.json"
PRUNE_AGE_SECONDS = 24 * 3600  # 24 hours


class NotificationState:
    """Manages the notified.json file for meeting deduplication.

    Composite key: calendarItemExternalIdentifier + "|" + start time ISO string.
    """

    def __init__(self) -> None:
        self._state: dict[str, float] = {}  # key -> timestamp
        self._load()

    def _load(self) -> None:
        if not NOTIFIED_FILE.exists():
            self._state = {}
            return
        try:
            with open(NOTIFIED_FILE) as f:
                self._state = json.load(f)
        except (json.JSONDecodeError, TypeError):
            self._state = {}

    def _save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(NOTIFIED_FILE, "w") as f:
            json.dump(self._state, f, indent=2)

    def is_notified(self, key: str) -> bool:
        return key in self._state

    def mark_notified(self, key: str) -> None:
        self._state[key] = time.time()
        self._save()

    def prune(self) -> None:
        """Remove entries older than 24 hours."""
        cutoff = time.time() - PRUNE_AGE_SECONDS
        before = len(self._state)
        self._state = {k: v for k, v in self._state.items() if v > cutoff}
        if len(self._state) != before:
            self._save()
