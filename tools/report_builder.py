from tools.summary_engine import summarize_contract
from tools.key_clause_extractor import extract_key_clauses
from tools.structured_analyzer import structured_analysis
from tools.full_risk_engine import analyze_full_contract_risk
from tools.unclear_detector import find_unclear_or_missing
from tools.legal_question_generator import generate_legal_questions

def build_full_report(store, vector_store):
    """
    One-call report builder.
    Returns dict you can print or save as JSON.
    """

    summary = summarize_contract(store)
    key_clauses = extract_key_clauses(store, vector_store, top_k=3)
    print("\nKEY CLAUSES:\n",key_clauses)
    structured = structured_analysis(store, vector_store, k_per_section=5)
    risk_report = analyze_full_contract_risk(store)

    unclear = find_unclear_or_missing(store)
    questions = generate_legal_questions(vector_store, k=4)

    return {
        "summary": summary,
        "key_clauses": key_clauses,
        "structured_analysis": structured,
        "risk_report": risk_report,
        "unclear_or_missing": unclear,
        "questions_to_ask_lawyer": questions,
    }