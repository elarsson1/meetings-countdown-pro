# Back-to-Back Meeting Handling Investigation

**Status:** Resolved
**Date:** 2026-03-31
**Fixed In:*** commit '35168d0' release '0.1.4'

## Problem Statement

Two issues identified with back-to-back meeting handling:

1. **Filter bypass:** `is_meeting_in_progress()` does not apply the same event filters as `fetch_upcoming()`, causing non-qualifying events to trigger back-to-back behavior.
2. **Misleading UI label:** The "Countdown + Music" option for back-to-back handling implies it forces music, but it actually falls through to the user's default countdown mode.

---

## Issue 1: Filter Bypass in `is_meeting_in_progress()`

### Current Behavior

When the countdown for Meeting B fires, `is_meeting_in_progress()` (`calendar_service.py:266`) checks if any event overlaps with "now." This method runs a **separate, unfiltered** EventKit query. It only skips all-day events and respects calendar selection — nothing else.

### Example

User has "Video Calls Only" enabled. Their calendar:
- 12:00–13:00 "Lunch with Dave" (no video link)
- 13:00–13:30 "Sprint Review" (Zoom link)

At ~12:58 when Sprint Review's countdown fires, `is_meeting_in_progress()` finds "Lunch with Dave" and returns `True`. The user's back-to-back setting kicks in (e.g., silent countdown or skip), even though "Lunch with Dave" would never have triggered a countdown itself.

### Filter Comparison

| Filter | `fetch_upcoming` | `is_meeting_in_progress` |
|--------|-----------------|--------------------------|
| Calendar selection | Yes | Yes |
| All-day exclusion | Yes | Yes (hardcoded) |
| Declined events | Yes | **No** |
| Tentative events | Yes (configurable) | **No** |
| Video-only mode | Yes | **No** |
| Canceled events | No (separate gap) | **No** |

### SPEC Reference

Section 11.2 says: "Check if any **monitored** meeting is currently in progress." The word "monitored" implies it should respect the same filters that `fetch_upcoming` applies.

### Recommended Fix

Reuse `_convert_event()` + `_passes_filters()` inside `is_meeting_in_progress()` instead of checking raw EKEvent objects. Something like:

```python
def is_meeting_in_progress(self, settings: Settings) -> bool:
    # ... query events as before ...
    now = datetime.now(timezone.utc)
    for ev in events:
        meeting = self._convert_event(ev)
        if not meeting:
            continue
        if not self._passes_filters(meeting, settings):
            continue
        if meeting.start <= now < meeting.end:
            return True
    return False
```

This ensures back-to-back detection only considers events that would themselves be countdown-worthy.

---

## Issue 2: Misleading "Countdown + Music" Label

### Current Behavior

The back-to-back dropdown in Settings (`settings_window.py:248`) shows three options:

| UI Label | Internal Value | Actual Behavior |
|----------|---------------|-----------------|
| **Countdown + Music** | `countdown_music` | Falls through to `self._settings.mode` (the user's global countdown mode) |
| **Silent Countdown** | `silent` | Forces silent countdown regardless of global mode |
| **Skip Countdown** | `skip` | Suppresses countdown entirely |

Confirmed in `app.py:261-273`:
```python
if self._calendar.is_meeting_in_progress(self._settings):
    b2b = self._settings.back_to_back
    if b2b == "skip":
        return
    elif b2b == "silent":
        effective_mode = "silent"
    else:
        effective_mode = self._settings.mode  # <-- uses global mode, not forced music
```

### The Problem

"Countdown + Music" implies it will always play music for back-to-back meetings. But if the user's global mode is "Silent Countdown," they get a silent countdown for back-to-backs too. The label promises something the code doesn't deliver.

### Deliberation

The current **behavior** is correct. The back-to-back setting should be an override, not a mode selector. It makes no sense for back-to-backs to play music when the user's normal setting is silent. The three options are really:

1. **No override** — use whatever the normal countdown behavior is
2. **Force silent** — downgrade to silent even if normal mode has music
3. **Force skip** — suppress the countdown entirely

### Recommended Fix

Rename the first option from "Countdown + Music" to "Use Default Behavior" (or "Normal Countdown"). Also rename the internal value from `countdown_music` to `default` for clarity.

| Current Label | New Label | Internal Value |
|---------------|-----------|---------------|
| Countdown + Music | Use Default Behavior | `default` |
| Silent Countdown | Silent Countdown | `silent` |
| Skip Countdown | Skip Countdown | `skip` |

Update in:
- `settings_window.py:248` — combo box item label
- `settings_window.py:474,531` — internal value mapping
- `settings.py` — default value (if referenced)
- `SPEC.md` — settings table row 11

---

## Implementation Plan

1. ~~Fix `is_meeting_in_progress()` to reuse `_convert_event()` + `_passes_filters()`~~ **Done**
2. ~~Rename "Countdown + Music" to "Use Default Behavior" in UI and internal value~~ **Done**
3. ~~Update SPEC.md settings table and section 11.2~~ **Done**
4. ~~When complete, move this file to `archive/investigations/`~~ **Done**
