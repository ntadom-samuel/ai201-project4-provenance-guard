# Spec: Confidence Scoring & Uncertainty

**Implemented in:** `scoring.py` (blend + buckets) and `detector.py` (orchestration + short-input rule)

## Purpose

Blend the three signals into a single `confidence` score in `[0, 1]` (high = likely AI) and map it to a bucket. The score is an **aggregate heuristic**, not a calibrated statistical probability.

## Combine rule — `combine(llm, ttr, punct) -> float` (`scoring.py`)

```
confidence = 0.60 * llm + 0.20 * ttr + 0.20 * punct   # WEIGHTS in scoring.py
```

Result is clamped to `[0, 1]` and rounded to 4 dp. The LLM carries the majority weight (only semantically-aware signal); TTR + punctuation split the remaining 40% and mostly matter near the middle. `WEIGHTS` lives at the top of `scoring.py` for tuning.

## Buckets — `bucket(confidence) -> str` (`scoring.py`)

Returns one of the module constants `LIKELY_AI` / `UNCERTAIN` / `LIKELY_HUMAN`:

| Combined `confidence` | Constant       | String value    |
| --------------------- | -------------- | --------------- |
| `>= 0.70` (`AI_THRESHOLD`)    | `LIKELY_AI`    | `"likely_ai"`   |
| `0.40 – 0.69`                 | `UNCERTAIN`    | `"uncertain"`   |
| `< 0.40` (`HUMAN_THRESHOLD`)  | `LIKELY_HUMAN` | `"likely_human"`|

## Short-input rule (`detector.py`)

`MIN_TOKENS = 50` (in `scoring.py`). If `token_count(text) < MIN_TOKENS`, the pipeline forces `attribution = "uncertain"` regardless of the raw score and sets `short_input = True` in the result. All signals are still computed and reported.

## Pipeline orchestrator — `analyze(text) -> dict` (`detector.py`)

Runs all three signals, blends them, applies the short-input rule, and generates the label. Returns:

```python
{
  "confidence": float,
  "attribution": "likely_ai" | "uncertain" | "likely_human",
  "label": str,
  "signals": {
    "llm":   {"confidence": float, "reason": str},
    "ttr":   {"confidence": float, "ttr": float},
    "punct": {"confidence": float, "density": float},
  },
  "short_input": bool,
}
```

## Meaning of a score

`confidence = 0.6` means: "signals lean AI, but not decisively — treat as a weak indication." The number surfaced to users is a heuristic, phrased accordingly in the transparency label.

## Verification (per AI Tool Plan, M4)

Feed clearly-AI vs. clearly-human vs. ambiguous text and confirm obvious cases land near the extremes / outer buckets, ambiguous text lands in Uncertain, and `0.51` vs `0.95` produce different labels. Confirmed: driving the LLM signal to 0.9 / 0.5 / 0.1 yields combined 0.74 (`likely_ai`) / 0.50 (`uncertain`) / 0.26 (`likely_human`). Use inputs longer than `MIN_TOKENS` so the short-input rule doesn't override the bucket.