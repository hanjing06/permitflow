import json
import math
import os
from typing import Iterator

import requests

OLLAMA_URL = os.getenv(
    "OLLAMA_URL",
    "http://localhost:11434/v1/chat/completions",
)
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "nemotron-3-super:latest")

NIM_EMBED_URL = os.getenv(
    "NIM_EMBED_URL",
    "http://localhost:8003/v1/embeddings",
)
NIM_EMBED_MODEL = os.getenv("NIM_EMBED_MODEL", "nv-embedqa-e5-v5")
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "5"))

SYSTEM_PROMPT = (
    "You are PermitFlow, an infrastructure planning assistant for the City of Toronto. "
    "Be concise. Reply in one short paragraph unless asked otherwise."
)

CANNED_SCENARIOS = [
    {
        "id": "coordination",
        "label": "Biggest coordination opportunity",
        "query": "What's the biggest coordination opportunity on the hero block?",
    },
    {
        "id": "conflict",
        "label": "Conflict near Danforth & Pape",
        "query": "Show me a conflict near Danforth & Pape.",
    },
    {
        "id": "why-not",
        "label": "Why isn't permit X piggybacking?",
        "query": "Why isn't permit road_resurfacing:1138 piggybacking on a nearby anchor?",
    },
]

# Module-level cache for permit embeddings keyed by the embedding text.
_PERMIT_EMBED_CACHE: dict[str, list[float]] = {}


def build_cluster_prompt(cluster):
    return f"""
Analyze this road work consolidation opportunity.

Cluster ID: {cluster["cluster_id"]}
Projects: {cluster["permit_count"]}
Road openings saved: {cluster["road_openings_saved"]}
Estimated savings: ${cluster["estimated_savings"]}
Priority: {cluster["priority"]}
Locations: {cluster["locations"]}
Projects: {cluster["projects"]}
Statuses: {cluster["statuses"]}

Explain:
1. Why this cluster should or should not be consolidated
2. Expected benefit to the city
3. Risks or coordination concerns
4. Recommended next action
""".strip()


def ask_local_llm(prompt, max_tokens=800):
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": OLLAMA_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "max_tokens": max_tokens,
        },
        timeout=120,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


# ---------------------------------------------------------------------------
# Phase 4 — chat panel helpers (RAG + streaming + graceful degradation).
# ---------------------------------------------------------------------------


def embed_query(text: str) -> list[float] | None:
    """Embed a single string via the NIM embedder.

    Returns the embedding vector on success, or ``None`` on any failure
    (unreachable, non-200, malformed payload). Never raises.
    """
    try:
        response = requests.post(
            NIM_EMBED_URL,
            json={
                "input": [text],
                "model": NIM_EMBED_MODEL,
                "input_type": "query",
            },
            timeout=10,
        )
        if response.status_code != 200:
            return None
        data = response.json()
        return data["data"][0]["embedding"]
    except (requests.RequestException, ValueError, KeyError, IndexError, TypeError):
        return None


def cosine_sim(a, b) -> float:
    """Pure-Python cosine similarity. Returns 0.0 if either vector is empty
    or has zero magnitude."""
    if not a or not b:
        return 0.0
    if len(a) != len(b):
        # Fall back to the shorter prefix rather than raising.
        n = min(len(a), len(b))
        a = a[:n]
        b = b[:n]
    dot = 0.0
    mag_a = 0.0
    mag_b = 0.0
    for x, y in zip(a, b):
        dot += x * y
        mag_a += x * x
        mag_b += y * y
    if mag_a == 0.0 or mag_b == 0.0:
        return 0.0
    return dot / (math.sqrt(mag_a) * math.sqrt(mag_b))


def _permit_text(permit: dict) -> str:
    street = (permit.get("street_name") or "").strip()
    work = (permit.get("work_type") or "").strip()
    return f"{street} {work}".strip()


def _keyword_score(query: str, permits: list[dict], top_k: int) -> list[dict]:
    tokens = [t for t in query.lower().split() if t]
    scored: list[tuple[float, dict]] = []
    for p in permits:
        haystack = _permit_text(p).lower()
        if not haystack:
            continue
        score = sum(1 for tok in tokens if tok in haystack)
        if score > 0:
            enriched = dict(p)
            enriched["relevance_score"] = float(score)
            scored.append((float(score), enriched))
    scored.sort(key=lambda kv: kv[0], reverse=True)
    return [p for _, p in scored[:top_k]]


def retrieve_permits(
    query: str,
    permits: list[dict],
    top_k: int = RAG_TOP_K,
) -> list[dict]:
    """Return the top_k permits most relevant to ``query``.

    Primary path: NIM embedder cosine similarity. Fallback paths:
    - keyword token overlap if the embedder is unreachable
    - keyword scoring when the permit set is too large (>200) to embed
      synchronously without hammering the embedder during a demo.
    """
    if not permits or top_k <= 0:
        return []

    # Escape hatch: don't hammer the embedder on huge sets.
    if len(permits) > 200:
        return _keyword_score(query, permits, top_k)

    query_vec = embed_query(query)
    if query_vec is None:
        return _keyword_score(query, permits, top_k)

    scored: list[tuple[float, dict]] = []
    for p in permits:
        text = _permit_text(p)
        if not text:
            continue
        vec = _PERMIT_EMBED_CACHE.get(text)
        if vec is None:
            vec = embed_query(text)
            if vec is None:
                # Mid-flight embedder failure → fall back to keyword scoring
                # entirely so results stay coherent.
                return _keyword_score(query, permits, top_k)
            _PERMIT_EMBED_CACHE[text] = vec
        score = cosine_sim(query_vec, vec)
        enriched = dict(p)
        enriched["relevance_score"] = float(score)
        scored.append((score, enriched))

    scored.sort(key=lambda kv: kv[0], reverse=True)
    return [p for _, p in scored[:top_k]]


def lookup_conflict_edges(
    street_names: list[str],
    conflict_graph: list[dict],
) -> list[dict]:
    """Return up to 10 conflict edges whose shared_streets intersect any of
    ``street_names`` (case-insensitive)."""
    if not street_names or not conflict_graph:
        return []
    wanted = {s.lower() for s in street_names if s}
    out: list[dict] = []
    for edge in conflict_graph:
        shared = edge.get("shared_streets") or []
        if not shared:
            continue
        if any(isinstance(s, str) and s.lower() in wanted for s in shared):
            out.append(edge)
            if len(out) >= 10:
                break
    return out


def extract_street_mentions(query: str, permits: list[dict]) -> list[str]:
    """Pick up to 5 street names from ``permits`` that appear (case-insensitively)
    as substrings of ``query``."""
    if not query or not permits:
        return []
    q = query.lower()
    seen: set[str] = set()
    out: list[str] = []
    for p in permits:
        name = (p.get("street_name") or "").strip()
        if not name:
            continue
        key = name.lower()
        if key in seen:
            continue
        # Match against the leading street token (before " | From:") too —
        # full street_name strings often contain segment metadata.
        head = key.split("|", 1)[0].strip()
        if (head and head in q) or key in q:
            out.append(name)
            seen.add(key)
            if len(out) >= 5:
                break
    return out


def _format_permit_line(p: dict) -> str:
    return (
        f"- [{p.get('permit_id','?')}] {p.get('street_name','?')} "
        f"— {p.get('work_type','?')} "
        f"({p.get('start_date','?')} → {p.get('end_date','?')}) "
        f"status={p.get('status','?')} "
        f"opt={p.get('optimization_status','?')}"
    )


def _format_edge_line(e: dict) -> str:
    shared = ", ".join(e.get("shared_streets") or [])
    return (
        f"- {e.get('permit_a','?')} vs {e.get('permit_b','?')} "
        f"on [{shared}] score={e.get('conflict_score','?')}"
    )


def build_chat_messages(
    query: str,
    context_permits: list[dict],
    conflict_edges: list[dict],
    metrics: dict | None,
) -> list[dict]:
    """Compose the OpenAI ``messages`` array for the chat completion call."""
    parts: list[str] = [SYSTEM_PROMPT, "<context>"]

    if metrics:
        parts.append(
            "Headline metrics: "
            f"permits_considered={metrics.get('permits_considered','?')}, "
            f"excavations_avoided={metrics.get('excavations_avoided','?')}, "
            f"cost_avoidance=${metrics.get('cost_avoidance','?')}."
        )

    if context_permits:
        parts.append("Retrieved permits:")
        for p in context_permits:
            parts.append(_format_permit_line(p))
    else:
        parts.append("No directly relevant permits retrieved.")

    if conflict_edges:
        parts.append("Conflict edges:")
        for e in conflict_edges:
            parts.append(_format_edge_line(e))

    parts.append("</context>")
    system_content = "\n".join(parts)

    # Cap the context block to keep prompts small. Truncate the *permit list*
    # portion if the system message grows past ~3000 chars.
    if len(system_content) > 3000:
        # Rebuild with progressively fewer permits.
        for keep in range(len(context_permits) - 1, -1, -1):
            trimmed = build_chat_messages(
                query, context_permits[:keep], conflict_edges, metrics
            )
            if len(trimmed[0]["content"]) <= 3000:
                trimmed[0]["content"] += "\n(context truncated)"
                return trimmed
        # Even with zero permits we're still over budget — just hard-truncate.
        system_content = system_content[:3000] + "\n(context truncated)"

    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": query},
    ]


SKILL_HELP_TEXT = (
    "PermitFlow chat skills:\n"
    "\n"
    "  /whatif <street>   — Conflict-graph analysis for a street.\n"
    "                       Example: /whatif Bridgman Ave\n"
    "  /clusters [N]      — Top N clusters by trench-share savings (default 5).\n"
    "                       Example: /clusters 3\n"
    "  /permit <id>       — Explain a specific permit. Accepts full IDs\n"
    "                       (road_resurfacing:1007) or just the number (1007).\n"
    "                       Example: /permit road_resurfacing:1007\n"
    "  /help              — Show this message.\n"
    "\n"
    "Or just ask a question in plain English — the chat retrieves the top-5\n"
    "permits via embeddings and any conflict edges that mention streets you\n"
    "named, then streams the answer from Nemotron-3 Super on the GX10."
)


def stream_help_skill() -> Iterator[str]:
    """Emit the /help text as a stream of small chunks so the SSE pipe stays
    consistent with the streaming chat path."""
    # Stream in two chunks so the user sees the "typing" cadence.
    yield "🔧 Skill: /help\n\n"
    yield SKILL_HELP_TEXT


def stream_whatif_skill(
    street: str,
    whatif_result: dict,
    context_permits: list[dict],
    conflict_edges: list[dict],
    metrics: dict | None,
) -> Iterator[str]:
    """Run the /whatif skill: emit a one-line factual prefix from the structured
    `what_if_by_street` result, then stream a Nemotron summary grounded in it.

    The structured prefix arrives first (judges see hard data in 1 token-round-
    trip), then the model commentary streams afterwards (the "model thinks"
    moment). On Ollama failure, only the structured prefix lands."""
    if not street:
        yield (
            "🔧 Skill: /whatif\n\n"
            "Usage: /whatif <street name>\n"
            "Example: /whatif Bridgman Ave"
        )
        return

    impact = whatif_result.get("impact", "?")
    matching = whatif_result.get("matching_permits") or []
    conflicts = whatif_result.get("conflicts") or []

    # Emit the structured prefix as ONE SSE-friendly chunk.
    prefix_lines = [
        f"🔧 Skill: /whatif `{street}`",
        "",
        f"Impact: **{impact}** · {len(matching)} affected permit(s) · "
        f"{len(conflicts)} conflict edge(s) in graph.",
    ]
    if matching:
        prefix_lines.append("")
        prefix_lines.append("Affected permits:")
        for p in matching[:5]:
            prefix_lines.append(
                f"  • {p.get('permit_id','?')} — {p.get('street_name','?')} "
                f"({p.get('start_date','?')} → {p.get('end_date','?')})"
            )
    if conflicts:
        prefix_lines.append("")
        prefix_lines.append("Top conflicts in graph:")
        for c in conflicts[:3]:
            shared = ", ".join(c.get("shared_streets") or [])
            prefix_lines.append(
                f"  • {c.get('permit_a','?')} vs {c.get('permit_b','?')} on "
                f"[{shared}] (score {c.get('conflict_score','?')})"
            )
    if not matching and not conflicts:
        prefix_lines.append("")
        prefix_lines.append(
            f"No permits matched '{street}' in the optimized timeline."
        )
    prefix_lines.append("")
    prefix_lines.append("---")
    prefix_lines.append("")
    yield "\n".join(prefix_lines) + "\n"

    # Now stream a model summary GROUNDED in the structured result.
    system_msg = (
        "You are PermitFlow's coordination assistant. The user invoked the "
        f"/whatif skill on street '{street}'. Here is the live conflict-graph "
        f"analysis for that street:\n\n{json.dumps(whatif_result, indent=2)}\n\n"
        "Write 2-3 plain sentences answering: how risky is closing this street "
        "during the impact window, what is the strongest conflict, and what "
        "should be coordinated. Be concrete. Reference permit IDs. Do NOT "
        "restate the JSON. Skip pleasantries."
    )
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": f"/whatif {street}"},
    ]
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 400,
        "stream": True,
    }
    try:
        response = requests.post(OLLAMA_URL, json=payload, stream=True, timeout=120)
        if response.status_code != 200:
            yield (
                f"\n[Nemotron unavailable — HTTP {response.status_code}. "
                "Structured what-if data above is the primary result.]"
            )
            return
        for raw in response.iter_lines():
            if not raw:
                continue
            if not raw.startswith(b"data: "):
                continue
            payload_bytes = raw[len(b"data: "):]
            if payload_bytes.strip() == b"[DONE]":
                break
            try:
                obj = json.loads(payload_bytes.decode("utf-8"))
            except (UnicodeDecodeError, ValueError):
                continue
            try:
                delta = obj["choices"][0].get("delta") or {}
            except (KeyError, IndexError, TypeError):
                continue
            content = delta.get("content")
            if content:
                yield content
    except requests.RequestException:
        yield (
            "\n[Nemotron unreachable. Structured what-if data above is the "
            "primary result.]"
        )
        return


def _stream_ollama_chat(messages: list[dict], max_tokens: int = 400) -> Iterator[str]:
    """Shared helper: stream Nemotron chunks for the given messages array.

    Yields plain text chunks. On any failure yields one bracketed fallback
    line so the caller's skill output stays coherent."""
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": max_tokens,
        "stream": True,
    }
    try:
        response = requests.post(OLLAMA_URL, json=payload, stream=True, timeout=120)
        if response.status_code != 200:
            yield (
                f"\n[Nemotron unavailable — HTTP {response.status_code}. "
                "Structured data above is the primary result.]"
            )
            return
        for raw in response.iter_lines():
            if not raw:
                continue
            if not raw.startswith(b"data: "):
                continue
            payload_bytes = raw[len(b"data: "):]
            if payload_bytes.strip() == b"[DONE]":
                break
            try:
                obj = json.loads(payload_bytes.decode("utf-8"))
            except (UnicodeDecodeError, ValueError):
                continue
            try:
                delta = obj["choices"][0].get("delta") or {}
            except (KeyError, IndexError, TypeError):
                continue
            content = delta.get("content")
            if content:
                yield content
    except requests.RequestException:
        yield (
            "\n[Nemotron unreachable. Structured data above is the "
            "primary result.]"
        )


def stream_clusters_skill(
    n: int,
    clusters: list[dict],
    metrics: dict | None,
) -> Iterator[str]:
    """List the top N clusters by savings, then stream a Nemotron summary.

    Filters to clusters that aren't review_only (i.e. confirmed trench-share
    + piggyback), sorted by estimated_savings descending. Review-only
    same-street clusters are surfaced as a tail note so judges see they
    exist without conflating them with the savings claim."""
    n = max(1, min(int(n) if n else 5, 25))
    confirmed = [c for c in clusters if not c.get("review_only")]
    confirmed.sort(
        key=lambda c: (c.get("estimated_savings", 0), c.get("permit_count", 0)),
        reverse=True,
    )
    review = [c for c in clusters if c.get("review_only")]

    prefix_lines = [
        f"🔧 Skill: /clusters (top {n})",
        "",
        f"Confirmed trench-share clusters: **{len(confirmed)}**  ·  "
        f"Review-only same-street clusters: **{len(review)}**",
        "",
    ]
    if confirmed:
        prefix_lines.append("Top confirmed clusters:")
        for i, c in enumerate(confirmed[:n], 1):
            members = ", ".join(c.get("member_permit_ids", [])[:3])
            if len(c.get("member_permit_ids", [])) > 3:
                members += f", +{len(c['member_permit_ids']) - 3} more"
            prefix_lines.append(
                f"  {i}. [{c.get('cluster_id','?')}] {c.get('type','?')} "
                f"({c.get('match_type','?')}) — "
                f"{c.get('permit_count','?')} permits, "
                f"saves {c.get('lane_days_saved',0)} lane-days, "
                f"~${c.get('estimated_savings',0):,}"
            )
            prefix_lines.append(f"      members: {members}")
    else:
        prefix_lines.append("No confirmed trench-share clusters in current scope.")
    if review:
        prefix_lines.append("")
        prefix_lines.append(
            f"+ {len(review)} review-only same-street clusters surfaced for the "
            f"city to investigate (not counted in savings)."
        )
    prefix_lines.append("")
    prefix_lines.append("---")
    prefix_lines.append("")
    yield "\n".join(prefix_lines) + "\n"

    confirmed_summary = json.dumps(
        [
            {
                "cluster_id": c.get("cluster_id"),
                "match_type": c.get("match_type"),
                "permit_count": c.get("permit_count"),
                "lane_days_saved": c.get("lane_days_saved"),
                "estimated_savings": c.get("estimated_savings"),
                "members": c.get("member_permit_ids", [])[:5],
            }
            for c in confirmed[:n]
        ],
        indent=2,
    )
    metrics_line = ""
    if metrics:
        metrics_line = (
            f"\n\nHeadline metrics: "
            f"permits_considered={metrics.get('permits_considered')}, "
            f"excavations_avoided={metrics.get('excavations_avoided')}, "
            f"cost_avoidance=${metrics.get('cost_avoidance'):,}, "
            f"coordination_opportunities={metrics.get('coordination_opportunities')}."
        )
    system_msg = (
        "You are PermitFlow's coordination assistant. The user invoked the "
        f"/clusters skill (top {n}). Here are the top confirmed clusters as "
        f"JSON:\n\n{confirmed_summary}{metrics_line}\n\n"
        "Write 2-3 plain sentences highlighting which cluster is most valuable "
        "and why. Reference cluster IDs. Do NOT restate the JSON. Skip pleasantries."
    )
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": f"/clusters {n}"},
    ]
    yield from _stream_ollama_chat(messages, max_tokens=350)


def stream_permit_skill(
    raw_id: str,
    permit_optimized: dict | None,
    permit_naive: dict | None,
    cluster: dict | None,
    conflicts: list[dict],
) -> Iterator[str]:
    """Explain one permit. Streams a structured prefix + a Nemotron summary.

    `permit_optimized` is the permit's row from optimized.json (with cluster /
    conflict_deferred status); `permit_naive` is the same row from naive.json
    (for date-shift comparison); `cluster` is its cluster recommendation if
    any; `conflicts` are graph edges touching this permit."""
    if not permit_optimized:
        yield (
            f"🔧 Skill: /permit\n\n"
            f"No permit matched `{raw_id}` in the optimized timeline.\n"
            f"Try the full ID (road_resurfacing:1007) or just the number (1007)."
        )
        return

    p = permit_optimized
    n = permit_naive or {}
    prefix_lines = [
        f"🔧 Skill: /permit `{p.get('permit_id','?')}`",
        "",
        f"**{p.get('street_name','?')}**",
        f"Work: {p.get('work_type','?')} · Status: {p.get('status','?')} · "
        f"Role: {p.get('role','?')}",
        f"Window: {p.get('start_date','?')} → {p.get('end_date','?')} "
        f"({p.get('lane_days','?')} lane-days)",
        f"Optimization: **{p.get('optimization_status','?')}** "
        f"(cluster={p.get('cluster_id','—')})",
    ]
    # Date-shift vs naive
    if n.get("start_date") and p.get("start_date") and n["start_date"] != p["start_date"]:
        prefix_lines.append(
            f"Schedule shifted: {n['start_date']} → {p['start_date']} "
            f"(originally as-applied; optimizer moved it)"
        )
    if cluster:
        prefix_lines.append("")
        prefix_lines.append(
            f"In cluster [{cluster.get('cluster_id','?')}] "
            f"({cluster.get('match_type','?')}): "
            f"{cluster.get('permit_count','?')} permits, "
            f"saves {cluster.get('lane_days_saved',0)} lane-days, "
            f"~${cluster.get('estimated_savings',0):,}."
        )
    if conflicts:
        prefix_lines.append("")
        prefix_lines.append(f"Top conflict edge(s) ({len(conflicts)} total):")
        for c in conflicts[:3]:
            other = c["permit_b"] if c.get("permit_a") == p.get("permit_id") else c.get("permit_a", "?")
            shared = ", ".join(c.get("shared_streets") or [])
            prefix_lines.append(
                f"  • vs {other} on [{shared}] (score {c.get('conflict_score','?')})"
            )
    prefix_lines.append("")
    prefix_lines.append("---")
    prefix_lines.append("")
    yield "\n".join(prefix_lines) + "\n"

    permit_json = json.dumps(
        {
            "permit": p,
            "naive_window": {
                "start_date": n.get("start_date"),
                "end_date": n.get("end_date"),
            } if n else None,
            "cluster": cluster,
            "conflicts": conflicts[:5],
        },
        indent=2,
        default=str,
    )
    system_msg = (
        "You are PermitFlow's coordination assistant. The user invoked the "
        f"/permit skill on `{p.get('permit_id')}`. Here is everything we know "
        f"about it as JSON:\n\n{permit_json}\n\n"
        "Write 2-3 plain sentences explaining: what this permit is, what the "
        "optimizer decided about it (coordinated / deferred / singleton) and "
        "why. Reference specific dates or other permit IDs from the data. Do "
        "NOT restate the JSON. Skip pleasantries."
    )
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": f"/permit {raw_id}"},
    ]
    yield from _stream_ollama_chat(messages, max_tokens=350)


def stream_chat(
    query: str,
    context_permits: list[dict],
    conflict_edges: list[dict],
    metrics: dict | None,
) -> Iterator[str]:
    """Stream chat completion chunks from Ollama.

    Yields plain text content chunks (the SSE framing is the caller's job).
    On unreachable Ollama / request failure, yields a single human-readable
    fallback string instead of raising.
    """
    messages = build_chat_messages(query, context_permits, conflict_edges, metrics)
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 800,
        "stream": True,
    }

    try:
        response = requests.post(
            OLLAMA_URL,
            json=payload,
            stream=True,
            timeout=120,
        )
        if response.status_code != 200:
            excavations = (metrics or {}).get("excavations_avoided", "n/a")
            yield (
                f"[chat unavailable — Ollama responded {response.status_code}. "
                f"Demo fallback: the optimizer found {excavations} "
                "excavations to avoid on the hero block.]"
            )
            return

        for raw in response.iter_lines():
            if not raw:
                continue
            if not raw.startswith(b"data: "):
                continue
            payload_bytes = raw[len(b"data: "):]
            if payload_bytes.strip() == b"[DONE]":
                break
            try:
                obj = json.loads(payload_bytes.decode("utf-8"))
            except (UnicodeDecodeError, ValueError):
                continue
            try:
                delta = obj["choices"][0].get("delta") or {}
            except (KeyError, IndexError, TypeError):
                continue
            content = delta.get("content")
            if content:
                yield content
    except requests.RequestException:
        excavations = (metrics or {}).get("excavations_avoided", "n/a")
        yield (
            "[chat unavailable — Ollama is offline. "
            f"Demo fallback: the optimizer found {excavations} "
            "excavations to avoid on the hero block.]"
        )
        return
