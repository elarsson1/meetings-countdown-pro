"""Tests for NotificationState — dedup and pruning."""

from __future__ import annotations

import json
import time

import pytest

from meetings_countdown_pro.notification_state import NotificationState


# ===================================================================
# Core operations
# ===================================================================

class TestCoreOps:
    def test_unknown_key_not_notified(self, config_dir):
        ns = NotificationState()
        assert ns.is_notified("unknown-key") is False

    def test_mark_then_check(self, config_dir):
        ns = NotificationState()
        ns.mark_notified("meeting-1|2026-04-01T14:00:00")
        assert ns.is_notified("meeting-1|2026-04-01T14:00:00") is True

    def test_independent_keys(self, config_dir):
        ns = NotificationState()
        ns.mark_notified("key-a")
        ns.mark_notified("key-b")
        assert ns.is_notified("key-a") is True
        assert ns.is_notified("key-b") is True
        assert ns.is_notified("key-c") is False

    def test_persistence_across_instances(self, config_dir):
        ns1 = NotificationState()
        ns1.mark_notified("persist-key")

        ns2 = NotificationState()
        assert ns2.is_notified("persist-key") is True


# ===================================================================
# Pruning
# ===================================================================

class TestPruning:
    def test_prune_old_entries(self, config_dir):
        old_ts = time.time() - 25 * 3600  # 25 hours ago
        data = {"old-key": old_ts, "recent-key": time.time()}
        (config_dir / "notified.json").write_text(json.dumps(data))

        ns = NotificationState()
        ns.prune()
        assert ns.is_notified("old-key") is False
        assert ns.is_notified("recent-key") is True

    def test_prune_keeps_recent(self, config_dir):
        ns = NotificationState()
        ns.mark_notified("fresh")
        ns.prune()
        assert ns.is_notified("fresh") is True

    def test_prune_all_old(self, config_dir):
        old_ts = time.time() - 48 * 3600
        data = {"a": old_ts, "b": old_ts}
        (config_dir / "notified.json").write_text(json.dumps(data))

        ns = NotificationState()
        ns.prune()
        assert ns.is_notified("a") is False
        assert ns.is_notified("b") is False


# ===================================================================
# Edge cases
# ===================================================================

class TestEdgeCases:
    def test_corrupt_file(self, config_dir):
        (config_dir / "notified.json").write_text("{{bad json")
        ns = NotificationState()
        assert ns.is_notified("anything") is False
        # Can still mark new entries
        ns.mark_notified("new-key")
        assert ns.is_notified("new-key") is True

    def test_missing_file(self, config_dir):
        ns = NotificationState()
        assert ns.is_notified("anything") is False
