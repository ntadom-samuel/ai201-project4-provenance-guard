"""Confidence scoring: blend the three signals and bucket the result.

See specs/confidence_scoring.md. The score is an aggregate heuristic, not a
calibrated statistical probability.
"""

# LLM-dominant blend; weights live here so they can be tuned in one place.
WEIGHTS = {"llm": 0.60, "ttr": 0.20, "punct": 0.20}

# Bucket thresholds
AI_THRESHOLD = 0.70       # >= this -> likely AI
HUMAN_THRESHOLD = 0.40    # < this  -> likely human; between -> uncertain

# Inputs shorter than this are statistically unstable -> forced to uncertain.
MIN_TOKENS = 50

LIKELY_AI = "likely_ai"
UNCERTAIN = "uncertain"
LIKELY_HUMAN = "likely_human"


def combine(llm, ttr, punct):
    """Weighted average of the three normalized signal confidences."""
    score = WEIGHTS["llm"] * llm + WEIGHTS["ttr"] * ttr + WEIGHTS["punct"] * punct
    return round(max(0.0, min(1.0, score)), 4)


def bucket(confidence):
    """Map a combined confidence to an attribution bucket."""
    if confidence >= AI_THRESHOLD:
        return LIKELY_AI
    if confidence < HUMAN_THRESHOLD:
        return LIKELY_HUMAN
    return UNCERTAIN