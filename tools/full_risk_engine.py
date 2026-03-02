from tools.hybrid_risk_engine import analyze_risks_hybrid
from tools.risk_analyzer import analyze_contract_risk
from tools.open_risk_discovery import discover_additional_risks


def compute_overall_risk_score(present_risks):
    if not present_risks:
        return 0.0

    weight_map = {"High": 1.0, "Medium": 0.7, "Low": 0.4}
    scores = []
    for r in present_risks:
        level = r.get("risk_level", "Medium")
        conf = r.get("confidence", 0.5)
        weight = weight_map.get(level, 0.7)
        scores.append(weight * conf)

    return round(sum(scores) / len(scores), 3)


def analyze_full_contract_risk(store, vector_store=None):
    """
    FAST:
    - Present risks: FAISS retrieval per template + 1 LLM validation call (small candidates)
    - Missing risks: rule-based
    - Additional risks: LLM on subset clauses only
    """

    if vector_store is None:
        present_risks = []
        missing_risks = analyze_contract_risk(store)
        return {
            "present_risks": present_risks,
            "missing_risks": missing_risks,
            "additional_risks": [],
            "overall_risk_score": 0.0,
            "_meta": {"warning": "vector_store was None; skipped retrieval risks"},
        }

    # Cost Cutting
    present_risks = analyze_risks_hybrid(
        store,
        vector_store,
        per_template_k=2,     # was 4
        max_candidates=12     # was 24
    )

    overall_score = compute_overall_risk_score(present_risks)

    missing_risks = analyze_contract_risk(store)

    additional_risks = discover_additional_risks(
        store,
        existing_risks=present_risks,
        vector_store=vector_store,
        k=10,                 # was 18
    )

    return {
        "present_risks": present_risks,
        "missing_risks": missing_risks,
        "additional_risks": additional_risks,
        "overall_risk_score": overall_score,
        "_meta": {
            "per_template_k": 2,
            "max_candidates": 12,
            "open_discovery_k": 10,
        },
    }