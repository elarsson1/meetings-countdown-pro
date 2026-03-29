# Test Mode

The Settings window includes two testing buttons at the bottom that let you preview and calibrate your countdown setup without waiting for a real meeting.

## Test Countdown

Click **Test Countdown** to launch a full countdown using your current settings (duration, sound file, clock offset, volume) with sample meeting data. The test uses a mock meeting with dummy attendees from multiple organizations, so you can see the full attendee panel layout.

This is useful for:

- Previewing the countdown window appearance for the first time.
- Hearing your selected audio with the configured sync timing.
- Seeing the full end-of-countdown animation sequence (ACTION! clapperboard → LIVE badge).
- Verifying your [AI Integration](ai-integration.md) setup, if enabled — the test countdown triggers the agent launch with mock meeting data.

The test countdown runs in real-time at your configured duration, so if your countdown is set to 89 seconds, the test will take 89 seconds.

**Note:** The Test Countdown button is disabled while a countdown (real or test) is already running. Close the current countdown window first.

## Quick Test (10s)

Click **Quick Test (10s)** for a rapid 10-second countdown. This uses the same mock meeting data but overrides your countdown duration to 10 seconds.

This is ideal for:

- **Clock offset calibration** — quickly iterate on the [Clock Offset](settings-audio.md#clock-offset) value to align visual ticks with audio beats without sitting through a full-length countdown each time.
- Quick sanity checks after changing audio settings.

The Quick Test plays the last 10 seconds of your audio file (if the file is longer than 10 seconds), so you hear the same ending you'd hear in a real countdown.
