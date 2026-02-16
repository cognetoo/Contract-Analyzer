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

def generate_legal_questions(store, vector_store, k: int = 4):
    """
    Generate lawyer-style questions based on contract evidence.
    Returns ONLY JSON.
    """

    evidence_blocks = []
    for key, query in QUESTION_AREAS:
        hits = vector_store.search(query, k=k)  # [(clause_id, clause_text), ...]
        # Keep short evidence snippets to reduce tokens
        block = "\n\n".join([f"[Clause {cid}] {text[:600]}" for cid, text in hits])
        evidence_blocks.append(f"## {key}\n{block}")

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
  {
    "question": "string",
    "reason": "string",
    "citations": [1, 5, 9]
  }
]
"""
    joined_evidence = '\n\n'.join(evidence_blocks) 
    user_prompt = f"""
Evidence:
{joined_evidence}

Return 8-10 high-value questions.
"""

    raw = call_llm(system_prompt=system_prompt, user_prompt=user_prompt)

    try:
        return safe_json_load(raw)
    except Exception:
        return {"parse_error": raw}