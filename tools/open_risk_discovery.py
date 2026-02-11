import json
from llm import call_llm

def discover_additional_risks(store):
    """
    Open-ended LLM risk discovery.
    Finds risks not covered by predefined templates.
    """

    full_text = "\n\n".join([c["text"] for c in store.clauses])

    system_prompt = """
You are a senior employment contract risk analyst.

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
Analyze this employment contract:

{full_text}
"""

    response = call_llm(system_prompt, user_prompt)

    try:
        return json.loads(response.strip())
    except:
        return []
