"""
Small Valhalla client used by Phase 3.

The artifact builder has a deterministic proxy conflict graph so the demo can
run offline. This client is for live `/whatif` checks when the GX10 Valhalla
service is available at :5000.
"""

from __future__ import annotations

import json
import os
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen


VALHALLA_URL = os.getenv("VALHALLA_URL", "http://localhost:5000")


def route(locations, exclude_polygons=None, costing="auto"):
    payload = {
        "locations": locations,
        "costing": costing,
        "directions_options": {"units": "kilometers"},
    }
    if exclude_polygons:
        payload["exclude_polygons"] = exclude_polygons

    request = Request(
        f"{VALHALLA_URL.rstrip('/')}/route",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=8) as response:
            return json.loads(response.read().decode("utf-8"))
    except (URLError, HTTPError, TimeoutError, json.JSONDecodeError) as exc:
        return {"error": str(exc), "valhalla_url": VALHALLA_URL}


def is_available():
    sample = route([
        {"lat": 43.6532, "lon": -79.3832},
        {"lat": 43.6617, "lon": -79.3950},
    ])
    return "trip" in sample
