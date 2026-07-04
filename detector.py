"""Detection pipeline orchestrator.

Runs all three signals, blends them into one confidence score, applies the
short-input rule, and produces the transparency label. Returns a single
structured result the endpoint and audit log both consume.
"""

from signals import signal_llm, signal_ttr, signal_punctuation, token_count
from scoring import combine, bucket, UNCERTAIN, MIN_TOKENS
from labels import make_label


def analyze(text):
    """Analyze text and return the full attribution result.

    Shape:
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
    """
    llm = signal_llm(text)
    ttr = signal_ttr(text)
    punct = signal_punctuation(text)

    confidence = combine(llm["confidence"], ttr["confidence"], punct["confidence"])

    # Short-input rule: too little text to trust any signal -> uncertain.
    short_input = token_count(text) < MIN_TOKENS
    attribution = UNCERTAIN if short_input else bucket(confidence)

    label = make_label(confidence, attribution)

    return {
        "confidence": confidence,
        "attribution": attribution,
        "label": label,
        "signals": {"llm": llm, "ttr": ttr, "punct": punct},
        "short_input": short_input,
    }