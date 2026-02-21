from tools.hybrid_risk_engine import analyze_risks_hybrid
from tools.risk_analyzer import analyze_contract_risk
from tools.open_risk_discovery import discover_additional_risks

def compute_overall_risk_score(present_risks):
    if not present_risks:
        return 0.0

    weight_map = {
        "High": 1.0,
        "Medium": 0.7,
        "Low": 0.4
    }

    scores = []
    for r in present_risks:
        level = r.get("risk_level", "Medium")
        conf = r.get("confidence", 0.5)
        weight = weight_map.get(level, 0.7)
        scores.append(weight * conf)

    return round(sum(scores) / len(scores), 3)


def analyze_full_contract_risk(store):

    # 1.Template-based present risks
    present_risks = analyze_risks_hybrid(store)
    overall_score = compute_overall_risk_score(present_risks=present_risks)

    # 2️.Missing clause risks
    missing_risks = analyze_contract_risk(store)

    # 3️.Open-ended discovery
    additional_risks = discover_additional_risks(store,present_risks)

    return {
        "present_risks": present_risks,
        "missing_risks": missing_risks,
        "additional_risks": additional_risks,
        "overall_risk_score":overall_score
    }
