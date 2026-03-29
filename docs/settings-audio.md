# Audio Settings

The Audio tab controls your countdown music, volume, output device, and timing calibration.

![Audio Settings](images/prefs_audio.png)

## Sound File

### Countdown Music

Click **Choose File...** to select an audio file. Supported formats: **MP3, WAV, FLAC, AAC (M4A)**. The app uses macOS native codecs via AVFoundation, so anything QuickTime can play should work.

After selecting a file, you'll see:
- The file name displayed next to the button.
- A **Preview** button (▶) — plays the first 10 seconds of the file so you can confirm it's the right one. Click again to stop.
- A **Clear** button (✕) — removes the sound file. Countdowns will be silent (visual only).

The app does not ship with audio — you provide your own.

### Duration Override

When you select a sound file, the app automatically detects its duration. This is shown as **Auto** with the detected length.

If auto-detection is inaccurate (rare, but possible with certain file formats), you can enter a manual duration override.

## Playback

### Volume

Master volume slider for countdown audio, from 0% to 100%.

**Default:** 100%

### Audio Output Device

Select which audio output device plays the countdown music. Options:

- **System Default** — follows whatever macOS is currently set to (recommended for most users).
- Any other audio output device currently connected to your Mac (e.g., specific speakers, headphones, or audio interfaces).

The device list refreshes each time you open the dropdown, so newly connected devices will appear.

**Default:** System Default

## Timing Calibration

### Clock Offset

Fine-tunes the alignment between the visual countdown numbers and your audio. The offset delays (or advances, if negative) the first visual tick of the countdown after the window opens.

- **Range:** -2000 to +2000 milliseconds
- **Default:** 0 ms

**Why you'd use this:** Some audio tracks have a beat or tone on each second (like the BBC News Countdown). The clock offset lets you align the visual number change with that beat. Without calibration, the numbers might tick slightly before or after the audio cue.

**How to calibrate:**

1. Go to the Audio tab and note your current offset (default 0 ms).
2. Click **Quick Test (10s)** at the bottom of the Settings window.
3. Watch and listen — do the numbers change in sync with the audio beats?
4. If the numbers tick **before** the beat, increase the offset (positive values delay the tick).
5. If the numbers tick **after** the beat, decrease the offset (negative values advance the tick).
6. Repeat until the visual and audio are in sync.

Typical offsets are small — usually between -200 and +200 ms. If you need more than that, your audio file might have an unusual lead-in.

## How Audio Sync Works

The app ensures your audio **ends exactly when the countdown reaches zero**, regardless of whether your audio is longer or shorter than the countdown duration:

| Scenario | What Happens |
|---|---|
| Audio is **longer** than countdown | Playback starts partway through the file (skips the beginning) so the ending aligns with zero. |
| Audio **matches** countdown | Plays from the beginning. Perfect alignment. |
| Audio is **shorter** than countdown | Countdown window opens silently. Audio starts playing later so it finishes at zero. |

For example, if your countdown is 60 seconds and your audio file is 89 seconds long, the app starts playing at 29 seconds into the file. The last 60 seconds of your audio play over the full countdown.
