import numpy as np
from sentence_transformers import SentenceTransformer
from llm import call_llm
import json
import json
import re

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


SIMILARITY_THRESHOLD = 0.45


def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def analyze_risks_hybrid(store):
    """
    Production-grade hybrid risk engine:
    - Semantic filtering
    - Single LLM batch evaluation
    """

    risky_candidates = []

    # Embed all templates once
    template_embeddings = {
        name: model.encode(desc)
        for name, desc in RISK_TEMPLATES.items()
    }

    # Scan clauses semantically
    for idx,clause in enumerate(store.clauses):
        clause_text = clause["text"]
        clause_embedding = model.encode(clause_text)

        for risk_name, template_embedding in template_embeddings.items():
            similarity = cosine_similarity(clause_embedding, template_embedding)

            if similarity > SIMILARITY_THRESHOLD:
                risky_candidates.append({
                    "risk_type": risk_name,
                    "clause_id":idx+1,
                    "clause_text": clause_text,
                    "similarity_score": round(float(similarity), 3)
                })

    if not risky_candidates:
        return []


    return evaluate_risks_with_llm(risky_candidates)


def evaluate_risks_with_llm(risky_candidates):
    """
    Single batch LLM evaluation
    """

    formatted_clauses = "\n\n".join([
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

Return a JSON list with this exact structure:

[
  {
    "risk_type": "string",
    "clause_id": integer,
    "clause_text": "original clause text",
    "risk_level": "Low | Medium | High",
    "explanation": "short explanation",
    "mitigation": "suggested improvement",
    "similarity_score": float
  }
]

Return structured output clearly separated for each clause.

Rules:
- Copy clause_id exactly as provided
- Copy clause_text exactly as provided
- Do NOT add markdown
- Do NOT wrap in ```json
- Return ONLY valid JSON
"""

    user_prompt = f"""
Here are potentially risky clauses:

{formatted_clauses}

Provide professional structured risk analysis.
"""

    response = call_llm(system_prompt=system_prompt, user_prompt=user_prompt)

    response = re.sub(r"```json|```", "", response).strip()

    try:
      return json.loads(response)
    except Exception as e:
      print("JSON Parse Error:", e)
      return [
        {
            "risk_type": "LLM Parsing Error",
            "clause_id": -1,
            "clause_text": "Parsing failed",
            "risk_level": "Unknown",
            "explanation": response,
            "mitigation": "Manual review required",
            "similarity_score": "N/A"
        }
    ]