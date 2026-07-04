"""Milestone 4 verification harness.

Runs the four deliberately-chosen test inputs through the detection pipeline
and prints the per-signal breakdown, combined confidence, bucket, and label.
Use this to confirm scores vary meaningfully across clearly-different inputs
and to capture score-separation evidence for the README.

Run:  python demo_test.py
(Requires GROQ_API_KEY in .env — the LLM signal makes a live API call.)
"""

from detector import analyze
from signals import token_count

CASES = [
    (
        "Clearly AI-generated (expect high)",
        "Artificial intelligence represents a transformative paradigm shift in modern "
        "society. It is important to note that while the benefits of AI are numerous, it "
        "is equally essential to consider the ethical implications. Furthermore, "
        "stakeholders across various sectors must collaborate to ensure responsible "
        "deployment. In conclusion, a balanced and thoughtful approach will be paramount "
        "to navigating the challenges and opportunities that lie ahead for everyone.",
    ),
    (
        "Clearly human-written (expect low)",
        "ok so i finally tried that new ramen place downtown and honestly? underwhelming. "
        "the broth was fine but they put WAY too much sodium in it and i was thirsty for "
        "like three hours after. my friend got the spicy version and said it was better. "
        "probably won't go back unless someone drags me there. also the wait was insane, "
        "like forty minutes on a tuesday?? for that? nah. lesson learned i guess lol",
    ),
    (
        "Borderline: formal human writing (may score mid-high)",
        "The relationship between monetary policy and asset price inflation has been "
        "extensively studied in the literature. Central banks face a fundamental tension "
        "between their mandate for price stability and the unintended consequences of "
        "prolonged low interest rates on equity and real estate valuations. Empirical "
        "evidence remains contested, and reasonable economists continue to disagree over "
        "the magnitude and persistence of these distributional effects across cycles.",
    ),
    (
        "Borderline: lightly edited AI output (expect mid-range)",
        "I've been thinking a lot about remote work lately. There are genuine tradeoffs — "
        "flexibility and no commute on one side, isolation and blurred work-life "
        "boundaries on the other. Studies show productivity varies widely by individual "
        "and role type. Honestly, I don't think there's a one-size-fits-all answer here; "
        "it really depends on the person and the kind of work they actually do day to day.",
    ),
]


def run():
    for title, text in CASES:
        result = analyze(text)
        s = result["signals"]
        print("=" * 78)
        print(title)
        print(f"tokens={token_count(text)}  short_input={result['short_input']}")
        print("-" * 78)
        print(f"  llm   : conf={s['llm']['confidence']:.3f}  ({s['llm']['reason']})")
        print(f"  ttr   : conf={s['ttr']['confidence']:.3f}  (ttr={s['ttr']['ttr']:.3f})")
        print(f"  punct : conf={s['punct']['confidence']:.3f}  (density={s['punct']['density']:.3f})")
        print("-" * 78)
        print(f"  COMBINED confidence = {result['confidence']:.3f}  ->  {result['attribution']}")
        print(f"  LABEL: {result['label']}")
        print()


if __name__ == "__main__":
    run()