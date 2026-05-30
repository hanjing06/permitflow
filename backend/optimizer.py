import json
import pandas as pd
from sklearn.cluster import DBSCAN


def extract_lat_lon(geometry_str):
    try:
        geo = json.loads(geometry_str)
        coords = geo["coordinates"]

        if len(coords) == 0:
            return None, None

        midpoint = coords[len(coords) // 2]

        lon = float(midpoint[0])
        lat = float(midpoint[1])

        return lat, lon

    except Exception:
        return None, None


def load_permits(csv_path="../data/open_toronto_permits.csv"):
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
    df["start_year"] = df["START_YEAR"].fillna("Unknown")

    return df


def cluster_permits(df):
    coords = df[["lat", "lon"]].values

    clustering = DBSCAN(
        eps=0.01,
        min_samples=2
    ).fit(coords)

    df["cluster_id"] = clustering.labels_
    return df


def calculate_cluster_metrics(group):
    permit_count = len(group)
    road_openings_saved = max(permit_count - 1, 0)

    unique_locations = group["street_name"].nunique()
    unique_projects = group["work_type"].nunique()

    # MVP scoring model
    disruption_score = (
        permit_count * 10
        + unique_locations * 4
        + unique_projects * 3
    )

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
            "action": "Coordinate nearby road work projects into a single closure window.",
            "reason": "Projects are geographically close, so coordinating them may reduce repeated road disruption.",
            "priority": get_priority(metrics["disruption_score"]),
        })

    recommendations.sort(
        key=lambda r: r["disruption_score"],
        reverse=True
    )

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

    largest_cluster = 0
    if len(recommendations) > 0:
        largest_cluster = max(r["permit_count"] for r in recommendations)

    return {
        "total_projects": int(len(df)),
        "clustered_projects": int(len(clustered)),
        "consolidation_opportunities": int(len(recommendations)),
        "largest_cluster": int(largest_cluster),
        "road_openings_saved": int(total_saved),
        "estimated_savings": int(total_savings),
    }


def what_if_analysis(df, cluster_id, delay_weeks):
    cluster = df[df["cluster_id"] == cluster_id]

    if cluster.empty:
        return {
            "error": "Cluster not found"
        }

    metrics = calculate_cluster_metrics(cluster)

    if delay_weeks <= 2:
        impact = "Low"
        reason = "A short delay is unlikely to significantly change the consolidation opportunity."
    elif delay_weeks <= 6:
        impact = "Medium"
        reason = "A moderate delay may reduce coordination benefits and create schedule conflicts."
    else:
        impact = "High"
        reason = "A long delay may cause projects to separate into different construction windows."

    return {
        "cluster_id": int(cluster_id),
        "delay_weeks": int(delay_weeks),
        "impact": impact,
        "reason": reason,
        "current_road_openings_saved": metrics["road_openings_saved"],
        "current_estimated_savings": metrics["estimated_savings"],
        "recommendation": "Review contractor timelines before approving the delay."
    }
