from tools.report_builder import build_full_report
from tools.full_risk_engine import analyze_full_contract_risk

from tools.summary_engine import summarize_contract
from tools.key_clause_extractor import extract_key_clauses
from tools.structured_analyzer import structured_analysis
from tools.unclear_detector import find_unclear_or_missing
from tools.legal_question_generator import generate_legal_questions

from tools.rule_based_qa import rule_based_answer
from tools.llm_qa import answer_with_llm

from tools.confidence import average_confidence, top_confidence, l2_to_confidence


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


def _extract_clause_ids(hits):
    """
    hits: List[(clause_id, text)]
    """
    cids = []
    for h in hits:
        if isinstance(h, tuple) and len(h) >= 2:
            cid = h[0]
            if isinstance(cid, int):
                cids.append(cid)
    return sorted(list(set(cids)))


def _run_qa(user_query: str, store, vector_store, k: int):
    """
    RAW QA result (JSON-friendly):
    {
      "answer": "...",
      "confidence": 0.0..1.0,
      "method": "rule_based" | "llm",
      "citations": [clause_ids...],           # filtered for strength
      "evidence": [{"clause_id": id, "confidence": 0..1}, ...]
    }
    """
    hits_scored = vector_store.search_with_scores(user_query, k=k)  # [(cid, txt, dist), ...]

    distances = [dist for _, _, dist in hits_scored] if hits_scored else []
    avg_conf = average_confidence(distances) if distances else 0.0
    best_conf = top_confidence(distances) if distances else 0.0

    hits = [(cid, txt) for (cid, txt, _) in hits_scored]

    evidence = [
        {"clause_id": cid, "confidence": round(l2_to_confidence(dist), 3)}
        for (cid, _, dist) in hits_scored
    ]

    # Only citing clauses with reasonably strong evidence
    CITE_THRESHOLD = 0.55
    strong_cites = sorted({
        e["clause_id"] for e in evidence
        if isinstance(e.get("clause_id"), int) and (e.get("confidence") or 0) >= CITE_THRESHOLD
    })

    # 1. Rule-based first
    rb = rule_based_answer(user_query, hits)
    if rb and not rb.startswith("NO_RULE_MATCH"):
        conf = min(0.98, max(0.80, best_conf + 0.10))
        return {
            "answer": rb,
            "confidence": round(conf, 3),
            "method": "rule_based",
            "citations": strong_cites,  
            "evidence": evidence
        }

    # 2. LLM fallback
    ans = answer_with_llm(user_query, hits)

    ans_norm = str(ans).strip().lower()
    if ans_norm in {"not found", "not found."}:
        citations = []
    else:
        citations = strong_cites

    return {
        "answer": ans,
        "confidence": round(avg_conf, 3),
        "method": "llm",
        "citations": citations,
        "evidence": evidence
    }


def execute(plan_obj: dict, user_query: str, store, vector_store):
    """
    Executes a plan produced by planner.

    Supports:
    1) New-style plan: {"steps":[{"tool":"...","args":{...}}, ...], "k":5}
    2) Old-style plan: {"intent":"summary_only", "k":5}

    IMPORTANT: This executor returns RAW results (dict/list/str), no pretty formatting.
    Formatting belongs in CLI only (not API).
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

            if tool == "qa":
                results["qa"] = _run_qa(user_query, store, vector_store, k=k)
                continue

            fn = TOOL_REGISTRY[tool]

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

        if len(results) == 1:
            return next(iter(results.values()))
        return results

    # OLD: intent-based execution (RAW)
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
        return generate_legal_questions(vector_store, 4)

    # default: QA
    return _run_qa(user_query, store, vector_store, k=k)
