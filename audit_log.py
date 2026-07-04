"""Structured audit log (SQLite).

Records every attribution decision with its individual signal scores, and
records appeals by flipping the original row's status to ``under_review`` and
storing the creator's reasoning. See specs/audit_log.md.
"""

import uuid
import sqlite3
from datetime import datetime, timezone

DB_PATH = "audit_log.db"


def _now():
    return datetime.now(timezone.utc).isoformat()


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_log (
                content_id        TEXT PRIMARY KEY,
                creator_id        TEXT,
                timestamp         TEXT,
                text_excerpt      TEXT,
                attribution       TEXT,
                confidence        REAL,
                llm_score         REAL,
                ttr_score         REAL,
                punct_score       REAL,
                label             TEXT,
                status            TEXT,
                appeal_id         TEXT,
                appeal_reasoning  TEXT,
                appeal_timestamp  TEXT
            )
            """
        )


def log_decision(entry):
    """Insert one classification decision. ``entry`` supplies all fields
    except timestamp/status/appeal columns, which are defaulted here."""
    row = {
        "content_id": entry["content_id"],
        "creator_id": entry.get("creator_id"),
        "timestamp": _now(),
        "text_excerpt": entry.get("text_excerpt"),
        "attribution": entry.get("attribution"),
        "confidence": entry.get("confidence"),
        "llm_score": entry.get("llm_score"),
        "ttr_score": entry.get("ttr_score"),
        "punct_score": entry.get("punct_score"),
        "label": entry.get("label"),
        "status": "classified",
        "appeal_id": None,
        "appeal_reasoning": None,
        "appeal_timestamp": None,
    }
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO audit_log VALUES (
                :content_id, :creator_id, :timestamp, :text_excerpt, :attribution,
                :confidence, :llm_score, :ttr_score, :punct_score, :label,
                :status, :appeal_id, :appeal_reasoning, :appeal_timestamp
            )
            """,
            row,
        )
    return row["content_id"]


def get_entry(content_id):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM audit_log WHERE content_id = ?", (content_id,)
        ).fetchone()
    return dict(row) if row else None


def record_appeal(content_id, reasoning):
    """Flip an existing decision to ``under_review`` and attach the appeal.

    Returns the appeal record (with a new appeal_id) or None if the
    content_id doesn't exist.
    """
    if get_entry(content_id) is None:
        return None

    appeal_id = str(uuid.uuid4())
    appeal_timestamp = _now()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            UPDATE audit_log
               SET status = 'under_review',
                   appeal_id = ?,
                   appeal_reasoning = ?,
                   appeal_timestamp = ?
             WHERE content_id = ?
            """,
            (appeal_id, reasoning, appeal_timestamp, content_id),
        )
    return {
        "appeal_id": appeal_id,
        "content_id": content_id,
        "status": "under_review",
        "appeal_timestamp": appeal_timestamp,
    }


def read_log(limit=20):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(row) for row in rows]


def get_appeals():
    """Rows currently under review — the reviewer queue."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM audit_log WHERE status = 'under_review' "
            "ORDER BY appeal_timestamp DESC"
        ).fetchall()
    return [dict(row) for row in rows]