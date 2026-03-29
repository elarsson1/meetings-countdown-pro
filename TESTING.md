# Meetings Countdown Pro — Testing Plan

Manual testing plan covering all functionality defined in SPEC.md v0.5.

**Prerequisites for all tests:**
- Python 3.14+ from python.org (recommended), venv activated, dependencies installed
- At least one macOS Calendar account with events
- A countdown audio file (e.g., BBC News Countdown, ~60–90s)
- An internal domain configured in Settings (e.g., `axeltech.com`)

---

## 1. Application Lifecycle

### 1.1 Launch
- [X] `python -m meetings_countdown_pro` starts without errors
- [X] `python main.py` starts without errors
- [X] Menu bar icon appears in the system tray
- [X] App does not appear in the Dock (background process)
- [X] Console shows INFO-level log messages at startup (calendar access, initial poll)

### 1.2 Debug Mode
- [X] `python -m meetings_countdown_pro --debug` starts with DEBUG-level output
- [X] Debug output includes EventKit query parameters, raw event counts, per-event details

### 1.3 Quit
- [X] Quit from menu bar exits cleanly (no segfault)
- [X] Quit after audio playback exits cleanly (no segfault)
- [X] Quit during active countdown exits cleanly (no segfault)
- [X] Quit with no audio file configured exits cleanly

---

## 2. Calendar Access & Permissions

### 2.1 First Launch (No Permission)
- [X] App prompts for calendar access via macOS permission dialog (reset with `tccutil reset Calendar org.python.python` to re-test)
- [X] Granting access: calendar polling begins, events appear in menu bar
- [X] Denying access: menu bar shows "⚠ Calendar access required"

### 2.2 Permission Revoked
- [X] If permission is revoked in System Settings → Privacy → Calendars, menu bar reflects the denied state on next poll

### 2.3 Calendar Enumeration
- [X] Settings → Calendars tab shows all accounts and calendars from macOS Calendar
- [X] Calendars grouped by account name (iCloud, Google, Exchange, etc.)
- [X] Calendar colors displayed correctly

---

## 3. Menu Bar

### 3.1 Next Meeting Display
- [X] Shows next meeting title, time, and relative time (e.g., "in 23 min")
- [X] Title truncated with ellipsis if longer than ~28 characters
- [X] Relative time shows minutes when < 60 min away
- [X] Relative time shows hours + minutes when >= 60 min away
- [X] Shows "(now)" when meeting is starting
- [X] Shows "No more meetings today" when no remaining meetings
- [X] Updates on each 30-second poll cycle
- [X] Detects meetings across the entire day, not just the next few minutes

### 3.2 Mode Selection
- [X] Three radio options: Countdown + Music, Countdown (Silent), Off
- [X] Only one mode can be selected at a time
- [X] Selected mode persists across app restarts
- [X] Changing mode updates `settings.json`

### 3.3 Menu Actions
- [X] "Settings..." opens the Settings window
- [X] "Quit Meetings Countdown Pro" exits the app

---

## 4. Calendar Polling & Event Detection

### 4.1 Basic Detection
- [X] Events from all enabled calendars are detected
- [X] Events from disabled calendars are not detected
- [X] Poll runs every 30 seconds
- [X] Query window spans from now to end of local day

### 4.2 Attendee Handling
- [X] Organizer (event sender) included in attendee list
- [X] Regular attendees included in attendee list
- [ ] Duplicate attendees deduplicated by email (case-insensitive)
- [X] Organizer who also appears in attendees list shown only once
- [X] Display name parsed from `"Name" <email>` format
- [X] Bare email addresses shown as-is when no display name available

### 4.3 Filters
- [X] Declined events are always excluded
- [X] Tentative events excluded when "Include Tentative" is off
- [X] Tentative events included when "Include Tentative" is on
- [X] All-day events excluded when "Include All-Day Events" is off
- [X] All-day events included when "Include All-Day Events" is on
- [X] "Video Calls Only" filter: only events with Zoom/Meet/Teams links trigger countdown
- [X] "Video Calls Only" off: all eligible events trigger countdown

### 4.4 Calendar Selection
- [X] Selecting specific calendars in Settings only monitors those calendars
- [X] Deselecting all calendars falls back to monitoring all calendars
- [X] Changes take effect on next poll cycle after saving settings

---

## 5. Countdown Window

### 5.1 Window Appearance & Behavior
- [X] Window appears in upper-right corner of primary display, inset ~20px
- [X] Frameless window with rounded corners and drop shadow
- [X] Dark background theme (broadcast aesthetic)
- [X] Slides in from right edge (~300ms animation)
- [X] Floats above regular windows but below system dialogs
- [X] Escape key closes the window
- [X] Close button (X) closes the window
- [X] Closing stops audio playback
- [X] Meeting is marked as notified after window is closed (no repeat)

### 5.2 Countdown Display
- [X] Large, bold, proportional sans-serif font (Helvetica Neue / SF Pro)
- [X] Shows seconds only (e.g., `90`, `47`, `3`) — no MM:SS format
- [X] Ticks every 1 second
- [X] Countdown transitions to ACTION! phase at T-2s, then LIVE at T=0

### 5.3 Meeting Info Panel
- [X] Meeting title displayed in bold
- [X] Long titles truncated with ellipsis
- [X] Start – End time shown in local timezone
- [X] Attendee summary line: "{N} attendees · {X} internal · {Y} external from {Z} orgs"
- [X] Internal attendees listed under "INTERNAL" header, sorted alphabetically
- [X] External attendees listed under "EXTERNAL" header, grouped by domain
- [X] Each domain group shows favicon + domain name
- [X] Attendees within each domain group sorted alphabetically
- [X] Domain groups sorted alphabetically by domain name
- [X] Left pane scrollable when attendee list is long

### 5.4 Video Link Detection
- [X] Zoom links detected (`https://...zoom.us/j/...`, `https://...zoom.us/my/...`)
- [ ] Google Meet links detected (`https://meet.google.com/...`)
- [X] Microsoft Teams links detected (`https://teams.microsoft.com/l/meetup-join/...`)
- [X] Links detected in URL field, location field, and notes/body
- [X] Priority order: URL field > location > notes (first match wins)
- [X] "Join Now" button shown only when video link is detected
- [X] "Join Now" opens link in system default browser
- [X] No "Join Now" button when no video link found

### 5.5 Simultaneous Meetings
- [X] When 2+ meetings start at the same time, all shown in left pane
- [X] Each meeting has its own title, time, attendees, and individual Join button
- [X] Right-side Join Now button is hidden (individual buttons only)
- [X] Auto-join is disabled for simultaneous meetings
- [X] Countdown still counts down to the shared start time

### 5.6 Favicon Handling
- [X] Favicons fetched and displayed for external attendee domains
- [X] Failed favicon fetch shows generic globe icon (no error to user)
- [X] Favicon fetch does not block window rendering
- [X] Favicons cached in memory and on disk (`~/.config/.../favicon-cache/`)

---

## 6. Countdown End Animation

### 6.1 Phase 1 — "ACTION!" (~2 seconds before meeting start)
- [X] Countdown area transitions to clapperboard SVG graphic
- [X] "ACTION!" text displayed
- [X] Clapperboard top bar animates a clap (rotation animation) — re-test after fix

### 6.2 Phase 2 — "LIVE" (at meeting start, persists)
- [X] Transitions to red pulsing "LIVE" badge
- [X] Red dot pulsates (opacity animation)
- [X] Window stays visible until user closes it
- [X] Join button remains functional during LIVE phase

---

## 7. Audio Playback

### 7.1 Format Support
- [X] MP3 files play correctly
- [ ] WAV files play correctly
- [ ] AAC/M4A files play correctly
- [ ] FLAC files play correctly (if macOS codec available)

### 7.2 Sync Logic
- [X] Audio longer than countdown (`D > C`): audio starts at position `D - C`, plays to end at T=0
- [X] Audio equal to countdown (`D == C`): plays from beginning, ends at T=0
- [X] Audio shorter than countdown (`D < C`): countdown starts silent, audio begins at `C - D` seconds in

### 7.3 Clock Offset
- [X] Offset 0ms: visual ticks aligned with real seconds
- [X] Positive offset: visual ticks delayed by configured ms
- [X] Negative offset: visual ticks advanced by configured ms
- [X] Offset range enforced: -2000 to +2000 ms

### 7.4 Audio Duration Detection
- [X] Duration auto-detected when sound file is selected in Settings
- [X] Detected duration displayed in Settings
- [X] Manual duration override accepted

### 7.5 Mute Toggle
- [X] Speaker icon visible in lower-right of countdown window when audio is playing
- [X] Clicking toggles mute (audio silenced, playback continues for timing)
- [X] Icon changes between speaker and speaker-muted states
- [X] Mute toggle hidden in Silent mode
- [X] Mute toggle hidden when no sound file configured

### 7.6 Volume & Output Device
- [X] Volume slider in settings controls playback volume (0–100%)
- [X] Audio output device selector lists available devices
- [X] Selecting a specific device routes audio to that device
- [X] "System Default" follows macOS system output
- [X] Device preference persists if device is temporarily unavailable (falls back to default)

---

## 8. Late Start Handling

- [ ] Laptop wake from sleep with meeting < C seconds away: countdown opens with remaining time
- [ ] Audio start position adjusted: `max(0, D - R)` so audio ends at meeting time
- [ ] Meeting < 5 seconds away: countdown skipped entirely, marked as notified
- [ ] Meeting already started (`R ≤ 0`): no countdown, marked as notified
- [ ] App launch during countdown window triggers countdown on main thread (no crash)

---

## 9. No-Repeat Notification State

### 9.1 Normal Dedup
- [X] Countdown fires once per meeting; re-poll does not trigger again
- [X] `notified.json` updated with composite key on countdown trigger

### 9.2 Recurring Meetings
- [X] Each occurrence of a recurring meeting gets its own countdown (different start time = different key)
- [X] Past occurrences don't block future ones

### 9.3 Rescheduled Meetings
- [X] Moving a meeting to a new time triggers a new countdown (same UID + new start time = new key)
- [X] Original time slot does not fire again

### 9.4 Pruning
- [ ] Entries older than 24 hours pruned on app launch
- [ ] `notified.json` does not grow unbounded over days of use

---

## 10. Back-to-Back Meeting Handling

### 10.1 One Countdown at a Time
- [X] Second countdown skipped while first is still open
- [X] Skipped meeting marked as notified (no repeat)
- [X] Test Countdown button ignored while countdown is active

### 10.2 Back-to-Back Behavior
- [ ] Setting "Countdown + Music": full countdown during in-progress meeting
- [ ] Setting "Silent Countdown": visual countdown only, no audio
- [ ] Setting "Skip Countdown": no window opened, meeting marked as notified

---

## 11. Settings Window

### 11.1 General Tab
- [X] Launch at Login toggle creates/removes LaunchAgent plist
- [X] LaunchAgent plist at `~/Library/LaunchAgents/com.axeltech.meetingscountdownpro.plist`
- [X] Countdown Duration spin box: range 10–300 seconds
- [X] Video Calls Only toggle
- [X] Include Tentative toggle
- [X] Include All-Day Events toggle
- [X] Back-to-Back Handling dropdown (3 options)
- [X] Auto-Join at Countdown End toggle
- [X] Internal Email Domain text field
- [X] Clock Offset input: range -2000 to +2000 ms

### 11.2 Calendars Tab
- [X] Lists all accounts with nested calendars
- [X] Checkboxes for individual calendar selection
- [X] Select All / Deselect All functionality (if implemented)
- [X] Reflects current macOS Calendar accounts

### 11.3 Audio Tab
- [X] Sound file picker (accepts MP3, WAV, FLAC, AAC)
- [X] Clear button removes selected sound file
- [X] File name and detected duration displayed when file selected
- [X] Preview button plays first 10 seconds of selected file
- [X] Preview stops when toggled off or after 10 seconds
- [X] Volume slider (0–100%)
- [X] Audio output device dropdown
- [X] Device list refreshed when dropdown opened

### 11.4 Test Mode
- [X] "Test Countdown" button launches full countdown with mock data
- [X] Mock meeting has sample subject, attendees (internal + external)
- [X] Uses current settings (duration, sound file, offset)
- [X] Runs in real-time with full animation sequence
- [X] "Quick Test" (10-second) countdown available
- [X] Test countdown button disabled while countdown is active
- [X] Repeated test countdowns play audio reliably

### 11.5 Persistence
- [X] All settings saved to `~/.config/meetings-countdown-pro/settings.json`
- [X] Settings loaded correctly on app restart
- [X] Changes applied on save

---

## 12. AI Integration

### 12.1 Menu Bar Toggle
- [ ] "Enable AI Integration" checkbox visible in menu bar dropdown
- [ ] Checkbox reflects current `agent_enabled` setting
- [ ] Toggling updates `settings.json` immediately
- [ ] State syncs with AI Integration tab in Settings (change in one reflects in the other)

### 12.2 Settings — AI Integration Tab
- [ ] Fourth tab labeled "AI Integration" present in Settings window
- [ ] Enable AI Integration checkbox
- [ ] Terminal Application dropdown: "Terminal.app" and "iTerm2" options
- [ ] Working Directory text field with Browse button
- [ ] Browse button opens directory picker, selected path populates the field
- [ ] Command Template text field (default: `claude {Prompt}`)
- [ ] Prompt Template multi-line text area (default: `Please help me prep for this meeting: {MeetingData}`)
- [ ] All AI Integration settings persist across app restarts

### 12.3 Agent Launch — Real Countdown
- [ ] AI enabled + real countdown triggers: terminal window opens with agent command
- [ ] Terminal.app: new window created via AppleScript with `zsh -l` login shell
- [ ] iTerm2: new window created via AppleScript with `zsh -l` login shell
- [ ] Working directory is respected (agent starts in configured directory)
- [ ] `{MeetingData}` replaced with JSON containing meeting title, date, times, calendar, video_link, attendees
- [ ] `{Prompt}` replaced with shell-escaped rendered prompt
- [ ] Agent session persists after countdown ends (normal interactive terminal)
- [ ] AI disabled: no terminal window opened on countdown

### 12.4 Agent Launch — Test Mode
- [ ] Test Countdown with AI enabled: agent launches with mock meeting data
- [ ] Quick Test (10s) with AI enabled: agent launches with mock meeting data
- [ ] Mock data includes sample internal + external attendees
- [ ] AI disabled: Test Countdown does not launch agent

### 12.5 Simultaneous Meetings
- [ ] All simultaneous meetings included in `{MeetingData}` JSON `meetings` array
- [ ] Only one agent session launched (not one per meeting)

### 12.6 Shell Escaping & Safety
- [ ] Meeting titles with special characters (quotes, $, backticks) do not break the command
- [ ] JSON values use `ensure_ascii=True` (unicode/emoji escaped to `\uXXXX`)
- [ ] Rendered prompt wrapped with `shlex.quote()` for safe shell passing
- [ ] Launch script written to `~/.config/meetings-countdown-pro/agent-launch.sh`
- [ ] Launch script is executable

### 12.7 Error Handling
- [ ] Terminal launch failure (e.g., iTerm2 not installed): logged as warning, countdown proceeds normally
- [ ] Empty command template with AI enabled: agent launch skipped with log warning
- [ ] Working directory does not exist: shell reports error in terminal, app unaffected

---

## 13. Error Handling

- [X] Calendar permission denied: clear message in menu bar
- [ ] Sound file missing/moved: countdown proceeds silently
- [ ] Sound file corrupt/unreadable: countdown proceeds silently
- [ ] Favicon fetch failure: globe icon placeholder, no user-visible error
- [X] EventKit query failure: logged, retry on next 30s poll
- [X] App crash recovery: `notified.json` prevents re-firing already-notified meetings
- [ ] AI Integration terminal launch fails: logged, countdown proceeds normally
- [ ] AI Integration command not found (e.g., `claude` not in PATH): terminal shows shell error, app unaffected

---

## 14. macOS Integration

- [X] Calendar permission prompt on first launch
- [X] LaunchAgent plist correctly formatted and functional (will need update for PyInstaller packaging)
- [ ] App launches at login when LaunchAgent enabled
- [ ] App does not launch at login when LaunchAgent removed
- [X] No Dock icon (background/agent app)
- [X] Config stored only in `~/.config/meetings-countdown-pro/`
- [X] No root access required
- [X] Clean exit with no segfault after audio playback

---

## 15. Edge Cases

- [ ] No calendars configured on macOS: graceful handling
- [X] Empty calendar (no events today): "No more meetings today"
- [ ] Meeting with no attendees: countdown shows meeting info without attendee section
- [ ] Meeting with no title: shows "Untitled"
- [X] Meeting with very long title: truncated with ellipsis
- [ ] Meeting with 50+ attendees: left pane scrolls without performance issues
- [ ] Organizer sends invite to themselves: shown once (deduplicated by email)
- [X] Multiple calendar providers (iCloud + Google + Exchange): all detected
- [ ] Timezone changes: times display in local timezone
- [ ] App running overnight: next day's meetings detected after midnight
