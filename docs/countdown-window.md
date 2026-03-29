# Countdown Window

The countdown window is the main event. When a meeting is approaching, it slides in from the right side of your screen with your chosen audio playing in sync.

![Countdown Window](images/countdown.png)

## Window Behavior

- **Position:** Upper-right corner of your primary display.
- **Always on top:** Floats above regular windows but below system dialogs.
- **Frameless:** No title bar — dark background with rounded corners for a broadcast studio look.
- **Draggable:** Click and drag anywhere on the window to reposition it.
- **Dismissing:** Click the X button or press **Escape** to close the window and stop audio. The meeting is still marked as notified — you won't get a repeat countdown.

## Layout

### Left Panel — Meeting Details

The left side shows everything you need to know about who you're about to meet:

- **Meeting title** in bold.
- **Time range** (start – end).
- **Attendee summary line** — e.g., "8 attendees · 8 external from 3 orgs". This is always visible, even if the full list is long.
- **Attendee list**, grouped into:
  - **Internal attendees** — people whose email domain matches your configured [Internal Email Domain](settings-general.md#internal-email-domain). Listed alphabetically.
  - **External attendees** — grouped by organization (email domain), with each group headed by the organization's favicon and domain name. Sorted alphabetically within each group.

The entire left panel scrolls if the attendee list is long.

If no Internal Email Domain is configured, all attendees appear in a single flat list.

### Right Panel — Countdown & Join

- **Countdown timer** — large, bold seconds display (e.g., `83`). Always whole seconds, no MM:SS format.
- **Join Now button** — opens the meeting link in your default browser. Supports Zoom, Microsoft Teams, and Google Meet links. The button only appears when a video link is detected in the calendar event.
- **Mute toggle** (bottom-right) — mutes/unmutes audio without stopping playback, so timing stays in sync. Only visible when audio is actually playing (hidden in Silent mode or when no sound file is configured).

## Simultaneous Meetings

When two or more meetings start at the same time, all meetings are listed in the left panel, each with their own attendee list and individual **Join Now** button. In this case:

- The right-side Join Now button is hidden (use each meeting's inline button instead).
- **Auto-join is disabled** — you choose which meeting to join.
- The countdown clock still counts down to the shared start time.

## End-of-Countdown Sequence

When the timer hits zero, two animation phases play:

### Phase 1 — ACTION! (~2 seconds)

The countdown area transitions to a movie clapperboard with "ACTION!" text. The clapperboard's top bar animates a clap.

![ACTION!](images/action.png)

### Phase 2 — LIVE (persists)

The clapperboard transitions to a red pulsing "LIVE" badge, styled like a broadcast studio tally light. The window stays open until you close it, so you can still use the Join Now button.

![LIVE](images/live.png)

## Late Starts

If the app triggers a countdown when the meeting start is less than the full countdown duration away (e.g., your laptop just woke from sleep), it adjusts automatically:

- The countdown starts at the remaining seconds.
- Audio playback is seeked forward so it still ends at the right time.
- If less than 5 seconds remain, the countdown is skipped entirely — it would be more jarring than helpful.
