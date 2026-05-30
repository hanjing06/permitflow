import json
import pandas as pd
from sklearn.cluster import DBSCAN


def extract_lat_lon(geometry_str):
    try:
        geo = json.loads(geometry_str)

        coords = geo["coordinates"]

        if len(coords) == 0:
            return None, None

        # Use midpoint of LineString
        midpoint = coords[len(coords) // 2]

        lon = float(midpoint[0])
        lat = float(midpoint[1])

        return lat, lon

    except Exception as e:
        print(f"Geometry parsing error: {e}")
        return None, None


def load_permits(csv_path="../data/open_toronto_permits.csv"):
    df = pd.read_csv(csv_path)

    # Remove empty geometry rows
    df = df.dropna(subset=["geometry"])

    # Extract coordinates
    coords = df["geometry"].apply(
        lambda g: pd.Series(extract_lat_lon(g))
    )

    coords.columns = ["lat", "lon"]

    df = pd.concat([df, coords], axis=1)

    # Ensure numeric
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")

    df = df.dropna(subset=["lat", "lon"])

    # Open Toronto mappings
    df["permit_id"] = df["_id"].astype(str)
    df["street_name"] = df["LOCATION"].fillna("Unknown location")
    df["work_type"] = df["PROJECT"].fillna("Road reconstruction")
    df["status"] = df["STATUS"].fillna("Unknown")
    df["start_year"] = df["START_YEAR"].fillna("Unknown")

    return df


def cluster_permits(df):
    coords = df[["lat", "lon"]].values

    clustering = DBSCAN(
        eps=0.01,      # ~1km for testing
        min_samples=2
    ).fit(coords)

    df["cluster_id"] = clustering.labels_

    return df


def recommend_consolidations(df):
    recommendations = []

    clustered = df[df["cluster_id"] != -1]

    for cluster_id, group in clustered.groupby("cluster_id"):
        recommendations.append({
            "cluster_id": int(cluster_id),
            "permit_count": int(len(group)),
            "locations": group["street_name"].unique().tolist(),
            "projects": group["work_type"].unique().tolist(),
            "statuses": group["status"].unique().tolist(),
            "action": "Coordinate nearby road work projects into a single closure window.",
            "reason": "Projects are geographically close and may reduce repeated road disruption if planned together."
        })

    return recommendations
