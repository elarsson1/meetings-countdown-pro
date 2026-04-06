"""Tests for About dialog."""

from __future__ import annotations

import pytest
from PyQt6.QtWidgets import QLabel, QPushButton

from meetings_countdown_pro import __version__, __copyright_years__, __author__
from meetings_countdown_pro.about_window import AboutWindow, _UpdateCheckThread


class TestAboutWindow:
    def test_creates_without_error(self, qtbot):
        w = AboutWindow()
        qtbot.addWidget(w)
        w.show()
        assert w.isVisible()

    def test_displays_correct_version(self, qtbot):
        w = AboutWindow()
        qtbot.addWidget(w)
        version_labels = [
            lbl.text() for lbl in w.findChildren(QLabel) if __version__ in lbl.text()
        ]
        assert len(version_labels) == 1
        assert version_labels[0] == f"Version {__version__}"

    def test_displays_copyright(self, qtbot):
        w = AboutWindow()
        qtbot.addWidget(w)
        copyright_labels = [
            lbl.text() for lbl in w.findChildren(QLabel) if __author__ in lbl.text()
        ]
        assert len(copyright_labels) == 1
        assert __copyright_years__ in copyright_labels[0]

    def test_ok_button_closes(self, qtbot):
        w = AboutWindow()
        qtbot.addWidget(w)
        w.show()
        buttons = [b for b in w.findChildren(QPushButton) if b.text() == "OK"]
        assert len(buttons) == 1
        buttons[0].click()
        assert not w.isVisible()

    def test_check_for_updates_button_exists(self, qtbot):
        w = AboutWindow()
        qtbot.addWidget(w)
        buttons = [b for b in w.findChildren(QPushButton) if "Update" in b.text()]
        assert len(buttons) == 1


class TestVersionComparison:
    def test_newer_patch(self):
        assert AboutWindow._is_newer("1.0.1", "1.0.0") is True

    def test_newer_minor(self):
        assert AboutWindow._is_newer("1.1.0", "1.0.0") is True

    def test_newer_major(self):
        assert AboutWindow._is_newer("2.0.0", "1.0.0") is True

    def test_same_version(self):
        assert AboutWindow._is_newer("1.0.0", "1.0.0") is False

    def test_older_version(self):
        assert AboutWindow._is_newer("0.9.0", "1.0.0") is False

    def test_with_v_prefix(self):
        assert AboutWindow._is_newer("1.1.0", "1.0.0") is True


class TestUpdateResult:
    def test_up_to_date(self, qtbot):
        w = AboutWindow()
        qtbot.addWidget(w)
        w._on_update_result(__version__, "https://example.com/release")
        assert not w._update_label.isHidden()
        assert "up to date" in w._update_label.text().lower()

    def test_new_version_available(self, qtbot):
        w = AboutWindow()
        qtbot.addWidget(w)
        w._on_update_result("99.0.0", "https://example.com/release")
        assert not w._update_label.isHidden()
        assert "99.0.0" in w._update_label.text()
        assert "Download" in w._update_label.text()

    def test_error(self, qtbot):
        w = AboutWindow()
        qtbot.addWidget(w)
        w._on_update_result("", "Could not connect to GitHub")
        assert not w._update_label.isHidden()
        assert "Could not connect" in w._update_label.text()

    def test_button_re_enabled_after_result(self, qtbot):
        w = AboutWindow()
        qtbot.addWidget(w)
        w._on_update_result(__version__, "https://example.com")
        assert w._update_btn.isEnabled()
        assert w._update_btn.text() == "Check for Updates"
