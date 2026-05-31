from llm import (
    build_cluster_prompt,
    ask_local_llm,
    embed_query,
    retrieve_permits,
    lookup_conflict_edges,
    extract_street_mentions,
    build_chat_messages,
    stream_chat,
    stream_help_skill,
    stream_whatif_skill,
    stream_clusters_skill,
    stream_permit_skill,
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


def _sse_wrap(generator):
    """Wrap a text-chunk generator in SSE framing.

    Each chunk becomes one ``data: ...\\n\\n`` event with embedded newlines
    escaped so multi-line model output stays in a single SSE frame the
    browser can parse without buffering across boundaries.
    """
    for chunk in generator:
        safe = chunk.replace("\r", "").replace("\n", "\\n")
        yield f"data: {safe}\n\n"
    yield "data: [DONE]\n\n"


@app.post("/chat")
def chat(req: ChatRequest):
    query = (req.query or "").strip()

    # ----- Skill routing (explicit slash commands) -----
    # /help — list available skills.
    if query == "/help" or query.startswith("/help "):
        return StreamingResponse(
            _sse_wrap(stream_help_skill()),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    # /clusters [N] — list top N clusters by trench-share savings.
    if query == "/clusters" or query.startswith("/clusters "):
        arg = query[len("/clusters"):].strip()
        try:
            n = int(arg) if arg else 5
        except ValueError:
            n = 5
        try:
            clusters = load_artifact_or_build("clusters.json") or []
        except Exception:
            clusters = []
        try:
            metrics_doc = load_artifact_or_build("metrics.json")
        except Exception:
            metrics_doc = None
        return StreamingResponse(
            _sse_wrap(stream_clusters_skill(n, clusters, metrics_doc)),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    # /permit <id> — explain a specific permit by id.
    if query == "/permit" or query.startswith("/permit "):
        raw_id = query[len("/permit"):].strip()
        # Resolve loose IDs: accept "road_resurfacing:1007", "road_resurfacing #1007",
        # or just "1007" (matches any source where the numeric tail matches).
        def _find_permit(arr):
            if not raw_id:
                return None
            target = raw_id.replace("#", "").strip()
            # Exact match first.
            for row in arr:
                if row.get("permit_id") == target:
                    return row
            # Numeric tail match.
            if target.isdigit():
                suffix = ":" + target
                for row in arr:
                    if str(row.get("permit_id", "")).endswith(suffix):
                        return row
            # Substring fallback (covers "road_resurfacing 1007" w/o colon).
            for row in arr:
                pid = str(row.get("permit_id", ""))
                if target.lower() in pid.lower():
                    return row
            return None
        try:
            opt_rows = load_artifact_or_build("optimized.json") or []
        except Exception:
            opt_rows = []
        try:
            nv_rows = load_artifact_or_build("naive.json") or []
        except Exception:
            nv_rows = []
        try:
            clusters_doc = load_artifact_or_build("clusters.json") or []
        except Exception:
            clusters_doc = []
        try:
            conflict_graph = load_artifact_or_build("conflict-graph.json") or []
        except Exception:
            conflict_graph = []
        permit_opt = _find_permit(opt_rows)
        permit_naive = _find_permit(nv_rows) if permit_opt else None
        cluster_match = None
        if permit_opt:
            target_id = permit_opt["permit_id"]
            for c in clusters_doc:
                if target_id in (c.get("member_permit_ids") or []):
                    cluster_match = c
                    break
        permit_conflicts = []
        if permit_opt:
            target_id = permit_opt["permit_id"]
            for edge in conflict_graph:
                if target_id in (edge.get("permit_a"), edge.get("permit_b")):
                    permit_conflicts.append(edge)
            permit_conflicts.sort(
                key=lambda e: e.get("conflict_score", 0), reverse=True
            )
        return StreamingResponse(
            _sse_wrap(
                stream_permit_skill(
                    raw_id, permit_opt, permit_naive, cluster_match, permit_conflicts
                )
            ),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    # /whatif <street> — ground the model in the conflict graph.
    if query.startswith("/whatif"):
        # Allow both "/whatif Bridgman Ave" and bare "/whatif".
        street = query[len("/whatif"):].strip()
        whatif_result = what_if_by_street(street) if street else {}
        # Reuse the normal context-building helpers so the skill has the same
        # situational awareness as the natural-language chat would.
        permits = load_artifact_or_build(
            "optimized.json" if req.view == "optimized" else "naive.json"
        )
        context_permits = retrieve_permits(street or query, permits, top_k=5)
        try:
            conflict_graph = load_artifact_or_build("conflict-graph.json")
        except Exception:
            conflict_graph = []
        streets = [street] if street else []
        edges = lookup_conflict_edges(streets, conflict_graph) if streets else []
        try:
            metrics_doc = load_artifact_or_build("metrics.json")
        except Exception:
            metrics_doc = None
        return StreamingResponse(
            _sse_wrap(
                stream_whatif_skill(
                    street, whatif_result, context_permits, edges, metrics_doc
                )
            ),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    # ----- Default path: natural-language RAG chat -----
    permits = load_artifact_or_build(
        "optimized.json" if req.view == "optimized" else "naive.json"
    )
    context_permits = retrieve_permits(query, permits, top_k=5)
    try:
        conflict_graph = load_artifact_or_build("conflict-graph.json")
    except Exception:
        conflict_graph = []
    streets = extract_street_mentions(query, context_permits)
    edges = lookup_conflict_edges(streets, conflict_graph) if streets else []
    try:
        metrics_doc = load_artifact_or_build("metrics.json")
    except Exception:
        metrics_doc = None

    return StreamingResponse(
        _sse_wrap(stream_chat(query, context_permits, edges, metrics_doc)),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
