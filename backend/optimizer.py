"""
Space+time DBSCAN clustering of Toronto permits.

Fixes from review:
  - Project lat/lon to meters (not raw degrees) before DBSCAN — eps is meters
  - Add a time dimension so permits years apart don't cluster together
  - eps_meters tunable; default 150m (≈ 1 typical city block)
  - time_scale_m_per_year controls how aggressively years separate clusters
"""

import json
import math
import os
import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN


# Toronto-local equirectangular projection constants (centered at ~43.7°N)
TORONTO_LAT_REF = 43.7
LAT_M_PER_DEG = 111_320.0
LON_M_PER_DEG = LAT_M_PER_DEG * math.cos(math.radians(TORONTO_LAT_REF))

EPS_METERS = float(os.getenv("PERMITFLOW_EPS_M", "50"))
MIN_SAMPLES = int(os.getenv("PERMITFLOW_MIN_SAMPLES", "2"))
# 1 year of separation costs this many meters of "distance" in DBSCAN space
TIME_SCALE_M_PER_YEAR = float(os.getenv("PERMITFLOW_TIME_M_PER_YEAR", "800"))


def extract_lat_lon(geometry_str):
    try:
        geo = json.loads(geometry_str)
        coords = geo["coordinates"]
        if len(coords) == 0:
            return None, None
        midpoint = coords[len(coords) // 2]
        return float(midpoint[1]), float(midpoint[0])
    except Exception:
        return None, None


def load_permits(csv_path=None):
    if csv_path is None:
        csv_path = os.path.join(
            os.path.dirname(__file__), "..", "data", "open_toronto_permits.csv"
        )

    df = pd.read_csv(csv_path)
    df = df.dropna(subset=["geometry"])

    coords = df["geometry"].apply(lambda g: pd.Series(extract_lat_lon(g)))
    coords.columns = ["lat", "lon"]
    df = pd.concat([df, coords], axis=1)

    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
    df = df.dropna(subset=["lat", "lon"])

    df["permit_id"] = df["_id"].astype(str)
    df["street_name"] = df["LOCATION"].fillna("Unknown location")
    df["work_type"] = df["PROJECT"].fillna("Road reconstruction")
    df["status"] = df["STATUS"].fillna("Unknown")
    df["start_year"] = pd.to_numeric(df["START_YEAR"], errors="coerce")

    # Fill missing years with the median so they don't dominate the time dim
    median_year = df["start_year"].median()
    df["start_year"] = df["start_year"].fillna(median_year)

    return df


def _to_metric_features(df):
    """(lat, lon, year) → (x_m, y_m, t_m) for DBSCAN with eps in meters."""
    x_m = (df["lon"].values - df["lon"].mean()) * LON_M_PER_DEG
    y_m = (df["lat"].values - df["lat"].mean()) * LAT_M_PER_DEG
    t_m = (df["start_year"].values - df["start_year"].mean()) * TIME_SCALE_M_PER_YEAR
    return np.column_stack([x_m, y_m, t_m])


def cluster_permits(df):
    features = _to_metric_features(df)
    clustering = DBSCAN(eps=EPS_METERS, min_samples=MIN_SAMPLES).fit(features)
    df = df.copy()
    df["cluster_id"] = clustering.labels_
    return df


def calculate_cluster_metrics(group):
    permit_count = len(group)
    road_openings_saved = max(permit_count - 1, 0)
    unique_locations = group["street_name"].nunique()
    unique_projects = group["work_type"].nunique()

    disruption_score = (
        permit_count * 10
        + unique_locations * 4
        + unique_projects * 3
    )

    # Placeholder: per Phase 6 D-53 this should be back-of-envelope from
    # Toronto's congestion / capital budget, with the math shown on the slide.
    estimated_savings = road_openings_saved * 15000

    return {
        "permit_count": int(permit_count),
        "road_openings_saved": int(road_openings_saved),
        "unique_locations": int(unique_locations),
        "unique_projects": int(unique_projects),
        "disruption_score": int(disruption_score),
        "estimated_savings": int(estimated_savings),
    }


def recommend_consolidations(df):
    recommendations = []
    clustered = df[df["cluster_id"] != -1]

    for cluster_id, group in clustered.groupby("cluster_id"):
        metrics = calculate_cluster_metrics(group)

        recommendations.append({
            "cluster_id": int(cluster_id),
            **metrics,
            "locations": group["street_name"].astype(str).unique().tolist()[:8],
            "projects": group["work_type"].astype(str).unique().tolist()[:5],
            "statuses": group["status"].astype(str).unique().tolist(),
            "years": sorted({int(y) for y in group["start_year"].unique()}),
            "action": "Coordinate nearby road work projects into a single closure window.",
            "reason": "Projects are geographically close and time-aligned, "
                      "so coordinating them may reduce repeated road disruption.",
            "priority": get_priority(metrics["disruption_score"]),
        })

    recommendations.sort(key=lambda r: r["disruption_score"], reverse=True)
    return recommendations


def get_priority(score):
    if score >= 100:
        return "High"
    if score >= 50:
        return "Medium"
    return "Low"


def get_metrics(df):
    clustered = df[df["cluster_id"] != -1]
    recommendations = recommend_consolidations(df)

    total_saved = sum(r["road_openings_saved"] for r in recommendations)
    total_savings = sum(r["estimated_savings"] for r in recommendations)
    largest_cluster = max((r["permit_count"] for r in recommendations), default=0)

    return {
        # Per Phase 3 D-28 tri-stat counter: keep both "considered" and "avoided"
        "permits_considered": int(len(df)),
        "excavations_avoided": int(total_saved),
        "estimated_savings": int(total_savings),
        # Backwards-compatible fields the existing UI reads:
        "total_projects": int(len(df)),
        "clustered_projects": int(len(clustered)),
        "consolidation_opportunities": int(len(recommendations)),
        "largest_cluster": int(largest_cluster),
        "road_openings_saved": int(total_saved),
    }


def what_if_analysis(df, cluster_id, delay_weeks):
    cluster = df[df["cluster_id"] == cluster_id]
    if cluster.empty:
        return {"error": "Cluster not found"}

    metrics = calculate_cluster_metrics(cluster)

    if delay_weeks <= 2:
        impact, reason = (
            "Low",
            "A short delay is unlikely to significantly change the consolidation opportunity.",
        )
    elif delay_weeks <= 6:
        impact, reason = (
            "Medium",
            "A moderate delay may reduce coordination benefits and create schedule conflicts.",
        )
    else:
        impact, reason = (
            "High",
            "A long delay may cause projects to separate into different construction windows.",
        )

    return {
        "cluster_id": int(cluster_id),
        "delay_weeks": int(delay_weeks),
        "impact": impact,
        "reason": reason,
        "current_road_openings_saved": metrics["road_openings_saved"],
        "current_estimated_savings": metrics["estimated_savings"],
        "recommendation": "Review contractor timelines before approving the delay.",
    }
