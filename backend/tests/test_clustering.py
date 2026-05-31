"""Tests for the Phase-8 rewrite of backend.optimizer.cluster_leftover_candidates.

Covers the GEO_ID-first → same-normalized-street → temporal sub-bucketing
algorithm and the additive match_type field on every recommendation.

Runnable two ways:
  - pytest:     nix develop -c pytest backend/tests/test_clustering.py -v
  - standalone: nix develop -c python -m backend.tests.test_clustering
"""

from __future__ import annotations

from datetime import date, timedelta

from backend.optimizer import (
    STREET_CLUSTER_WINDOW_DAYS,
    cluster_leftover_candidates,
)


def _candidate(
    permit_id,
    *,
    geo_id=None,
    normalized_street="",
    start=date(2026, 7, 1),
    days=5,
    lat=43.66,
    lon=-79.36,
    street_name="Generic Street",
    work_type="Utility work",
    status="Planned",
):
    return {
        "permit_id": permit_id,
        "source": "utility_cut",
        "role": "candidate",
        "street_name": street_name,
        "work_type": work_type,
        "status": status,
        "start_date": start,
        "end_date": start + timedelta(days=days - 1),
        "lane_days": days,
        "lat": lat,
        "lon": lon,
        "normalized_street": normalized_street,
        "direction": "",
        "geo_id": geo_id,
    }


def test_geo_id_match_produces_same_segment():
    a = _candidate("u:1", geo_id="71568", normalized_street="robina avenue",
                   start=date(2026, 7, 1), days=5)
    b = _candidate("u:2", geo_id="71568", normalized_street="robina ave",  # data noise
                   start=date(2026, 7, 6), days=4)
    recs = cluster_leftover_candidates([a, b], set())
    assert len(recs) == 1, recs
    assert recs[0]["match_type"] == "same_segment", recs[0]
    assert set(recs[0]["member_permit_ids"]) == {"u:1", "u:2"}


def test_street_match_produces_same_street():
    a = _candidate("u:1", normalized_street="danforth avenue",
                   start=date(2026, 7, 1), days=4)
    b = _candidate("u:2", normalized_street="danforth avenue",
                   start=date(2026, 7, 20), days=3)
    c = _candidate("u:3", normalized_street="danforth avenue",
                   start=date(2026, 8, 5), days=2)
    recs = cluster_leftover_candidates([a, b, c], set())
    assert len(recs) == 1, recs
    assert recs[0]["match_type"] == "same_street", recs[0]
    assert recs[0]["permit_count"] == 3, recs[0]


def test_empty_normalized_street_does_NOT_cluster():
    a = _candidate("u:1", normalized_street="", start=date(2026, 7, 1))
    b = _candidate("u:2", normalized_street="", start=date(2026, 7, 2))
    recs = cluster_leftover_candidates([a, b], set())
    assert recs == [], recs


def test_parallel_streets_no_longer_cluster():
    # Different streets + different geo_ids, lat/lon 100m apart. Old DBSCAN
    # would have merged; new code keeps them apart.
    a = _candidate("u:1", normalized_street="danforth avenue",
                   geo_id="A", lat=43.6657, lon=-79.3642,
                   start=date(2026, 7, 1))
    b = _candidate("u:2", normalized_street="mortimer avenue",
                   geo_id="B", lat=43.6666, lon=-79.3640,
                   start=date(2026, 7, 1))
    recs = cluster_leftover_candidates([a, b], set())
    assert recs == [], recs


def test_same_street_far_apart_NOW_clusters():
    # Two permits on the same street, lat/lon 400m apart (over the old
    # eps=220m). Old DBSCAN missed them; new code catches them.
    a = _candidate("u:1", normalized_street="danforth avenue",
                   lat=43.6657, lon=-79.3642,
                   start=date(2026, 7, 1), days=4)
    b = _candidate("u:2", normalized_street="danforth avenue",
                   lat=43.6657, lon=-79.3692,  # ~400m east-west delta
                   start=date(2026, 7, 10), days=3)
    recs = cluster_leftover_candidates([a, b], set())
    assert len(recs) == 1, recs
    assert recs[0]["match_type"] == "same_street", recs[0]


def test_temporal_split_within_street():
    # Three permits on the same street; two early, one 200 days later.
    a = _candidate("u:1", normalized_street="danforth avenue",
                   start=date(2026, 7, 1), days=4)
    b = _candidate("u:2", normalized_street="danforth avenue",
                   start=date(2026, 7, 5), days=3)
    c = _candidate("u:3", normalized_street="danforth avenue",
                   start=date(2027, 1, 20), days=3)
    recs = cluster_leftover_candidates([a, b, c], set())
    # Only the two-permit bucket survives — the singleton is dropped.
    assert len(recs) == 1, recs
    assert recs[0]["permit_count"] == 2, recs[0]
    assert set(recs[0]["member_permit_ids"]) == {"u:1", "u:2"}, recs[0]


def test_recommendation_shape_is_schema_compliant():
    a = _candidate("u:1", geo_id="999", normalized_street="rh1",
                   start=date(2026, 7, 1), days=4)
    b = _candidate("u:2", geo_id="999", normalized_street="rh1",
                   start=date(2026, 7, 5), days=3)
    recs = cluster_leftover_candidates([a, b], set())
    assert len(recs) == 1
    required_keys = {
        "type", "cluster_id", "member_permit_ids", "merged_window",
        "savings_lane_days", "lane_days_saved", "excavations_avoided",
        "permit_count", "road_openings_saved", "estimated_savings", "priority",
        "locations", "projects", "statuses", "action", "reason", "match_type",
    }
    missing = required_keys - set(recs[0].keys())
    assert not missing, f"missing keys: {missing}"
    assert recs[0]["match_type"] in {"same_segment", "same_street"}, recs[0]
    assert "start" in recs[0]["merged_window"]
    assert "end" in recs[0]["merged_window"]


def test_cluster_ids_are_unique():
    perms = []
    # Build 3 independent same-street clusters (different streets).
    for street_idx in range(3):
        street = f"street {street_idx}"
        perms.append(_candidate(f"u:{street_idx}-a", normalized_street=street,
                                start=date(2026, 7, 1)))
        perms.append(_candidate(f"u:{street_idx}-b", normalized_street=street,
                                start=date(2026, 7, 5)))
    recs = cluster_leftover_candidates(perms, set())
    assert len(recs) == 3
    ids = [r["cluster_id"] for r in recs]
    assert len(ids) == len(set(ids)), f"duplicate cluster_ids: {ids}"
    for cid in ids:
        assert cid.startswith("merge:"), cid


def test_constant_default_is_reasonable():
    # The 60-day default is documented in the algorithm. If somebody bumps it
    # accidentally to 6 the temporal_split test still passes (200 days > 60)
    # but a tighter sanity check belongs here.
    assert STREET_CLUSTER_WINDOW_DAYS >= 14
    assert STREET_CLUSTER_WINDOW_DAYS <= 365


TESTS = [
    test_geo_id_match_produces_same_segment,
    test_street_match_produces_same_street,
    test_empty_normalized_street_does_NOT_cluster,
    test_parallel_streets_no_longer_cluster,
    test_same_street_far_apart_NOW_clusters,
    test_temporal_split_within_street,
    test_recommendation_shape_is_schema_compliant,
    test_cluster_ids_are_unique,
    test_constant_default_is_reasonable,
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
