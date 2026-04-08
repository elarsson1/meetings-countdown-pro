# General Settings

The General tab is organized into three group boxes arranged in a single column: Startup, Countdown, and Working Hours.

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

### Automatically open meeting link at countdown end

When enabled and a video meeting link is detected, the link is automatically opened in your default browser when the countdown reaches zero. The Join Now button is still available for manual use at any time during the countdown.

**Default:** Off

### Continue countdown after joining

By default, clicking **Join Now** (or an inline Join button for simultaneous meetings) opens the meeting link and **closes the countdown window**. Enable this option to bring the drama with you into the meeting — the countdown window stays open so you can watch the full ACTION! clapperboard and LIVE animation play out while your colleagues wonder why you look so excited to be here.

**Default:** Off

### Back-to-Back Meetings

Controls what happens when a new meeting's countdown would fire while a previous meeting is still in progress:

| Option | Behavior |
|---|---|
| **Use Default Behavior** | Use whatever your current countdown mode is (Countdown + Music, Silent, or Off) — no override. |
| **Silent Countdown** | Countdown window appears but audio is suppressed — useful if you're already on a call. |
| **Skip Countdown** | No countdown window at all. The meeting is still marked as notified. |

**Default:** Use Default Behavior

> **Looking for the Internal Email Domain or Meeting Filters?** Internal Email Domain has moved to the [Attendees](settings-attendees.md) tab. Meeting Filters (including "Only meetings with video links") have moved to the [Calendars](settings-calendars.md#meeting-filters) tab.

## Working Hours

### Only start countdowns during working hours

When enabled, countdowns are suppressed outside of your configured working days and hours — the same behavior as setting the mode to "Off." Meetings outside working hours still appear in the menu bar so you can see what's coming up, but no countdown window will fire. A small orange badge dot appears on the menu bar icon when you are currently outside working hours.

This is useful if your calendar spans multiple time zones or includes weekend events you don't need a dramatic entrance for.

**Default:** Off

### Days

Select which days of the week are considered working days. Days are displayed Sunday through Saturday as toggle buttons — click a day to include or exclude it.

**Default:** Monday–Friday

### Hours

Set the start and end times for your working hours window. Meetings starting at or after the start time and before the end time will trigger countdowns. The end time is exclusive — a meeting starting exactly at 5:00 PM with a 5:00 PM end time will not trigger.

The time inputs accept flexible formats: `9:00 AM`, `9AM`, `14:30`, `2:30 PM`, etc. The value normalizes to a standard display (e.g., `9:00 AM`) when you tab out of the field. Invalid input is highlighted with a red border and an error message.

- **Start default:** 9:00 AM
- **End default:** 5:00 PM
