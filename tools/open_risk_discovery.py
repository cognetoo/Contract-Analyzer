import json
from llm import call_llm

def discover_additional_risks(store,existing_risks):
    """
    Open-ended LLM risk discovery.
    Finds risks not covered by predefined templates.
    """
    existing_risk_types = list(set([
    r["risk_type"] for r in existing_risks
]))
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

    response = call_llm(system_prompt, user_prompt)

    try:
        new_risks = json.loads(response.strip())

        # Deterministic safeguard
        filtered = [
            r for r in new_risks
            if r["risk_type"] not in existing_risk_types
        ]

        return filtered

    except:
        return []
