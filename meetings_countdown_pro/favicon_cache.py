"""Favicon cache — async fetching with disk cache and fallback."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QObject, QRunnable, QThreadPool, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QPixmap

from meetings_countdown_pro.settings import CONFIG_DIR

log = logging.getLogger(__name__)

CACHE_DIR = CONFIG_DIR / "favicon-cache"
FETCH_TIMEOUT = 0.5  # 500ms per request


class _FetchSignals(QObject):
    finished = pyqtSignal(str, QPixmap)  # domain, pixmap


class _FetchTask(QRunnable):
    """Background task to fetch a favicon for a domain."""

    def __init__(self, domain: str, cache_path: Path) -> None:
        super().__init__()
        self.domain = domain
        self.cache_path = cache_path
        self.signals = _FetchSignals()

    @pyqtSlot()
    def run(self) -> None:
        import requests

        pixmap = QPixmap()
        data: Optional[bytes] = None

        # Try direct favicon first
        try:
            resp = requests.get(
                f"https://{self.domain}/favicon.ico",
                timeout=FETCH_TIMEOUT,
                allow_redirects=True,
            )
            if resp.status_code == 200 and len(resp.content) > 0:
                data = resp.content
        except Exception:
            pass

        # Fallback to Google's favicon service
        if not data:
            try:
                resp = requests.get(
                    f"https://www.google.com/s2/favicons?domain={self.domain}&sz=32",
                    timeout=FETCH_TIMEOUT,
                )
                if resp.status_code == 200 and len(resp.content) > 0:
                    data = resp.content
            except Exception:
                pass

        if data:
            # Save to disk cache
            try:
                self.cache_path.parent.mkdir(parents=True, exist_ok=True)
                self.cache_path.write_bytes(data)
            except OSError:
                pass
            pixmap.loadFromData(data)

        self.signals.finished.emit(self.domain, pixmap)


class FaviconCache(QObject):
    """In-memory + disk cache for domain favicons, fetched asynchronously."""

    favicon_ready = pyqtSignal(str, QPixmap)  # domain, pixmap

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._memory_cache: dict[str, QPixmap] = {}
        self._pending: set[str] = set()

    def get(self, domain: str) -> Optional[QPixmap]:
        """Get favicon from cache (memory or disk). Returns None if not cached."""
        if domain in self._memory_cache:
            pm = self._memory_cache[domain]
            return pm if not pm.isNull() else None
        # Check disk
        path = self._cache_path(domain)
        if path.exists():
            pm = QPixmap(str(path))
            if not pm.isNull():
                self._memory_cache[domain] = pm
                return pm
        return None

    def fetch(self, domain: str) -> None:
        """Fetch favicon asynchronously. Emits favicon_ready when done."""
        if not domain or domain in self._memory_cache or domain in self._pending:
            return

        # Check disk first
        path = self._cache_path(domain)
        if path.exists():
            pm = QPixmap(str(path))
            if not pm.isNull():
                self._memory_cache[domain] = pm
                self.favicon_ready.emit(domain, pm)
                return

        # Fetch in background
        self._pending.add(domain)
        task = _FetchTask(domain, path)
        task.signals.finished.connect(self._on_fetched)
        QThreadPool.globalInstance().start(task)

    def _on_fetched(self, domain: str, pixmap: QPixmap) -> None:
        self._pending.discard(domain)
        self._memory_cache[domain] = pixmap
        self.favicon_ready.emit(domain, pixmap)

    @staticmethod
    def _cache_path(domain: str) -> Path:
        safe = hashlib.md5(domain.encode()).hexdigest()[:12]
        return CACHE_DIR / f"{safe}_{domain}.ico"
