from llm import call_llm
from tools.json_utils import safe_json_load
import re

def summarize_contract(store,max_clauses : int = 40):
    """
    Produces a grounded summary using clause citations.
    Returns dict: {summary, bullets, key_citations}
    """

    clauses = store.clauses[:max_clauses]

    context = "\n\n".join(
        [f"[Clause {c['clause_id']}] {c['text']}" for c in clauses]
    )


    system_prompt = """
You are a legal contract summarizer.

Rules:
- Summarize ONLY from provided clauses
- Include clause citations like [Clause 12]
- Return ONLY valid JSON (no markdown,no triple backticks)

JSON schema:
{
  "summary": "short paragraph",
  "bullets": ["..."],
  "key_citations": [12, 5, 9]
}   
"""

    user_prompt = f"""
Contract clauses:
{context}

Create a clear executive summary + 5-10 bullet points.
"""
    
    raw = call_llm(system_prompt=system_prompt, user_prompt=user_prompt)
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw).strip()
    return safe_json_load(raw)

    try:
        return safe_json_load(raw)
    except Exception:
        # fallback
        return {"parse_error": raw}