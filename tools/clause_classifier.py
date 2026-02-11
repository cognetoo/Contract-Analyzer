from llm import call_llm
CLAUSE_TYPES = {
    "termination": ["terminate", "termination", "cancel", "end this agreement"],
    "payment": ["payment", "fee", "compensation", "invoice", "charges"],
    "liability": ["liability", "indemnify", "damages", "loss"],
    "confidentiality": ["confidential", "non-disclosure", "nda"],
    "governing_law": ["governing law", "jurisdiction", "court"],
}

def classify_clause_rule_based(clause:str):
    clause_lower = clause.lower()
    for clause_type,keywords in CLAUSE_TYPES.items():
        for keyword in keywords:
            if keyword in clause_lower:
                return clause_type
            
    return "unknown"


def classify_clause_llm(clause:str):
    system_prompt = """
     You are a legal assistant.
     Classify the clauses into one category:
    termination,payment,liability,confidentiality,governing_law,other.
    Return only the category
"""
    user_prompt = clause
    response = call_llm(system_prompt=system_prompt,user_prompt=user_prompt)

    return response.strip().lower()

def classify_clause(clause:str):
    rule_result = classify_clause_rule_based(clause)
    if rule_result != "unknown":
        return rule_result
    
    return classify_clause_llm(clause)