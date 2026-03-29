# Meetings Countdown Pro

### Start every meeting like you're about to announce election results.

A macOS menu bar app that plays a dramatic, broadcast-style countdown before your calendar meetings. Complete with synchronized music, attendee intel, and a one-click join button. Because "you're on mute" shouldn't be the most exciting part of your day.

---

| Countdown | ACTION! | LIVE |
|:-:|:-:|:-:|
| ![Countdown](docs/images/countdown.png) | ![ACTION!](docs/images/action.png) | ![LIVE](docs/images/live.png) |

Inspired by [@rtwlz](https://x.com/rtwlz/status/2036082537949434164) on X. 

## Why This Exists

**Your Zoom meeting reminders are broken.** They fire at wrong times across timezones, don't update when meetings get rescheduled, and don't exist at all for meetings on other platforms. If your day spans Zoom, Teams, and Google Meet, you're going to miss one.

Meetings Countdown Pro uses your **macOS Calendar as the single source of truth**. It doesn't care if the meeting is on Zoom, Teams, Google Meet, or a carrier pigeon with a webcam strapped to it. If it's on your calendar, you get a countdown. (The Join Now button currently works with Zoom, Microsoft Teams, and Google Meet links specifically.)

**You don't know who you're about to meet.** We've all done it: hopped on a call expecting a casual internal sync, only to find the customer staring back at you while you're mid-bite into a sandwich. The attendee display groups participants by organization, so you can see at a glance whether this is an internal huddle or an external meeting that requires pants.

**You need AI in your meeting workflow.** Or at least, that's what we're told. More on this below.

## Features

- **Broadcast-style countdown** with synchronized music (bring your own dramatic audio)
- **Menu bar app** — lives quietly in your menu bar, monitors your calendar, pops up when it's go time
- **Works with everything** — if it's on your macOS Calendar, you get a countdown
- **Attendee intelligence** — see who's on the call before you join, grouped by internal vs. external with org-level grouping and favicons
- **One-click join** — hit "Join Now" or let it auto-open the meeting link when the countdown ends (supports Zoom, Microsoft Teams, and Google Meet)
- **Fully configurable** — countdown duration, audio file, calendar selection, timing offset, volume, output device, and more

### AI Integration (yes, really)

Meetings Countdown Pro is *the* meeting countdown app for the age of AI.

When a countdown starts, the app can automatically launch a coding agent (like [Claude Code](https://claude.com/product/claude-code), [Kiro](https://kiro.dev/), or any terminal command) with full meeting context — title, attendees, time, organizations — so your AI assistant can prep you before the call.

The practical use case: many of us now use AI agents to organize meeting notes in markdown files. This feature lets the agent pull up relevant context, previous notes, and prep materials *automatically* as the countdown runs. By the time the music stops, you and your AI assistant are both ready.

**But let's be clear:** you do not have to connect this to anything AI-related. The "AI Integration" feature is really just "run a terminal command with meeting data." You could wire it up to a shell script that opens a folder, curls a weather API, or plays a second, even more dramatic soundtrack. We're still going to call it AI Integration, though. Because Marketing told us we had to. 

## Installation

### Download (recommended)

1. Download the latest `.zip` from [Releases](https://github.com/elarsson1/meetings-countdown-pro/releases)
2. Unzip it
3. Drag **Meetings Countdown Pro.app** into your **Applications** folder
4. **First launch — bypass Gatekeeper** (the app is ad-hoc signed but not notarized, because I am not yet paying the $99/year Apple Developer Tax. This may change if enough people use this, or if I win the lottery):
   1. Double-click the app — macOS will block it and show a warning. Click **Done** (do not move it to Trash).
   2. Open **System Settings → Privacy & Security**.
   3. Scroll down to the Security section — you'll see a message that "Meetings Countdown Pro" was blocked. Click **Allow Anyway**.
   4. Double-click the app again and click **Open** in the confirmation dialog.
5. Grant calendar access when prompted

## How It Works

1. The app sits in your menu bar and polls your macOS Calendar for upcoming meetings
2. When a meeting with a video link is approaching, a countdown window slides in from the right
3. Your chosen audio plays in sync while the attendee panel shows who's on the call — internal vs. external, grouped by organization
4. When the countdown hits zero: **ACTION!** (clapperboard animation) then **LIVE** (broadcast tally light)
5. Click **Join Now** at any point, or let auto-join open the link when the countdown ends

Start your meeting with gravitas!

## Audio

The app does not ship with audio — you provide your own. Drop any MP3, WAV, FLAC, or AAC file into the Audio settings tab. The countdown will synchronize to your audio file's duration, or you can set a custom countdown length.

Popular choices: the BBC News Countdown, a dramatic orchestral piece, or the Jeopardy! think music if you like to live dangerously.

## Requirements

- macOS 12 (Monterey) or later
- Apple Silicon Mac
- At least one calendar account configured in macOS Calendar (iCloud, Google, Microsoft 365, Exchange, CalDAV — anything that syncs to Calendar.app)
- An anchor desk for your home office is not a strict requirement, but imagine the possibilities. If you're on a budget, a broadcast studio virtual background will do in a pinch.

## Contributing

Pull requests are welcome! See [CONTRIBUTING.md](./CONTRIBUTING.md) for development setup, build instructions, debugging, and how to submit changes.

## License

[MIT](./LICENSE) — do whatever you want with it.

## Remember to Countdown Responsibly

This software is provided as-is for your meeting-joining pleasure. The author assumes no responsibility for any injuries sustained while getting overly exuberant before your 9 AM standup, nor for any disciplinary action resulting from playing the BBC News theme at full volume in an open-plan office.
