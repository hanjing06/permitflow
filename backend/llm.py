import os
import requests

OLLAMA_URL = os.getenv(
    "OLLAMA_URL",
    "http://localhost:11434/v1/chat/completions",
)
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "nemotron-3-super:latest")

SYSTEM_PROMPT = (
    "You are PermitFlow, an infrastructure planning assistant for the City of Toronto. "
    "Be concise. Reply in one short paragraph unless asked otherwise."
)


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


def mock_llm_response(cluster):
    return (
        f"Cluster {cluster['cluster_id']} should be reviewed for consolidation "
        f"because it contains {cluster['permit_count']} nearby road work projects. "
        f"Coordinating them could avoid ~{cluster['road_openings_saved']} separate "
        f"road openings and save an estimated ${cluster['estimated_savings']:,}. "
        f"Main risk is coordination complexity between project owners and contractors. "
        f"Recommended action: assign as {cluster['priority']} priority and compare "
        f"contractor schedules before approving separate closures."
    )


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
