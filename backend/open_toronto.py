"""
Toronto Open Data ingestion.

Per planning D-79: optimizer is anchor + piggyback.
  Anchors   (planned city openings) — fixed-date windows utility work can piggyback into.
  Candidates (flexible utility work) — short permits looking for an anchor or each other.

Run as: python open_toronto.py            # downloads all datasets
        python open_toronto.py utility    # downloads candidates only
        python open_toronto.py anchors    # downloads anchors only
"""

import os
import sys
import requests
import pandas as pd


CKAN_URL = "https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action/package_show"
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

# D-79 dataset tiers
ANCHORS = {
    "road_reconstruction": "road-reconstruction-program",
    "road_resurfacing":    "road-resurfacing-program",
    "sidewalk_construction": "sidewalk-construction-program",
}
CANDIDATES = {
    "utility_cuts":       "utility-cut-permits",
    "building_permits":   "building-permits-active",
}
CONTEXT = {
    "watermain_breaks":   "watermain-breaks",
    "road_restrictions":  "road-restrictions",
}


def fetch_package(package_id):
    response = requests.get(CKAN_URL, params={"id": package_id}, timeout=30)
    response.raise_for_status()
    return response.json()["result"]


def download_dataset(name, package_id):
    print(f"--- {name}  ({package_id}) ---")
    package = fetch_package(package_id)

    resources = [
        r for r in package["resources"]
        if r.get("format", "").lower() in ("csv", "geojson", "json")
        and r.get("url")
    ]
    if not resources:
        print(f"  (no downloadable resources)")
        return

    resource = resources[0]
    out_path = os.path.join(DATA_DIR, f"{name}.csv")
    print(f"  fetching {resource['format']} from {resource['url']}")

    try:
        df = pd.read_csv(resource["url"])
        df.to_csv(out_path, index=False)
        print(f"  saved {len(df)} rows → {out_path}")
    except Exception as exc:
        print(f"  failed: {exc}")


def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    mode = sys.argv[1] if len(sys.argv) > 1 else "all"

    if mode in ("all", "anchors"):
        for name, pid in ANCHORS.items():
            download_dataset(name, pid)
    if mode in ("all", "utility", "candidates"):
        for name, pid in CANDIDATES.items():
            download_dataset(name, pid)
    if mode in ("all", "context"):
        for name, pid in CONTEXT.items():
            download_dataset(name, pid)


if __name__ == "__main__":
    main()
