# Plan: Employee Directory Links + Settings Reorganization

**Status:** Shipped
**Date:** 2026-04-07
**Shipped in:** commit `610e0d4` · release `v1.2.0`

## Goal

1. **New feature:** Make internal attendee names in the countdown window clickable links that open a configurable employee-directory URL.
2. **Settings reorg:** Introduce a new **Attendees** tab and rebalance which settings live on which tab so the dialog stops feeling cramped.

The mockup at `mockups/settings-window.html` is the source of truth for the target UI. Match it.

---

## Scope of UI changes

### Tab structure (5 tabs)

| Tab | Contents |
|---|---|
| **General** | Startup · Countdown · Working Hours |
| **Calendars** | Calendar tree · **Meeting Filters** *(moved here from General; now also includes "Only meetings with video links")* |
| **Attendees** *(new)* | Organization (internal email domain, *moved from General*) · Employee Directory (new URL template field) |
| **Audio** | unchanged |
| **AI Integration** | unchanged (Ghostty already supported; mockup updated) |

### What moves where

- `internal_domain` field: General → **Attendees**
- Meeting Filters group (`include_tentative`, `include_free`, `include_all_day`): General → **Calendars**
- `video_calls_only` checkbox: was in the Countdown group on General → moves into Meeting Filters on **Calendars** and is renamed to **"Only meetings with video links"** (it's a true event filter — also affects the "Next Meeting" menu display, not just countdown firing).
- Working Hours: **stays on General** with the Countdown group (it gates *whether countdowns fire*, not what counts as a meeting).
- General tab returns to a single-column layout. The two-column trick from commit `73b982c` is no longer needed.
- Long-form labels restored on General (undoing the shortenings from `73b982c`):
  - "Automatically open meeting link at countdown end"
  - "Continue countdown after joining"
  - "Back-to-Back Meetings" with options "Use Default Behavior / Silent Countdown / Skip Countdown"

### New Attendees-tab fields

- **Internal Email Domain** — same `QLineEdit` as today, just relocated. Hint text: *"Attendees with this domain are grouped as 'Internal' in the countdown window."*
- **Directory URL Template** — new `QLineEdit`. Empty = feature disabled (no separate enable checkbox). Hint text lists supported variables.

### Substitution variables (matches existing AI Integration convention)

| Token | Replaced with | Example |
|---|---|---|
| `{Email}` | full email address | `jane.doe@acme.com` |
| `{Username}` | local-part (left of `@`) | `jane.doe` |
| `{Domain}` | domain (right of `@`) | `acme.com` |

URL-encode each substitution before insertion (`urllib.parse.quote`, `safe=""`). Use `str.replace` rather than `str.format` to match how `agent_launcher.py` handles `{Prompt}` / `{MeetingData}` and to avoid `KeyError` if the user types literal braces.

### Countdown window behavior

- Only **internal** attendees (as determined by `internal_domain`) become clickable.
- Clickable name shows underline on hover and changes the cursor to a pointing hand. No icon next to the name.
- If the directory template is empty, behavior is unchanged (names render as plain labels).
- External attendees are never clickable (parking-lot item: LinkedIn template later).
- Click opens the rendered URL in the user's default browser via `QDesktopServices.openUrl(QUrl(...))`.
- If the email address is malformed (no `@`), fall back to non-clickable rendering — don't try to substitute.

---

## Code changes

### `meetings_countdown_pro/settings.py`
- Add field: `directory_url_template: str = ""`
- Add to `to_dict` / `from_dict` (or whatever the existing serialization is — verify before editing).

### `meetings_countdown_pro/settings_window.py`
- Add `_build_attendees_tab` method.
- Register the new tab in the `addTab` list (between Calendars and Audio) with a "people" SVG icon (use the Feather `users` glyph already added to the mockup).
- Move the `_internal_domain` `QLineEdit` construction out of `_build_general_tab` into `_build_attendees_tab`.
- Move Meeting Filters group out of `_build_general_tab` into `_build_calendars_tab`. Include `_video_only` in that group, *first*.
- Restore the long-form labels listed above on the General tab.
- General tab: collapse two-column rows back to single-column `QVBoxLayout`. Delete the helper plumbing that's no longer needed. Working Hours stays at the bottom of General.
- Wire `_directory_url_template` `QLineEdit` to load/save the new settings field.
- Verify the tab order matches the mockup: General · Calendars · Attendees · Audio · AI Integration.

### `meetings_countdown_pro/countdown_window.py`
- In the attendee rendering path, when an attendee is internal AND `settings.directory_url_template` is non-empty AND the email parses cleanly, render the name as a clickable label (e.g., `QLabel` with rich text + `linkActivated` signal, or a `QPushButton` styled flat with underline-on-hover stylesheet — pick whichever fits the existing widget tree better).
- Add a small helper (e.g., `_build_directory_url(template, email) -> str | None`) that handles the substitution + URL-encoding. Put this in a place that's easy to unit-test (probably `meetings_countdown_pro/attendee_links.py` as a new module, or alongside `meeting.py`).
- Hover styling: cursor `PointingHandCursor`, underline on hover only.

### `meetings_countdown_pro/calendar_service.py`
- No functional changes expected — `video_calls_only` filter logic stays where it is. Only the *label* moves in the UI.

### Settings file migration
- Old config files won't have `directory_url_template`. The default of `""` means existing users see no behavior change until they set it. No migration code needed beyond `dataclasses.field(default="")` (or equivalent).

---

## Worked examples for the Directory URL Template

These should ship in `docs/settings-attendees.md` and be referenced from the field's hint text. The goal is to give users *real* employee-directory deep links they can copy, paste, and tweak — not chat / mail shortcuts.

### 1. Custom internal directory (the canonical case)

Most companies run a homegrown or vendor directory (Workday, BambooHR, Rippling, custom SharePoint, internal "people" site) at a known URL pattern. Pick the variable that matches your URL shape:

```
https://directory.acme.com/u/{Username}
https://people.acme.com/profile?email={Email}
https://intranet.acme.com/employees/{Username}
```

`{Username}` is usually right when the URL uses a slug; `{Email}` when it uses a query parameter.

### 2. Microsoft 365 profile (Delve / SharePoint)

Microsoft 365 exposes each employee's profile page — with org chart, contact info, recent docs, and reporting line — at a tenant-scoped URL that accepts an **email address** as a query parameter. This is the closest thing to a built-in M365 employee directory deep link.

```
https://{Tenant}-my.sharepoint.com/_layouts/15/me.aspx/?p={Email}&v=work
```

Replace `{Tenant}` with your organization's SharePoint tenant slug (the part before `-my.sharepoint.com` when you visit your own OneDrive — e.g. `acmecorp`). Microsoft now redirects these to the unified microsoft365.com profile experience, so the same URL keeps working as the surface evolves.

This is the recommended setting for any team on Microsoft 365 / Office 365.

> **Implementation note:** since `{Tenant}` is a per-deployment constant baked into the user's template string, the app does **not** need to treat `{Tenant}` as a substitution variable. The user types their tenant directly into the template; only `{Email}`, `{Username}`, and `{Domain}` are substituted at click time.

### 3. Glean

Glean's people search is keyed off email and lands on the matching person's profile. The exact path depends on your Glean tenant, but the general shape is:

```
https://app.glean.com/search?q={Email}&t=people
```

Glean does not publicly document a stable profile-by-email deep link, so users should confirm the URL pattern against their own Glean instance before relying on it.

### Known limitations (document explicitly so users don't fight them)

- **Microsoft Teams org chart** — Teams' Org Explorer does not expose a public deep link by email. The only documented Teams deep links accepting an email are for starting *chats*, not for opening a profile/org-chart view, so we don't recommend a Teams URL here.
- **Slack profiles / DMs** — Slack's deep-link scheme (`slack://user?team=…&id=…`) requires Slack's internal user ID and team ID, not an email. Since this app only knows the attendee's email, **Slack is not a viable directory target.**
- **Google Workspace** — Google does not publish a stable per-employee profile deep link keyed on email. Users on Google Workspace will typically fall back to category 1 (a custom internal directory).

### Variable cheat sheet (also rendered in the field's hint text)

Given an attendee `jane.doe@acme.com`:

| Token | Value |
|---|---|
| `{Email}` | `jane.doe@acme.com` |
| `{Username}` | `jane.doe` |
| `{Domain}` | `acme.com` |

All substitutions are URL-encoded before insertion, so emails containing `+` or other reserved characters work correctly.

---

## Tests

### New tests

**`tests/test_attendee_links.py`** *(new file)*
- `build_directory_url` returns `None` when template is empty.
- `build_directory_url` returns `None` when email has no `@`.
- `{Email}`, `{Username}`, `{Domain}` substitution each work in isolation.
- All three substitutions in one template work.
- URL-unsafe characters in email (e.g., `+`, spaces if any) are percent-encoded.
- Template with no recognized variables passes through unchanged.
- Repeated tokens (e.g., template that uses `{Username}` twice) substitute all occurrences.

**`tests/test_countdown_window.py`** *(extend)*
- Internal attendee renders as clickable when template is set.
- Internal attendee renders as plain label when template is empty.
- External attendee never renders as clickable, even when template is set.
- Click on a clickable attendee invokes `QDesktopServices.openUrl` with the expected URL (mock it).
- Malformed email on internal attendee falls back to plain label.

### Existing tests to update

**`tests/test_settings.py`**
- Add `directory_url_template` to the round-trip serialization test.
- Add a default-value assertion (`""`).

**`tests/test_filters.py`**
- No logic change, but if any tests pin label strings or import locations, update.

**`tests/test_working_hours.py`**
- Should be unaffected (Working Hours stays on General). Smoke-check.

### Manual smoke tests after the reorg
- All five tabs render and switch correctly.
- Save / Load round-trip preserves every setting on every tab (especially the moved ones).
- Live-update: changing the internal domain on the new Attendees tab still affects the next countdown's internal/external grouping.
- Empty directory template → no clickable names.
- Set a template → click an internal name → browser opens to the right URL.
- Resetting `~/.config/meetings-countdown-pro/` and launching with no settings file produces sane defaults across all five tabs.

---

## Documentation updates

### `docs/quick-start.md`
- The 5-minute walkthrough currently points users at General → Internal Email Domain. Update that step to point to the new **Attendees** tab.
- Optionally add a one-liner about the Directory URL Template ("Optional: paste your employee directory URL here to make internal attendee names clickable").
- Re-check any screenshots or callouts that reference the old General-tab layout.

### `docs/settings-general.md`
- Remove the Organization section.
- Remove the Meeting Filters section.
- Remove the "Only countdown for meetings with video links" bullet from the Countdown section.
- Confirm the long-form labels match the rebuilt UI.
- Working Hours section stays.

### `docs/settings-calendars.md`
- Add a Meeting Filters section documenting all four filters, with **"Only meetings with video links"** explicitly noted as also affecting the Next Meeting menu display.

### `docs/settings-attendees.md` *(new file)*
- Document the Internal Email Domain field (moved from General — link from settings-general.md for users following old links).
- Document the Directory URL Template, including:
  - The three variables (`{Email}`, `{Username}`, `{Domain}`).
  - The "empty = disabled" behavior (no separate enable toggle).
  - The fact that only internal attendees become clickable.
  - A worked example with a fictional `directory.acme.com` URL.

### `docs/countdown-window.md`
- Add a short subsection on clickable internal attendees and what triggers it.

### `docs/README.md`
- Add the new Attendees settings page to the navigation list.

### `README.md`
- Optional: add a one-line bullet under "Features" mentioning directory links.
- Update the "Settings: General · Calendars · Audio · AI Integration" line to include Attendees.

### `SPEC.md`
- Add the directory-link feature under the relevant Attendees / Countdown Window section.
- Document the settings reorganization (which tab owns what) so the spec stays in sync with reality.

### `TESTING.md`
- Add manual test cases for:
  - Each tab renders correctly after the reorg.
  - Directory link click opens the browser with the correctly substituted URL.
  - Disabled state (empty template) shows non-clickable names.
  - Internal-only behavior (external names never become clickable).
- Update any section that referenced "General → Internal Email Domain" or "General → Meeting Filters" to point to the new locations.

### Screenshots
- `docs/images/prefs_general.png` — regenerate (layout changed significantly).
- `docs/images/prefs_calendars.png` — regenerate if it exists (now has Meeting Filters group).
- `docs/images/prefs_attendees.png` — new screenshot.
- `docs/images/countdown.png` — optional regen if you want to show the underline-on-hover state.

---

## Out of scope (parking lot)

- LinkedIn / external-attendee directory template.
- Per-domain directory URLs (e.g., different URLs per internal subsidiary).
- An icon next to clickable names (decided against — clean text underline only).
- A separate "enable directory links" checkbox (decided against — empty template = disabled).

---

## Suggested commit breakdown

1. **Settings reorg only, no new feature** — move fields between tabs, restore long labels, drop two-column layout, add empty Attendees tab. All existing tests still pass with label/location updates. Update General/Calendars docs.
2. **Add directory link feature** — new `directory_url_template` setting, `build_directory_url` helper + tests, countdown window rendering changes + tests, new Attendees doc page, SPEC + TESTING + README updates.
3. **Regenerate screenshots** — separate commit so the diff is reviewable as text first.

Splitting it this way means commit 1 is a pure refactor (easy to review and revert), and commit 2 is the actual feature on top of a clean settings layout.
