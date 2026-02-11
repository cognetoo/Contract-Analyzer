def can_terminate_early(termination_clauses):
    """
    Checks whether early termination is allowed.
    """

    for clause in termination_clauses:
        text = clause.lower()
        if "terminate" in text and (
            "notice" in text
            or "prior" in text
            or "before" in text
            or "early" in text):
          return (
                    "Yes, the contract allows early termination.\n\n"
                    f"Relevant clause:\n{clause}"
                )

    return "No explicit early termination clause was found."
