# EventKit Filtering Investigation

**Status:** Open
**Date:** 2026-03-31

## Problem Statement

The calendar service (`calendar_service.py`) queries EventKit for upcoming meetings but only filters on a subset of available event properties. A comprehensive review of the EKEvent data model revealed several gaps where irrelevant events could trigger countdowns.

## Current Filters

| Filter | API | Behavior |
|--------|-----|----------|
| Participant status | `ev.myStatus()` | Exclude declined; optionally exclude tentative |
| All-day events | `ev.isAllDay()` | Exclude unless `include_all_day` is on |
| Video link presence | Parsed from location/notes/URL | "Video calls only" mode |
| Calendar selection | `predicateForEvents...calendars:` | User picks which calendars to monitor |

## Gaps Identified

### 1. Canceled events not filtered (high priority)

`ev.status()` returns `EKEventStatusCanceled` (3) for events the organizer has canceled but that remain in the calendar store. This is common with Exchange and Google calendars. Currently these pass through all filters and could trigger a countdown for a meeting that no longer exists.

**Recommendation:** Filter out in `_convert_event` — return `None` when `ev.status() == 3`. Canceled events should never produce a countdown.

**EKEventStatus values:**
| Value | Constant | Action |
|-------|----------|--------|
| 0 | None | Keep (default for locally-created events) |
| 1 | Confirmed | Keep |
| 2 | Tentative | Keep (event itself is tentative, rare) |
| 3 | Canceled | **Filter out** |

### 2. "Free" availability not filtered (medium priority)

`ev.availability()` returns `EKEventAvailabilityFree` (1) for events marked "Show As: Free" in the calendar client. These are typically FYI blocks, focus time, or OOO placeholders that don't warrant a broadcast countdown.

**Recommendation:** Add a config toggle (default: skip free events). Most users won't want a countdown for a "Focus Time" block.

**EKEventAvailability values:**
| Value | Constant | Action |
|-------|----------|--------|
| -1 | NotSupported | Keep (treat as busy) |
| 0 | Busy | Keep (default) |
| 1 | Free | **Optionally filter out** (new setting) |
| 2 | Tentative | Keep |
| 3 | Unavailable | Keep (blocked time) |

### 3. Delegated participant status not handled (low priority)

`ev.myStatus()` can return `EKParticipantStatusDelegated` (5), meaning the user formally delegated their attendance to someone else ("go in my place"). Our default-to-accepted logic currently treats this as accepted.

**Deliberation:** We considered whether filtering delegated events could accidentally exclude meetings where the user simply added extra attendees. Conclusion: **safe to filter**. The `Delegated` status is a formal calendar protocol operation (CalDAV/Exchange) that specifically means "someone else is attending for me." It does NOT fire when:
- Adding attendees to a meeting you accepted (your status stays `Accepted`)
- Forwarding a calendar invite via email (outside EventKit entirely)

That said, this status is genuinely rare in the wild. Most calendar clients don't even expose delegation as a UI action. Low priority.

**Recommendation:** Treat `Delegated` (5) like `Declined` (3) in the filter logic.

### 4. `conferenceURL()` not used as video link source (medium priority)

Apple parses video conference links from structured calendar data (CalDAV/Exchange meeting metadata) and exposes them via `ev.conferenceURL()`. We currently only regex-parse `location()`, `notes()`, and `URL()`, which can miss links that Apple detects natively (e.g., Webex, GoTo, structured Exchange meeting data).

**Recommendation:** Check `ev.conferenceURL()` as an additional source when building the `video_link` property, before falling back to regex parsing.

### 5. Birthday/Subscription calendars (low priority)

`ev.calendar().type()` can be `4` (Birthday) or `3` (Subscription — holiday feeds, sports schedules). These are largely caught by the calendar selection UI already, but a defensive check could be added.

**Recommendation:** Low priority. The calendar selection UI is the right UX for this. A defensive skip for Birthday type (4) in `_convert_event` would be harmless.

## Properties Reviewed and Deemed Not Relevant

| Property | Why no filter needed |
|----------|---------------------|
| `isDetached()` | Modified recurring instance; EventKit returns correct times |
| `isPhantom()` | Internal unsynced state; shouldn't appear in predicate queries |
| `hasRecurrenceRules()` | Already on model; no filter relevance |
| `privacyLevel()` | Private events still belong to the user |
| `needsResponse()` | Pending invitations should still trigger countdowns |
| `organizedByMe()` | Self-organized events are always relevant |
| `hasAttendeeProposedTimes()` | Informational only; doesn't change the event |
| `isBirthday()` | Redundant with calendar type check + all-day filter |

## API Hygiene Note

We currently use `ev.myStatus()` which is technically an undocumented API. The public equivalent is `selfParticipantStatus()` — same enum values, but the official API name. Consider swapping when we touch this code.

## Implementation Plan

1. ~~Filter out canceled events (`ev.status() == 3`) in `_convert_event`~~ **Done**
2. ~~Add `availability` field to `Meeting` model; add "Skip free events" toggle to settings~~ **Done**
3. Use `conferenceURL()` as additional video link source — **Out of scope** (prefer controlling supported platforms for test matrix)
4. Treat delegated status as declined — **Deferred** (rare in the wild)
5. Swap `myStatus()` for `selfParticipantStatus()` — **Deferred** (current API works)
6. ~~Update SPEC.md filter pipeline to document these new filters~~ **Done**

When implementation is complete, move this file to `archive/investigations/`.
