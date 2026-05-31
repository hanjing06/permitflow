"""Unit tests for backend.street_norm.normalize_street.

Runnable two ways:
  - Under pytest (if available): nix develop -c pytest backend/tests/test_street_norm.py -v
  - Standalone (no pytest):       nix develop -c python -m backend.tests.test_street_norm

Both modes call the same test functions, so the assertions are identical.
"""

from __future__ import annotations

from backend.street_norm import normalize_street


def test_anchor_location_with_from_to():
    result = normalize_street("DANFORTH AVE | From: PAPE AVE | To: BROADVIEW AVE")
    assert result == {
        "normalized": "danforth avenue",
        "direction": "",
        "display": "DANFORTH AVENUE",
    }, result


def test_utility_cut_display_desc_with_house_number_and_between():
    result = normalize_street("154 ROBINA AVE (Between GLENHURST AVE AND EARLSDALE AVE)")
    assert result == {
        "normalized": "robina avenue",
        "direction": "",
        "display": "ROBINA AVENUE",
    }, result


def test_building_permit_with_direction_prefix():
    result = normalize_street("E DANFORTH AVE")
    assert result == {
        "normalized": "danforth avenue",
        "direction": "E",
        "display": "DANFORTH AVENUE",
    }, result


def test_already_canonical_full_form_unchanged():
    result = normalize_street("YONGE STREET")
    assert result == {
        "normalized": "yonge street",
        "direction": "",
        "display": "YONGE STREET",
    }, result


def test_abbreviation_canonicalization_roundtrip():
    a = normalize_street("BLOOR ST W")
    b = normalize_street("W BLOOR STREET")
    # Both forms (prefix direction vs suffix direction) MUST collapse to the
    # same normalized key and direction — this is the core grouping invariant.
    assert a["normalized"] == "bloor street", a
    assert b["normalized"] == "bloor street", b
    assert a["direction"] == "W", a
    assert b["direction"] == "W", b


def test_empty_and_unknown_return_empty_normalized():
    assert normalize_street(None)["normalized"] == ""
    assert normalize_street("")["normalized"] == ""
    assert normalize_street("Unknown location")["normalized"] == ""
    assert normalize_street(float("nan"))["normalized"] == ""


def test_compound_street_name_preserved():
    result = normalize_street("OLD KINGSTON RD")
    assert result == {
        "normalized": "old kingston road",
        "direction": "",
        "display": "OLD KINGSTON ROAD",
    }, result


def test_no_leading_house_number_when_first_token_not_digits():
    result = normalize_street("ROBINA AVE")
    assert result["normalized"] == "robina avenue", result
    assert result["display"] == "ROBINA AVENUE", result
    assert result["direction"] == ""


TESTS = [
    test_anchor_location_with_from_to,
    test_utility_cut_display_desc_with_house_number_and_between,
    test_building_permit_with_direction_prefix,
    test_already_canonical_full_form_unchanged,
    test_abbreviation_canonicalization_roundtrip,
    test_empty_and_unknown_return_empty_normalized,
    test_compound_street_name_preserved,
    test_no_leading_house_number_when_first_token_not_digits,
]


def main() -> int:
    failures = 0
    for fn in TESTS:
        try:
            fn()
            print(f"PASS  {fn.__name__}")
        except Exception as exc:  # pragma: no cover
            failures += 1
            print(f"FAIL  {fn.__name__}: {exc}")
    print(f"\n{len(TESTS) - failures}/{len(TESTS)} tests passed")
    return 1 if failures else 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
