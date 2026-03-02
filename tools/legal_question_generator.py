import re
from llm import call_llm
from tools.json_utils import safe_json_load


QUESTION_AREAS = [
    ("payment", "salary CTC compensation pay wages bonus allowance deduction PF ESI reimbursement"),
    ("termination", "termination notice resignation severance bond liquidated damages"),
    ("confidentiality", "confidentiality NDA trade secrets duration exceptions"),
    ("non_compete", "non compete non solicit restraint competitor client solicitation"),
    ("ip", "intellectual property inventions source code ownership"),
    ("disputes", "arbitration dispute resolution jurisdiction governing law"),
    ("liability", "liability indemnity damages limits employee responsible loss"),
]

def _clean(raw: str) -> str:
    raw = (raw or "").strip()
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw).strip()
    return raw

def generate_legal_questions(vector_store, k: int = 3):
    evidence_blocks = []

    for key, query in QUESTION_AREAS:
        hits = []
        if hasattr(vector_store, "search_with_scores"):
            hits = vector_store.search_with_scores(query, k=k)
            block = "\n\n".join([f"[Clause {cid}] {text[:450]}" for cid, text, _ in hits])
        else:
            hits = vector_store.search(query, k=k)  
            block = "\n\n".join([f"[Clause {cid}] {text[:450]}" for cid, text in hits])

        evidence_blocks.append(f"## {key}\n{block if block else 'Not found'}")

    system_prompt = """
You are a senior legal advisor.

Task:
Generate the most important questions the user should ask a lawyer before signing.

Rules:
- Use ONLY the provided evidence
- Each question must include a short reason
- Add citations as clause IDs used to form that question
- Return ONLY valid JSON (no markdown)

Schema:
[
  {"question":"string","reason":"string","citations":[1,5]}
]
"""

    user_prompt = f"""
Evidence:
{'\n\n'.join(evidence_blocks)}

Return 6-8 high-value questions (not more).
"""

    raw = call_llm(system_prompt=system_prompt, user_prompt=user_prompt)
    raw = _clean(raw)

    try:
        return safe_json_load(raw)
    except Exception:
        return {"parse_error": raw}