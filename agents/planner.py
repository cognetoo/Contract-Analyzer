from llm import call_llm
from tools.json_utils import safe_json_load
import re

ALLOWED_INTENTS = {
    "qa",
    "summary_only",
    "key_clauses_only",
    "structured_only",
    "unclear_only",
    "lawyer_questions_only",
    "risk_only",
    "full_report",
}

def _extract_mode_tag(raw: str):
    """
    If prompt starts with __MODE__:xyz, return (xyz, remaining_text).
    """
    if not raw:
        return None, raw
    m = re.match(r"^\s*__MODE__\s*:\s*([a-z_]+)\s*\n?(.*)$", raw.strip(), flags=re.I | re.S)
    if not m:
        return None, raw
    mode = (m.group(1) or "").strip().lower()
    rest = (m.group(2) or "").strip()
    if mode in ALLOWED_INTENTS:
        return mode, rest
    return None, raw

def plan(user_query: str) -> dict:
    raw = (user_query or "").strip()

    # 0) HARD OVERRIDE: frontend mode tag wins
    mode, remaining = _extract_mode_tag(raw)
    if mode:
        tool_map = {
            "full_report": "build_full_report",
            "risk_only": "analyze_full_contract_risk",
            "summary_only": "summarize_contract",
            "key_clauses_only": "extract_key_clauses",
            "structured_only": "structured_analysis",
            "unclear_only": "find_unclear_or_missing",
            "lawyer_questions_only": "generate_legal_questions",
            "qa": "qa",
        }
        return {
            "intent": mode,
            "k": 5,
            "steps": [{"tool": tool_map[mode], "args": {}}],
            "notes": "mode_tag_override",
        }
    q = remaining.strip().lower()

    # Deterministic overrides
    if q == "report":
        return {
            "intent": "full_report",
            "k": 5,
            "steps": [{"tool": "build_full_report", "args": {}}],
            "notes": "deterministic_override",
        }

    if "risk" in q:
        return {
            "intent": "risk_only",
            "k": 5,
            "steps": [{"tool": "analyze_full_contract_risk", "args": {}}],
            "notes": "deterministic_override",
        }

    if "summary" in q and "only" in q:
        return {
            "intent": "summary_only",
            "k": 5,
            "steps": [{"tool": "summarize_contract", "args": {}}],
            "notes": "deterministic_override",
        }

    # LLM planner fallback
    system_prompt = """
You are a planning router for a contract-analyzer CLI.

You MUST return a JSON plan with:
- intent
- k
- steps: list of tools to call (in order)

Available tools (exact names):
- summarize_contract
- extract_key_clauses
- structured_analysis
- find_unclear_or_missing
- generate_legal_questions
- analyze_full_contract_risk
- build_full_report
- qa  (means normal Q&A: retrieval + rule_based + fallback LLM)

Allowed intents:
- qa
- summary_only
- key_clauses_only
- structured_only
- unclear_only
- lawyer_questions_only
- risk_only
- full_report

Rules:
- Return ONLY JSON. No markdown.
- Otherwise default qa -> steps=[qa]

Schema:
{
  "intent": "qa",
  "k": 5,
  "steps": [{"tool":"qa","args":{}}],
  "notes": ""
}
"""
    user_prompt = f"User query:\n{raw}\n\nReturn the plan JSON."

    resp = call_llm(system_prompt=system_prompt, user_prompt=user_prompt).strip()
    resp = re.sub(r"^```(?:json)?\s*|\s*```$", "", resp).strip()

    try:
        obj = safe_json_load(resp)
        if not isinstance(obj, dict):
            return {"intent": "qa", "k": 5, "steps": [{"tool": "qa", "args": {}}], "notes": "planner_not_dict"}

        obj.setdefault("intent", "qa")
        obj.setdefault("k", 5)
        obj.setdefault("steps", [{"tool": "qa", "args": {}}])
        obj.setdefault("notes", "")

        if not isinstance(obj["steps"], list) or len(obj["steps"]) == 0:
            obj["steps"] = [{"tool": "qa", "args": {}}]

        return obj
    except Exception:
        return {"intent": "qa", "k": 5, "steps": [{"tool": "qa", "args": {}}], "notes": "planner_parse_error"}