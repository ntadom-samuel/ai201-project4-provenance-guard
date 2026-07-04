# Spec: Detection Signals

**Implemented in:** `signals.py`

## Purpose

Classify submitted text using **three distinct signals**. Each signal produces a normalized `confidence` in `[0, 1]` where `0 = strongly human` and `1 = strongly AI`. Only the LLM signal reads meaning; the two statistical signals corroborate and act as tie-breakers.

## Shared helpers (`signals.py`)

- `_tokens(text)` — lowercase word tokenizer (`[A-Za-z']+`), used by TTR and punctuation so all signals count words the same way.
- `token_count(text)` — public helper the pipeline uses for the short-input rule (see `confidence_scoring.md`).
- `_clamp(value, low, high)` — bound a value to a range.

## Signals

### 1. LLM classifier — `signal_llm(text) -> {"confidence": float, "reason": str}`

- **Measures:** whether the prose *reads* as machine-generated — fluency, generic phrasing, lack of idiosyncrasy.
- **Implementation:** calls Groq (`groq` package; key loaded from `.env` via `python-dotenv`). Model constant `LLM_MODEL = "llama-3.1-8b-instant"`. Uses `response_format={"type": "json_object"}`, `temperature=0`, and a system prompt instructing the model to return `{"confidence": <0.0-1.0>, "reason": "<one sentence>"}`.
- **Output handling:** parse JSON, clamp `confidence` to `[LLM_FLOOR, LLM_CEIL] = [0.05, 0.95]` so a hallucinated `0.0`/`1.0` still leaves room for the other signals.
- **Failure mode:** any error (missing key, network, unparseable JSON) returns `{"confidence": 0.5, "reason": "..."}` — the pipeline never crashes on a bad LLM response.

### 2. Type-token ratio — `signal_ttr(text) -> {"confidence": float, "ttr": float}`

- **Measures:** vocabulary diversity = `unique_words / total_words`. AI drafts often reuse a narrower vocabulary.
- **Implementation:** computed on a fixed `TTR_WINDOW = 200` tokens (TTR is length-sensitive).
- **Raw → confidence mapping** (low diversity → higher AI confidence):
  - `ttr >= 0.70` (`TTR_HUMAN_AT`) → `0.20` (`TTR_HUMAN_CONF`)
  - `ttr <= 0.45` (`TTR_AI_AT`) → `0.80` (`TTR_AI_CONF`)
  - linear interpolation in between.

### 3. Punctuation density — `signal_punctuation(text) -> {"confidence": float, "density": float}`

- **Measures:** `punct_marks / word_count`. AI text trends toward uniform, textbook punctuation; human creative text is more erratic.
- **Raw → confidence mapping** (distance from a "suspiciously average" band):
  - density inside `PUNCT_BAND = (0.06, 0.10)` → `0.65` (`PUNCT_BAND_CONF`)
  - farther outside the band → decreases linearly toward `0.30` (`PUNCT_FAR_CONF`) over `PUNCT_FAR_SPAN = 0.10`.

## Verification (per AI Tool Plan, M3 + M4)

Call each signal function **directly** (outside the endpoint) on an obvious-AI paragraph and an obvious-human paragraph; confirm each returns a `confidence` in `[0, 1]` pointing the expected direction before wiring into `/submit`. (Done — see the standalone test run in the project notes.)

## Known limitations

- On short samples nearly every word is unique, so **TTR barely discriminates** (both AI and human score ~0.2). This is why the LLM carries 60% of the blend.
- Formal/technical human prose can score falsely high on the statistical signals.
- Short, repetition-heavy poetry drives TTR down and can be flagged as AI.
- Lightly "humanized" AI text can slip under thresholds (false negative).
- Inputs `< MIN_TOKENS` tokens are routed to Uncertain (see `confidence_scoring.md`).