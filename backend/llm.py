import requests


LOCAL_LLM_URL = "http://localhost:8001/v1/chat/completions"


def build_cluster_prompt(cluster):
    return f"""
You are PermitFlow, an infrastructure planning assistant for the City of Toronto.

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

Keep it practical and decision-focused.
"""


def mock_llm_response(cluster):
    return f"""
Cluster {cluster["cluster_id"]} should be reviewed for consolidation because it contains {cluster["permit_count"]} nearby road work projects.

The main benefit is reducing repeated disruption. If coordinated, this cluster could avoid approximately {cluster["road_openings_saved"]} separate road openings and save an estimated ${cluster["estimated_savings"]:,}.

The main risk is coordination complexity between project owners, contractors, and construction timelines.

Recommended next action: assign this as a {cluster["priority"]} priority review item and compare contractor schedules before approving separate closures.
"""


def ask_local_llm(prompt):
    response = requests.post(
        LOCAL_LLM_URL,
        json={
            "model": "nemotron",
            "messages": [
                {
                    "role": "system",
                    "content": "You are PermitFlow, an infrastructure planning assistant."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.2
        },
        timeout=60
    )

    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]
