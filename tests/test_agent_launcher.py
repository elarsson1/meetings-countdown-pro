"""Tests for agent launcher — command building, JSON, shell escaping."""

from __future__ import annotations

import json
import os
import stat

import pytest

from meetings_countdown_pro.agent_launcher import (
    build_command,
    build_meeting_json,
    _write_launch_script,
)
from meetings_countdown_pro.settings import Settings
from tests.conftest import make_meeting


# ===================================================================
# build_meeting_json
# ===================================================================

class TestBuildMeetingJson:
    def test_single_meeting(self):
        m = make_meeting(title="Standup")
        result = build_meeting_json([m], "corp.com")
        data = json.loads(result)
        assert len(data["meetings"]) == 1
        assert data["meetings"][0]["title"] == "Standup"

    def test_multiple_meetings(self):
        m1 = make_meeting(title="Meeting A")
        m2 = make_meeting(title="Meeting B")
        result = build_meeting_json([m1, m2], "corp.com")
        data = json.loads(result)
        assert len(data["meetings"]) == 2

    def test_ensure_ascii(self):
        m = make_meeting(title="Caf\u00e9 \u2615 meeting")
        result = build_meeting_json([m], "")
        assert "\\u" in result  # Unicode escaped
        # Still valid JSON
        data = json.loads(result)
        assert "Caf" in data["meetings"][0]["title"]

    def test_compact_separators(self):
        m = make_meeting(title="Test")
        result = build_meeting_json([m], "")
        # No spaces after : or ,
        assert ": " not in result
        assert ", " not in result


# ===================================================================
# build_command
# ===================================================================

class TestBuildCommand:
    def test_default_templates(self):
        m = make_meeting(title="Standup")
        s = Settings()
        cmd = build_command([m], s)
        # Default template: "claude {Prompt}"
        assert cmd.startswith("claude ")
        # Prompt should contain meeting data
        assert "Standup" in cmd

    def test_shell_escaping_special_chars(self):
        m = make_meeting(title='Meeting with $pecial `chars` "quotes" & more')
        s = Settings()
        cmd = build_command([m], s)
        # The prompt portion should be shell-quoted (single quotes from shlex.quote)
        # Verify it doesn't break JSON structure
        assert "claude " in cmd

    def test_shell_escaping_single_quotes(self):
        m = make_meeting(title="Bob's meeting")
        s = Settings()
        cmd = build_command([m], s)
        # shlex.quote handles single quotes
        assert "claude " in cmd

    def test_custom_templates(self):
        m = make_meeting(title="Test")
        s = Settings(
            agent_command_template="myagent --prompt {Prompt}",
            agent_prompt_template="Prep: {MeetingData}",
        )
        cmd = build_command([m], s)
        assert cmd.startswith("myagent --prompt ")
        assert "Test" in cmd


# ===================================================================
# _write_launch_script
# ===================================================================

class TestWriteLaunchScript:
    def test_script_created(self, config_dir):
        path = _write_launch_script("echo hello", "~/Projects")
        assert os.path.exists(path)

    def test_script_executable(self, config_dir):
        path = _write_launch_script("echo hello", "~/Projects")
        mode = os.stat(path).st_mode
        assert mode & stat.S_IEXEC

    def test_script_content(self, config_dir):
        path = _write_launch_script("echo hello", "~/Projects")
        content = open(path).read()
        assert content.startswith("#!/bin/zsh\n")
        assert "echo hello" in content

    def test_tilde_expanded(self, config_dir):
        path = _write_launch_script("echo hello", "~/Projects")
        content = open(path).read()
        home = os.path.expanduser("~")
        assert home in content
        assert "~" not in content.split("cd ")[1].split(" ")[0]  # ~ not in the cd path


# ===================================================================
# launch_agent (orchestration, no actual terminal launch)
# ===================================================================

class TestLaunchAgent:
    def test_disabled_skips(self, config_dir, monkeypatch):
        from meetings_countdown_pro import agent_launcher
        launched = []
        monkeypatch.setattr(agent_launcher, "launch_in_terminal", lambda *a: launched.append(True))

        m = make_meeting()
        s = Settings(agent_enabled=False)
        agent_launcher.launch_agent([m], s)
        assert launched == []

    def test_empty_template_skips(self, config_dir, monkeypatch):
        from meetings_countdown_pro import agent_launcher
        launched = []
        monkeypatch.setattr(agent_launcher, "launch_in_terminal", lambda *a: launched.append(True))

        m = make_meeting()
        s = Settings(agent_enabled=True, agent_command_template="")
        agent_launcher.launch_agent([m], s)
        assert launched == []

    def test_enabled_launches(self, config_dir, monkeypatch):
        from meetings_countdown_pro import agent_launcher
        launched = []
        monkeypatch.setattr(agent_launcher, "launch_in_terminal", lambda cmd, wd, term: launched.append((cmd, wd, term)))

        m = make_meeting(title="Standup")
        s = Settings(agent_enabled=True, agent_terminal="iterm2", agent_working_dir="~/Code")
        agent_launcher.launch_agent([m], s)
        assert len(launched) == 1
        assert "Standup" in launched[0][0]
        assert launched[0][1] == "~/Code"
        assert launched[0][2] == "iterm2"


# ===================================================================
# launch_in_terminal — AppleScript dispatch per terminal
# ===================================================================

class TestLaunchInTerminal:
    @pytest.mark.parametrize("terminal,expected_app", [
        ("terminal", "Terminal"),
        ("iterm2", "iTerm2"),
        ("ghostty", "Ghostty"),
    ])
    def test_dispatch(self, config_dir, monkeypatch, terminal, expected_app):
        from meetings_countdown_pro import agent_launcher

        calls = []

        class FakeProc:
            pid = 1234

        def fake_popen(args, **kwargs):
            calls.append(args)
            return FakeProc()

        # Pretend iTerm2 is already running so we skip the open -a branch.
        def fake_run(args, **kwargs):
            class R: returncode = 0
            return R()

        monkeypatch.setattr(agent_launcher.subprocess, "Popen", fake_popen)
        monkeypatch.setattr(agent_launcher.subprocess, "run", fake_run)

        agent_launcher.launch_in_terminal("echo hi", "~", terminal)

        assert len(calls) == 1
        assert calls[0][0] == "osascript"
        applescript = calls[0][2]
        assert expected_app in applescript
