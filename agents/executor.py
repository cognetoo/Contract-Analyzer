from tools.report_builder import build_full_report
from tools.full_risk_engine import analyze_full_contract_risk

from tools.summary_engine import summarize_contract
from tools.key_clause_extractor import extract_key_clauses
from tools.structured_analyzer import structured_analysis
from tools.unclear_detector import find_unclear_or_missing
from tools.legal_question_generator import generate_legal_questions

from tools.rule_based_qa import rule_based_answer
from tools.llm_qa import answer_with_llm


# Map tool name -> callable
TOOL_REGISTRY = {
    "build_full_report": build_full_report,
    "analyze_full_contract_risk": analyze_full_contract_risk,
    "summarize_contract": summarize_contract,
    "extract_key_clauses": extract_key_clauses,
    "structured_analysis": structured_analysis,
    "find_unclear_or_missing": find_unclear_or_missing,
    "generate_legal_questions": generate_legal_questions,
    "qa": None,  # handled specially
}


def _run_qa(user_query: str, store, vector_store, k: int):
    """
    Retrieval + rule-based + fallback LLM QA.
    vector_store.search returns [(clause_id, clause_text), ...]
    """
    hits = vector_store.search(user_query, k=k)

    rb = rule_based_answer(user_query, hits)
    if rb and not rb.startswith("NO_RULE_MATCH"):
        return rb

    return answer_with_llm(user_query, hits)


def execute(plan_obj: dict, user_query: str, store, vector_store):
    """
    Executes a plan produced by planner.

    Supports:
    1) New-style plan: {"steps":[{"tool":"...","args":{...}}, ...], "k":5}
    2) Old-style plan: {"intent":"summary_only", "k":5}
    """
    plan_obj = plan_obj or {}
    k = plan_obj.get("k", 5)

    # NEW: step-based execution 
    steps = plan_obj.get("steps")
    if isinstance(steps, list) and steps:
        results = {}

        for i, step in enumerate(steps):
            tool = (step or {}).get("tool")
            args = (step or {}).get("args") or {}

            if tool not in TOOL_REGISTRY:
                results[f"step_{i}_error"] = f"Unknown tool: {tool}"
                continue

            # Special tool: qa
            if tool == "qa":
                results["qa"] = _run_qa(user_query, store, vector_store, k=k)
                continue

            fn = TOOL_REGISTRY[tool]

            # Dispatch rules
            if tool == "build_full_report":
                results["full_report"] = fn(store, vector_store)

            elif tool == "analyze_full_contract_risk":
                results["risk_report"] = fn(store)

            elif tool == "summarize_contract":
                max_clauses = args.get("max_clauses", 40)
                results["summary"] = fn(store, max_clauses=max_clauses)

            elif tool == "extract_key_clauses":
                top_k = args.get("top_k", 3)
                results["key_clauses"] = fn(store, vector_store, top_k=top_k)

            elif tool == "structured_analysis":
                k_per_section = args.get("k_per_section", 5)
                results["structured_analysis"] = fn(store, vector_store, k_per_section=k_per_section)

            elif tool == "find_unclear_or_missing":
                results["unclear_or_missing"] = fn(store)

            elif tool == "generate_legal_questions":
                qk = args.get("k", 4)
                results["lawyer_questions"] = fn(vector_store, qk)

        # If only one step/tool, return that directly
        if len(results) == 1:
            return next(iter(results.values()))

        return results

    # OLD: intent-based execution
    intent = plan_obj.get("intent", "qa")

    if intent == "full_report":
        return build_full_report(store, vector_store)

    if intent == "risk_only":
        return analyze_full_contract_risk(store)

    if intent == "summary_only":
        return summarize_contract(store)

    if intent == "key_clauses_only":
        return extract_key_clauses(store, vector_store)

    if intent == "structured_only":
        return structured_analysis(store, vector_store)

    if intent == "unclear_only":
        return find_unclear_or_missing(store)

    if intent == "lawyer_questions_only":
        return generate_legal_questions(store, vector_store, k=4)

    # default: QA
    return _run_qa(user_query, store, vector_store, k=k)