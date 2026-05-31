from llm import (
    build_cluster_prompt,
    ask_local_llm,
    embed_query,
    retrieve_permits,
    lookup_conflict_edges,
    extract_street_mentions,
    build_chat_messages,
    stream_chat,
    CANNED_SCENARIOS,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi import FastAPI
from pydantic import BaseModel
from optimizer import (
    load_permits,
    cluster_permits,
    recommend_consolidations,
    get_metrics,
    what_if_analysis,
    what_if_by_street,
    load_artifact_or_build,
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

@app.get("/hero-block")
def hero_block():
    return load_artifact_or_build("hero-block.json")


@app.get("/clusters")
def clusters():
    return load_artifact_or_build("clusters.json")


@app.get("/conflict-graph")
def conflict_graph():
    return load_artifact_or_build("conflict-graph.json")


@app.get("/naive")
def naive():
    return load_artifact_or_build("naive.json")


@app.get("/optimized")
def optimized():
    return load_artifact_or_build("optimized.json")


@app.get("/whatif-street")
def whatif_street(street: str, date: str | None = None):
    return what_if_by_street(street, date)


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


# ---------------------------------------------------------------------------
# Phase 4 — chat panel: SSE /chat, RAG /retrieve, GET /chat/scenarios.
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    query: str
    view: str = "optimized"  # "naive" | "optimized"


class RetrieveRequest(BaseModel):
    query: str
    view: str = "optimized"
    top_k: int = 5


@app.get("/chat/scenarios")
def chat_scenarios():
    return {"scenarios": CANNED_SCENARIOS}


@app.post("/retrieve")
def retrieve(req: RetrieveRequest):
    permits = load_artifact_or_build(
        "optimized.json" if req.view == "optimized" else "naive.json"
    )
    hits = retrieve_permits(req.query, permits, top_k=req.top_k)
    used_embedder = embed_query("__healthcheck__") is not None
    return {
        "query": req.query,
        "view": req.view,
        "used_embedder": used_embedder,
        "top_k": req.top_k,
        "results": hits,
    }


@app.post("/chat")
def chat(req: ChatRequest):
    permits = load_artifact_or_build(
        "optimized.json" if req.view == "optimized" else "naive.json"
    )
    context_permits = retrieve_permits(req.query, permits, top_k=5)
    try:
        conflict_graph = load_artifact_or_build("conflict-graph.json")
    except Exception:
        conflict_graph = []
    streets = extract_street_mentions(req.query, context_permits)
    edges = lookup_conflict_edges(streets, conflict_graph) if streets else []
    try:
        metrics_doc = load_artifact_or_build("metrics.json")
    except Exception:
        metrics_doc = None

    def event_stream():
        # SSE framing: each chunk is `data: <text>\n\n`. Escape embedded
        # newlines so each model chunk stays a single SSE event the client
        # can parse without buffering across frames.
        for chunk in stream_chat(req.query, context_permits, edges, metrics_doc):
            safe = chunk.replace("\r", "").replace("\n", "\\n")
            yield f"data: {safe}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
