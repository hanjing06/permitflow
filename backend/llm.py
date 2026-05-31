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
    "  /whatif <street>   — Ground the model in our conflict graph for that\n"
    "                       street. Example: /whatif Bridgman Ave\n"
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
