from tools.hybrid_risk_engine import analyze_risks_hybrid
from tools.risk_analyzer import analyze_contract_risk
from tools.open_risk_discovery import discover_additional_risks

def analyze_full_contract_risk(store):

    # 1️⃣ Template-based present risks
    present_risks = analyze_risks_hybrid(store)

    # 2️⃣ Missing clause risks
    missing_risks = analyze_contract_risk(store)

    # 3️⃣ Open-ended discovery
    additional_risks = discover_additional_risks(store,present_risks)

    return {
        "present_risks": present_risks,
        "missing_risks": missing_risks,
        "additional_risks": additional_risks
    }
