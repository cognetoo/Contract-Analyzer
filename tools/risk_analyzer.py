def analyze_contract_risk(store):
    """
    Analyzes contract clauses and assigns risk score
    """

    risk_score = 0
    findings = []

    confidentiality = store.get_by_type("confidentiality")
    if not confidentiality:
        risk_score+=2
        findings.append("Missing confidentiality clause(High Risk)")

    termination = store.get_by_type("termination")
    if not termination:
        risk_score+=2
        findings.append("Missing termination clause(High Risk)")

    payment = store.get_by_type("payment")
    if not payment:
        risk_score+=1
        findings.append("Missing payment clause(Medium Risk)")

    if risk_score >=4:
        level = "HIGH RISK"
    
    elif risk_score >=2:
        level = "MEDIUM RISK"

    else:
        level = "LOW RISK"

    return {
        "risk_score":risk_score,
        "risk_level":level,
        "findings":findings
    }
