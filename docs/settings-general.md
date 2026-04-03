# General Settings

The General tab contains startup, countdown, organization, and meeting filter settings.

![General Settings](images/prefs_general.png)

## Startup

### Launch at Login

When enabled, the app starts automatically when you log in to your Mac. This creates a macOS LaunchAgent in `~/Library/LaunchAgents/`. Disabling it removes the LaunchAgent.

**Default:** Off

## Countdown

### Countdown Duration

How many seconds before the meeting start time the countdown window appears. This is also how long the countdown timer runs (unless the app triggers late — see [Late Starts](countdown-window.md#late-starts)).

- **Range:** 10–300 seconds
- **Default:** 60 seconds

If you have a custom audio file, you may want to match this to your audio duration for a perfect sync. See [Audio Synchronization](settings-audio.md#how-audio-sync-works) for details on how the app handles mismatches.

### Only countdown for meetings with video links

When enabled, the app only fires countdowns for calendar events that contain a detected video call link (Zoom, Microsoft Teams, or Google Meet). Events without a video link are ignored.

When disabled, all eligible meetings trigger a countdown — even that "Lunch with Dave" event that's just a calendar block.

**Default:** Off

### Automatically open meeting link at countdown end

When enabled and a video meeting link is detected, the link is automatically opened in your default browser when the countdown reaches zero. The Join Now button is still available for manual use at any time during the countdown.

**Default:** Off

### Continue countdown after joining

By default, clicking **Join Now** (or an inline Join button for simultaneous meetings) opens the meeting link and **closes the countdown window**. Enable this option to bring the drama with you into the meeting — the countdown window stays open so you can watch the full ACTION! clapperboard and LIVE animation play out while your colleagues wonder why you look so excited to be here.

**Default:** Off

## Organization

### Internal Email Domain

Your company's email domain (e.g., `acme.com`). This tells the app how to classify meeting attendees:

- **Internal attendees** — email addresses matching this domain.
- **External attendees** — everyone else, grouped by their email domain with organization favicons.

The countdown window's attendee summary line (e.g., "8 attendees · 5 internal, 3 external from 2 orgs") depends on this being set. If left blank, all attendees appear in a single flat list without internal/external classification.

**Default:** Empty

## Meeting Filters

### Include Tentatively Accepted

When enabled, meetings you've tentatively accepted — or marked "Show As: Tentative" — will trigger countdowns. When disabled, only confirmed/accepted meetings are included.

**Default:** Off

### Include Free Events

When enabled, events marked "Show As: Free" in your calendar (focus time, OOO placeholders, FYI blocks) will trigger countdowns. When disabled, these events are silently skipped.

**Default:** Off

### Include All-Day Events

When enabled, all-day and multi-day events are included in countdown triggers. These are usually things like "Company Holiday" or "Sprint 47" that don't need a broadcast-style entrance.

**Default:** Off

### Back-to-Back Meetings

Controls what happens when a new meeting's countdown would fire while a previous meeting is still in progress:

| Option | Behavior |
|---|---|
| **Use Default Behavior** | Use whatever your current countdown mode is (Countdown + Music, Silent, or Off) — no override. |
| **Silent Countdown** | Countdown window appears but audio is suppressed — useful if you're already on a call. |
| **Skip Countdown** | No countdown window at all. The meeting is still marked as notified. |

**Default:** Use Default Behavior
