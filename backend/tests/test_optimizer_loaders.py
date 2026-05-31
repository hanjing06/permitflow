"""Tests for the Phase-8 additions to backend.optimizer permit constructors.

Verifies that `_permit_from_open_toronto` and `_permit_from_simple_csv` now
populate `normalized_street`, `direction`, and `geo_id` for all three input
schemas (anchor CSVs, utility_cuts.csv, building_permits.csv), without
regressing any existing field.

Runnable two ways:
  - pytest:    nix develop -c pytest backend/tests/test_optimizer_loaders.py -v
  - standalone: nix develop -c python -m backend.tests.test_optimizer_loaders
"""

from __future__ import annotations

import json
from datetime import date

from backend.optimizer import (
    _coerce_geo_id,
    _permit_from_open_toronto,
    _permit_from_simple_csv,
)


def _anchor_row(location="DANFORTH AVE&lt;br&gt; From: PAPE AVE&lt;br&gt; To: BROADVIEW AVE "):
    return {
        "_id": 999,
        "LOCATION": location,
        "PROJECT": "Road Resurfacing",
        "STATUS": "Active",
        "START_YEAR": 2026,
        "DURATION/ Construction Timeline": "Q2 2026 - Q4 2026",
        "geometry": json.dumps({
            "type": "LineString",
            "coordinates": [[-79.36, 43.66], [-79.35, 43.665]],
        }),
        "GEO_ID": None,
    }


def test_anchor_permit_has_geo_id_none():
    row = _anchor_row()
    permit = _permit_from_open_toronto(row, source="road_resurfacing", role="anchor")
    assert permit is not None
    assert permit["geo_id"] is None, permit
    assert permit["source"] == "road_resurfacing"
    assert permit["role"] == "anchor"


def test_anchor_permit_normalized_street_strips_from_to_tail():
    # clean_text converts &lt;br&gt; to " | "; normalize_street then strips
    # everything after the first " | ", leaving "DANFORTH AVE".
    row = _anchor_row("DANFORTH AVE&lt;br&gt; From: PAPE AVE&lt;br&gt; To: BROADVIEW AVE ")
    permit = _permit_from_open_toronto(row, source="road_resurfacing", role="anchor")
    assert permit["normalized_street"] == "danforth avenue", permit
    # Existing street_name display field MUST still be a non-empty string
    # (Phase 4 frontend renders it in popups — see SCHEMAS.md).
    assert isinstance(permit["street_name"], str) and permit["street_name"], permit


def test_utility_cut_permit_geo_id_loaded_from_GEO_ID_column():
    row = {
        "_id": 1,
        "PERMIT_NUMBER": "999995001",
        "GEO_ID": 71568.0,
        "DISPLAY_DESC": "154 ROBINA AVE (Between GLENHURST AVE AND EARLSDALE AVE)",
        "PROPOSED_FROM_DATE": "2026-07-01",
        "PROPOSED_TO_DATE": "2026-07-10",
        "PERMIT_STATUS": "PERMIT ISSUED",
        "INSTALLATION_TYPE_DESC": "Water and Sewer Connection",
        "lat": 43.66,
        "lon": -79.36,
    }
    permit = _permit_from_simple_csv(row, source="utility_cut", role="candidate")
    assert permit is not None, "row with lat/lon should yield a permit"
    assert permit["geo_id"] == "71568", permit
    assert permit["normalized_street"] == "robina avenue", permit


def test_building_permit_composes_street_from_three_columns():
    row = {
        "_id": 42,
        "PERMIT_NUM": "16 134540 HVA",
        "STREET_DIRECTION": "E",
        "STREET_NAME": "DANFORTH",
        "STREET_TYPE": "AVE",
        "GEO_ID": 12345.0,
        "ISSUED_DATE": "2026-07-15",
        "COMPLETED_DATE": "2026-08-20",
        "STATUS": "Active",
        "WORK": "Building Permit Related(MS)",
        "lat": 43.68,
        "lon": -79.34,
    }
    permit = _permit_from_simple_csv(row, source="building_permit", role="candidate")
    assert permit is not None
    assert permit["normalized_street"] == "danforth avenue", permit
    assert permit["geo_id"] == "12345", permit
    assert permit["direction"] == "E", permit


def test_geo_id_missing_becomes_none():
    # _coerce_geo_id direct unit checks
    assert _coerce_geo_id(None) is None
    assert _coerce_geo_id("") is None
    assert _coerce_geo_id(float("nan")) is None
    assert _coerce_geo_id("nan") is None
    # And via a row that omits GEO_ID
    row = _anchor_row()
    row.pop("GEO_ID", None)
    permit = _permit_from_open_toronto(row, source="road_resurfacing", role="anchor")
    assert permit["geo_id"] is None


def test_existing_fields_unchanged_regression():
    permit = _permit_from_open_toronto(
        _anchor_row(), source="road_resurfacing", role="anchor"
    )
    required_keys = {
        "permit_id", "source", "role", "street_name", "work_type", "status",
        "start_date", "end_date", "lane_days", "lat", "lon",
    }
    missing = required_keys - set(permit.keys())
    assert not missing, f"regression: anchor permit missing keys {missing}"
    assert isinstance(permit["permit_id"], str)
    assert isinstance(permit["start_date"], date)
    assert isinstance(permit["end_date"], date)
    assert isinstance(permit["lane_days"], int)
    assert isinstance(permit["lat"], float)
    assert isinstance(permit["lon"], float)
    # Critically, the human-readable street_name must NOT be overwritten with
    # the normalized lowercase form — Phase 4 popups read it as-is.
    assert "danforth ave" not in permit["street_name"].lower() or "DANFORTH AVE" in permit["street_name"].upper(), permit


TESTS = [
    test_anchor_permit_has_geo_id_none,
    test_anchor_permit_normalized_street_strips_from_to_tail,
    test_utility_cut_permit_geo_id_loaded_from_GEO_ID_column,
    test_building_permit_composes_street_from_three_columns,
    test_geo_id_missing_becomes_none,
    test_existing_fields_unchanged_regression,
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
