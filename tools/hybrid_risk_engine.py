import re
import numpy as np
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer

from llm import call_llm
from tools.json_utils import safe_json_load

model = SentenceTransformer("all-MiniLM-L6-v2")

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

SIMILARITY_THRESHOLD = 0.55

RISK_LEVEL_WEIGHT = {
    "High": 1.00,
    "Medium": 0.85,
    "Low": 0.70
}


def _threshold_penalty(sim: float) -> float:
    # map sim from [threshold..1] -> [0.85..1.0]
    if sim <= SIMILARITY_THRESHOLD:
        return 0.85
    span = 1.0 - SIMILARITY_THRESHOLD
    if span <= 0:
        return 0.85
    ratio = min(max((sim - SIMILARITY_THRESHOLD) / span, 0.0), 1.0)
    return 0.85 + 0.15 * ratio


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def analyze_risks_hybrid(store) -> List[Dict[str, Any]]:
    risky_candidates: List[Dict[str, Any]] = []
    template_embeddings = {name: model.encode(desc) for name, desc in RISK_TEMPLATES.items()}

    for clause in store.clauses:
        clause_text = clause["text"]
        clause_embedding = model.encode(clause_text)

        for risk_name, template_embedding in template_embeddings.items():
            sim = cosine_similarity(clause_embedding, template_embedding)
            if sim >= SIMILARITY_THRESHOLD:
                risky_candidates.append({
                    "risk_type": risk_name,
                    "clause_id": clause.get("clause_id", -1),
                    "clause_text": clause_text,
                    "similarity_score": round(sim, 3),
                    "_raw_similarity": float(sim),
                })

    if not risky_candidates:
        return []

    return evaluate_risks_with_llm(risky_candidates)


def evaluate_risks_with_llm(risky_candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    formatted = "\n\n".join([
        f"Clause ID: {r['clause_id']}\n"
        f"Risk Type: {r['risk_type']}\n"
        f"Similarity Score: {r['similarity_score']}\n"
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

        # lookup similarity from candidates
        sim_lookup: Dict[tuple, float] = {}
        for c in risky_candidates:
            key = (c.get("clause_id"), c.get("risk_type"))
            sim_lookup[key] = float(c.get("_raw_similarity", c.get("similarity_score", 0.0)))

        for r in parsed:
            key = (r.get("clause_id"), r.get("risk_type"))
            sim = sim_lookup.get(key, 0.0)

            level = str(r.get("risk_level", "Medium")).strip().title()
            weight = RISK_LEVEL_WEIGHT.get(level, 0.80)

            penalty = _threshold_penalty(sim)
            conf = sim * weight * penalty
            conf = max(0.0, min(conf, 1.0))

            r["similarity_score"] = round(float(r.get("similarity_score", sim)), 3)
            r["confidence"] = round(conf, 3)

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