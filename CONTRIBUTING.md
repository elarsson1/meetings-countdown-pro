# Contributing to Meetings Countdown Pro

Thanks for your interest in contributing! This guide covers everything you need to get a development environment running, build the macOS app bundle, and submit changes.

## Prerequisites

- **macOS 12+** (Monterey or later)
- **Python 3.14+** from the [python.org macOS installer](https://www.python.org/downloads/macos/) (recommended). Homebrew Python also works, but be aware that `brew upgrade` can silently break virtual environments. Do not use the system Python shipped with Xcode Command Line Tools (3.9, EOL).
- **Xcode Command Line Tools** (for `codesign` and `iconutil`):
  ```bash
  xcode-select --install
  ```
- **Git**

## Getting Started

```bash
git clone https://github.com/elarsson1/meetings-countdown-pro.git
cd meetings-countdown-pro
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Running the App

```bash
python -m meetings_countdown_pro
```

Or equivalently:

```bash
python main.py
```

On first launch, macOS will prompt for calendar access. Grant it — the app reads calendar events via EventKit to schedule countdowns.

## Project Structure

```
meetings-countdown-pro/
├── main.py                        # Entry point
├── requirements.txt               # Pinned dependencies
├── MeetingsCountdownPro.spec      # PyInstaller build spec
├── meetings_countdown_pro/        # Main package
│   ├── __init__.py
│   ├── __main__.py                # python -m support
│   ├── app.py                     # QApplication, menu bar, polling loop
│   ├── calendar_service.py        # EventKit integration (pyobjc)
│   ├── countdown_window.py        # Countdown window UI + animations
│   ├── audio_player.py            # QMediaPlayer wrapper, audio sync
│   ├── meeting.py                 # Meeting data model
│   ├── settings.py                # Settings model, load/save
│   ├── settings_window.py         # Settings UI (General, Calendars, Audio, AI)
│   ├── favicon_cache.py           # Async favicon fetching + disk cache
│   ├── notification_state.py      # Dedup state (notified.json)
│   ├── agent_launcher.py          # AI Integration: terminal launch
│   └── assets/                    # SVG icons
├── assets/                        # App icon (SVG source + .icns)
├── tests/                         # Tests
├── mockups/                       # HTML/CSS design mockups
├── SPEC.md                        # Product specification
└── TESTING.md                     # Manual test plan
```

## Logging and Debugging

### Debug Mode

Run with `--debug` to enable verbose logging:

```bash
python -m meetings_countdown_pro --debug
```

This sets the log level to `DEBUG` (default is `INFO`). Log output goes to stderr in the format:

```
2026-03-28 14:30:00,123 [meetings_countdown_pro.app] DEBUG: Polling for upcoming meetings (mode=countdown_and_music)
```

### What Gets Logged

| Module | What it logs |
|---|---|
| `app.py` | Calendar access status, poll results, meeting scheduling, countdown triggers, back-to-back decisions, launch agent install/remove |
| `calendar_service.py` | EventKit queries, attendee parsing, meeting filtering |
| `audio_player.py` | Audio load/play/stop, device selection, sync timing |
| `agent_launcher.py` | AI integration command assembly, terminal launch |
| `settings_window.py` | Settings save/load issues |

### Test Mode (Settings UI)

The Settings window has two test buttons at the bottom:

- **Test Countdown** — runs a full countdown using your configured duration and audio file with a fake meeting
- **Quick Test (10s)** — runs an abbreviated 10-second countdown for quick iteration

These are useful for testing UI changes, audio sync, and animation timing without waiting for a real meeting.

## Building the macOS App Bundle

### Install PyInstaller

```bash
pip install pyinstaller
```

### Build

```bash
pyinstaller MeetingsCountdownPro.spec --noconfirm
```

This produces `dist/Meetings Countdown Pro.app` (~100 MB). The spec file handles:

- Bundling the Python interpreter and all dependencies
- Including SVG assets
- Setting the app icon, bundle identifier (`com.axeltech.meetings-countdown-pro`), and Info.plist metadata
- Configuring `LSUIElement` (menu-bar app, no Dock icon)
- Adding calendar permission descriptions for macOS privacy prompts

### Ad-Hoc Code Signing

The app must be signed to run on macOS (especially Apple Silicon). Ad-hoc signing is free and requires no Apple Developer account:

```bash
codesign --force --deep -s - "dist/Meetings Countdown Pro.app"
```

Verify the signature:

```bash
codesign --verify --deep --strict "dist/Meetings Countdown Pro.app"
```

### Regenerating the App Icon

If you modify `assets/icon.svg`, regenerate the `.icns` file:

```bash
python3 -c "
import os, subprocess, sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtCore import Qt, QSize

app = QApplication(sys.argv)
renderer = QSvgRenderer('assets/icon.svg')
iconset = 'assets/AppIcon.iconset'
sizes = {
    'icon_16x16.png': 16, 'icon_16x16@2x.png': 32,
    'icon_32x32.png': 32, 'icon_32x32@2x.png': 64,
    'icon_128x128.png': 128, 'icon_128x128@2x.png': 256,
    'icon_256x256.png': 256, 'icon_256x256@2x.png': 512,
    'icon_512x512.png': 512, 'icon_512x512@2x.png': 1024,
}
for name, size in sizes.items():
    img = QImage(QSize(size, size), QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    renderer.render(p)
    p.end()
    img.save(os.path.join(iconset, name))
subprocess.run(['iconutil', '-c', 'icns', iconset, '-o', 'assets/AppIcon.icns'], check=True)
print('Done')
"
```

### Full Build + Sign (One-Liner)

```bash
pyinstaller MeetingsCountdownPro.spec --noconfirm && codesign --force --deep -s - "dist/Meetings Countdown Pro.app"
```

## Submitting Changes

1. Fork the repository and create a feature branch from `main`.
2. Make your changes. Try to keep commits focused and well-described.
3. Test your changes:
   - Run the app and verify the feature or fix works.
   - Use Test Countdown and Quick Test in Settings to exercise the countdown flow.
   - If you changed packaging or assets, do a full build and verify the `.app` launches.
4. Open a pull request against `main` with a clear description of what changed and why.

## Configuration Files

The app stores user configuration in `~/.config/meetings-countdown-pro/`. During development you may want to reset settings by removing this directory:

```bash
rm -rf ~/.config/meetings-countdown-pro/
```

## Key References

- [SPEC.md](./SPEC.md) — full product specification
- [TESTING.md](./TESTING.md) — manual test plan
- [mockups/](./mockups/) — HTML/CSS design mockups for all UI states
