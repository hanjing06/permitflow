"""
Pure street-name normalization helper for PermitFlow's street-based clustering pass.

Used by `backend.optimizer.cluster_leftover_candidates` (Phase 8, Layer 1) to group
permits by the *same physical road* rather than by euclidean radius. Also exposes
the parsed direction prefix (`E`/`W`/`N`/`S`/...) so that "Yonge St E" and
"Yonge St W" do not collapse together.

This module is intentionally I/O-free and depends only on the standard library so
it can be imported from anywhere in the codebase without pulling pandas.

Algorithm:
  1. Reject empty / None / NaN / "Unknown location" → empty result.
  2. Take only the FIRST segment of `raw.split(" | ")` — drops "From: X | To: Y"
     tails that the anchor LOCATION column carries after `clean_text` runs.
  3. Drop everything from the first "(" onward — drops "(Between A AND B)" tails
     that `utility_cuts.DISPLAY_DESC` ships.
  4. Strip a leading all-digits token (the house number, e.g. "154 ROBINA AVE").
  5. If the first remaining token is in DIRECTION_PREFIXES (single-letter
     compass direction), pop it into `direction`.
  6. If the last remaining token is in STREET_TYPE_CANONICAL, replace with the
     canonical full form. STREET_TYPE_CANONICAL also maps the full form to
     itself so the lookup is a single dict access.
  7. Reassemble; `display` is uppercase, `normalized` is the lowercased version
     of `display` (used as a dict key for grouping).

The empty-normalized result is a soft signal — callers MUST treat an empty
`normalized` as "no group" (singleton). Never group unparseable permits under a
shared "unknown" bucket.
"""

from __future__ import annotations

import math


STREET_TYPE_CANONICAL: dict[str, str] = {
    # Abbreviation -> canonical full form
    "AVE": "AVENUE",
    "ST": "STREET",
    "RD": "ROAD",
    "BLVD": "BOULEVARD",
    "CRES": "CRESCENT",
    "DR": "DRIVE",
    "LN": "LANE",
    "PL": "PLACE",
    "CT": "COURT",
    "PKWY": "PARKWAY",
    "TR": "TRAIL",
    "TER": "TERRACE",
    "GDNS": "GARDENS",
    "SQ": "SQUARE",
    "CIR": "CIRCLE",
    "HTS": "HEIGHTS",
    "GRV": "GROVE",
    "WAY": "WAY",
    "PROM": "PROMENADE",
    # Canonical full form -> itself (so a single dict lookup suffices)
    "AVENUE": "AVENUE",
    "STREET": "STREET",
    "ROAD": "ROAD",
    "BOULEVARD": "BOULEVARD",
    "CRESCENT": "CRESCENT",
    "DRIVE": "DRIVE",
    "LANE": "LANE",
    "PLACE": "PLACE",
    "COURT": "COURT",
    "PARKWAY": "PARKWAY",
    "TRAIL": "TRAIL",
    "TERRACE": "TERRACE",
    "GARDENS": "GARDENS",
    "SQUARE": "SQUARE",
    "CIRCLE": "CIRCLE",
    "HEIGHTS": "HEIGHTS",
    "GROVE": "GROVE",
    "PROMENADE": "PROMENADE",
}

DIRECTION_PREFIXES: set[str] = {"E", "W", "N", "S", "NE", "NW", "SE", "SW"}

_EMPTY: dict = {"normalized": "", "direction": "", "display": ""}


def normalize_street(raw) -> dict:
    """Normalize a raw street string into {normalized, direction, display}.

    Returns the empty result ({"normalized": "", "direction": "", "display": ""})
    for None / NaN / empty / "Unknown location" inputs. Callers MUST treat the
    empty case as "no group" — singleton — never as a clusterable key.
    """
    # 1. Guard nones / NaN / empty / sentinel strings.
    if raw is None:
        return dict(_EMPTY)
    if isinstance(raw, float) and math.isnan(raw):
        return dict(_EMPTY)
    text = str(raw).strip()
    if not text:
        return dict(_EMPTY)
    if text.lower() in {"unknown location", "unknown", "nan"}:
        return dict(_EMPTY)

    # 2. Drop "From: ... | To: ..." tails (anchor LOCATION post-clean_text).
    text = text.split(" | ")[0].strip()

    # 3. Drop "(Between A AND B)" tails (utility_cut DISPLAY_DESC).
    if "(" in text:
        text = text.split("(", 1)[0].strip()

    if not text:
        return dict(_EMPTY)

    # 4. Tokenize, drop a leading all-digits house number.
    tokens = text.split()
    if not tokens:
        return dict(_EMPTY)
    if tokens[0].isdigit():
        tokens = tokens[1:]
    if not tokens:
        return dict(_EMPTY)

    # Uppercase everything for canonical comparison.
    tokens = [t.upper() for t in tokens]

    # 5. Pop a single-letter compass direction off the front OR the tail.
    # Toronto data mixes both forms ("W BLOOR STREET" and "BLOOR ST W"); we
    # peel either side so both collapse to direction="W" + name="bloor street".
    direction = ""
    if tokens and tokens[0] in DIRECTION_PREFIXES:
        direction = tokens[0]
        tokens = tokens[1:]
    elif len(tokens) >= 2 and tokens[-1] in DIRECTION_PREFIXES:
        direction = tokens[-1]
        tokens = tokens[:-1]
    if not tokens:
        return dict(_EMPTY)

    # 6. Canonicalize the trailing street type, if recognizable.
    if tokens[-1] in STREET_TYPE_CANONICAL:
        tokens[-1] = STREET_TYPE_CANONICAL[tokens[-1]]

    # 7. Reassemble.
    display = " ".join(tokens).strip()
    if not display:
        return dict(_EMPTY)

    return {
        "normalized": display.lower(),
        "direction": direction,
        "display": display,
    }
