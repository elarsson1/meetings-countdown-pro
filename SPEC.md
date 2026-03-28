# Meetings Countdown Pro - Product Specification

**Version:** 0.4 (Draft)
**Date:** 2026-03-27
**Status:** Under Review

---

## 1. Overview

Meetings Countdown Pro is a native macOS desktop application that monitors the user's calendar and provides a dramatic, broadcast-style countdown before each video meeting. Inspired by the BBC News Countdown concept, this is the "enterprise-grade" version designed for professionals whose workdays are filled with back-to-back video calls (sales teams, account managers, consultants, etc.).

The application runs as a background process with a macOS menu bar presence, polls the system calendar for upcoming meetings, and at a configurable time before each meeting, opens a countdown window with synchronized music, meeting details, and a one-click join button.

---

## 2. Platform & Technology Stack

| Component | Technology |
|---|---|
| Language | Python 3.11+ (python.org framework build; see Section 13.1) |
| GUI Framework | PyQt6 |
| Calendar Access | `pyobjc` (EventKit framework bindings) — accesses macOS Calendar.app data directly, supporting any provider synced to macOS Calendar (Google, Microsoft 365, iCloud, Exchange, CalDAV, etc.) |
| Audio Playback | `QMediaPlayer` (PyQt6 multimedia) — leverages macOS native codecs via AVFoundation for MP3, WAV, FLAC, AAC support |
| Animations | Qt-native (`QPropertyAnimation` + `QPainter` + SVG assets) — zero extra dependencies, crisp Retina rendering |
| Favicon Retrieval | `requests` with aggressive timeouts; fallback to Google's favicon service |
| Configuration | JSON file(s) in `~/.config/meetings-countdown-pro/` |
| Packaging | PyInstaller for native macOS .app bundle (self-contained, no Python required by end user) |
| Minimum macOS Version | macOS 13 (Ventura) — required for current EventKit APIs |

---

## 3. Architecture

### 3.1 Process Model

```
┌─────────────────────────────────────────────────┐
│                  Main Process                    │
│                                                  │
│  ┌──────────────┐  ┌─────────────────────────┐  │
│  │  Menu Bar     │  │  Calendar Poll Timer    │  │
│  │  (NSStatusItem│  │  (QTimer, every 30s)    │  │
│  │   via PyQt)   │  │                         │  │
│  └──────────────┘  └────────┬────────────────┘  │
│                              │                   │
│                    ┌─────────▼─────────┐         │
│                    │  Meeting Scheduler │         │
│                    │  (evaluates next   │         │
│                    │   countdown)       │         │
│                    └─────────┬─────────┘         │
│                              │                   │
│                    ┌─────────▼─────────┐         │
│                    │ Countdown Window   │         │
│                    │ (QWidget, shown    │         │
│                    │  when triggered)   │         │
│                    └───────────────────┘         │
└─────────────────────────────────────────────────┘
```

### 3.2 Calendar Polling

- A `QTimer` fires every **30 seconds** to query macOS EventKit for calendar events.
- Query window: now → end of local day (23:59:59). This ensures the menu bar always shows the next upcoming meeting regardless of how far away it is.
- Results are filtered per user configuration (calendar selection, video-only, tentative/accepted, all-day exclusion).
- The next eligible meeting is identified and a one-shot `QTimer` is scheduled to trigger the countdown window at exactly `meeting_start - countdown_seconds`.

### 3.3 State Persistence

Two files in `~/.config/meetings-countdown-pro/`:

| File | Purpose |
|---|---|
| `settings.json` | All user configuration (see Section 8) |
| `notified.json` | Dictionary of meeting occurrence UUIDs already notified, with timestamps. Entries older than 24 hours are pruned on each app launch to prevent unbounded growth. |

---

## 4. Menu Bar

### 4.1 Icon

A small clock/countdown-themed icon in the macOS menu bar. The icon should have two visual states:
- **Active (enabled):** Full-color icon
- **Disabled:** Greyed-out icon

### 4.2 Drop-down Menu

```
┌──────────────────────────────────────┐
│  Next: 2:00 PM — Weekly Standup     │
│  ─────────────────────────────────── │
│  ● Countdown + Music                │
│  ○ Countdown (Silent)               │
│  ○ Off                              │
│  ─────────────────────────────────── │
│  Settings...                         │
│  ─────────────────────────────────── │
│  Quit Meetings Countdown Pro         │
└──────────────────────────────────────┘
```

- **Next meeting line:** Shows subject, time, and a countdown like "(in 23 min)". If no upcoming meetings today, shows "No more meetings today".
- **Mode radio group:** Three mutually exclusive options:
  - **Countdown + Music** — full experience (default)
  - **Countdown (Silent)** — visual countdown only, no audio
  - **Off** — countdowns disabled entirely; app remains in menu bar for quick re-enable
- **Settings...** — opens the Settings window
- **Quit** — exits the application

---

## 5. Countdown Window

### 5.1 Window Behavior

- **Position:** Upper-right corner of the primary display, inset ~20px from screen edges.
- **Size:** Approximately 600×300pt (to be refined in mockups).
- **Window level:** Floating window (always on top of regular windows, but below system dialogs).
- **Appearance:** Frameless (no title bar), with rounded corners and a subtle drop shadow. Dark background theme for a broadcast/studio aesthetic.
- **Animation:** Slides in from the right edge of the screen over ~300ms.
- **Close behavior:** Clicking the X button or pressing Escape dismisses the window and stops audio. The meeting is still marked as notified (no repeat countdown).

### 5.2 Layout

```
┌──────────────────────────────────────────────────────────────┐
│  [X]                                                         │
│                                                              │
│  ┌─────────────────────────────┐  ┌────────────────────────┐ │
│  │  MEETING SUBJECT HEADING    │  │                        │ │
│  │  2:00 PM – 2:30 PM         │  │        00:47           │ │
│  │  5 attendees · 2 internal   │  │                        │ │
│  │  3 external from 2 orgs     │  │   (large countdown)    │ │
│  │                             │  │                        │ │
│  │  ┌─ scrollable ──────────┐  │  │                        │ │
│  │  │ INTERNAL ATTENDEES    │  │  └────────────────────────┘ │
│  │  │ • Alice Smith         │  │                             │
│  │  │ • Bob Jones           │  │                             │
│  │  │                       │  │  ┌────────────────────────┐ │
│  │  │ EXTERNAL ATTENDEES    │  │  │     [ Join Now ]       │ │
│  │  │ 🌐 acme.com          │  │  └────────────────────────┘ │
│  │  │   • Carol White       │  │                             │
│  │  │   • Dave Brown        │  │            🔊              │
│  │  │ 🌐 globex.net        │  │                             │
│  │  │   • Eve Black         │  │                             │
│  │  └───────────────────────┘  │                             │
│  └─────────────────────────────┘                             │
└──────────────────────────────────────────────────────────────┘
```

### 5.3 Countdown Display

- **Font:** Large, bold, proportional sans-serif (e.g., SF Pro Display or Helvetica Neue) — consistent with the BBC Countdown aesthetic. Not monospaced.
- **Format:** Always seconds only (e.g., `90`, `47`, `3`). No `MM:SS` — matches the real BBC Countdown which counts down from 90 in whole seconds.
- **Update frequency:** Every 1 second (visual tick), with millisecond-precision timing internally to prevent drift.
- **Color:** White text, or optionally shifts to amber/red in the final 10 seconds.

### 5.4 Meeting Info Panel (Left Side)

The entire left pane is a single scrollable area containing meeting details and attendee lists.

**Single meeting (typical case):**

- **Subject:** Meeting title in bold, prominent text. Truncated with ellipsis if too long.
- **Time:** Start – End time in the user's local timezone.
- **Attendee summary line:** Always shown below the time. Format: "{N} attendees · {X} internal, {Y} external from {Z} orgs". If no internal domain is configured, just "{N} attendees". This gives at-a-glance context even if the full list is long.
- **Attendee list:**
  - **Internal Attendees:** Listed under an "Internal" header. Sorted alphabetically by display name. Attendees whose email domain matches the configured internal domain.
  - **External Attendees:** Listed under an "External" header. **Grouped by email domain**, each domain group headed by the domain's favicon (16×16) and the domain name. Within each domain group, sorted alphabetically by display name. Domain groups themselves are sorted alphabetically by domain name.
- **Join Now button:** Shown inline at the bottom of the meeting details (in addition to the right-side button).

**Multiple simultaneous meetings:**

When two or more meetings start at the same time, all meetings are listed sequentially in the left pane, each with their own subject, time, attendee summary, attendee list, and individual Join Now button. The user scrolls to see all meetings. In this scenario:
- The right-side Join Now button is hidden (each meeting has its own inline Join button).
- **Auto-join is disabled** — the user must explicitly choose which meeting to join.
- The countdown clock still counts down to the shared start time.

**Attendee display rules:**
- Show display name (from calendar) if available.
- If the calendar provides a formatted address like `"Axel Larsson" <alarsson@example.com>`, parse out the display name.
- If only a bare email address is available (e.g., `alarsson@example.com`), show the email as-is.
- **No self-exclusion:** The user's own name will appear in the attendee list (typically as an internal attendee). Reliably identifying the user across calendar providers is not worth the complexity for v1.

### 5.5 Favicon Handling

- Favicons are fetched from `https://{domain}/favicon.ico` with a **500ms timeout** per request.
- If the direct fetch fails, fall back to `https://www.google.com/s2/favicons?domain={domain}&sz=32` (also with 500ms timeout).
- **Cache:** Favicons are cached in memory for the lifetime of the app session and on disk in `~/.config/meetings-countdown-pro/favicon-cache/` to avoid repeated fetches.
- **Failure mode:** If both fetch attempts fail or timeout, display a generic globe icon as placeholder. Never block window rendering.
- All favicon fetches happen asynchronously on a background thread.

### 5.6 Join Now Button

- Displayed only when a video meeting link is detected in the calendar event.
- **Detection:** Scan the event's URL field, location field, and notes/body for patterns matching:
  - **Zoom:** `https://.*zoom.us/j/...` or `https://.*zoom.us/my/...`
  - **Google Meet:** `https://meet.google.com/...`
  - **Microsoft Teams:** `https://teams.microsoft.com/l/meetup-join/...`
- If multiple links are found, use the first match (priority order: URL field > location > notes).
- **Action:** Opens the meeting link in the system default browser via `QDesktopServices.openUrl()`.
- **Auto-join option:** If the "Auto-Join at Countdown End" setting is enabled, the meeting link is automatically opened when the countdown reaches zero. The Join Now button remains available for manual use at any time during the countdown.
- **Style:** Prominent, high-contrast button (e.g., green or blue).

### 5.7 Countdown End Animation

Built entirely with Qt-native animations (`QPropertyAnimation`, `QPainter`, SVG assets) for zero extra dependencies and crisp Retina rendering.

When the countdown reaches `00:00`:

1. **Phase 1 — "Action" Clapperboard (~2 seconds):** The countdown number area transitions to a stylized movie clapperboard/slate SVG graphic with "ACTION!" text. The clapperboard top bar animates a clap via `QPropertyAnimation` (rotation).
2. **Phase 2 — "LIVE" Indicator (persists until window closed):** Transitions to a red pulsing "LIVE" badge, styled like a broadcast studio tally light. Red dot pulsates via `QPropertyAnimation` on opacity.
3. The window remains visible until the user closes it (so they can still use the Join button).

### 5.8 Audio Mute Toggle

- **Position:** Lower-right corner of the countdown window.
- **Icons:** Speaker icon (unmuted) / Speaker-with-slash icon (muted).
- **Behavior:** Toggles audio mute instantly. Does not stop playback — just mutes output so timing is preserved.
- **Visibility:** Only shown when audio is playing (i.e., mode is "Countdown + Music" and a sound file is configured). **Hidden entirely** when in Silent mode or when no sound file is set — no point showing a mute button when there's nothing to mute.

---

## 6. Audio Playback

### 6.1 Supported Formats

MP3, WAV, FLAC, AAC (M4A). Leverages macOS native codecs via QMediaPlayer/AVFoundation.

### 6.2 Synchronization Logic

Given:
- `C` = configured countdown duration (seconds)
- `D` = detected audio file duration (seconds)
- `O` = configured clock offset (milliseconds)

The goal is for the audio to **end exactly when the countdown reaches zero**.

| Scenario | Behavior |
|---|---|
| `D > C` (audio longer than countdown) | Begin audio playback at position `D - C` seconds into the file. The countdown window opens and audio starts simultaneously. |
| `D == C` | Play audio from the beginning. Perfect alignment. |
| `D < C` (audio shorter than countdown) | Countdown window opens silently. Audio begins playing from the start at `C - D` seconds into the countdown. |

### 6.3 Clock Offset

- The clock offset `O` delays the first visual tick of the countdown numbers by `O` milliseconds after the countdown window opens.
- Purpose: Allows the user to align the visual number changes with beats/tones in the audio (e.g., BBC News Countdown has a tone every second).
- **Default:** 0 ms.
- The total real-time duration of the countdown is still `C` seconds; the offset shifts when the visual ticks occur within that window.

### 6.4 Audio Duration Detection

When the user selects a sound file in settings:
- Automatically detect and display the duration using QMediaPlayer metadata.
- Allow manual override in case auto-detection is inaccurate.

---

## 7. Late Start Handling

If the application triggers a countdown and the meeting start is **less than `C` seconds away** (e.g., laptop woke from sleep):

1. Calculate remaining time `R` until meeting start.
2. Open the countdown window with `R` seconds on the clock.
3. Calculate audio start position: `max(0, D - R)` — so audio still ends at meeting time.
4. Apply clock offset proportionally (if `R` is very small, offset may be skipped).
5. If `R ≤ 0` (meeting already started), skip the countdown entirely. Do not notify.

**Threshold:** If `R < 5` seconds, skip the countdown — it would be more distracting than helpful.

---

## 8. Configuration (Settings Window)

### 8.1 Settings UI

A standard macOS-style preferences window with organized sections (tabs or scrollable form).

### 8.2 Settings Reference

| # | Setting | Type | Default | Description |
|---|---|---|---|---|
| 1 | Launch at Login | Toggle | Off | Creates/removes a macOS LaunchAgent plist at `~/Library/LaunchAgents/com.axeltech.meetingscountdownpro.plist` |
| 2 | Calendar Accounts | Multi-select checklist | All | Select which macOS Calendar accounts to monitor. Shows account names with their calendars nested below as individually toggleable. |
| 3 | Video Calls Only | Toggle | Off | When on, only fires countdown for events containing a detected video call link (Zoom, Meet, Teams). When off, fires for all eligible meetings. |
| 4 | Countdown Duration | Numeric input (spin box) | 60 seconds | Range: 10–300 seconds. How far before the meeting the countdown window appears. |
| 5 | Sound File | File picker + Clear button | None | Accepts MP3, WAV, FLAC, AAC files. Shows file name and detected duration when set. |
| 6 | Sound Duration | Read-only (auto-detected) + manual override | Auto | Detected when sound file is selected. Manual override available. |
| 7 | Clock Offset | Numeric input (ms) | 0 ms | Milliseconds to delay the visual countdown tick after audio begins. Range: -2000 to +2000 ms. |
| 8 | Internal Email Domain | Text field | Empty | e.g., `example.com`. Used to classify attendees as internal vs. external. If empty, all attendees shown in a single list (no internal/external split). |
| 9 | Include Tentative | Toggle | No | Whether to include meetings the user has tentatively accepted. |
| 10 | Include All-Day Events | Toggle | No | Whether to include all-day/multi-day events in countdown triggers. Off by default (all-day events are skipped). |
| 11 | Back-to-Back Handling | Dropdown | Countdown + Music | What to do when the previous meeting is still in progress at notification time. Options: "Countdown + Music", "Silent Countdown", "Skip Countdown". |
| 12 | Auto-Join at Countdown End | Toggle | Off | When enabled and a video meeting link is detected, automatically open the meeting link when the countdown reaches zero. |
| 13 | Volume | Slider | 100% | Master volume for countdown audio playback. Range: 0–100%. |
| 14 | Audio Output Device | Dropdown | System Default | Select audio output device. Options: "System Default" (follows macOS system output) or any currently available audio output device. List is refreshed when the dropdown is opened. |

### 8.3 Test Mode

A **"Test Countdown"** button in the Settings window launches a full countdown using a dummy meeting event. This allows the user to:

- Preview the countdown window appearance with sample data (mock subject, attendees from sample internal/external domains).
- Hear the selected sound file with the configured sync timing.
- Calibrate the clock offset to align visual ticks with audio beats.
- See the end-of-countdown animation sequence (clapperboard → LIVE).

The test countdown uses the current settings (duration, sound file, clock offset) and runs in real-time. A shorter "Quick Test" option (10-second countdown) is also available for rapid offset tuning.

### 8.4 Sound Preview

The sound file picker includes a **"Preview"** button that plays the first 10 seconds of the selected audio file. Playback stops when the button is toggled off, or when the preview finishes.

### 8.5 Persistence

- All settings saved to `~/.config/meetings-countdown-pro/settings.json`.
- Settings are loaded on app launch and applied immediately.
- Changes in the Settings window are applied on save (explicit "Save" button, or auto-save on window close with confirmation for unsaved changes).

---

## 9. No-Repeat Notification State

### 9.1 Tracking

- **Composite key:** `calendarItemExternalIdentifier` + event start time (ISO 8601 string).
- This naturally handles all cases:
  - **Recurring meetings:** Same UID but different start times → unique keys per occurrence.
  - **Rescheduled meetings:** Same UID but new start time → treated as new notification.
  - **Normal meetings:** Unique UID + start time → straightforward dedup.
- When a countdown is triggered (window opened) or deliberately skipped (meeting already started, or mode is Off), the composite key is written to `~/.config/meetings-countdown-pro/notified.json` with a timestamp.

### 9.2 Pruning

- On each app launch, entries older than **48 hours** are pruned.
- This prevents unbounded file growth while still covering edge cases like overnight/weekend meetings.

### 9.3 Edge Cases

- If the user manually closes the countdown window early, the meeting is still marked as notified.

---

## 10. Back-to-Back Meeting Handling

### 10.1 One Countdown at a Time

Only one countdown window can be active at a time. If a new countdown would trigger while one is already showing:

- **Overlapping meetings (not simultaneous):** The second meeting's countdown is skipped (marked as notified). The user must close the current countdown window before a new one can appear.
- **Test Countdown from Settings:** The button is ignored while a countdown is running. The user must close the countdown window first.

This avoids audio/UI conflicts. A future enhancement may merge overlapping meetings into the existing countdown's left pane.

### 10.2 Back-to-Back with In-Progress Meeting

When the countdown for Meeting B would fire while Meeting A is still in progress:

1. Check if any monitored meeting is currently in progress (start ≤ now < end).
2. If yes, apply the user's "Back-to-Back Handling" setting:
   - **Countdown + Music:** Full countdown as normal.
   - **Silent Countdown:** Open the countdown window but suppress audio.
   - **Skip Countdown:** Do not open the countdown window. Still mark the meeting as notified.

---

## 11. macOS Integration

### 11.1 Calendar Permissions

- On first launch, the app must request calendar access permission via macOS's EventKit permission dialog.
- If permission is denied, show a clear message in the menu bar drop-down and Settings window explaining how to grant access in System Settings > Privacy & Security > Calendars.

### 11.2 LaunchAgent

- When "Launch at Login" is enabled, write a standard launchd plist to `~/Library/LaunchAgents/`.
- When disabled, remove the plist file.
- The plist should configure the app to launch after login with `RunAtLoad = true`.

### 11.3 Notifications Permission

- **Not required.** This app uses its own custom window rather than macOS Notification Center. This is intentional — we want the rich, branded countdown experience rather than a system notification.

---

## 12. Error Handling Summary

| Scenario | Behavior |
|---|---|
| Calendar permission denied | Menu bar shows "Calendar access required" message with link to System Settings. |
| No calendars found | Menu bar shows "No calendars configured." |
| Favicon fetch fails/times out | Generic globe icon used; no error shown to user. |
| Sound file missing/moved | Countdown proceeds silently; menu bar shows brief warning. |
| Sound file unreadable/corrupt | Same as missing — countdown proceeds silently with warning. |
| EventKit query fails | Log error; retry on next poll cycle (30s). |
| Meeting already started | Skip countdown; mark as notified. |
| Multiple meetings at same time | Show all meetings in the left pane with individual Join buttons. Auto-join disabled. See Section 5.4. |
| App crash recovery | On relaunch, check `notified.json` — don't re-fire countdowns for already-notified meetings. |

---

## 13. Development & Distribution

### 13.1 Development Environment

- **Python:** Python 3.11+ from the [python.org macOS framework installer](https://www.python.org/downloads/macos/). This provides a proper framework build (required for full macOS GUI integration via pyobjc), is actively maintained, and installs to `/Library/Frameworks/Python.framework/` without conflicting with system or Homebrew Python.
- **Why not system Python:** macOS ships Python 3.9.6 via Xcode CLT, but it is EOL (October 2025), frozen in place, and `pyobjc` has dropped 3.9 support (requires >= 3.10). System Python is an Apple internal dependency, not intended for third-party development.
- **Why not Homebrew Python:** Homebrew's `brew upgrade` can silently break virtual environments. The python.org installer provides a stable, predictable base.
- **Virtual environment:** A standard `venv` created from the python.org interpreter, stored in the project directory.
- **Setup process for contributors:**
  ```bash
  # Prerequisites: Install Python 3.11+ from https://www.python.org/downloads/macos/
  git clone https://github.com/<org>/meetings-countdown-pro.git
  cd meetings-countdown-pro
  python3 -m venv venv
  source venv/bin/activate
  pip install -r requirements.txt
  python -m meetings_countdown_pro  # or: python main.py
  ```

### 13.2 Project Structure (Source)

```
meetings-countdown-pro/
├── README.md
├── requirements.txt           # Pinned dependencies
├── meetings_countdown_pro.spec # PyInstaller spec for .app packaging
├── main.py                    # Entry point
├── meetings_countdown_pro/    # Main package
│   ├── __init__.py
│   ├── __main__.py            # Allows `python -m meetings_countdown_pro`
│   ├── app.py                 # QApplication setup, menu bar
│   ├── calendar_service.py    # EventKit integration via pyobjc
│   ├── countdown_window.py    # Countdown window UI
│   ├── audio_player.py        # QMediaPlayer wrapper, sync logic
│   ├── meeting.py             # Meeting data model
│   ├── settings.py            # Settings model, load/save
│   ├── settings_window.py     # Settings UI
│   ├── favicon_cache.py       # Async favicon fetching + caching
│   ├── notification_state.py  # notified.json management
│   └── assets/                # SVG icons, placeholder images
│       ├── menubar_icon.svg
│       ├── clapperboard.svg
│       ├── live_badge.svg
│       ├── speaker.svg
│       ├── speaker_muted.svg
│       └── globe_placeholder.svg
├── tests/                     # Unit and integration tests
├── venv/                      # Virtual environment (gitignored)
└── .gitignore
```

### 13.3 Distribution

- **For developers / GitHub:** Install Python 3.11+ from python.org, clone, create venv, `pip install -r requirements.txt` (see 13.1).
- **For end users:** PyInstaller bundles the application into a self-contained `Meetings Countdown Pro.app`. This includes the Python interpreter and all dependencies — end users do not need Python installed. The `.app` is code-signed (ad-hoc at minimum) and notarized for distribution.
- **No system interference:** The app writes only to `~/.config/meetings-countdown-pro/` and optionally `~/Library/LaunchAgents/` (if Launch at Login is enabled). No root access required. No modifications to system Python or system-level directories.
- **DMG distribution:** The `.app` bundle is packaged in a DMG for easy drag-to-Applications installation.

### 13.4 Dependencies (Preliminary)

| Package | Purpose |
|---|---|
| `PyQt6` | GUI framework |
| `PyQt6-Qt6` | Qt6 runtime (bundled with PyQt6) |
| `PyQt6-Multimedia` | QMediaPlayer for audio playback |
| `pyobjc-core` | Python ↔ Objective-C bridge |
| `pyobjc-framework-EventKit` | Calendar access |
| `requests` | Favicon HTTP fetches |
| `pyinstaller` | macOS .app packaging (dev dependency) |

### 13.5 Logging & Diagnostics

- **Default (INFO):** High-level operational messages — calendar access status, number of meetings found per poll, next meeting selected, countdown scheduling/trigger events.
- **Debug (`--debug`):** Verbose per-event detail — EventKit query parameters, raw event counts, individual meeting details (title, time, attendee count), filter exclusion reasons, notification-state skip reasons.
- **CLI usage:**
  ```bash
  python -m meetings_countdown_pro           # INFO level (default)
  python -m meetings_countdown_pro --debug   # DEBUG level
  ```
- **Format:** `%(asctime)s [%(name)s] %(levelname)s: %(message)s` — timestamps, module name, and severity for all log lines.
- **Output:** stderr (standard Python logging). No log files by default.

---

## 14. Out of Scope (v1)

The following are explicitly **not** in the initial version:

- Direct calendar API integration (Google/Microsoft APIs) — we rely solely on macOS Calendar sync.
- Custom themes or user-selectable color schemes.
- Multiple monitor selection (always uses primary display).
- Calendar event creation or modification.
- Snooze / remind-me-later functionality.
- Slack/Teams status integration.
- iPhone/iPad companion app.
- Self-exclusion from attendee lists (reliably identifying the user across calendar providers is not worth the complexity).

---

## 15. Resolved Decisions

| # | Question | Resolution |
|---|---|---|
| 1 | Long attendee lists | Scrollable left pane + always-visible summary line above it |
| 2 | Animation approach | Qt-native (QPropertyAnimation + QPainter + SVG) — zero deps, Retina-crisp |
| 3 | Auto-join at T=0 | Yes, as a configurable option (Setting #12) |
| 4 | Sound preview | Yes, plus full Test Mode with Quick Test option (see Section 8.3) |
| 5 | Self-identification | Not implemented in v1 — user appears as normal attendee |
| 6 | Audio backend | QMediaPlayer (PyQt6 multimedia) — native macOS codec support |
| 7 | Simultaneous meetings | Show all in scrollable left pane with individual Join buttons; auto-join disabled |
| 8 | Recurring meeting UIDs | UID + start time as composite key — unique per occurrence, handles rescheduling |
| 9 | Attendee count in menu bar | No — keep menu bar line simple |
| 10 | Negative clock offset | Yes, allow -2000 to +2000 ms |
| 11 | Display name parsing | Parse name from `"Name" <email>` format if present; show bare email as-is otherwise |
| 12 | Python version | Python 3.11+ from python.org framework installer (system Python 3.9 is EOL and incompatible with pyobjc) |
| 13 | Packaging tool | PyInstaller (over py2app) — better maintained, handles PyQt6 and code signing well |

---

## 16. Open Questions

All major questions have been resolved. The following are implementation details to confirm during development:

1. **EventKit `calendarItemExternalIdentifier` behavior:** Verify that this identifier is consistent across app restarts and stable for recurring event occurrences. If not, fall back to a hash of UID + calendar ID + start time.

2. **PyInstaller + pyobjc compatibility:** Confirm that PyInstaller correctly bundles the pyobjc EventKit framework bridge. May require custom hooks or hidden imports in the PyInstaller spec.

3. **Code signing and notarization:** Determine whether to ad-hoc sign for initial development or obtain an Apple Developer ID for proper distribution. Notarization requires the "allow unsigned executable memory" entitlement for Python.

---

## Appendix A: File Structure

```
~/.config/meetings-countdown-pro/
├── settings.json              # User configuration
├── notified.json              # Already-notified meeting UIDs
└── favicon-cache/             # Cached favicons by domain
    ├── acme.com.ico
    ├── globex.net.ico
    └── ...
```

## Appendix B: Meeting Detection Flow

```
Every 30 seconds:
  │
  ├─ Query EventKit for events in [now, end of local day]
  │
  ├─ Filter by:
  │   ├─ Selected calendar accounts/calendars
  │   ├─ Acceptance status (accepted, optionally tentative)
  │   ├─ Exclude all-day events (if configured)
  │   ├─ Exclude declined events (always)
  │   └─ Video call links only (if configured)
  │
  ├─ Exclude already-notified events (check notified.json)
  │
  ├─ Sort by start time, pick earliest
  │
  ├─ Calculate trigger time = event_start - countdown_duration
  │
  ├─ If trigger_time ≤ now:
  │   ├─ If event_start > now + 5s: Late start (adjust countdown)
  │   └─ If event_start ≤ now + 5s: Skip (too late)
  │
  ├─ If trigger_time > now:
  │   └─ Schedule one-shot timer for trigger_time
  │
  └─ On trigger:
      ├─ Check back-to-back status
      ├─ Mark event as notified
      ├─ Open countdown window
      └─ Start audio (per sync logic)
```
