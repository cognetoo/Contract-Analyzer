import re
from typing import List, Dict, Any
from llm import call_llm
from tools.json_utils import safe_json_load 

def discover_additional_risks(store, existing_risks: List[Dict[str, Any]]):
    """
    Open-ended LLM risk discovery.
    Finds risks not covered by predefined templates.
    Returns: List[{risk_type, risk_level, explanation, mitigation}]
    """

    existing_risk_types = sorted(list({r.get("risk_type", "") for r in existing_risks if r.get("risk_type")}))
    full_text = "\n\n".join([c["text"] for c in store.clauses])

    system_prompt = """
You are a senior employment contract risk analyst.

You will be given:
1) A list of risks already detected
2) The full contract text

Identify any significant legal risks or unfair provisions in this contract.

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
The following risks were already detected in this contract:
{existing_risk_types}

Analyze this employment contract:
{full_text}
"""

    response = call_llm(system_prompt=system_prompt, user_prompt=user_prompt)

    # Clean code fences if any
    response = response.strip()
    response = re.sub(r"^```(?:json)?\s*|\s*```$", "", response).strip()

    try:
        new_risks = safe_json_load(response)  
        if not isinstance(new_risks, list):
            return []

        # Deterministic safeguard: remove duplicates / repeated categories
        filtered = []
        for r in new_risks:
            if not isinstance(r, dict):
                continue
            rt = r.get("risk_type", "")
            if not rt or rt in existing_risk_types:
                continue
            # keep only required fields
            filtered.append({
                "risk_type": rt,
                "risk_level": r.get("risk_level", "Medium"),
                "explanation": r.get("explanation", ""),
                "mitigation": r.get("mitigation", "")
            })

        return filtered

    except Exception:
        return []