# Issues & Solutions

A running log of problems hit during development and how they were resolved.

## 1. `/submit` returned `403 Forbidden` instead of JSON

**Symptom:** `curl` to `http://localhost:5000/submit` returned an empty `403`, and piping to `python -m json.tool` failed (no JSON to parse).

**Cause:** On macOS, the **AirPlay Receiver** service listens on port **5000** and answers requests with an empty `403` (`Server: AirTunes/...`). Our Flask app was never actually being reached.

**How we spotted it:** `curl -i` showed the response header `Server: AirTunes/935.7.1` — not Flask.

**Solution:** Moved the Flask app off port 5000 to **5001** (`app.run(port=5001, debug=True)`) and hit `http://localhost:5001` instead.
_Alternative:_ disable AirPlay Receiver in System Settings → General → AirDrop & Handoff → AirPlay Receiver.

## 2. Port change didn't take effect after editing `app.py`

**Symptom:** Changed the port in `app.py` but the server kept serving on the old port.

**Cause:** The Flask debug auto-reloader does **not** re-run the `app.run(...)` line — that only executes at startup.

**Solution:** Fully stop (Ctrl-C) and restart the server after changing `app.run(...)`.

## 3. Rate-limit test showed all `403`s

**Symptom:** Looping 12 requests to test the `10 per minute` limit returned `403` every time instead of the expected `200 × 10` then `429`.

**Cause:** Same as Issue #1 — the loop was pointed at port **5000** (AirPlay), so the requests never reached Flask's rate limiter.

**Key tell:** A real rate-limit rejection is **`429 Too Many Requests`**, not `403`. Seeing `403` meant AirPlay again.

**Solution:** Re-ran the loop against port **5001**. Expected result: requests 1–10 → `200`, requests 11–12 → `429`.

## Takeaways

- On macOS, avoid port 5000 for local dev servers — AirPlay owns it.
- Use `curl -i` (or `-w "%{http_code}"`) when a piped `json.tool` fails; the status code and `Server` header reveal what actually answered.
- `403` = AirPlay interference; `429` = the real rate limiter; `000` = nothing listening (connection refused).
- Restart the server after changing `app.run(...)` — the reloader won't do it for you.