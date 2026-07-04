import uuid

from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from detector import analyze
from audit_log import (
    init_db,
    log_decision,
    record_appeal,
    read_log,
    get_appeals,
)

app = Flask(__name__)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://",
)

init_db()


@app.route("/")
def home():
    return "Provenance Guard is running."


@app.route("/submit", methods=["POST"])
@limiter.limit("10 per minute;100 per day")
def submit():
    data = request.get_json(silent=True) or {}
    text = data.get("text")
    creator_id = data.get("creator_id")

    if not text or not text.strip():
        return jsonify({"error": "Field 'text' is required."}), 400

    result = analyze(text)
    content_id = str(uuid.uuid4())
    signals = result["signals"]

    log_decision(
        {
            "content_id": content_id,
            "creator_id": creator_id,
            "text_excerpt": text[:200],
            "attribution": result["attribution"],
            "confidence": result["confidence"],
            "llm_score": signals["llm"]["confidence"],
            "ttr_score": signals["ttr"]["confidence"],
            "punct_score": signals["punct"]["confidence"],
            "label": result["label"],
        }
    )

    return jsonify(
        {
            "content_id": content_id,
            "creator_id": creator_id,
            "attribution": result["attribution"],
            "confidence": result["confidence"],
            "label": result["label"],
            "signals": signals,
            "short_input": result["short_input"],
        }
    )


@app.route("/appeal", methods=["POST"])
@limiter.limit("5 per minute")
def appeal():
    data = request.get_json(silent=True) or {}
    content_id = data.get("content_id")
    reasoning = data.get("creator_reasoning")

    if not content_id or not reasoning:
        return (
            jsonify({"error": "Fields 'content_id' and 'creator_reasoning' are required."}),
            400,
        )

    appeal_record = record_appeal(content_id, reasoning)
    if appeal_record is None:
        return jsonify({"error": f"No submission found for content_id {content_id}."}), 404

    return jsonify(
        {
            "message": "Appeal received. The content is now under review.",
            **appeal_record,
        }
    )


@app.route("/log", methods=["GET"])
def view_log():
    return jsonify({"entries": read_log()})


@app.route("/appeals", methods=["GET"])
def view_appeals():
    return jsonify({"appeals": get_appeals()})


@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({"error": "Rate limit exceeded.", "detail": str(e.description)}), 429


if __name__ == "__main__":
    app.run(port=5001, debug=True)