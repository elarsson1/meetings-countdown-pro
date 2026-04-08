"""Tests for meetings_countdown_pro.attendee_links."""

from meetings_countdown_pro.attendee_links import build_directory_url


def test_empty_template_returns_none():
    assert build_directory_url("", "jane@acme.com") is None


def test_missing_at_returns_none():
    assert build_directory_url("https://x/{Username}", "no-at-sign") is None


def test_empty_local_part_returns_none():
    assert build_directory_url("https://x/{Username}", "@acme.com") is None


def test_empty_domain_returns_none():
    assert build_directory_url("https://x/{Domain}", "jane@") is None


def test_substitute_email():
    assert (
        build_directory_url("https://p.acme.com/?e={Email}", "jane.doe@acme.com")
        == "https://p.acme.com/?e=jane.doe%40acme.com"
    )


def test_substitute_username():
    assert (
        build_directory_url("https://d.acme.com/u/{Username}", "jane.doe@acme.com")
        == "https://d.acme.com/u/jane.doe"
    )


def test_substitute_domain():
    assert (
        build_directory_url("https://x/?d={Domain}", "jane@acme.com")
        == "https://x/?d=acme.com"
    )


def test_all_three_substitutions_in_one_template():
    out = build_directory_url(
        "https://x/?e={Email}&u={Username}&d={Domain}", "jane@acme.com"
    )
    assert out == "https://x/?e=jane%40acme.com&u=jane&d=acme.com"


def test_url_unsafe_chars_are_encoded():
    out = build_directory_url(
        "https://x/?e={Email}", "jane+tag@acme.com"
    )
    # '+' must become %2B (otherwise the receiving server treats it as a space)
    assert out == "https://x/?e=jane%2Btag%40acme.com"


def test_template_with_no_recognized_variables_passes_through():
    assert (
        build_directory_url("https://example.com/static", "jane@acme.com")
        == "https://example.com/static"
    )


def test_repeated_token_substitutes_all_occurrences():
    out = build_directory_url(
        "https://x/{Username}/profile/{Username}.json", "jane.doe@acme.com"
    )
    assert out == "https://x/jane.doe/profile/jane.doe.json"
