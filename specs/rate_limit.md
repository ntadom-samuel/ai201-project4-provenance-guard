# Spec: Rate Limiting

**Implemented in:** `app.py` (Flask-Limiter, in-memory storage)

## Purpose

Protect the write endpoints — especially `/submit`, which makes a paid, latency-heavy Groq call per request — from abuse and runaway cost.

## Setup (`app.py`)

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    get_remote_address,      # limit key = client IP
    app=app,
    default_limits=[],
    storage_uri="memory://", # required by Flask-Limiter >= 3.x
)
```

## Chosen limits & reasoning

| Endpoint          | Decorator                              | Reasoning                                                             |
| ----------------- | -------------------------------------- | -------------------------------------------------------------------- |
| `POST /submit`    | `@limiter.limit("10 per minute;100 per day")` | Each call hits the LLM. 10/min is generous for a human submitting work; 100/day caps total cost. |
| `POST /appeal`    | `@limiter.limit("5 per minute")`       | Appeals are rare, deliberate actions; a low cap is plenty.           |
| `GET /log`, `GET /appeals` | none                          | Read-only, cheap, no LLM call.                                       |

## Behavior

- Exceeding a limit returns **HTTP 429**. A custom `@app.errorhandler(429)` returns JSON: `{"error": "Rate limit exceeded.", "detail": "<limit description>"}`.
- Counters are in-memory, so **restarting the app resets all limits** (useful during testing — clears the `100 per day` cap too).

## Verification

Fire `/submit` 12 times quickly against the running server (port 5001): requests 1–10 return `200`, requests 11–12 return `429`. Capture the status-code output for the README.

```bash
for i in $(seq 1 12); do
  curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:5001/submit \
    -H "Content-Type: application/json" \
    -d '{"text": "rate limit test with enough words to pass validation here", "creator_id": "ratelimit-test"}'
done
```

> Note: hit port **5001**, not 5000 — on macOS, AirPlay owns 5000 and returns empty `403`s (see `essentials/issues.md`). A real limit rejection is `429`.