"""About dialog — app icon, version, copyright, license, and update check."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

from PyQt6.QtCore import Qt, QRectF, QSize, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPalette, QPixmap
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from meetings_countdown_pro import (
    __app_name__,
    __author__,
    __author_email__,
    __copyright_years__,
    __license__,
    __repo_url__,
    __tagline__,
    __version__,
)

log = logging.getLogger(__name__)

ASSETS = Path(__file__).parent / "assets"

RED_ACCENT = "#ff6b6b"


# ------------------------------------------------------------------
# Background thread for the GitHub API call
# ------------------------------------------------------------------

class _UpdateCheckThread(QThread):
    """Fetch the latest release tag from GitHub in a background thread."""

    finished = pyqtSignal(str, str)  # (latest_version, release_url) or ("", error_msg)

    def __init__(self, repo_url: str, parent=None) -> None:
        super().__init__(parent)
        self._repo_url = repo_url

    def run(self) -> None:
        try:
            # Extract owner/repo from URL
            match = re.search(r"github\.com/([^/]+/[^/]+)", self._repo_url)
            if not match:
                self.finished.emit("", "Invalid repository URL")
                return
            owner_repo = match.group(1)
            api_url = f"https://api.github.com/repos/{owner_repo}/releases/latest"
            req = Request(api_url, headers={"Accept": "application/vnd.github+json"})
            with urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
            tag = data.get("tag_name", "")
            html_url = data.get("html_url", "")
            # Strip leading "v" if present (e.g. "v1.0.0" -> "1.0.0")
            version = tag.lstrip("v")
            self.finished.emit(version, html_url)
        except URLError as e:
            log.debug("Update check failed: %s", e)
            self.finished.emit("", "Could not connect to GitHub")
        except Exception as e:
            log.debug("Update check failed: %s", e)
            self.finished.emit("", str(e))


# ------------------------------------------------------------------
# About dialog
# ------------------------------------------------------------------

class AboutWindow(QDialog):
    """Modal-style About dialog."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"About {__app_name__}")
        self.setFixedSize(420, 420)

        self._dark = self._is_dark_mode()
        self._update_thread: _UpdateCheckThread | None = None

        # Palette-adaptive colors
        wordmark_color = "#a5b4fc" if self._dark else "#3b3b78"
        muted_color = "#aaa" if self._dark else "#555"
        dim_color = "#888" if self._dark else "#888"
        self._faint_color = "#777" if self._dark else "#999"
        divider_color = "rgba(255,255,255,0.12)" if self._dark else "#d4d4d4"
        self._link_color = "#818cf8" if self._dark else "#6366f1"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 20)
        layout.setSpacing(12)

        # ── Logo row: icon + wordmark ──
        logo_row = QHBoxLayout()
        logo_row.setSpacing(18)
        logo_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_label = QLabel()
        icon_label.setPixmap(self._render_icon(96))
        icon_label.setFixedSize(96, 96)
        logo_row.addWidget(icon_label)

        wordmark = QVBoxLayout()
        wordmark.setSpacing(0)

        lbl_meetings = QLabel("Meetings")
        lbl_meetings.setFont(self._font(26, QFont.Weight.Light))
        lbl_meetings.setStyleSheet(f"color: {wordmark_color};")
        wordmark.addWidget(lbl_meetings)

        lbl_countdown = QLabel("Countdown")
        lbl_countdown.setFont(self._font(26, QFont.Weight.Bold))
        lbl_countdown.setStyleSheet(f"color: {wordmark_color};")
        wordmark.addWidget(lbl_countdown)

        lbl_pro = QLabel("PRO")
        lbl_pro.setFont(self._font(13, QFont.Weight.DemiBold))
        lbl_pro.setStyleSheet(
            f"color: {RED_ACCENT}; letter-spacing: 4px; margin-top: 2px;"
        )
        wordmark.addWidget(lbl_pro)

        logo_row.addLayout(wordmark)
        layout.addLayout(logo_row)

        # ── Divider ──
        layout.addWidget(self._divider(divider_color))

        # ── Version + tagline ──
        info = QVBoxLayout()
        info.setSpacing(4)
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_version = QLabel(f"Version {__version__}")
        lbl_version.setFont(self._font(13, QFont.Weight.Medium))
        lbl_version.setStyleSheet(f"color: {muted_color};")
        lbl_version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info.addWidget(lbl_version)

        lbl_tagline = QLabel(__tagline__)
        lbl_tagline.setFont(self._font(12, QFont.Weight.Normal, italic=True))
        lbl_tagline.setStyleSheet(f"color: {dim_color};")
        lbl_tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_tagline.setWordWrap(True)
        lbl_tagline.setMaximumWidth(380)
        info.addWidget(lbl_tagline, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addLayout(info)

        # ── Update check ──
        update_row = QHBoxLayout()
        update_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        update_row.setSpacing(10)

        self._update_btn = QPushButton("Check for Updates")
        self._update_btn.setFont(self._font(12))
        self._update_btn.setStyleSheet(
            "QPushButton {"
            f"  color: {muted_color};"
            "  background: transparent;"
            f"  border: 1px solid {self._faint_color};"
            "  border-radius: 4px;"
            "  padding: 3px 12px;"
            "}"
            "QPushButton:hover {"
            f"  border-color: {self._link_color};"
            f"  color: {self._link_color};"
            "}"
        )
        self._update_btn.clicked.connect(self._check_for_updates)
        update_row.addWidget(self._update_btn)

        self._update_label = QLabel()
        self._update_label.setFont(self._font(12))
        self._update_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self._update_label.setOpenExternalLinks(True)
        self._update_label.hide()
        update_row.addWidget(self._update_label)

        layout.addLayout(update_row)

        # ── Divider ──
        layout.addWidget(self._divider(divider_color))

        # ── Copyright + license ──
        footer = QVBoxLayout()
        footer.setSpacing(2)
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_copyright = QLabel(
            f"\u00a9 {__copyright_years__} {__author__} \u00b7 {__author_email__}"
        )
        lbl_copyright.setFont(self._font(11))
        lbl_copyright.setStyleSheet(f"color: {self._faint_color};")
        lbl_copyright.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.addWidget(lbl_copyright)

        lbl_license = QLabel(f"Licensed under the {__license__} License")
        lbl_license.setFont(self._font(11))
        lbl_license.setStyleSheet(f"color: {self._faint_color};")
        lbl_license.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.addWidget(lbl_license)

        repo_display = __repo_url__.replace("https://", "")
        lbl_github = QLabel(
            f'<a href="{__repo_url__}"'
            f' style="color: {self._link_color};">{repo_display}</a>'
        )
        lbl_github.setFont(self._font(11))
        lbl_github.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_github.setOpenExternalLinks(True)
        footer.addWidget(lbl_github)

        layout.addLayout(footer)

        # ── OK button ──
        btn = QPushButton("OK")
        btn.setFixedWidth(100)
        btn.setFont(self._font(13, QFont.Weight.Medium))
        btn.setStyleSheet(
            "QPushButton {"
            "  color: white;"
            "  background: qlineargradient(y1:0, y2:1, stop:0 #6366f1, stop:1 #4f46e5);"
            "  border: 1px solid #4338ca;"
            "  border-radius: 6px;"
            "  padding: 5px 24px;"
            "}"
            "QPushButton:hover {"
            "  background: qlineargradient(y1:0, y2:1, stop:0 #7c7ff7, stop:1 #6366f1);"
            "}"
        )
        btn.clicked.connect(self.accept)
        layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)

    # ------------------------------------------------------------------
    # Update check
    # ------------------------------------------------------------------

    def _check_for_updates(self) -> None:
        self._update_btn.setEnabled(False)
        self._update_btn.setText("Checking...")
        self._update_label.hide()

        self._update_thread = _UpdateCheckThread(__repo_url__, parent=self)
        self._update_thread.finished.connect(self._on_update_result)
        self._update_thread.start()

    def _on_update_result(self, latest_version: str, release_url: str) -> None:
        self._update_btn.setEnabled(True)
        self._update_btn.setText("Check for Updates")

        if not latest_version:
            # Error — release_url contains the error message
            self._update_label.setStyleSheet(f"color: {self._faint_color};")
            self._update_label.setText(release_url)
            self._update_label.show()
            return

        if self._is_newer(latest_version, __version__):
            self._update_label.setStyleSheet("")
            self._update_label.setText(
                f'<span style="color: {RED_ACCENT};">New version {latest_version} available</span>'
                f' &mdash; <a href="{release_url}" style="color: {self._link_color};">Download</a>'
            )
        else:
            green = "#34d399" if self._dark else "#059669"
            self._update_label.setStyleSheet(f"color: {green};")
            self._update_label.setText("You are already up to date")

        self._update_label.show()

    @staticmethod
    def _is_newer(latest: str, current: str) -> bool:
        """Return True if latest is strictly newer than current (semver)."""
        def parse(v: str) -> tuple[int, ...]:
            return tuple(int(x) for x in re.findall(r"\d+", v))
        return parse(latest) > parse(current)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _is_dark_mode(self) -> bool:
        return self.palette().color(QPalette.ColorRole.Window).lightness() < 128

    @staticmethod
    def _render_icon(size: int) -> QPixmap:
        renderer = QSvgRenderer(str(ASSETS / "icon.svg"))
        ratio = 2  # retina
        pm = QPixmap(QSize(size * ratio, size * ratio))
        pm.setDevicePixelRatio(ratio)
        pm.fill(QColor(0, 0, 0, 0))
        painter = QPainter(pm)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Render in logical coordinates (painter scales to physical pixels)
        renderer.render(painter, QRectF(0, 0, size, size))
        painter.end()
        return pm

    @staticmethod
    def _font(
        size: int,
        weight: QFont.Weight = QFont.Weight.Normal,
        italic: bool = False,
    ) -> QFont:
        font = QFont("Helvetica Neue")
        font.setPixelSize(size)
        font.setWeight(weight)
        font.setItalic(italic)
        return font

    @staticmethod
    def _divider(color: str) -> QWidget:
        line = QWidget()
        line.setFixedHeight(1)
        line.setStyleSheet(f"background: {color};")
        return line
