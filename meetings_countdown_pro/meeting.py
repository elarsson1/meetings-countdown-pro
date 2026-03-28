"""Meeting data model."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

# Patterns for detecting video meeting links (priority order)
_VIDEO_LINK_PATTERNS = [
    re.compile(r"https?://[\w.-]*zoom\.us/(?:j|my)/[^\s\"'<>]+"),
    re.compile(r"https?://meet\.google\.com/[a-z]{3}-[a-z]{4}-[a-z]{3}[^\s\"'<>]*"),
    re.compile(r"https?://teams\.microsoft\.com/l/meetup-join/[^\s\"'<>]+"),
]

# Parse display name from "Name" <email> format
_NAME_EMAIL_RE = re.compile(r'^"?([^"<]+?)"?\s*<([^>]+)>$')


@dataclass
class Attendee:
    """A meeting attendee."""

    email: str
    display_name: str = ""
    is_organizer: bool = False

    @property
    def domain(self) -> str:
        """Extract domain from email address."""
        return self.email.rsplit("@", 1)[-1].lower() if "@" in self.email else ""

    @property
    def effective_name(self) -> str:
        """Display name if available, otherwise the raw email."""
        return self.display_name or self.email

    @classmethod
    def from_raw(cls, name_or_email: str, email: str = "", is_organizer: bool = False) -> Attendee:
        """Parse an attendee from potentially messy calendar data.

        Handles formats like:
          - "Alice Smith" <alice@example.com>
          - alice@example.com
          - Alice Smith (with separate email param)
        """
        display_name = ""
        resolved_email = email

        # Try to parse "Name" <email> format from the name field
        m = _NAME_EMAIL_RE.match(name_or_email)
        if m:
            display_name = m.group(1).strip()
            if not resolved_email:
                resolved_email = m.group(2).strip()
        elif "@" in name_or_email and not email:
            # Bare email as the name
            resolved_email = name_or_email.strip()
        else:
            display_name = name_or_email.strip()

        return cls(
            email=resolved_email.lower(),
            display_name=display_name,
            is_organizer=is_organizer,
        )


@dataclass
class Meeting:
    """Represents a calendar meeting event."""

    uid: str
    title: str
    start: datetime
    end: datetime
    calendar_name: str = ""
    calendar_color: Optional[tuple[int, int, int]] = None
    location: str = ""
    notes: str = ""
    url: str = ""
    attendees: list[Attendee] = field(default_factory=list)
    is_all_day: bool = False
    is_recurring: bool = False
    acceptance_status: str = "accepted"  # accepted, tentative, declined, none

    @property
    def notification_key(self) -> str:
        """Composite key for dedup: UID + start time ISO string."""
        return f"{self.uid}|{self.start.isoformat()}"

    @property
    def video_link(self) -> Optional[str]:
        """Detect and return the first video meeting link found.

        Search priority: URL field > location > notes/body.
        """
        for text in [self.url, self.location, self.notes]:
            if not text:
                continue
            for pattern in _VIDEO_LINK_PATTERNS:
                m = pattern.search(text)
                if m:
                    return m.group(0)
        return None

    @property
    def duration_seconds(self) -> float:
        """Meeting duration in seconds."""
        return (self.end - self.start).total_seconds()

    def classify_attendees(self, internal_domain: str) -> tuple[list[Attendee], dict[str, list[Attendee]]]:
        """Split attendees into internal and external (grouped by domain).

        Returns:
            (internal_list, {domain: [attendees]}) — external dict sorted by domain.
        """
        if not internal_domain:
            return self.attendees, {}

        internal_domain = internal_domain.lower()
        internal: list[Attendee] = []
        external_by_domain: dict[str, list[Attendee]] = {}

        for att in self.attendees:
            if att.domain == internal_domain:
                internal.append(att)
            else:
                external_by_domain.setdefault(att.domain, []).append(att)

        # Sort each group alphabetically
        internal.sort(key=lambda a: a.effective_name.lower())
        for domain in external_by_domain:
            external_by_domain[domain].sort(key=lambda a: a.effective_name.lower())

        # Sort domains alphabetically
        external_by_domain = dict(sorted(external_by_domain.items()))

        return internal, external_by_domain

    @property
    def attendee_count(self) -> int:
        return len(self.attendees)

    def to_json_data(self, internal_domain: str) -> dict:
        """Serialize meeting to a dict suitable for JSON output to the AI agent.

        Includes title, date, times, calendar, video link, and classified attendees.
        """
        attendees_data = []
        if internal_domain:
            internal, external_by_domain = self.classify_attendees(internal_domain)
            for att in internal:
                attendees_data.append({
                    "name": att.effective_name,
                    "email": att.email,
                    "type": "internal",
                })
            for domain, atts in external_by_domain.items():
                for att in atts:
                    attendees_data.append({
                        "name": att.effective_name,
                        "email": att.email,
                        "type": "external",
                        "org": domain,
                    })
        else:
            for att in sorted(self.attendees, key=lambda a: a.effective_name.lower()):
                attendees_data.append({
                    "name": att.effective_name,
                    "email": att.email,
                    "type": "attendee",
                })

        return {
            "title": self.title,
            "date": self.start.astimezone().strftime("%Y-%m-%d"),
            "start_time": self.start.astimezone().strftime("%-I:%M %p"),
            "end_time": self.end.astimezone().strftime("%-I:%M %p"),
            "calendar": self.calendar_name,
            "video_link": self.video_link,
            "attendees": attendees_data,
        }

    def attendee_summary(self, internal_domain: str) -> str:
        """Generate summary like '8 attendees · 3 internal, 5 external from 2 orgs'."""
        total = self.attendee_count
        if total == 0:
            return "No attendees"

        if not internal_domain:
            return f"{total} attendee{'s' if total != 1 else ''}"

        internal, external_by_domain = self.classify_attendees(internal_domain)
        n_internal = len(internal)
        n_external = total - n_internal
        n_orgs = len(external_by_domain)

        parts = [f"{total} attendee{'s' if total != 1 else ''}"]

        detail_parts = []
        if n_internal:
            detail_parts.append(f"{n_internal} internal")
        if n_external:
            org_suffix = f" from {n_orgs} org{'s' if n_orgs != 1 else ''}" if n_orgs > 0 else ""
            detail_parts.append(f"{n_external} external{org_suffix}")

        if detail_parts:
            parts.append(" · ".join(detail_parts))

        return " · ".join(parts)
