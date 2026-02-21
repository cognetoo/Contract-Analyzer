from tools.report_builder import build_full_report
from tools.full_risk_engine import analyze_full_contract_risk

from tools.summary_engine import summarize_contract
from tools.key_clause_extractor import extract_key_clauses
from tools.structured_analyzer import structured_analysis
from tools.unclear_detector import find_unclear_or_missing
from tools.legal_question_generator import generate_legal_questions

from tools.rule_based_qa import rule_based_answer
from tools.llm_qa import answer_with_llm

from tools.formatters import (
    format_summary,
    format_risk_report,
    format_full_report,
    format_lawyer_questions,
    format_key_clauses,
    format_structured_analysis,
    format_unclear,
    format_qa,
)

from tools.confidence import average_confidence, top_confidence, l2_to_confidence


TOOL_REGISTRY = {
    "build_full_report": build_full_report,
    "analyze_full_contract_risk": analyze_full_contract_risk,
    "summarize_contract": summarize_contract,
    "extract_key_clauses": extract_key_clauses,
    "structured_analysis": structured_analysis,
    "find_unclear_or_missing": find_unclear_or_missing,
    "generate_legal_questions": generate_legal_questions,
    "qa": None,
}


def _extract_clause_ids(hits):
    cids = []
    for h in hits:
        if isinstance(h, tuple) and len(h) >= 2:
            cid = h[0]
            if isinstance(cid, int):
                cids.append(cid)
    return sorted(list(set(cids)))


def _run_qa(user_query: str, store, vector_store, k: int):
    hits_scored = vector_store.search_with_scores(user_query, k=k)
    distances = [dist for _, _, dist in hits_scored] if hits_scored else []

    avg_conf = average_confidence(distances)
    best_conf = top_confidence(distances)

    hits = [(cid, txt) for (cid, txt, _) in hits_scored]

    rb = rule_based_answer(user_query, hits)
    if rb and not rb.startswith("NO_RULE_MATCH"):
        conf = min(0.98, max(0.80, best_conf + 0.10))
        return {
            "answer": rb,
            "confidence": round(conf, 3),
            "method": "rule_based",
            "citations": _extract_clause_ids(hits),
            "evidence": [
                {"clause_id": cid, "confidence": round(l2_to_confidence(dist), 3)}
                for (cid, _, dist) in hits_scored
            ]
        }

    ans = answer_with_llm(user_query, hits)

    return {
        "answer": ans,
        "confidence": round(avg_conf, 3),
        "method": "llm",
        "citations": _extract_clause_ids(hits),
        "evidence": [
            {"clause_id": cid, "confidence": round(l2_to_confidence(dist), 3)}
            for (cid, _, dist) in hits_scored
        ]
    }


def execute(plan_obj: dict, user_query: str, store, vector_store):
    plan_obj = plan_obj or {}
    k = plan_obj.get("k", 5)

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
                qa_obj = _run_qa(user_query, store, vector_store, k=k)
                results["qa"] = format_qa(qa_obj)
                continue

            fn = TOOL_REGISTRY[tool]

            if tool == "build_full_report":
                raw = fn(store, vector_store)
                results["full_report"] = format_full_report(raw)

            elif tool == "analyze_full_contract_risk":
                raw = fn(store)
                results["risk_report"] = format_risk_report(raw)

            elif tool == "summarize_contract":
                max_clauses = args.get("max_clauses", 40)
                raw = fn(store, max_clauses=max_clauses)
                results["summary"] = format_summary(raw)

            elif tool == "extract_key_clauses":
                top_k = args.get("top_k", 3)
                raw = fn(store, vector_store, top_k=top_k)
                results["key_clauses"] = format_key_clauses(raw)

            elif tool == "structured_analysis":
                k_per_section = args.get("k_per_section", 5)
                raw = fn(store, vector_store, k_per_section=k_per_section)
                results["structured_analysis"] = format_structured_analysis(raw)

            elif tool == "find_unclear_or_missing":
                raw = fn(store)
                results["unclear_or_missing"] = format_unclear(raw)

            elif tool == "generate_legal_questions":
                qk = args.get("k", 4)
                raw = fn(vector_store, qk)
                results["lawyer_questions"] = format_lawyer_questions(raw)

        if len(results) == 1:
            return next(iter(results.values()))
        return results

    # fallback old intent-based
    intent = plan_obj.get("intent", "qa")

    if intent == "full_report":
        return format_full_report(build_full_report(store, vector_store))

    if intent == "risk_only":
        return format_risk_report(analyze_full_contract_risk(store))

    if intent == "summary_only":
        return format_summary(summarize_contract(store))

    if intent == "key_clauses_only":
        return format_key_clauses(extract_key_clauses(store, vector_store))

    if intent == "structured_only":
        return format_structured_analysis(structured_analysis(store, vector_store))

    if intent == "unclear_only":
        return format_unclear(find_unclear_or_missing(store))

    if intent == "lawyer_questions_only":
        return format_lawyer_questions(generate_legal_questions(vector_store, 4))

    qa_obj = _run_qa(user_query, store, vector_store, k=k)
    return format_qa(qa_obj)