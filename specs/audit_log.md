# Spec: Audit Log

**Implemented in:** `audit_log.py` (SQLite, file `audit_log.db`)

## Purpose

Structured, queryable record of every attribution decision and every appeal, so decisions are reviewable and appeals tie back to the original result. At least **3 entries** must be visible via `GET /log`.

## Storage model

One row per submission (`content_id` is the primary key). An appeal does **not** create a second row — it **updates the original row in place**: flips `status` to `under_review` and fills the appeal columns. This matches the milestone test ("the `/log` entry shows `status: under_review` and `appeal_reasoning` populated").

## Schema (columns)

| Column             | Written on   | Description                                             |
| ------------------ | ------------ | ------------------------------------------------------- |
| `content_id`       | submit       | Primary key; unique id returned by `/submit`            |
| `creator_id`       | submit       | Submitter id                                            |
| `timestamp`        | submit       | ISO-8601 UTC decision time                              |
| `text_excerpt`     | submit       | First 200 chars of the submitted text                   |
| `attribution`      | submit       | `likely_ai` \| `uncertain` \| `likely_human`            |
| `confidence`       | submit       | Combined score `[0, 1]`                                 |
| `llm_score`        | submit       | LLM signal confidence                                   |
| `ttr_score`        | submit       | TTR signal confidence                                   |
| `punct_score`      | submit       | Punctuation signal confidence                           |
| `label`            | submit       | Transparency label text shown to the user               |
| `status`           | submit/appeal| `classified` → `under_review`                           |
| `appeal_id`        | appeal       | Unique id for the appeal (null until appealed)          |
| `appeal_reasoning` | appeal       | Creator's free-text explanation                         |
| `appeal_timestamp` | appeal       | ISO-8601 UTC appeal time                                |

## Interface (`audit_log.py`)

```python
init_db()                          # create table if absent (called at app startup)
log_decision(entry) -> content_id  # insert one classification; status defaults to "classified"
get_entry(content_id) -> dict|None # look up a single row
record_appeal(content_id, reasoning) -> dict|None
                                   # flip status→under_review, set appeal_* cols;
                                   # returns {appeal_id, content_id, status, appeal_timestamp}
                                   # or None if content_id not found
read_log(limit=20) -> list[dict]   # most recent rows (for GET /log)
get_appeals() -> list[dict]        # rows where status == "under_review" (reviewer queue)
```

`log_decision` accepts the signal scores flattened as `llm_score` / `ttr_score` / `punct_score`; `app.py` extracts these from `analyze()`'s nested `signals` dict.

## Note on schema changes

`init_db()` uses `CREATE TABLE IF NOT EXISTS`, so it will **not** migrate an old DB. If the schema changes, delete `audit_log.db` and let it recreate (done once already when moving from the 6-column placeholder schema).

## Verification

Run the M4 score-separation tests so ≥3 decision rows exist, then confirm `GET /log` returns them with full signal breakdowns, and that after an appeal the row shows `status: under_review` + `appeal_reasoning`. Confirmed end-to-end.