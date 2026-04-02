"""Tests for Meeting and Attendee data models."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from meetings_countdown_pro.meeting import Attendee, Meeting
from tests.conftest import make_attendee, make_meeting


# ===================================================================
# Attendee.from_raw()
# ===================================================================

class TestAttendeeFromRaw:
    def test_quoted_name_with_email(self):
        att = Attendee.from_raw('"Alice Smith" <alice@example.com>')
        assert att.display_name == "Alice Smith"
        assert att.email == "alice@example.com"

    def test_unquoted_name_with_email(self):
        att = Attendee.from_raw("Alice Smith <alice@example.com>")
        assert att.display_name == "Alice Smith"
        assert att.email == "alice@example.com"

    def test_bare_email(self):
        att = Attendee.from_raw("alice@example.com")
        assert att.email == "alice@example.com"
        assert att.display_name == ""

    def test_name_with_separate_email(self):
        att = Attendee.from_raw("Alice Smith", email="alice@example.com")
        assert att.display_name == "Alice Smith"
        assert att.email == "alice@example.com"

    def test_email_lowercased(self):
        att = Attendee.from_raw("ALICE@Example.COM")
        assert att.email == "alice@example.com"

    def test_email_lowercased_in_angle_brackets(self):
        att = Attendee.from_raw('"Alice" <ALICE@Example.COM>')
        assert att.email == "alice@example.com"

    def test_is_organizer_flag(self):
        att = Attendee.from_raw("Alice", email="a@b.com", is_organizer=True)
        assert att.is_organizer is True

    def test_whitespace_name(self):
        att = Attendee.from_raw("  ", email="a@b.com")
        assert att.email == "a@b.com"
        assert att.display_name == ""


# ===================================================================
# Attendee properties
# ===================================================================

class TestAttendeeProperties:
    def test_domain_extraction(self):
        assert make_attendee(email="alice@example.com").domain == "example.com"

    def test_domain_lowercased(self):
        assert Attendee(email="alice@SUB.Example.COM").domain == "sub.example.com"

    def test_domain_no_at(self):
        assert Attendee(email="noemail").domain == ""

    def test_effective_name_with_display_name(self):
        att = make_attendee(display_name="Alice", email="alice@example.com")
        assert att.effective_name == "Alice"

    def test_effective_name_without_display_name(self):
        att = make_attendee(display_name="", email="alice@example.com")
        assert att.effective_name == "alice@example.com"


# ===================================================================
# Meeting.video_link
# ===================================================================

class TestVideoLink:
    @pytest.mark.parametrize("url,expected_substr", [
        ("https://zoom.us/j/1234567890", "zoom.us/j/"),
        ("https://company.zoom.us/j/123?pwd=abc", "zoom.us/j/"),
        ("https://zoom.us/my/username", "zoom.us/my/"),
        ("https://meet.google.com/abc-defg-hij", "meet.google.com/"),
        ("https://meet.google.com/abc-defg-hij?authuser=0", "meet.google.com/"),
        ("https://teams.microsoft.com/l/meetup-join/19%3ameeting", "teams.microsoft.com/l/meetup-join/"),
    ])
    def test_detects_video_links_in_url_field(self, url, expected_substr):
        m = make_meeting(url=url)
        assert m.video_link is not None
        assert expected_substr in m.video_link

    def test_detects_link_in_location(self):
        m = make_meeting(location="https://zoom.us/j/999")
        assert m.video_link is not None
        assert "zoom.us" in m.video_link

    def test_detects_link_in_notes(self):
        m = make_meeting(notes="Join here: https://meet.google.com/abc-defg-hij thanks")
        assert m.video_link is not None
        assert "meet.google.com" in m.video_link

    def test_priority_url_over_location(self):
        m = make_meeting(
            url="https://zoom.us/j/111",
            location="https://meet.google.com/abc-defg-hij",
        )
        assert "zoom.us" in m.video_link

    def test_priority_url_over_notes(self):
        m = make_meeting(
            url="https://zoom.us/j/111",
            notes="https://teams.microsoft.com/l/meetup-join/abc",
        )
        assert "zoom.us" in m.video_link

    def test_priority_location_over_notes(self):
        m = make_meeting(
            location="https://meet.google.com/abc-defg-hij",
            notes="https://teams.microsoft.com/l/meetup-join/abc",
        )
        assert "meet.google.com" in m.video_link

    def test_no_match_returns_none(self):
        m = make_meeting(url="https://example.com/meeting", location="Room 5", notes="Bring your laptop")
        assert m.video_link is None

    def test_empty_fields_returns_none(self):
        m = make_meeting()
        assert m.video_link is None


# ===================================================================
# Meeting.classify_attendees
# ===================================================================

class TestClassifyAttendees:
    def test_all_internal(self):
        m = make_meeting(attendees=[
            Attendee(email="a@corp.com", display_name="Alice"),
            Attendee(email="b@corp.com", display_name="Bob"),
        ])
        internal, external = m.classify_attendees("corp.com")
        assert len(internal) == 2
        assert len(external) == 0

    def test_all_external(self):
        m = make_meeting(attendees=[
            Attendee(email="a@other.com", display_name="Alice"),
            Attendee(email="b@other.com", display_name="Bob"),
        ])
        internal, external = m.classify_attendees("corp.com")
        assert len(internal) == 0
        assert "other.com" in external
        assert len(external["other.com"]) == 2

    def test_mixed_split(self):
        m = make_meeting(attendees=[
            Attendee(email="a@corp.com", display_name="Alice"),
            Attendee(email="b@acme.com", display_name="Bob"),
            Attendee(email="c@globex.com", display_name="Carol"),
        ])
        internal, external = m.classify_attendees("corp.com")
        assert len(internal) == 1
        assert internal[0].email == "a@corp.com"
        assert set(external.keys()) == {"acme.com", "globex.com"}

    def test_alphabetical_sorting(self):
        m = make_meeting(attendees=[
            Attendee(email="z@corp.com", display_name="Zara"),
            Attendee(email="a@corp.com", display_name="Alice"),
            Attendee(email="m@corp.com", display_name="Mike"),
        ])
        internal, _ = m.classify_attendees("corp.com")
        names = [a.effective_name for a in internal]
        assert names == ["Alice", "Mike", "Zara"]

    def test_external_domains_sorted(self):
        m = make_meeting(attendees=[
            Attendee(email="x@zebra.com", display_name="X"),
            Attendee(email="y@alpha.com", display_name="Y"),
        ])
        _, external = m.classify_attendees("corp.com")
        assert list(external.keys()) == ["alpha.com", "zebra.com"]

    def test_empty_internal_domain(self):
        m = make_meeting(attendees=[
            Attendee(email="a@corp.com", display_name="Alice"),
        ])
        internal, external = m.classify_attendees("")
        assert len(internal) == 1
        assert len(external) == 0

    def test_no_attendees(self):
        m = make_meeting(attendees=[])
        internal, external = m.classify_attendees("corp.com")
        assert internal == []
        assert external == {}


# ===================================================================
# Meeting.attendee_summary
# ===================================================================

class TestAttendeeSummary:
    def test_no_attendees(self):
        m = make_meeting(attendees=[])
        assert m.attendee_summary("corp.com") == "No attendees"

    def test_one_attendee_no_domain(self):
        m = make_meeting(attendees=[Attendee(email="a@b.com")])
        assert m.attendee_summary("") == "1 attendee"

    def test_plural_attendees(self):
        m = make_meeting(attendees=[
            Attendee(email="a@b.com"), Attendee(email="c@d.com"),
        ])
        assert m.attendee_summary("") == "2 attendees"

    def test_mixed_internal_external(self):
        m = make_meeting(attendees=[
            Attendee(email="a@corp.com"),
            Attendee(email="b@corp.com"),
            Attendee(email="c@corp.com"),
            Attendee(email="d@acme.com"),
            Attendee(email="e@acme.com"),
            Attendee(email="f@acme.com"),
            Attendee(email="g@globex.com"),
            Attendee(email="h@globex.com"),
        ])
        summary = m.attendee_summary("corp.com")
        assert "8 attendees" in summary
        assert "3 internal" in summary
        assert "5 external" in summary
        assert "2 orgs" in summary

    def test_single_external_org(self):
        m = make_meeting(attendees=[
            Attendee(email="a@corp.com"),
            Attendee(email="b@acme.com"),
        ])
        summary = m.attendee_summary("corp.com")
        assert "1 org" in summary
        assert "orgs" not in summary


# ===================================================================
# Meeting.notification_key
# ===================================================================

class TestNotificationKey:
    def test_composite_key(self):
        start = datetime(2026, 4, 1, 14, 0, tzinfo=timezone.utc)
        m = make_meeting(uid="abc123", start=start)
        assert m.notification_key == "abc123|2026-04-01T14:00:00+00:00"

    def test_different_start_different_key(self):
        start1 = datetime(2026, 4, 1, 14, 0, tzinfo=timezone.utc)
        start2 = datetime(2026, 4, 1, 15, 0, tzinfo=timezone.utc)
        m1 = make_meeting(uid="abc", start=start1)
        m2 = make_meeting(uid="abc", start=start2)
        assert m1.notification_key != m2.notification_key


# ===================================================================
# Meeting.to_json_data
# ===================================================================

class TestToJsonData:
    def test_with_internal_domain(self):
        m = make_meeting(attendees=[
            Attendee(email="a@corp.com", display_name="Alice"),
            Attendee(email="b@acme.com", display_name="Bob"),
        ])
        data = m.to_json_data("corp.com")
        assert data["title"] == "Test Meeting"
        assert data["calendar"] == "Work"
        assert len(data["attendees"]) == 2
        types = {a["type"] for a in data["attendees"]}
        assert types == {"internal", "external"}

    def test_without_internal_domain(self):
        m = make_meeting(attendees=[
            Attendee(email="a@corp.com", display_name="Alice"),
        ])
        data = m.to_json_data("")
        assert data["attendees"][0]["type"] == "attendee"

    def test_external_has_org(self):
        m = make_meeting(attendees=[
            Attendee(email="b@acme.com", display_name="Bob"),
        ])
        data = m.to_json_data("corp.com")
        ext = [a for a in data["attendees"] if a["type"] == "external"]
        assert ext[0]["org"] == "acme.com"


# ===================================================================
# Meeting.duration_seconds
# ===================================================================

class TestDurationSeconds:
    def test_one_hour(self):
        start = datetime(2026, 4, 1, 14, 0, tzinfo=timezone.utc)
        end = datetime(2026, 4, 1, 15, 0, tzinfo=timezone.utc)
        m = make_meeting(start=start, end=end)
        assert m.duration_seconds == 3600.0
