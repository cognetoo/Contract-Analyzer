def route_question(question: str) -> str:
    """
    Routes question to a specific clause type.
    Returns:
        - "termination"
        - "payment"
        - "confidentiality"
        - "general"
    """

    q = question.lower()

    if any(word in q for word in ["terminate", "termination", "end contract", "early termination"]):
        return "termination"

    if any(word in q for word in ["payment", "salary", "compensation", "fee", "remuneration"]):
        return "payment"

    if any(word in q for word in ["confidential", "nda", "non disclosure", "secrecy"]):
        return "confidentiality"

    return "general"
