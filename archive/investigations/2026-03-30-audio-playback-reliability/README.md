# Audio Playback Reliability Investigation

**Status:** Resolved
**Date:** 2026-03-30
**Fixed in:** commit `b37afa6` · release `v0.1.2`

## Problem Statement

Sporadically, when a countdown window opens, no audio plays. Debug logs show no difference between success and failure — the player appears to be playing but produces no sound. Reproducible randomly by running repeated test countdowns. Other apps on the same Mac have stable audio.

### Updated Reproduction (2026-03-30)

The issue is **device-selection dependent**:

1. **"System Default" works consistently** — no sporadic failures observed.
2. **Selecting a specific device** (any device) causes sporadic silent playback.
3. **Switching back to "System Default"** after having selected a specific device causes **permanent silence** — no audio for any subsequent countdown until the app is fully restarted.

This was reproduced on both the work laptop and personal laptop.

---

## Prior Fixes (Commit History)

| Commit | Problem | Fix |
|--------|---------|-----|
| `01da451` | Segfault on exit | Added `cleanup()` — stop, clear source, detach output, `deleteLater()` on both objects. Connected to `aboutToQuit`. |
| `01da451` | Memory leak in device switching | `deleteLater()` on old `QAudioOutput` after creating replacement. |
| `5c9374e` | Silent replay after EndOfMedia | Force full source reload every time (`setSource(QUrl())` then `setSource(file)`) instead of reusing loaded source. |
| `5c9374e` | Unnecessary `QAudioOutput` recreation | Removed `_apply_output_device()` call from every playback start. |

The EndOfMedia fix in `5c9374e` addressed one class of silent playback but the problem persists intermittently.

---

## Root Cause Hypotheses

### H1: Qt6 FFmpeg Backend Race Condition (HIGH probability)

Since Qt 6.5, the **default** multimedia backend on all platforms is FFmpeg, not the native AVFoundation backend. The app does **not** set `QT_MEDIA_BACKEND`, so it uses whatever Qt defaults to.

Known issues with the FFmpeg backend:
- **QTBUG-98100**: Intermittent no-sound (5-10% success rate in one report). `positionChanged` fires normally but no audio output. Race condition in the multimedia pipeline.
- **Qt Forum reports**: FFmpeg backend freezes/silences when rapidly switching sources or after app has been running. More likely right after startup.
- **PyQt6-Qt6 6.6.3+ regressions**: Backend switching behaves erratically; `QT_MEDIA_BACKEND=darwin` may not actually switch.

The symptoms match exactly: logs show the player is "playing" (states transition normally) but no audio comes out, and it's intermittent.

### H2: Source Reload Timing Race (MEDIUM probability)

The current code does:
```python
self._player.setSource(QUrl())       # Clear
self._player.setSource(QUrl(...))    # Reload
```

Both calls are asynchronous. It's possible that on some runs, the second `setSource` arrives before the first has fully cleared, or the `LoadedMedia` callback fires from the *clear* operation and consumes the `_play_on_load` flag before the real load completes.

### H3: QAudioOutput Recreation Race Condition (HIGH probability — CONFIRMED as primary cause)

`_apply_output_device()` unconditionally creates a new `QAudioOutput`, attaches it to the player, and calls `deleteLater()` on the old one. This happens on **every countdown launch** (not just settings changes) because the app re-applies the device to handle hotplug scenarios (e.g., Bluetooth device disconnected between countdowns).

The race: `_apply_output_device()` recreates `QAudioOutput`, then `_ensure_source_and_play()` immediately clears and reloads the source. The new `QAudioOutput` may not be fully wired up by the time `LoadedMedia` fires and `play()` is called. This explains the sporadic failures when a specific device is selected.

**Additionally**, there is a bug in `app.py` lines 289-290 and 352-353:
```python
if countdown_settings.audio_output_device:
    self._audio.set_output_device(countdown_settings.audio_output_device)
```
When the user switches back to "System Default", `audio_output_device` is `""`, so the `if` guard **skips the call entirely**. The player remains wired to the old specific-device `QAudioOutput`, which may now be stale or invalid. This causes permanent silence until restart.

### H4: PyQt6 GC Collecting Audio Objects (LOW probability)

Python's garbage collector can destroy Qt objects that have no Python references. The current code stores `_audio_output` as `self._audio_output`, which should prevent this. However, during the `_apply_output_device` swap, there's a brief window where references are juggled.

---

## Investigation Plan

### Phase 1: Quick Win — Force Native macOS Backend

**Goal**: Determine if switching from FFmpeg to the native AVFoundation backend resolves the issue.

**Action**: Add this to `__main__.py` (or the earliest entry point), **before** `QApplication` is created:

```python
import os
os.environ["QT_MEDIA_BACKEND"] = "darwin"
```

**Verification**: Check logs for backend confirmation. Qt 6.6.3+ has a known bug where the env var is ignored — if that's the case, we need to pin `PyQt6-Qt6==6.6.2`.

**Test**: Run 20+ consecutive test countdowns and record success/failure rate.

**Why this first**: This is the lowest-effort change with the highest probability of impact. If the FFmpeg backend race condition is the cause, this eliminates it entirely.

### Phase 2: Automated Stress Test Harness

**Goal**: Create a repeatable, automated test loop that exercises the exact audio code path without requiring manual UI interaction.

**Design**:

```
tests/audio_stress_test.py
```

```python
"""
Headless stress test for AudioPlayer.
Runs N consecutive play cycles, monitoring for silent failures.

Usage:
    python tests/audio_stress_test.py [--cycles 50] [--sound-file path.mp3] [--backend darwin|ffmpeg]
"""

import os
import sys
import time
import logging

# Must set backend before importing Qt
backend = "darwin"  # or from CLI args
os.environ["QT_MEDIA_BACKEND"] = backend

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer, QUrl, QEventLoop
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

class AudioStressTester:
    """Exercises the same code path as a real countdown."""

    def __init__(self, sound_file: str, cycles: int):
        self.sound_file = sound_file
        self.total_cycles = cycles
        self.current_cycle = 0
        self.successes = 0
        self.failures = 0
        self.results = []  # list of (cycle, "ok"|"SILENT", duration_ms)

        # Create player exactly like AudioPlayer.__init__
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(1.0)

        self.player.mediaStatusChanged.connect(self._on_status)
        self.player.errorOccurred.connect(self._on_error)
        self.player.positionChanged.connect(self._on_position)

        self._play_on_load = False
        self._got_position_change = False
        self._playback_started_at = None

    def run_next_cycle(self):
        if self.current_cycle >= self.total_cycles:
            self._print_summary()
            QApplication.instance().quit()
            return

        self.current_cycle += 1
        self._got_position_change = False
        self._play_on_load = True
        self._playback_started_at = None

        log.info("=== CYCLE %d/%d ===", self.current_cycle, self.total_cycles)

        # Replicate the exact _ensure_source_and_play code path
        self.player.setSource(QUrl())
        self.player.setSource(QUrl.fromLocalFile(self.sound_file))

        # After 3 seconds, check if audio actually played
        QTimer.singleShot(3000, self._check_and_stop)

    def _on_status(self, status):
        log.debug("  Status: %s (play_on_load=%s)", status, self._play_on_load)
        if status == QMediaPlayer.MediaStatus.LoadedMedia:
            if self._play_on_load:
                self._play_on_load = False
                self.player.setPosition(0)
                self.player.play()
                self._playback_started_at = time.monotonic()
                log.info("  -> play() called")

    def _on_position(self, pos_ms):
        if pos_ms > 0:
            self._got_position_change = True

    def _on_error(self, error, message):
        log.warning("  ERROR: %s — %s", error, message)

    def _check_and_stop(self):
        """After letting it play for 3s, check if position advanced."""
        pos = self.player.position()
        state = self.player.playbackState()
        status = self.player.mediaStatus()

        if self._got_position_change and pos > 100:
            log.info("  RESULT: OK (position=%dms, state=%s)", pos, state)
            self.successes += 1
            self.results.append((self.current_cycle, "ok", pos))
        else:
            log.warning("  RESULT: *** SILENT *** (position=%dms, state=%s, status=%s)",
                        pos, state, status)
            self.failures += 1
            self.results.append((self.current_cycle, "SILENT", pos))

        self.player.stop()
        # Small pause between cycles
        QTimer.singleShot(500, self.run_next_cycle)

    def _print_summary(self):
        log.info("=" * 60)
        log.info("STRESS TEST COMPLETE: %d cycles", self.total_cycles)
        log.info("  Successes: %d (%.0f%%)", self.successes,
                 100 * self.successes / self.total_cycles)
        log.info("  Failures:  %d (%.0f%%)", self.failures,
                 100 * self.failures / self.total_cycles)
        if self.failures:
            silent_cycles = [r[0] for r in self.results if r[1] == "SILENT"]
            log.info("  Silent cycles: %s", silent_cycles)
        log.info("=" * 60)
```

**Key design decisions**:
- Replicates the **exact** code path (`setSource(empty)` → `setSource(file)` → wait for `LoadedMedia` → `play()`)
- Uses `positionChanged` signal + position check as the ground truth for whether audio is actually flowing (not just whether the player *thinks* it's playing)
- Records per-cycle results for pattern analysis (e.g., is it always the first cycle? every Nth cycle? random?)
- Configurable backend via CLI arg to A/B test FFmpeg vs darwin
- Runs headless (no countdown window) to isolate the audio stack from UI rendering
- 500ms pause between cycles mimics real-world usage gap

**Extended variant**: A second mode that also recreates the `QMediaPlayer` + `QAudioOutput` objects each cycle (to test whether object reuse is a factor).

### Phase 3: Add Observability to Production Code

Even with DEBUG logging, the current code cannot distinguish "playing with sound" from "playing silently". Add:

1. **Position polling**: After calling `play()`, start a `QTimer` that checks `self._player.position()` at 500ms intervals for the first 2 seconds. If position doesn't advance past 100ms, log a WARNING: `"Audio may be silent — position not advancing"`.

2. **Playback state logging**: Log `playbackStateChanged` signal (not just `mediaStatusChanged`) to capture the full state machine: `StoppedState → PlayingState` vs any unexpected transitions.

3. **Backend identification**: At startup, log which Qt multimedia backend is active:
   ```python
   log.info("Qt media backend: %s", os.environ.get("QT_MEDIA_BACKEND", "(default/auto)"))
   ```

4. **QAudioOutput state**: Log `audio_output.volume()` and `audio_output.isMuted()` immediately after `play()` to rule out volume/mute state bugs.

### Phase 4: Simplification Opportunities

The current implementation has several areas where complexity can be reduced:

1. **Remove the clear-then-set pattern**: Instead of `setSource(QUrl())` + `setSource(QUrl.fromLocalFile(...))`, try `player.stop()` + `player.setPosition(0)` + `player.setSource(QUrl.fromLocalFile(...))`. The double-set may itself be a race condition trigger (H2). Test this in the stress harness.

2. **Add a small delay between clear and reload**: If the double-set is needed, insert a `QTimer.singleShot(50, ...)` between the clear and the reload to let the first operation complete:
   ```python
   self._player.setSource(QUrl())
   QTimer.singleShot(50, lambda: self._player.setSource(QUrl.fromLocalFile(self._sound_file)))
   ```

3. **Preview method doesn't use deferred play**: `preview()` calls `play()` directly after `setSource()` without waiting for `LoadedMedia`. This is a known race condition. It should use the same deferred pattern as countdown playback.

4. **Consider a fresh QMediaPlayer per countdown**: Instead of reusing one player across the app lifetime, create a new `QMediaPlayer` + `QAudioOutput` for each countdown and destroy them after. This avoids any accumulated state bugs. The stress harness can test both approaches.

---

## Alternative Framework Assessment

### Current Stack: QMediaPlayer + QAudioOutput (PyQt6)

- **Pros**: Already integrated, Qt-native signals/slots
- **Cons**: Known sporadic silent failures, FFmpeg backend issues, source reload quirks, opaque failure modes, multiple open Qt bugs

### Option A: PyObjC AVPlayer (RECOMMENDED)

Direct Python bindings to Apple's AVFoundation — the same backend QMediaPlayer delegates to, but without the Qt middleware layer.

| Aspect | Assessment |
|--------|-----------|
| **Reliability** | Excellent — native Apple API, no intermediary |
| **MP3 + seeking** | Yes, full support |
| **Volume control** | Yes (`volume` property) |
| **Device selection** | Yes (`audioOutputDeviceUniqueID`) |
| **PyQt6 compat** | Good — uses KVO for async, bridge to Qt via `QTimer.singleShot(0, ...)` |
| **Dependencies** | `pyobjc-framework-AVFoundation` (we already use pyobjc for EventKit) |
| **Integration effort** | ~150-250 lines to replace `audio_player.py` |

**Why this is the top pick**: It eliminates the entire Qt multimedia abstraction that is causing problems, while using the exact same macOS audio engine underneath. We already depend on pyobjc, so it's a natural fit.

### Option B: miniaudio (via `pyminiaudio`)

Cross-platform C library with Python bindings. Uses Core Audio on macOS.

| Aspect | Assessment |
|--------|-----------|
| **Reliability** | Very good — battle-tested C library (4k+ GitHub stars) |
| **MP3 + seeking** | Yes (built-in decoder, no system codecs needed) |
| **Volume control** | Yes |
| **Device selection** | Yes (`PlaybackDevice(device_id=...)`) |
| **PyQt6 compat** | Good — runs on its own audio thread |
| **Dependencies** | `miniaudio` package (bundles the C lib) |
| **Integration effort** | ~120-180 lines |

**Tradeoff**: Zero system dependencies (brings its own MP3 decoder), but the Python bindings are a single-maintainer project.

### Option C: NSSound (via pyobjc-framework-Cocoa)

Simplest native option. ~80 lines.

**Disqualified**: Legacy API, known bugs with `setPlaybackDeviceIdentifier` after extended use. Apple is not investing in it.

### Option D: pygame.mixer

**Disqualified**: MP3 support "limited and not very reliable" per pygame's own docs. No device selection. Event loop conflicts with PyQt6.

### Option E: python-sounddevice

**Disqualified**: Raw audio I/O library, not a player. Would need MP3 decoding, buffer management, manual seeking — 300+ lines of low-level plumbing.

---

## Recommended Plan of Attack

### Step 1: Build the stress test harness ✅ DONE

Created `tests/audio_stress_test.py` — a configurable stress tester that:
- Replicates the exact `_ensure_source_and_play` code path (clear source → set source → wait for `LoadedMedia` → `play()`)
- Uses `positionChanged` + position check as ground truth for actual audio output
- Supports `--fresh-player` to recreate `QMediaPlayer`/`QAudioOutput` each cycle
- Supports `--ui` to simulate countdown window construction (widget tree, stylesheets, drop shadows, animations, tick timer) — creates event loop contention
- Supports `--backend darwin|ffmpeg` to A/B test backends
- Records per-cycle results with full DEBUG-level state machine traces

Also created `tests/run_audio_investigation.sh` — a runner that executes all 8 configurations and collects system info + logs into a timestamped directory.

### Step 2: Establish baseline failure rate — DONE

**Personal laptop results** (MacBook, macOS Tahoe, PyQt6 6.10.2, Qt 6.10.0):

| Configuration | Backend | Cycles | Successes | Failures |
|---|---|---|---|---|
| Headless, reused player | FFmpeg (default) | 50 | 50 (100%) | 0 |
| Headless, fresh player | FFmpeg (default) | 50 | 50 (100%) | 0 |
| UI contention, reused player | FFmpeg (default) | 50 | 50 (100%) | 0 |

**Work laptop results**: Test suite aborted early — all tests passing. The stress test harness does **not** exercise device selection, which is the actual trigger (see Updated Reproduction above).

**Conclusion**: The stress test doesn't reproduce the bug because it uses the system default device. The bug is specific to the device-selection code path.

### Step 3: Fix QAudioOutput device-switching bugs — NEXT

Three issues to fix in `audio_player.py` and `app.py`:

#### Fix 3a: Always call `set_output_device()` (fixes permanent silence on return to System Default)

In `app.py`, the `if` guard around `set_output_device()` skips the call when `audio_output_device` is empty (System Default). This means after switching away from a specific device, the player stays wired to the old (now stale) `QAudioOutput`. Fix: always call `set_output_device()`, passing `""` for System Default.

**Files**: `app.py` lines 289-290, 352-353 — remove the `if` guard.

#### Fix 3b: Skip `QAudioOutput` recreation when device hasn't changed (fixes sporadic failures)

`_apply_output_device()` unconditionally recreates `QAudioOutput` every time it's called, even when the device hasn't changed. This is the root cause of the race condition — the new `QAudioOutput` may not be ready when `play()` fires moments later.

Fix: Track `_active_device_id` (what's actually wired up) separately from `_preferred_device_id` (what the user wants). Only recreate `QAudioOutput` when:
- The preferred device ID has changed, OR
- The preferred device is no longer available (hotplug fallback to System Default)

When the active device already matches the preferred device, skip recreation entirely — just return.

**File**: `audio_player.py` `_apply_output_device()` — add early return when device matches.

#### Fix 3c: Preserve hotplug fallback behavior

The per-countdown device check must remain so that if a Bluetooth speaker or docking station is disconnected between countdowns, the app falls back to System Default. The logic in Fix 3b handles this: if the preferred device is no longer in `QMediaDevices.audioOutputs()`, the active device ID won't match, so `QAudioOutput` will be recreated with the system default.

**Sequence after all three fixes:**

1. Countdown starts → `set_output_device("bluetooth-xyz")` called
2. `_apply_output_device()` checks: is `_active_device_id` already `"bluetooth-xyz"`?
   - **Yes** → no-op, return immediately (no race condition)
   - **No** (first time, or device was unplugged and re-plugged) → recreate `QAudioOutput`, update `_active_device_id`
3. If preferred device not found in available devices → fall back to System Default, set `_active_device_id = ""`
4. `_ensure_source_and_play()` runs against a stable, already-wired `QAudioOutput`

### Step 4: Validate fixes

- Manually test: select a specific device, run 10+ countdowns → should be 100% reliable
- Manually test: switch back to System Default → audio should work immediately
- Manually test: select a Bluetooth device, disconnect it, trigger countdown → should fall back to System Default
- Update the stress test harness to include a `--device` flag for automated device-selection testing

### Step 5: Decision point — fix or replace

| If... | Then... |
|-------|---------|
| Step 3 fixes achieve 100% reliability | Ship it, add position-polling watchdog (Phase 3) for safety |
| Sporadic failures persist even with no-op optimization | Investigate whether the race is in `_ensure_source_and_play` source reload pattern (H2) |
| Nothing reliably fixes QMediaPlayer | Replace with PyObjC AVPlayer (Option A) |

### Step 6: If replacing — implement AVPlayer backend
- Create `audio_player_avfoundation.py` with the same public interface as current `AudioPlayer`
- Swap it in `app.py` (single import change)
- Validate with the stress harness
- Run through the full manual test plan (TESTING.md audio section)

---

## Timeline Estimate

- Step 1-2: Build harness + baseline — DONE (stress test doesn't cover device selection path)
- Step 3: Fix device-switching bugs — NEXT session (small code change in `audio_player.py` + `app.py`)
- Step 4: Manual validation — same session as Step 3
- Step 5: Decision — after Step 4 results
- Step 6 (if needed): AVPlayer rewrite — one session

---

## Current Environment

### Personal laptop (tested, no failures)
- **PyQt6**: 6.10.2
- **Qt**: 6.10.0
- **macOS**: Darwin 25.3.0 (macOS Tahoe)
- **Active backend**: FFmpeg 7.1.2 (confirmed via log output)

### Work laptop (to be tested)
- Run `tests/run_audio_investigation.sh` to capture full environment details automatically.

Note: Qt 6.10.0 is very recent. Many of the QTBUG fixes landed in 6.6-6.8, but new regressions are always possible. The FFmpeg backend has been the default since 6.5, meaning the app has likely never used the native darwin backend.

## Open Questions

1. ~~**Is FFmpeg or darwin backend actually active?**~~ Confirmed FFmpeg 7.1.2 on personal laptop. Work laptop TBD.
2. ~~**Why doesn't the stress test reproduce the bug?**~~ The stress test uses System Default device. The bug only triggers with explicit device selection.
3. **Does the fix in Step 3b fully eliminate sporadic failures?** The theory is sound (avoid unnecessary `QAudioOutput` recreation) but needs validation with real-world testing.
4. **Is there a secondary race in `_ensure_source_and_play`?** If sporadic failures persist after the device-switching fix, the `setSource(QUrl())` → `setSource(file)` pattern (H2) may also need attention.
