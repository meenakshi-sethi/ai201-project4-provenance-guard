import uuid
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

import signals
import audit

app = Flask(__name__)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://",
)


@app.route("/submit", methods=["POST"])
@limiter.limit("10 per minute;100 per day")
def submit():
    data = request.get_json(silent=True) or {}
    text = data.get("text", "").strip()
    creator_id = data.get("creator_id", "anonymous")

    if not text:
        return jsonify({"error": "text is required"}), 400

    llm = signals.llm_classify(text)
    stylo = signals.stylo_score(text)
    transition = signals.transition_score(text)
    confidence = signals.combine_scores(llm, stylo, transition)
    attr = signals.attribution(confidence)
    label = signals.make_label(confidence, attr)
    content_id = str(uuid.uuid4())

    audit.log_submission(content_id, creator_id, attr, confidence, llm, stylo, transition)

    return jsonify({
        "content_id": content_id,
        "attribution": attr,
        "confidence": confidence,
        "label": label,
        "signals": {"llm_score": llm, "stylo_score": stylo, "transition_score": transition},
    })


@app.route("/appeal", methods=["POST"])
def appeal():
    data = request.get_json(silent=True) or {}
    content_id = data.get("content_id", "").strip()
    reasoning = data.get("creator_reasoning", "").strip()

    if not content_id or not reasoning:
        return jsonify({"error": "content_id and creator_reasoning are required"}), 400

    found = audit.log_appeal(content_id, reasoning)
    if not found:
        return jsonify({"error": "content_id not found"}), 404

    return jsonify({
        "status": "received",
        "content_id": content_id,
        "message": "Your appeal has been logged and the content is now under review.",
    })


@app.route("/log", methods=["GET"])
def log():
    return jsonify({"entries": audit.get_log()})


@app.route("/analytics", methods=["GET"])
def analytics():
    entries = audit.get_log(limit=1000)
    total = len(entries)
    if total == 0:
        return jsonify({"total_submissions": 0})

    breakdown = {"likely_ai": 0, "uncertain": 0, "likely_human": 0}
    appeals = 0
    confidence_sum = 0.0

    for e in entries:
        breakdown[e.get("attribution", "uncertain")] = breakdown.get(e.get("attribution", "uncertain"), 0) + 1
        if e.get("appeal_reasoning"):
            appeals += 1
        confidence_sum += e.get("confidence", 0)

    return jsonify({
        "total_submissions": total,
        "attribution_breakdown": {
            k: {"count": v, "percent": round(v / total * 100, 1)}
            for k, v in breakdown.items()
        },
        "appeal_rate": round(appeals / total * 100, 1),
        "average_confidence": round(confidence_sum / total, 4),
    })


if __name__ == "__main__":
    app.run(debug=True, port=5001)
