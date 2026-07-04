"""Detection signals.

Each signal takes raw text and returns a dict with a normalized ``confidence``
in [0, 1] where 0 = strongly human and 1 = strongly AI. See
specs/detection_signals.md for the rationale and calibration ranges.
"""

import os
import re
import json

from dotenv import load_dotenv

load_dotenv()

# --- shared helpers ---------------------------------------------------------

_WORD_RE = re.compile(r"[A-Za-z']+")
_PUNCT_RE = re.compile(r"[.,;:!?\"'()\-—…]")

# LLM config
LLM_MODEL = "llama-3.3-70b-versatile"  # larger Groq model = more confident verdicts
LLM_FLOOR, LLM_CEIL = 0.05, 0.95    # clamp so a hallucinated 0/1 leaves room

# TTR calibration (see spec): high diversity -> human, low diversity -> AI
TTR_WINDOW = 200
TTR_HUMAN_AT, TTR_AI_AT = 0.70, 0.45
TTR_HUMAN_CONF, TTR_AI_CONF = 0.20, 0.80

# Punctuation calibration: "suspiciously average" band reads as AI
PUNCT_BAND = (0.06, 0.10)
PUNCT_BAND_CONF, PUNCT_FAR_CONF = 0.65, 0.30
PUNCT_FAR_SPAN = 0.10


def _tokens(text):
    return _WORD_RE.findall(text.lower())


def _clamp(value, low, high):
    return max(low, min(high, value))


# --- signal 1: LLM classifier (primary) -------------------------------------

def signal_llm(text):
    """Ask Groq whether the text reads as machine-generated.

    Returns {"confidence": float, "reason": str}. Degrades to a fully
    uncertain 0.5 if the API call or JSON parse fails, so the pipeline never
    crashes on a bad LLM response.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return {"confidence": 0.5, "reason": "GROQ_API_KEY not set; LLM signal skipped."}

    try:
        from groq import Groq

        client = Groq(api_key=api_key)
        completion = client.chat.completions.create(
            model=LLM_MODEL,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an AI-text detector. Judge whether the user's text "
                        "was written by an AI language model. Reply ONLY with JSON: "
                        '{"confidence": <0.0-1.0>, "reason": "<one sentence>"}. '
                        "confidence is the probability the text is AI-generated "
                        "(1.0 = certainly AI, 0.0 = certainly human)."
                    ),
                },
                {"role": "user", "content": text},
            ],
        )
        raw = completion.choices[0].message.content
        data = json.loads(raw)
        conf = _clamp(float(data.get("confidence", 0.5)), LLM_FLOOR, LLM_CEIL)
        reason = str(data.get("reason", "")).strip() or "No reason provided."
        return {"confidence": conf, "reason": reason}
    except Exception as exc:  # network error, bad JSON, missing field, etc.
        return {"confidence": 0.5, "reason": f"LLM signal failed: {exc}"}


# --- signal 2: type-token ratio ---------------------------------------------

def signal_ttr(text):
    """Vocabulary diversity on a fixed window. Low diversity -> higher AI conf."""
    tokens = _tokens(text)[:TTR_WINDOW]
    if not tokens:
        return {"confidence": 0.5, "ttr": 0.0}

    ttr = len(set(tokens)) / len(tokens)

    if ttr >= TTR_HUMAN_AT:
        conf = TTR_HUMAN_CONF
    elif ttr <= TTR_AI_AT:
        conf = TTR_AI_CONF
    else:  # linear interpolation between the two anchor points
        frac = (ttr - TTR_AI_AT) / (TTR_HUMAN_AT - TTR_AI_AT)
        conf = TTR_AI_CONF + frac * (TTR_HUMAN_CONF - TTR_AI_CONF)

    return {"confidence": round(conf, 4), "ttr": round(ttr, 4)}


# --- signal 3: punctuation density ------------------------------------------

def signal_punctuation(text):
    """Clean/average punctuation reads as AI; extremes read as more human."""
    word_count = len(_tokens(text))
    if word_count == 0:
        return {"confidence": 0.5, "density": 0.0}

    density = len(_PUNCT_RE.findall(text)) / word_count

    low, high = PUNCT_BAND
    if low <= density <= high:
        conf = PUNCT_BAND_CONF
    else:
        dist = (low - density) if density < low else (density - high)
        frac = min(dist / PUNCT_FAR_SPAN, 1.0)
        conf = PUNCT_BAND_CONF - frac * (PUNCT_BAND_CONF - PUNCT_FAR_CONF)

    return {"confidence": round(conf, 4), "density": round(density, 4)}


def token_count(text):
    """Public helper so the pipeline can apply the short-input rule."""
    return len(_tokens(text))