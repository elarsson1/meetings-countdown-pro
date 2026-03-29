# Calendars Settings

The Calendars tab lets you choose which calendar accounts and individual calendars the app monitors for meetings.

![Calendars Settings](images/prefs_cal.png)

## Calendar Selection

Your macOS Calendar accounts are shown in a tree view:

- **Account level** — the top-level entries (e.g., "axel@axeltech.com calendars", "Other", "Subscribed Calendars"). Check or uncheck an account to toggle all its calendars at once.
- **Calendar level** — individual calendars nested under each account. Toggle these independently to fine-tune which calendars trigger countdowns.

The app monitors any calendar that syncs to macOS Calendar — this includes iCloud, Google, Microsoft 365, Exchange, CalDAV, and any other provider configured in **System Settings → Internet Accounts** or directly in Calendar.app.

## Tips

- **Work-only monitoring:** Uncheck personal calendar accounts and keep only your work account enabled. This prevents countdowns for "Vet appointment" and "Pick up dry cleaning."
- **Shared/team calendars:** If your organization uses shared calendars for room bookings or team schedules, you can include or exclude them individually.
- **Subscribed calendars** (like public holidays) are listed under their own account. These are typically all-day events, so they're already filtered out by the [Include All-Day Events](settings-general.md#include-all-day-events) toggle unless you've enabled it.

## How Calendar Sync Works

The app reads calendar data through macOS EventKit — the same framework that powers Calendar.app. It does **not** connect directly to Google, Microsoft, or any other calendar provider. This means:

- Any calendar that shows up in Calendar.app is available to the app.
- Calendar sync frequency and reliability depend on your macOS calendar account settings, not this app.
- If a meeting isn't showing up, check Calendar.app first — if it's not there, the app can't see it either.

The app polls EventKit every 30 seconds for meetings between now and the end of the current day.
