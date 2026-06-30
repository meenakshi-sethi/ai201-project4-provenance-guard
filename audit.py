import json
import os
from datetime import datetime, timezone

LOG_FILE = os.path.join(os.path.dirname(__file__), "audit_log.json")


def _load() -> list:
    if not os.path.exists(LOG_FILE):
        return []
    with open(LOG_FILE) as f:
        return json.load(f)


def _save(entries: list) -> None:
    with open(LOG_FILE, "w") as f:
        json.dump(entries, f, indent=2)


def log_submission(content_id, creator_id, attribution, confidence, llm_score, stylo_score) -> None:
    entries = _load()
    entries.append({
        "content_id": content_id,
        "creator_id": creator_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "attribution": attribution,
        "confidence": confidence,
        "llm_score": llm_score,
        "stylo_score": stylo_score,
        "status": "classified",
        "appeal_reasoning": None,
    })
    _save(entries)


def log_appeal(content_id, reasoning) -> bool:
    entries = _load()
    for e in entries:
        if e["content_id"] == content_id:
            e["status"] = "under_review"
            e["appeal_reasoning"] = reasoning
            _save(entries)
            return True
    return False


def get_log(limit: int = 20) -> list:
    return _load()[-limit:]


def get_entry(content_id: str) -> dict | None:
    for e in _load():
        if e["content_id"] == content_id:
            return e
    return None
