from llm import build_cluster_prompt, ask_local_llm
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from optimizer import (
    load_permits,
    cluster_permits,
    recommend_consolidations,
    get_metrics,
    what_if_analysis
)

app = FastAPI(title="PermitFlow")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {
        "message": "PermitFlow backend is running"
    }


@app.get("/permits")
def get_permits():
    df = load_permits()
    df = cluster_permits(df)

    cols = [
        "permit_id",
        "street_name",
        "work_type",
        "status",
        "start_year",
        "lat",
        "lon",
        "cluster_id",
    ]

    return df[cols].head(500).to_dict(orient="records")

@app.get("/recommendations")
def get_recommendations():
    df = load_permits()
    df = cluster_permits(df)

    recommendations = recommend_consolidations(df)

    return {
        "recommendations": recommendations
    }


@app.get("/debug")
def debug():
    df = load_permits()
    df = cluster_permits(df)

    return {
        "total_projects": int(len(df)),
        "clusters_found": int(
            df[df["cluster_id"] != -1]["cluster_id"].nunique()
        ),
        "cluster_counts": {
            str(k): int(v)
            for k, v in df["cluster_id"].value_counts().to_dict().items()
        }
    }


@app.get("/inspect")
def inspect():
    df = load_permits()

    return {
        "rows": int(len(df)),
        "columns": list(df.columns),
        "sample_lat": float(df["lat"].iloc[0]),
        "sample_lon": float(df["lon"].iloc[0]),
        "sample_location": str(df["street_name"].iloc[0])
    }

@app.get("/metrics")
def metrics():
    df = load_permits()
    df = cluster_permits(df)
    return get_metrics(df)


@app.get("/whatif")
def whatif(cluster_id: int, delay_weeks: int = 2):
    df = load_permits()
    df = cluster_permits(df)
    return what_if_analysis(df, cluster_id, delay_weeks)

@app.get("/explain")
def explain(cluster_id: int):
    df = load_permits()
    df = cluster_permits(df)

    recommendations = recommend_consolidations(df)
    cluster = next(
        (r for r in recommendations if r["cluster_id"] == cluster_id),
        None,
    )
    if cluster is None:
        return {"error": "Cluster not found"}

    prompt = build_cluster_prompt(cluster)
    explanation = ask_local_llm(prompt)

    return {
        "cluster_id": cluster_id,
        "source": "ollama",
        "cluster": cluster,
        "explanation": explanation,
    }
