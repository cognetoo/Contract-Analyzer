from llm import call_llm
from tools.json_utils import safe_json_load
import re

def plan(user_query: str) -> dict:
    q = user_query.strip().lower()

    # Deterministic overrides
    if q == "report":
        return {
            "intent": "full_report",
            "k": 5,
            "steps": [{"tool": "build_full_report", "args": {}}],
            "notes": "deterministic_override"
        }

    if "risk" in q:
        return {
            "intent": "risk_only",
            "k": 5,
            "steps": [{"tool": "analyze_full_contract_risk", "args": {}}],
            "notes": "deterministic_override"
        }

    if "summary" in q and "only" in q:
        return {
            "intent": "summary_only",
            "k": 5,
            "steps": [{"tool": "summarize_contract", "args": {}}],
            "notes": "deterministic_override"
        }
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
- If user says exactly "report" -> intent=full_report and steps=[build_full_report]
- If user mentions risk/analyze risk -> intent=risk_only and steps=[analyze_full_contract_risk]
- If user asks only summary -> steps=[summarize_contract]
- If user asks only key clauses -> steps=[extract_key_clauses]
- If user asks only structured analysis -> steps=[structured_analysis]
- If user asks unclear/missing -> steps=[find_unclear_or_missing]
- If user asks questions to ask lawyer -> steps=[generate_legal_questions]
- Otherwise default qa -> steps=[qa]

Schema:
{
  "intent": "qa",
  "k": 5,
  "steps": [{"tool":"qa","args":{}}],
  "notes": ""
}
"""

    user_prompt = f"User query:\n{user_query}\n\nReturn the plan JSON."

    raw = call_llm(system_prompt=system_prompt, user_prompt=user_prompt).strip()
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw).strip()

    try:
        obj = safe_json_load(raw)
        if not isinstance(obj, dict):
            return {"intent":"qa","k":5,"steps":[{"tool":"qa","args":{}}],"notes":"planner_not_dict"}

        obj.setdefault("intent","qa")
        obj.setdefault("k",5)
        obj.setdefault("steps",[{"tool":"qa","args":{}}])
        obj.setdefault("notes","")

        # basic sanity
        if not isinstance(obj["steps"], list) or len(obj["steps"]) == 0:
            obj["steps"] = [{"tool":"qa","args":{}}]

        return obj
    except Exception:
        return {"intent":"qa","k":5,"steps":[{"tool":"qa","args":{}}],"notes":"planner_parse_error"}