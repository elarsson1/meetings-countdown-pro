# Design: AI Agent Integration

**Status:** Draft
**Date:** 2026-03-28

---

## 1. Overview

Launch a user-configured command (typically a coding agent like Claude Code or Kiro) in the user's preferred terminal when a countdown starts. The command receives meeting context via a prompt template with variable substitution, enabling AI-assisted meeting prep or any custom automation.

Despite the "AI" branding, the feature is terminal-command-generic — users can hook it up to a shell script, a different agent, or anything that runs in a terminal.

---

## 2. User Experience

When a countdown triggers and the feature is enabled:

1. The app substitutes meeting variables into the configured prompt template.
2. The app constructs the full command line (e.g., `claude "..."` or `kiro-cli chat "..."`).
3. The app opens the user's configured terminal application with that command, in the configured working directory.
4. The terminal window appears alongside the countdown window. The user can interact with the agent while the countdown runs.

The agent session persists after the countdown ends — it's a normal interactive terminal session.

---

## 3. Configuration (New "Agent" Preferences Tab)

### 3.1 Settings

| # | Setting | Type | Default | Description |
|---|---|---|---|---|
| 1 | Enable AI Agent | Checkbox | Off | Master toggle for the feature. Also controllable from the menu bar. |
| 2 | Terminal Application | Dropdown | Terminal.app | Which terminal to launch: "Terminal.app" or "iTerm2". |
| 3 | Working Directory | Directory picker + text field | `~` | The directory the agent starts in. This is where the user organizes their meeting notes/docs. |
| 4 | Command Template | Text field (single line) | `claude {Prompt}` | The shell command to execute. Must contain `{Prompt}` placeholder where the assembled prompt is inserted. No quotes around `{Prompt}` — `shlex.quote()` handles that. |
| 5 | Prompt Template | Multi-line text area | *(see below)* | The prompt text with the `{MeetingData}` variable placeholder. |

**Default Prompt Template:**
```
Please help me prep for this meeting: {MeetingData}
```

### 3.2 The `{MeetingData}` Variable

The prompt template supports a single variable: **`{MeetingData}`** — a JSON structure containing all meeting context from the countdown window. This avoids a proliferation of individual variables and handles all cases cleanly (single meeting, simultaneous meetings, missing fields).

The agent (or script) parses the JSON to extract what it needs.

**Example JSON (single meeting):**
```json
{
  "meetings": [
    {
      "title": "Q1 Pipeline Review with Acme Corp",
      "date": "2026-03-28",
      "start_time": "2:00 PM",
      "end_time": "2:30 PM",
      "calendar": "Work",
      "video_link": "https://zoom.us/j/1234567890",
      "attendees": [
        {"name": "Alice Chen", "email": "alice@example.com", "type": "internal"},
        {"name": "Bob Martinez", "email": "bob@example.com", "type": "internal"},
        {"name": "Carol White", "email": "carol@acme.com", "type": "external", "org": "acme.com"},
        {"name": "Eve Parker", "email": "eve@globex.net", "type": "external", "org": "globex.net"}
      ]
    }
  ]
}
```

**Example JSON (simultaneous meetings):**
```json
{
  "meetings": [
    {
      "title": "Q1 Pipeline Review with Acme Corp",
      "date": "2026-03-28",
      "start_time": "2:00 PM",
      "end_time": "2:30 PM",
      "calendar": "Work",
      "video_link": "https://zoom.us/j/1234567890",
      "attendees": [...]
    },
    {
      "title": "Globex Contract Discussion",
      "date": "2026-03-28",
      "start_time": "2:00 PM",
      "end_time": "3:00 PM",
      "calendar": "Work",
      "video_link": null,
      "attendees": [...]
    }
  ]
}
```

The `type` field on each attendee is `"internal"` or `"external"` based on the configured internal domain. If no internal domain is configured, all attendees have `"type": "attendee"`. The `org` field is only present for external attendees.

### 3.3 UI Layout Sketch

```
┌─ Agent ─────────────────────────────────────────────────┐
│                                                         │
│  [X] Enable AI Agent at countdown start                 │
│                                                         │
│  Terminal Application                                   │
│  [ iTerm2                              ▼ ]              │
│                                                         │
│  Working Directory                                      │
│  [ ~/Documents/meeting-notes     ] [ Browse... ]        │
│                                                         │
│  Command Template                                       │
│  [ claude --prompt "{Prompt}"                    ]      │
│                                                         │
│  Prompt Template                                        │
│  ┌──────────────────────────────────────────────┐       │
│  │ Please help me prep for this meeting using   │       │
│  │ the MeetingPrep template: {MeetingData}      │       │
│  │                                              │       │
│  └──────────────────────────────────────────────┘       │
│  {MeetingData} is replaced with a JSON object           │
│  containing meeting titles, times, attendees,           │
│  video links, and calendar info.                        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 4. Technical Design

### 4.1 Command Assembly & Shell Escaping

Assembly is a two-step process:

1. **Render the prompt:** Replace `{MeetingData}` in the prompt template with the compact JSON string.
2. **Insert into command:** Replace `{Prompt}` in the command template with the shell-escaped rendered prompt.

```python
import json
import shlex

meeting_json = json.dumps(meeting_data, ensure_ascii=True)  # compact, ASCII-safe
rendered_prompt = prompt_template.replace("{MeetingData}", meeting_json)
safe_prompt = shlex.quote(rendered_prompt)
command = command_template.replace("{Prompt}", safe_prompt)
```

**Escaping layers:**
- `json.dumps()` handles escaping of quotes and special characters within the JSON string values.
- `shlex.quote()` wraps the entire rendered prompt in single quotes for safe shell passing, escaping any internal single quotes.
- The user should NOT add quotes around `{Prompt}` in the command template — `shlex.quote()` handles that.

**Edge cases:**
- Meeting titles with quotes, ampersands, semicolons, backticks, etc. are all safe — handled by the JSON + shlex double escaping.
- If the prompt template doesn't contain `{MeetingData}`, it's sent as-is (static prompt).
- `ensure_ascii=True` avoids encoding issues in shell transport — emoji and Unicode in meeting titles are escaped to `\uXXXX` sequences in the JSON, which the agent decodes.

### 4.2 Terminal Launch

Each terminal app has a different mechanism for "open a new window, run this command in this directory":

**Terminal.app:**
```python
osascript -e '
  tell application "Terminal"
    activate
    do script "cd /path/to/dir && <command>"
  end tell
'
```

**iTerm2:**
```python
osascript -e '
  tell application "iTerm2"
    activate
    set newWindow to (create window with default profile)
    tell current session of newWindow
      write text "cd /path/to/dir && <command>"
    end tell
  end tell
'
```

Only Terminal.app and iTerm2 are supported in v1. Both have reliable AppleScript support. Additional terminals (Warp, Ghostty, etc.) can be added later if needed.

### 4.3 Trigger Point

In `app.py`, `_trigger_countdown()` is the natural place. After creating the countdown window:

```python
if self._settings.agent_enabled:
    self._launch_agent(meetings)
```

The launch is fire-and-forget — we don't track the terminal/agent process. The user manages their own terminal session.

### 4.4 Simultaneous Meetings

All simultaneous meetings are included in the `meetings` array in the JSON. The agent receives the full picture and can help prep for all of them. Only one agent session is launched — not one per meeting.

### 4.5 Test Mode

The "Test Countdown" button in Settings should also trigger the agent launch (if enabled), so users can verify their configuration without waiting for a real meeting.

---

## 5. Settings Persistence

New fields in `settings.json`:

```json
{
  "agent_enabled": false,
  "agent_terminal": "terminal",
  "agent_working_dir": "~/Documents/meeting-notes",
  "agent_command_template": "claude {Prompt}",
  "agent_prompt_template": "Please help me prep for this meeting: {MeetingData}"
}
```

---

## 6. Menu Bar Integration

The menu bar gets an additional toggle for the AI Agent feature, between the mode radio group and "Settings...":

```
┌──────────────────────────────────────┐
│  Next: 2:00 PM — Weekly Standup     │
│  ─────────────────────────────────── │
│  ● Countdown + Music                │
│  ○ Countdown (Silent)               │
│  ○ Off                              │
│  ─────────────────────────────────── │
│  ☑ AI Agent                         │
│  ─────────────────────────────────── │
│  Settings...                         │
│  ─────────────────────────────────── │
│  Quit Meetings Countdown Pro         │
└──────────────────────────────────────┘
```

- Checkbox toggle, synced with the "Enable AI Agent" setting in the Agent prefs tab.
- Toggling updates `settings.json` immediately (same as mode selection).
- Shown regardless of whether the agent is fully configured — lets the user quickly disable/enable without opening Settings.

---

## 7. Resolved Decisions

| # | Question | Resolution |
|---|---|---|
| 1 | Command template vs. agent picker | Command template — more flexible, supports non-AI use cases |
| 2 | Terminal detection | No auto-detection. Static dropdown: Terminal.app, iTerm2 |
| 3 | Multiple monitors | Let the OS decide terminal window placement |
| 4 | Agent launch timing | Immediately when countdown window opens |
| 5 | Temp script / other terminals | Not in v1. Only Terminal.app and iTerm2 via AppleScript |
| 6 | Menu bar control | Checkbox toggle in menu bar, synced with prefs |

---

## 8. Out of Scope (v1 of this feature)

- Tracking or interacting with the agent session programmatically
- Passing structured data (JSON) to the agent — prompt is plain text
- Multiple agent launches per meeting
- Agent-specific integrations (MCP servers, tool configurations, etc.)
- Linux/Windows support (macOS terminal launch only)
