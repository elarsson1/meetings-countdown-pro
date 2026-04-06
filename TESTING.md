# Meetings Countdown Pro — Testing Plan

Testing plan covering all functionality defined in SPEC.md v1.0.

---

## Automated Tests

228 automated tests cover business logic, filter logic, audio sync math, countdown window state, the App controller, and the About dialog. Run them with:

```bash
source venv/bin/activate
pip install -r requirements-dev.txt   # first time only
pytest -v
```

| Test file | Tests | What it covers |
|-----------|-------|----------------|
| `test_meeting.py` | 44 | Attendee parsing, video link regex (Zoom/Meet/Teams), classify attendees, summary, JSON serialization, notification key |
| `test_settings.py` | 32 | Validation clamping (duration, offset, volume, enums), save/load round-trip, corrupt/missing file handling, continue_after_join default |
| `test_countdown_window.py` | 28 | Phase transitions, join/mute button visibility, close signals, color transitions, multi-meeting rendering, join-closes-window behavior |
| `test_working_hours.py` | 27 | Day/time filtering, combined day+time, settings validation (invalid days, times, dedup) |
| `test_app.py` | 25 | Menu structure, polling, scheduling, dedup, back-to-back handling (skip/silent/default), mode toggle, one-at-a-time |
| `test_filters.py` | 18 | Full filter matrix (canceled, declined, tentative, all-day, free, video-only, combinations) |
| `test_audio_sync.py` | 15 | Audio sync math: seek position + delay for all D vs C scenarios including late start |
| `test_agent_launcher.py` | 15 | JSON building, command assembly, shell escaping, script writing, launch orchestration |
| `test_about_window.py` | 15 | Dialog rendering, version/copyright display, OK button, update check button, semver comparison, update result states (up to date, new version, error) |
| `test_notification_state.py` | 9 | Mark/check, persistence across instances, 24h pruning, corrupt file recovery |
| **Total** | **228** | **~1.5 second runtime** |

The manual checklist below covers everything that the automated tests do not: visual appearance, real audio playback, live EventKit integration, macOS system behavior, and end-to-end workflows.

---

## Manual Testing Checklist

**Prerequisites:**
- Python 3.14+ from python.org (recommended), venv activated, dependencies installed
- At least one macOS Calendar account with events
- A countdown audio file (e.g., BBC News Countdown, ~60–90s)
- An internal domain configured in Settings (e.g., `axeltech.com`)

---

### 1. Application Lifecycle

#### 1.1 Launch
- [ ] `python -m meetings_countdown_pro` starts without errors
- [ ] `python main.py` starts without errors
- [ ] Menu bar icon appears in the system tray
- [ ] App does not appear in the Dock (background process)
- [ ] Console shows INFO-level log messages at startup (calendar access, initial poll)

#### 1.2 Debug Mode
- [ ] `python -m meetings_countdown_pro --debug` starts with DEBUG-level output
- [ ] Debug output includes EventKit query parameters, raw event counts, per-event details

#### 1.3 Quit
- [ ] Quit from menu bar exits cleanly (no segfault)
- [ ] Quit after audio playback exits cleanly (no segfault)
- [ ] Quit during active countdown exits cleanly (no segfault)
- [ ] Quit with no audio file configured exits cleanly

---

### 2. Calendar Access & Permissions

- [ ] App prompts for calendar access via macOS permission dialog (reset with `tccutil reset Calendar org.python.python` to re-test)
- [ ] Granting access: calendar polling begins, events appear in menu bar
- [ ] Denying access: menu bar shows "⚠ Calendar access required"
- [ ] If permission is revoked in System Settings → Privacy → Calendars, menu bar reflects the denied state on next poll

#### 2.1 Calendar Enumeration
- [ ] Settings → Calendars tab shows all accounts and calendars from macOS Calendar
- [ ] Calendars grouped by account name (iCloud, Google, Exchange, etc.)
- [ ] Calendar colors displayed correctly

---

### 3. Menu Bar

- [ ] Three radio options: Countdown + Music, Countdown (Silent), Off
- [ ] Only one mode can be selected at a time
- [ ] Relative time shows minutes when < 60 min away
- [ ] Relative time shows hours + minutes when >= 60 min away
- [ ] Shows "(now)" when meeting is starting
- [ ] Detects meetings across the entire day, not just the next few minutes
- [ ] "Settings..." opens the Settings window
- [ ] "About Meetings Countdown Pro" opens the About dialog
- [ ] "Quit Meetings Countdown Pro" exits the app

#### 3.1 Icon States
- [ ] Countdown + Music mode: full-opacity clock icon
- [ ] Silent mode: dimmed clock icon
- [ ] Off mode: dimmed clock with strike-through line
- [ ] Icon updates immediately when mode is changed
- [ ] Working Hours enabled + currently outside hours: orange badge dot visible
- [ ] Working Hours enabled + currently inside hours: no badge dot
- [ ] Working Hours disabled: no badge dot regardless of time
- [ ] Badge dot appears/disappears as time crosses working hours boundary (within 30s poll interval)

---

### 4. Calendar Polling & Event Detection

#### 4.1 Live Calendar Integration
- [ ] Events from all enabled calendars are detected
- [ ] Events from disabled calendars are not detected
- [ ] Query window spans from now to end of local day

#### 4.2 Attendee Handling (live data)
- [ ] Organizer (event sender) included in attendee list
- [ ] Regular attendees included in attendee list
- [ ] Duplicate attendees deduplicated by email (case-insensitive)
- [ ] Organizer who also appears in attendees list shown only once

#### 4.3 Calendar Selection
- [ ] Selecting specific calendars in Settings only monitors those calendars
- [ ] Deselecting all calendars falls back to monitoring all calendars
- [ ] Changes take effect on next poll cycle after saving settings

---

### 5. Countdown Window

#### 5.1 Window Appearance
- [ ] Window appears in upper-right corner of primary display, inset ~20px
- [ ] Frameless window with rounded corners and drop shadow
- [ ] Dark background theme (broadcast aesthetic)
- [ ] Slides in from right edge (~300ms animation)
- [ ] Floats above regular windows but below system dialogs
- [ ] Close button (X) closes the window

#### 5.2 Countdown Display
- [ ] Large, bold, proportional sans-serif font (Helvetica Neue / SF Pro)
- [ ] Ticks every 1 second

#### 5.3 Meeting Info Panel
- [ ] Meeting title displayed in bold
- [ ] Long titles truncated with ellipsis
- [ ] Start – End time shown in local timezone
- [ ] Each domain group shows favicon + domain name
- [ ] Left pane scrollable when attendee list is long

#### 5.4 Video Link & Join Behavior
- [ ] "Join Now" opens link in system default browser
- [ ] "Join Now" closes countdown window (default behavior)
- [ ] With "Continue countdown after joining" enabled, window stays open after joining
- [ ] Window close after join emits closed signal (audio stops, poll resumes)

#### 5.5 Simultaneous Meetings
- [ ] Auto-join is disabled for simultaneous meetings
- [ ] Countdown still counts down to the shared start time
- [ ] Clicking any inline "Join" button closes the countdown window (default)
- [ ] With "Continue countdown after joining" enabled, inline join keeps window open

#### 5.6 Favicon Handling
- [ ] Favicons fetched and displayed for external attendee domains
- [ ] Failed favicon fetch shows generic globe icon (no error to user)
- [ ] Favicon fetch does not block window rendering
- [ ] Favicons cached in memory and on disk (`~/.config/.../favicon-cache/`)

---

### 6. Countdown End Animation

- [ ] Clapperboard top bar animates a clap (rotation animation)
- [ ] "ACTION!" text displayed
- [ ] Red dot pulsates (opacity animation)
- [ ] Window stays visible until user closes it
- [ ] Join button remains functional during LIVE phase

---

### 7. Audio Playback

#### 7.1 Format Support
- [ ] MP3 files play correctly
- [ ] WAV files play correctly
- [ ] AAC/M4A files play correctly
- [ ] FLAC files play correctly (if macOS codec available)

#### 7.2 Clock Offset
- [ ] Offset 0ms: visual ticks aligned with real seconds
- [ ] Positive offset: visual ticks delayed by configured ms
- [ ] Negative offset: visual ticks advanced by configured ms

#### 7.3 Audio Duration Detection
- [ ] Duration auto-detected when sound file is selected in Settings
- [ ] Detected duration displayed in Settings
- [ ] Manual duration override accepted

#### 7.4 Mute Toggle
- [ ] Icon changes between speaker and speaker-muted states

#### 7.5 Volume & Output Device
- [ ] Volume slider in settings controls playback volume (0–100%)
- [ ] Audio output device selector lists available devices
- [ ] Selecting a specific device routes audio to that device
- [ ] "System Default" follows macOS system output
- [ ] Device preference persists if device is temporarily unavailable (falls back to default)

#### 7.6 Device Switching & Hotplug
- [ ] Changing device in Settings → audio plays on new device on next countdown
- [ ] Switching from specific device back to System Default → audio plays immediately (no restart required)
- [ ] Repeated countdowns on a specific device → 100% reliable (no sporadic silent playback)
- [ ] Repeated countdowns on System Default → 100% reliable
- [ ] System Default tracks macOS default device: connecting headphones → audio switches to headphones
- [ ] System Default tracks macOS default device: disconnecting headphones → audio switches to speakers
- [ ] Specific device disconnected → next countdown falls back to system default
- [ ] Specific device disconnected then reconnected → next countdown returns to preferred device
- [ ] Specific device disconnected during active countdown → current playback may be lost (known limitation), next countdown falls back
- [ ] Settings window with disconnected preferred device → shows device as "(disconnected)" in dropdown
- [ ] Saving settings with disconnected device → preference preserved (not silently reset to System Default)
- [ ] Test Countdown from Settings with disconnected device → fallback plays on system default, preference preserved

---

### 8. Late Start Handling

- [ ] Laptop wake from sleep with meeting < C seconds away: countdown opens with remaining time
- [ ] Meeting already started (`R ≤ 0`): no countdown, marked as notified
- [ ] App launch during countdown window triggers countdown on main thread (no crash)

---

### 9. No-Repeat Notification State

- [ ] Past occurrences don't block future ones
- [ ] Moving a meeting to a new time triggers a new countdown (same UID + new start time = new key)
- [ ] Original time slot does not fire again
- [ ] `notified.json` does not grow unbounded over days of use

---

### 10. Back-to-Back Meeting Handling

- [ ] Skipped meeting marked as notified (no repeat)
- [ ] Test Countdown button ignored while countdown is active
- [ ] Back-to-back detection respects same filters as normal detection (video-only, declined, tentative, free, all-day)

---

### 11. Settings Window

#### 11.1 General Tab
- [ ] Launch at Login toggle creates/removes LaunchAgent plist
- [ ] LaunchAgent plist at `~/Library/LaunchAgents/com.axeltech.meetingscountdownpro.plist`
- [ ] Video Calls Only toggle
- [ ] Include Tentative toggle
- [ ] Include Free Events toggle
- [ ] Include All-Day Events toggle
- [ ] Auto-Join at Countdown End toggle
- [ ] Continue Countdown After Joining toggle (default unchecked)
- [ ] Internal Email Domain text field
- [ ] Back-to-Back Meetings dropdown (Default / Silent / Skip)
- [ ] Working Hours toggle (default unchecked)
- [ ] Working Hours day/time controls disabled when toggle unchecked, enabled when checked
- [ ] Working Hours day pills Sun–Sat, Mon–Fri selected by default
- [ ] Working Hours time inputs accept 12h ("9:00 AM") and 24h ("09:00") formats
- [ ] Countdown suppressed outside configured working hours (meeting still shown in menu bar)
- [ ] Countdown fires normally within configured working hours

#### 11.2 Calendars Tab
- [ ] Lists all accounts with nested calendars
- [ ] Checkboxes for individual calendar selection
- [ ] Select All / Deselect All functionality (if implemented)
- [ ] Reflects current macOS Calendar accounts

#### 11.3 Audio Tab
- [ ] Sound file picker (accepts MP3, WAV, FLAC, AAC)
- [ ] Clear button removes selected sound file
- [ ] File name and detected duration displayed when file selected
- [ ] Preview button plays first 10 seconds of selected file
- [ ] Preview stops when toggled off or after 10 seconds
- [ ] Audio output device dropdown
- [ ] Device list refreshed when dropdown opened

#### 11.4 Test Mode
- [ ] "Test Countdown" button launches full countdown with mock data
- [ ] Mock meeting has sample subject, attendees (internal + external)
- [ ] Uses current settings (duration, sound file, offset)
- [ ] Runs in real-time with full animation sequence
- [ ] "Quick Test" (10-second) countdown available
- [ ] Test countdown button disabled while countdown is active
- [ ] Repeated test countdowns play audio reliably

---

### 12. AI Integration

#### 12.1 Menu Bar Toggle
- [ ] "Enable AI Integration" checkbox visible in menu bar dropdown
- [ ] Checkbox reflects current `agent_enabled` setting
- [ ] State syncs with AI Integration tab in Settings (change in one reflects in the other)

#### 12.2 Settings — AI Integration Tab
- [ ] Fourth tab labeled "AI Integration" present in Settings window
- [ ] Enable AI Integration checkbox
- [ ] Working Directory text field with Browse button
- [ ] Browse button opens directory picker, selected path populates the field
- [ ] Command Template text field (default: `claude {Prompt}`)
- [ ] Prompt Template multi-line text area (default: `Please help me prep for this meeting: {MeetingData}`)
- [ ] All AI Integration settings persist across app restarts

#### 12.3 Agent Launch — Real Countdown
- [ ] AI enabled + real countdown triggers: terminal window opens with agent command
- [ ] Terminal.app: new window created via AppleScript with `zsh -l` login shell
- [ ] iTerm2: new window created via AppleScript with `zsh -l` login shell
- [ ] Working directory is respected (agent starts in configured directory)
- [ ] Agent session persists after countdown ends (normal interactive terminal)

#### 12.4 Agent Launch — Test Mode
- [ ] Test Countdown with AI enabled: agent launches with mock meeting data
- [ ] Quick Test (10s) with AI enabled: agent launches with mock meeting data
- [ ] Mock data includes sample internal + external attendees
- [ ] AI disabled: Test Countdown does not launch agent

#### 12.5 Error Handling
- [ ] Terminal launch failure (e.g., iTerm2 not installed): logged as warning, countdown proceeds normally
- [ ] Working directory does not exist: shell reports error in terminal, app unaffected

---

### 13. About Dialog

- [ ] Dialog renders correctly (icon, wordmark, version, copyright, repo link, OK button)
- [ ] "Check for Updates" returns a result (up to date or new version available) without crashing
- [ ] Update check with no network shows an error message and re-enables the button

---

### 14. Error Handling

- [ ] Sound file missing/moved: countdown proceeds silently
- [ ] Sound file corrupt/unreadable: countdown proceeds silently
- [ ] Favicon fetch failure: globe icon placeholder, no user-visible error
- [ ] EventKit query failure: logged, retry on next 30s poll
- [ ] AI Integration terminal launch fails: logged, countdown proceeds normally
- [ ] AI Integration command not found (e.g., `claude` not in PATH): terminal shows shell error, app unaffected

---

### 15. macOS Integration

- [ ] Calendar permission prompt on first launch
- [ ] LaunchAgent plist correctly formatted and functional (will need update for PyInstaller packaging)
- [ ] App launches at login when LaunchAgent enabled
- [ ] App does not launch at login when LaunchAgent removed
- [ ] No Dock icon (background/agent app)
- [ ] Config stored only in `~/.config/meetings-countdown-pro/`
- [ ] No root access required
- [ ] Clean exit with no segfault after audio playback

---

### 16. Edge Cases

- [ ] No calendars configured on macOS: graceful handling
- [ ] Meeting with no title: shows "Untitled"
- [ ] Meeting with 50+ attendees: left pane scrolls without performance issues
- [ ] Organizer sends invite to themselves: shown once (deduplicated by email)
- [ ] Multiple calendar providers (iCloud + Google + Exchange): all detected
- [ ] Timezone changes: times display in local timezone
- [ ] App running overnight: next day's meetings detected after midnight
