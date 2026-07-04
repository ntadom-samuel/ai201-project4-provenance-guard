# Spec: Transparency Label

**Implemented in:** `labels.py`

## Purpose

Convert the combined `confidence` and its bucket into plain-language text shown to a non-technical reader. Each variant states the finding, the confidence in plain terms, and that it's an automated estimate. The label **must vary** with the score — never a constant string.

## Interface — `make_label(confidence, attribution) -> str`

Takes the combined `confidence` (float) and the bucket string from `scoring.bucket()`, and returns the matching variant with percentages filled in. The **human** variant reports `1 - confidence` ("confidence this is human"); the other two report `confidence` directly. Percentages use `{value:.0%}`.

## The three variants (verbatim)

### High-confidence AI (`attribution == "likely_ai"`, `confidence >= 0.70`)

> Likely AI-generated. Our automated checks strongly suggest this text was produced with AI assistance (confidence: {confidence:.0%}). This is an automated estimate, not a certainty — the creator can appeal.

### High-confidence human (`attribution == "likely_human"`, `confidence < 0.40`)

> Likely human-written. Our automated checks found little sign of AI generation (confidence this is human: {1-confidence:.0%}). This is an automated estimate, not a guarantee.

### Uncertain (`attribution == "uncertain"`, `0.40 <= confidence < 0.70`, or short-input override)

> Uncertain origin. Our checks were inconclusive for this text (AI-likelihood: {confidence:.0%}). We can't confidently attribute it to a human or AI. Treat this result as a weak signal only.

## Verification (per AI Tool Plan, M5)

Submit inputs that fall in each bucket and confirm all three variants are reachable and the displayed percentage matches the combined score. Confirmed reachable for `likely_ai` (0.85), `uncertain` (0.55), and `likely_human` (0.15) via direct `make_label` calls.