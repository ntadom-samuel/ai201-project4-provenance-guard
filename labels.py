"""Transparency labels — plain-language text shown to readers.

The three variants are verbatim from planning.md / specs/transparency_label.md.
The label MUST change with the confidence score, never a constant string.
"""

from scoring import LIKELY_AI, LIKELY_HUMAN


def make_label(confidence, attribution):
    """Return the reader-facing label string for a given score + bucket.

    Note: the human variant reports ``1 - confidence`` ("confidence this is
    human"); the other two report ``confidence`` directly.
    """
    if attribution == LIKELY_AI:
        return (
            f"Likely AI-generated. Our automated checks strongly suggest this "
            f"text was produced with AI assistance (confidence: {confidence:.0%}). "
            f"This is an automated estimate, not a certainty — the creator can appeal."
        )
    if attribution == LIKELY_HUMAN:
        return (
            f"Likely human-written. Our automated checks found little sign of AI "
            f"generation (confidence this is human: {1 - confidence:.0%}). "
            f"This is an automated estimate, not a guarantee."
        )
    return (
        f"Uncertain origin. Our checks were inconclusive for this text "
        f"(AI-likelihood: {confidence:.0%}). We can't confidently attribute it to a "
        f"human or AI. Treat this result as a weak signal only."
    )
