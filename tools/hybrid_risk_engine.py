import re
from typing import List, Dict, Any, Tuple

from llm import call_llm
from tools.json_utils import safe_json_load
from tools.confidence import l2_to_confidence 


RISK_TEMPLATES = {
    "Unilateral Termination":
        "Clause allows one party to terminate without cause, short notice, or gives employer excessive termination discretion.",
    "Penalty / Liquidated Damages":
        "Clause imposes financial penalty, bond amount, or liquidated damages on early termination or breach.",
    "Broad Confidentiality":
        "Confidentiality clause has unlimited scope, worldwide coverage, no time limit, or vague definition of confidential information.",
    "Non-Compete Restriction":
        "Clause restricts employee from working with competitors after employment, possibly unreasonable in duration or geography.",
    "Intellectual Property Assignment":
        "Clause assigns all intellectual property rights to employer, possibly without limitation or compensation.",
    "Mandatory Arbitration":
        "Disputes must be resolved through arbitration instead of courts, possibly limiting legal remedies.",
    "Unlimited Liability":
        "Employee may be liable for unlimited damages, losses, or indemnification obligations.",
    "Indemnification Obligation":
        "Clause requires employee to indemnify employer broadly for losses or third-party claims.",
    "Discretionary Employer Rights":
        "Employer may modify terms, policies, salary, or duties unilaterally without employee consent.",
    "Notice Period Imbalance":
        "Notice period obligations are unequal between employer and employee.",
    "Governing Law / Jurisdiction Risk":
        "Governing law or jurisdiction may disadvantage employee or require distant legal proceedings.",
    "Automatic Renewal":
        "Contract renews automatically unless terminated, possibly locking employee into continued service."
}


def analyze_risks_hybrid(store, vector_store, per_template_k: int = 4, max_candidates: int = 24) -> List[Dict[str, Any]]:
    """
    FAST hybrid risk detection:
    - Use FAISS vector_store retrieval to pick candidate clauses for each risk template
    - Then confirm + grade with LLM

    Returns: List[{risk_type, clause_id, risk_level, explanation, mitigation, similarity_score, confidence}]
    """

    # 1) Retrieve candidates per template using FAISS 
    candidates: List[Dict[str, Any]] = []
    seen: set[Tuple[int, str]] = set()

    for risk_name, desc in RISK_TEMPLATES.items():
        hits_scored = vector_store.search_with_scores(desc, k=per_template_k)  # [(cid, txt, dist), ...]
        for cid, txt, dist in hits_scored:
            if not isinstance(cid, int):
                continue
            key = (cid, risk_name)
            if key in seen:
                continue
            seen.add(key)

            # Turn L2 distance into a 0..1-ish confidence
            conf = float(l2_to_confidence(dist))
            candidates.append({
                "risk_type": risk_name,
                "clause_id": cid,
                "clause_text": txt,
                "similarity_score": round(conf, 3),  
                "_raw_conf": conf,
            })

    # sort strongest first and cap
    candidates.sort(key=lambda x: float(x.get("_raw_conf", 0.0)), reverse=True)
    candidates = candidates[:max_candidates]

    if not candidates:
        return []

    return evaluate_risks_with_llm(candidates)


def evaluate_risks_with_llm(risky_candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    formatted = "\n\n".join([
        f"Clause ID: {r['clause_id']}\n"
        f"Risk Type: {r['risk_type']}\n"
        f"Retrieval Score: {r['similarity_score']}\n"
        f"Clause:\n{r['clause_text']}"
        for r in risky_candidates
    ])

    system_prompt = """
You are a senior legal risk analyst.

Analyze each clause and:
- Confirm whether the risk is valid
- Assign a risk level: Low / Medium / High
- Briefly explain why
- Suggest mitigation if needed

Return a JSON list exactly like:

[
  {
    "risk_type": "string",
    "clause_id": integer,
    "risk_level": "Low | Medium | High",
    "explanation": "short explanation",
    "mitigation": "suggested improvement",
    "similarity_score": float
  }
]

Rules:
- Copy clause_id exactly as provided
- Do NOT add markdown
- Do NOT wrap in ```json
- Return ONLY valid JSON
"""

    user_prompt = f"""
Here are potentially risky clauses:

{formatted}

Provide professional structured risk analysis.
"""

    response = call_llm(system_prompt=system_prompt, user_prompt=user_prompt)
    response = response.strip()
    response = re.sub(r"^```(?:json)?\s*|\s*```$", "", response).strip()

    try:
        parsed = safe_json_load(response)
        if not isinstance(parsed, list):
            raise ValueError("LLM did not return a JSON list")

        lookup: Dict[Tuple[int, str], float] = {}
        for c in risky_candidates:
            lookup[(c.get("clause_id"), c.get("risk_type"))] = float(c.get("_raw_conf", 0.0))

        for r in parsed:
            cid = r.get("clause_id")
            rt = r.get("risk_type")
            base = lookup.get((cid, rt), 0.0)
            # mild bump for higher risk levels
            lvl = str(r.get("risk_level", "Medium")).strip().title()
            mult = 1.0 if lvl == "High" else 0.9 if lvl == "Medium" else 0.8
            r["confidence"] = round(max(0.0, min(base * mult, 1.0)), 3)

            try:
                r["similarity_score"] = float(r.get("similarity_score", base))
            except Exception:
                r["similarity_score"] = float(base)

        return parsed

    except Exception as e:
        print("JSON Parse Error:", e)
        return [{
            "risk_type": "LLM Parsing Error",
            "clause_id": -1,
            "risk_level": "Unknown",
            "explanation": response[:4000],
            "mitigation": "Manual review required",
            "similarity_score": None,
            "confidence": 0.0
        }]