"""Helpers for building employee-directory links from attendee email addresses."""

from __future__ import annotations

from urllib.parse import quote


def build_directory_url(template: str, email: str) -> str | None:
    """Render a directory URL from a template + an attendee email.

    Substitutes ``{Email}``, ``{Username}``, ``{Domain}`` (URL-encoded) into
    ``template``. Uses ``str.replace`` rather than ``str.format`` to mirror how
    ``agent_launcher`` handles ``{Prompt}`` / ``{MeetingData}`` and to avoid
    ``KeyError`` if the template contains literal ``{...}`` segments.

    Returns ``None`` when the template is empty or the email is malformed
    (no ``@``), so callers can fall back to a non-clickable rendering.
    """
    if not template:
        return None
    if "@" not in email:
        return None
    username, _, domain = email.partition("@")
    if not username or not domain:
        return None
    return (
        template
        .replace("{Email}", quote(email, safe=""))
        .replace("{Username}", quote(username, safe=""))
        .replace("{Domain}", quote(domain, safe=""))
    )
