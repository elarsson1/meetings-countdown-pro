"""AI Agent launcher — assembles command from templates and launches in a terminal."""

from __future__ import annotations

import json
import logging
import os
import shlex
import stat
import subprocess

from meetings_countdown_pro.meeting import Meeting
from meetings_countdown_pro.settings import CONFIG_DIR, Settings

log = logging.getLogger(__name__)


def build_meeting_json(meetings: list[Meeting], internal_domain: str) -> str:
    """Build the compact JSON string for {MeetingData} substitution."""
    data = {"meetings": [m.to_json_data(internal_domain) for m in meetings]}
    result = json.dumps(data, ensure_ascii=True, separators=(",", ":"))
    log.debug("Meeting JSON built: %d meeting(s), %d chars", len(meetings), len(result))
    return result


def build_command(meetings: list[Meeting], settings: Settings) -> str:
    """Assemble the full shell command from templates and meeting data.

    1. Render {MeetingData} into the prompt template.
    2. Shell-escape the rendered prompt.
    3. Insert into the command template at {Prompt}.
    """
    log.debug(
        "Building command: template=%r, prompt_template=%r",
        settings.agent_command_template, settings.agent_prompt_template[:80],
    )
    meeting_json = build_meeting_json(meetings, settings.internal_domain)
    rendered_prompt = settings.agent_prompt_template.replace("{MeetingData}", meeting_json)
    log.debug("Rendered prompt: %d chars", len(rendered_prompt))
    safe_prompt = shlex.quote(rendered_prompt)
    command = settings.agent_command_template.replace("{Prompt}", safe_prompt)
    log.debug("Final command: %s", command[:300])
    return command


def _write_launch_script(command: str, working_dir: str) -> str:
    """Write the agent command to a temp shell script and return its path.

    Using a script file avoids escaping issues when passing long commands
    with JSON through AppleScript's write text / do script.
    """
    resolved_dir = os.path.expanduser(working_dir)
    script_path = CONFIG_DIR / "agent-launch.sh"
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    script_content = f"#!/bin/zsh\ncd {shlex.quote(resolved_dir)} && {command}\n"
    script_path.write_text(script_content)
    script_path.chmod(script_path.stat().st_mode | stat.S_IEXEC)
    log.debug("Launch script written: %s (%d bytes)", script_path, len(script_content))
    return str(script_path)


def launch_in_terminal(command: str, working_dir: str, terminal: str) -> None:
    """Launch a command in a new terminal window via AppleScript.

    Supports 'terminal' (Terminal.app) and 'iterm2' (iTerm2).
    The command is written to a temp script to avoid AppleScript escaping issues.
    """
    script_file = _write_launch_script(command, working_dir)
    zsh_cmd = f"zsh -l {shlex.quote(script_file)}"

    if terminal == "iterm2":
        # Use the 'command' parameter on create window — this runs the
        # command as the session's shell process directly, avoiding the
        # unreliable 'write text' approach which simulates typing.
        applescript = f'''
            tell application "iTerm2"
                activate
                create window with default profile command "{zsh_cmd}"
            end tell
        '''
    else:
        # Terminal.app (default)
        applescript = f'''
            tell application "Terminal"
                activate
                do script "{zsh_cmd}"
            end tell
        '''

    log.info("Launching agent in %s (script: %s)", terminal, script_file)
    log.debug("AppleScript command: %s", zsh_cmd)

    try:
        proc = subprocess.Popen(
            ["osascript", "-e", applescript],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        log.debug("osascript launched (pid: %d)", proc.pid)
    except OSError as e:
        log.warning("Failed to launch agent terminal: %s", e)


def launch_agent(meetings: list[Meeting], settings: Settings) -> None:
    """High-level entry point: build command and launch in configured terminal."""
    if not settings.agent_enabled:
        log.debug("Agent launch skipped (disabled)")
        return
    if not settings.agent_command_template:
        log.warning("Agent enabled but no command template configured")
        return

    log.debug(
        "Agent launch: terminal=%s, working_dir=%s, %d meeting(s)",
        settings.agent_terminal, settings.agent_working_dir, len(meetings),
    )
    command = build_command(meetings, settings)
    launch_in_terminal(command, settings.agent_working_dir, settings.agent_terminal)
