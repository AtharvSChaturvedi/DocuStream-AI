"""
Heuristic 'IEEE Submission Readiness' analysis.

This is NOT a statistically validated acceptance predictor - no public
dataset of IEEE accept/reject decisions exists (rejected papers are
never published anywhere, so there's nothing to train or calibrate
against). Instead, this evaluates a paper against the criteria IEEE
reviewers actually look for - structure, novelty framing, methodology
rigor, related-work grounding, clarity, evaluation strength, citation
practices - and returns a transparent percentage built from those
per-criterion scores, plus specific, actionable feedback.
"""
import os
import json
import re
from groq import Groq
from app.chroma_client import get_collection

groq_client = Groq(api_key=os.environ["GROQ_API_KEY"])
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")

CRITERIA = [
    "structure_and_formatting",
    "novelty_and_contribution",
    "methodology_rigor",
    "related_work_grounding",
    "clarity_and_writing",
    "results_and_evaluation",
    "citation_practices",
]

CRITERIA_LABELS = {
    "structure_and_formatting": "Structure & Formatting",
    "novelty_and_contribution": "Novelty & Contribution",
    "methodology_rigor": "Methodology Rigor",
    "related_work_grounding": "Related Work Grounding",
    "clarity_and_writing": "Clarity & Writing",
    "results_and_evaluation": "Results & Evaluation",
    "citation_practices": "Citation Practices",
}

SYSTEM_PROMPT = f"""You are an experienced IEEE conference/journal reviewer.
Assess the paper below against these criteria, each scored 0-10:
{", ".join(CRITERIA)}

Be honest and critical, not encouraging by default - most first-draft
papers score in the 4-7 range on most criteria. Base every score
strictly on evidence in the text, not on assumed intent.

Respond with ONLY valid JSON, no markdown fences, no preamble, in this
exact shape:
{{
  "scores": {{"structure_and_formatting": 0, "novelty_and_contribution": 0,
              "methodology_rigor": 0, "related_work_grounding": 0,
              "clarity_and_writing": 0, "results_and_evaluation": 0,
              "citation_practices": 0}},
  "feedback": {{"structure_and_formatting": "one or two sentence justification", "...": "..."}},
  "top_strengths": ["...", "..."],
  "top_improvements": ["...", "..."]
}}
"""


def _get_paper_text(owner_id, paper_id, max_chars=60000):
    """Reconstructs a paper's full text in original order from Chroma."""
    collection = get_collection()
    data = collection.get(
        where={"$and": [{"owner_id": owner_id}, {"paper_id": paper_id}]},
        include=["documents"],
    )
    ids = data.get("ids", [])
    docs = data.get("documents", [])
    if not docs:
        raise ValueError("Paper not found.")

    # ids are formatted "<paper_id>-<chunk_index>" - sort numerically so
    # the reconstructed text follows the paper's original order.
    def chunk_index(item_id):
        try:
            return int(item_id.rsplit("-", 1)[-1])
        except ValueError:
            return 0

    ordered = sorted(zip(ids, docs), key=lambda pair: chunk_index(pair[0]))
    full_text = "\n".join(text for _, text in ordered)
    return full_text[:max_chars]


def check_readiness(owner_id, paper_id, title):
    paper_text = _get_paper_text(owner_id, paper_id)

    completion = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Paper title: {title}\n\nPaper text:\n{paper_text}"},
        ],
        temperature=0.2,
    )
    raw = completion.choices[0].message.content.strip()

    # Models occasionally wrap JSON in markdown fences despite instructions -
    # strip those defensively before parsing.
    raw = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.MULTILINE).strip()

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        raise ValueError(
            "Couldn't parse the reviewer model's response. Try again."
        )

    scores = {c: int(parsed.get("scores", {}).get(c, 0)) for c in CRITERIA}
    total = sum(scores.values())
    max_total = len(CRITERIA) * 10
    readiness_pct = round((total / max_total) * 100) if max_total else 0

    feedback = parsed.get("feedback", {})

    return {
        "readiness_score": readiness_pct,
        "criteria": [
            {
                "key": c,
                "label": CRITERIA_LABELS[c],
                "score": scores[c],
                "feedback": feedback.get(c, ""),
            }
            for c in CRITERIA
        ],
        "top_strengths": parsed.get("top_strengths", []),
        "top_improvements": parsed.get("top_improvements", []),
    }