from typing import List
import re

from llm import call_llm
from tools.json_utils import safe_json_load


QUESTION_AREAS = [
    ("payment", "Salary / payment schedule / deductions / penalties"),
    ("termination", "Termination terms / notice / severance / penalties"),
    ("confidentiality", "Confidentiality scope / duration / exceptions"),
    ("non_compete", "Non-compete / non-solicit enforceability"),
    ("ip", "IP ownership / inventions / side projects"),
    ("disputes", "Arbitration / jurisdiction / governing law"),
    ("liability", "Liability / indemnity / damages limits"),
]


def _clean_json(raw: str) -> str:
    raw = (raw or "").strip()
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw).strip()
    return raw


def generate_legal_questions(vector_store, k: int = 2):
    evidence_blocks: List[str] = []

    for key, query in QUESTION_AREAS:
        hits = vector_store.search(query, k=k)  # [(clause_id, clause_text), ...]
        block = "\n\n".join([f"[Clause {cid}] {text[:350]}" for cid, text in hits])
        evidence_blocks.append(f"{key}:\n{block}")

    joined_evidence = "\n\n".join(evidence_blocks)

    system_prompt = """
You are a senior legal advisor.

Rules:
- Use ONLY the provided evidence
- Each item must include: question, reason, citations
- Return ONLY valid JSON (no markdown)

Schema:
[
  {
    "question": "string",
    "reason": "string",
    "citations": [1, 5, 9]
  }
]
"""

    user_prompt = f"""
Evidence:
{joined_evidence}

Return 6 high-value questions (not more).
"""

    raw = call_llm(system_prompt=system_prompt, user_prompt=user_prompt)
    raw = _clean_json(raw)

    try:
        data = safe_json_load(raw)
        return data if isinstance(data, list) else []
    except Exception:
        return {"parse_error": raw}