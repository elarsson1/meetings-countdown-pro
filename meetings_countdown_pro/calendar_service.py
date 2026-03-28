"""Calendar service — EventKit integration via pyobjc."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import objc
from EventKit import (
    EKAuthorizationStatusAuthorized,
    EKAuthorizationStatusFullAccess,
    EKEntityTypeEvent,
    EKEventStore,
    EKParticipantStatusAccepted,
    EKParticipantStatusTentative,
    EKParticipantStatusDeclined,
)
from Foundation import NSDate

from meetings_countdown_pro.meeting import Attendee, Meeting
from meetings_countdown_pro.settings import Settings

log = logging.getLogger(__name__)


class CalendarService:
    """Queries macOS Calendar via EventKit for upcoming meetings."""

    def __init__(self) -> None:
        self._store = EKEventStore.alloc().init()
        self._authorized = False

    # ------------------------------------------------------------------
    # Authorization
    # ------------------------------------------------------------------

    def request_access(self, callback: Optional[callable] = None) -> None:
        """Request calendar access. Calls callback(granted: bool) when done."""

        def _handler(granted: bool, error: objc.objc_object) -> None:
            self._authorized = granted
            if error:
                log.error("Calendar access error: %s", error)
            if callback:
                callback(granted)

        # macOS 14+ uses requestFullAccessToEventsWithCompletion:
        # macOS 13 uses requestAccessToEntityType:completion:
        if hasattr(self._store, "requestFullAccessToEventsWithCompletion_"):
            self._store.requestFullAccessToEventsWithCompletion_(_handler)
        else:
            self._store.requestAccessToEntityType_completion_(
                EKEntityTypeEvent, _handler
            )

    @property
    def is_authorized(self) -> bool:
        """Check current authorization status."""
        status = EKEventStore.authorizationStatusForEntityType_(EKEntityTypeEvent)
        # EKAuthorizationStatusFullAccess (macOS 14+) or EKAuthorizationStatusAuthorized (macOS 13)
        self._authorized = status in (
            EKAuthorizationStatusAuthorized,
            EKAuthorizationStatusFullAccess,
        )
        return self._authorized

    # ------------------------------------------------------------------
    # Calendar enumeration
    # ------------------------------------------------------------------

    def get_calendars(self) -> dict[str, list[dict]]:
        """Return calendars grouped by account.

        Returns: {account_name: [{name, uid, color_hex}]}
        """
        result: dict[str, list[dict]] = {}
        for cal in self._store.calendarsForEntityType_(EKEntityTypeEvent):
            account = cal.source().title() if cal.source() else "Local"
            color = cal.color()
            r, g, b = 128, 128, 128
            if color:
                r = int(color.redComponent() * 255)
                g = int(color.greenComponent() * 255)
                b = int(color.blueComponent() * 255)
            result.setdefault(account, []).append(
                {
                    "name": str(cal.title()),
                    "uid": str(cal.calendarIdentifier()),
                    "color": (r, g, b),
                }
            )
        return result

    # ------------------------------------------------------------------
    # Event querying
    # ------------------------------------------------------------------

    def fetch_upcoming(self, settings: Settings) -> list[Meeting]:
        """Fetch upcoming calendar events based on settings filters.

        Query window: now → now + countdown_duration + 5 min buffer.
        """
        if not self.is_authorized:
            return []

        now = datetime.now(timezone.utc)
        window_end = now + timedelta(seconds=settings.countdown_duration + 300)

        ns_start = NSDate.dateWithTimeIntervalSince1970_(now.timestamp())
        ns_end = NSDate.dateWithTimeIntervalSince1970_(window_end.timestamp())

        # Build calendar filter
        calendars = self._resolve_calendars(settings)
        predicate = self._store.predicateForEventsWithStartDate_endDate_calendars_(
            ns_start, ns_end, calendars
        )
        ek_events = self._store.eventsMatchingPredicate_(predicate) or []

        meetings: list[Meeting] = []
        for ev in ek_events:
            meeting = self._convert_event(ev)
            if meeting and self._passes_filters(meeting, settings):
                meetings.append(meeting)

        meetings.sort(key=lambda m: m.start)
        return meetings

    def _resolve_calendars(self, settings: Settings) -> list | None:
        """Resolve selected calendars to EKCalendar objects. None = all."""
        if not settings.selected_calendars:
            return None  # all calendars

        all_cals = self._store.calendarsForEntityType_(EKEntityTypeEvent)
        selected = []
        for cal in all_cals:
            account = cal.source().title() if cal.source() else "Local"
            cal_name = str(cal.title())
            if account in settings.selected_calendars:
                if cal_name in settings.selected_calendars[account]:
                    selected.append(cal)
        return selected or None

    def _convert_event(self, ev: objc.objc_object) -> Optional[Meeting]:
        """Convert an EKEvent to our Meeting model."""
        try:
            uid = str(ev.calendarItemExternalIdentifier() or ev.calendarItemIdentifier())
            title = str(ev.title() or "Untitled")

            start_ns = ev.startDate()
            end_ns = ev.endDate()
            if not start_ns or not end_ns:
                return None

            start = datetime.fromtimestamp(start_ns.timeIntervalSince1970(), tz=timezone.utc)
            end = datetime.fromtimestamp(end_ns.timeIntervalSince1970(), tz=timezone.utc)

            # Calendar info
            cal = ev.calendar()
            cal_name = str(cal.title()) if cal else ""
            cal_color = None
            if cal and cal.color():
                c = cal.color()
                cal_color = (
                    int(c.redComponent() * 255),
                    int(c.greenComponent() * 255),
                    int(c.blueComponent() * 255),
                )

            # Attendees
            attendees = []
            ek_attendees = ev.attendees() or []
            for att in ek_attendees:
                url = att.URL()
                email = str(url.resourceSpecifier()) if url else ""
                if email.startswith("//"):
                    email = email[2:]
                name = str(att.name() or "")
                is_org = bool(att.isCurrentUser()) if hasattr(att, "isCurrentUser") else False
                attendees.append(Attendee.from_raw(name, email, is_organizer=is_org))

            # Acceptance status
            acceptance = "accepted"
            if ev.respondsToSelector_("myStatus"):
                my_status = ev.myStatus()
            else:
                my_status = None

            if my_status is not None:
                if my_status == EKParticipantStatusDeclined:
                    acceptance = "declined"
                elif my_status == EKParticipantStatusTentative:
                    acceptance = "tentative"

            return Meeting(
                uid=uid,
                title=title,
                start=start,
                end=end,
                calendar_name=cal_name,
                calendar_color=cal_color,
                location=str(ev.location() or ""),
                notes=str(ev.notes() or ""),
                url=str(ev.URL().absoluteString()) if ev.URL() else "",
                attendees=attendees,
                is_all_day=bool(ev.isAllDay()),
                is_recurring=bool(ev.hasRecurrenceRules()),
                acceptance_status=acceptance,
            )
        except Exception:
            log.exception("Failed to convert calendar event")
            return None

    def _passes_filters(self, meeting: Meeting, settings: Settings) -> bool:
        """Check if a meeting passes the user's configured filters."""
        # Always exclude declined
        if meeting.acceptance_status == "declined":
            return False

        # Exclude tentative unless setting is on
        if meeting.acceptance_status == "tentative" and not settings.include_tentative:
            return False

        # Exclude all-day events if configured
        if meeting.is_all_day and not settings.include_all_day:
            return False

        # Video calls only filter
        if settings.video_calls_only and not meeting.video_link:
            return False

        return True

    def is_meeting_in_progress(self, settings: Settings) -> bool:
        """Check if any monitored meeting is currently in progress."""
        if not self.is_authorized:
            return False

        now = datetime.now(timezone.utc)
        ns_start = NSDate.dateWithTimeIntervalSince1970_(
            (now - timedelta(hours=8)).timestamp()
        )
        ns_end = NSDate.dateWithTimeIntervalSince1970_(now.timestamp())

        calendars = self._resolve_calendars(settings)
        predicate = self._store.predicateForEventsWithStartDate_endDate_calendars_(
            ns_start, ns_end, calendars
        )
        events = self._store.eventsMatchingPredicate_(predicate) or []

        for ev in events:
            if ev.isAllDay():
                continue
            start_ts = ev.startDate().timeIntervalSince1970()
            end_ts = ev.endDate().timeIntervalSince1970()
            now_ts = now.timestamp()
            if start_ts <= now_ts < end_ts:
                return True
        return False
