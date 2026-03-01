import re
from typing import List, Dict, Any

from llm import call_llm
from tools.json_utils import safe_json_load


def discover_additional_risks(store, existing_risks: List[Dict[str, Any]], vector_store=None, k: int = 18):
    """
    Faster open-ended risk discovery:
    - DO NOT send full contract text
    - Send only top relevant clauses based on a generic 'risk' query
    """

    existing_risk_types = sorted(list({
        r.get("risk_type", "") for r in existing_risks if isinstance(r, dict) and r.get("risk_type")
    }))

    # Build smaller context
    if vector_store is not None:
        hits = vector_store.search_with_scores(
            "employment contract risks, unfair terms, penalties, termination, confidentiality, non-compete, damages, liability, arbitration",
            k=k
        )
        context = "\n\n".join([f"[Clause {cid}]\n{txt}" for (cid, txt, _) in hits if isinstance(cid, int)])
    else:
        # fallback: first N clauses
        context = "\n\n".join([c["text"] for c in store.clauses[:k]])

    system_prompt = """
You are a senior employment contract risk analyst.

You will be given:
1) A list of risks already detected
2) A subset of contract clauses (most relevant)

Identify any significant legal risks or unfair provisions NOT already covered.

IMPORTANT:
- Do NOT repeat risks already categorized under:
  Unilateral Termination, Broad Confidentiality, Mandatory Arbitration,
  Non-Compete, Penalty, IP Assignment, Indemnity, Unlimited Liability,
  Discretionary Rights, Notice Imbalance, Governing Law, Automatic Renewal.

Return JSON list with:
[
  {
    "risk_type": "Short label",
    "risk_level": "Low | Medium | High",
    "explanation": "brief explanation",
    "mitigation": "suggested improvement"
  }
]
Return ONLY valid JSON.
"""

    user_prompt = f"""
Already detected risk categories:
{existing_risk_types}

Relevant contract excerpts:
{context}
"""

    response = call_llm(system_prompt=system_prompt, user_prompt=user_prompt)
    response = response.strip()
    response = re.sub(r"^```(?:json)?\s*|\s*```$", "", response).strip()

    try:
        new_risks = safe_json_load(response)
        if not isinstance(new_risks, list):
            return []

        filtered = []
        for r in new_risks:
            if not isinstance(r, dict):
                continue
            rt = r.get("risk_type", "")
            if not rt or rt in existing_risk_types:
                continue
            filtered.append({
                "risk_type": rt,
                "risk_level": r.get("risk_level", "Medium"),
                "explanation": r.get("explanation", ""),
                "mitigation": r.get("mitigation", "")
            })

        return filtered

    except Exception:
        return []