import json
import os
import re
from typing import Any
import requests

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

SYSTEM_PROMPT = """
You are an intent parser for a customer-support analytics application.
Return ONLY valid JSON. Never return SQL.
Allowed intents and fields:
1) count: filters may include status, priority, category
2) agent_resolved_most: no filters required
3) critical_not_resolved_within: hours (number), default 12
4) average_rating: optional category
5) anomalies: no parameters
6) unresolved_high_priority_older_than: hours (number), default 24
7) list_tickets: optional filters status, priority, category
8) agent_lowest_rating: no filters required

JSON schema:
{"intent":"...","filters":{},"hours":12}
Use null/empty values when a filter is absent.
"""


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.S)
        if not match:
            raise ValueError("LLM did not return JSON")
        return json.loads(match.group(0))


def parse_with_ollama(question: str) -> dict[str, Any]:
    payload = {
        "model": OLLAMA_MODEL,
        "system": SYSTEM_PROMPT,
        "prompt": question,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0}
    }
    response = requests.post(OLLAMA_URL, json=payload, timeout=45)
    response.raise_for_status()
    return _extract_json(response.json().get("response", ""))


def parse_intent(question: str) -> tuple[dict[str, Any], str]:
    try:
        return parse_with_ollama(question), "ollama"
    except Exception:
        # Deterministic fallback keeps the demo usable if Ollama is temporarily unavailable.
        q = question.lower()
        if "open" in q and "how many" in q:
            return {"intent": "count", "filters": {"status": "Open"}}, "fallback"
        if "critical" in q and ("unresolved" in q or "not resolved" in q):
            hours = 12 if "12" in q else 24
            return {"intent": "critical_not_resolved_within", "hours": hours, "filters": {}}, "fallback"
        if "average" in q and "rating" in q:
            category = next((c for c in ["Technical", "Billing", "General"] if c.lower() in q), None)
            return {"intent": "average_rating", "filters": {"category": category}}, "fallback"
        if "lowest" in q and "rating" in q:
            return {"intent": "agent_lowest_rating", "filters": {}}, "fallback"
        if "resolved the most" in q or "most tickets" in q and "agent" in q:
            return {"intent": "agent_resolved_most", "filters": {}}, "fallback"
        if "anomal" in q:
            return {"intent": "anomalies", "filters": {}}, "fallback"
        return {"intent": "list_tickets", "filters": {}}, "fallback"
