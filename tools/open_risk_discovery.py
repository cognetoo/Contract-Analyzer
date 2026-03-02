import re
from typing import List, Dict, Any, Optional, Tuple

from llm import call_llm
from tools.json_utils import safe_json_load
from tools.confidence import l2_to_confidence


BLOCKLIST = {
    "Unilateral Termination",
    "Broad Confidentiality",
    "Mandatory Arbitration",
    "Non-Compete Restriction",
    "Penalty / Liquidated Damages",
    "Intellectual Property Assignment",
    "Indemnification Obligation",
    "Unlimited Liability",
    "Discretionary Employer Rights",
    "Notice Period Imbalance",
    "Governing Law / Jurisdiction Risk",
    "Automatic Renewal",
}

def _clean_json(raw: str) -> str:
    raw = (raw or "").strip()
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw).strip()
    return raw

def _cap(s: str, n: int = 700) -> str:
    s = (s or "").strip()
    return s if len(s) <= n else s[:n] + "…"


def discover_additional_risks(
    store,
    existing_risks: List[Dict[str, Any]],
    vector_store=None,
    k: int = 18,
) -> List[Dict[str, Any]]:

    existing_types = sorted({r.get("risk_type", "") for r in (existing_risks or []) if r.get("risk_type")})

    if vector_store is None:
        return []

    DISCOVERY_QUERIES = [
        "unfair obligations or one-sided terms employee must follow penalties",
        "hidden restrictions resignation early termination bond damages section 73 74",
        "employer discretion modify terms from time to time policy unilateral change",
        "liability indemnity unlimited damages employee responsible loss",
        "confidentiality very broad perpetual worldwide trade secrets",
    ]

    seen: set[int] = set()
    picked: List[Tuple[int, str, float]] = []

    # Pulls stronger clauses first 
    for q in DISCOVERY_QUERIES:
        hits = vector_store.search_with_scores(q, k=max(6, k // 2))  
        for cid, txt, dist in hits:
            if not isinstance(cid, int):
                continue
            if cid in seen:
                continue
            seen.add(cid)
            picked.append((cid, txt, float(dist)))

    if not picked:
        return []

    picked.sort(key=lambda x: x[2]) 
    picked = picked[:k]

    evidence = "\n\n".join([f"[Clause {cid}] {_cap(txt, 800)}" for cid, txt, _ in picked])

    system_prompt = """
You are a senior employment contract risk analyst.

You will be given:
1) Risk categories already detected
2) A small set of relevant contract clauses (NOT the full contract)

Task:
Find any additional significant risks / unfair provisions NOT covered by existing categories.

IMPORTANT:
- Do NOT repeat risks already categorized under the blocklist categories.
- Keep answers short and professional.
- Return ONLY valid JSON (no markdown).

Schema:
[
  {
    "risk_type": "Short label",
    "risk_level": "Low | Medium | High",
    "explanation": "brief explanation",
    "mitigation": "suggested improvement",
    "citations": [1,2]
  }
]
"""

    user_prompt = f"""
Already detected risk categories:
{existing_types}

Evidence clauses:
{evidence}

Return 3-6 additional risks max.
"""

    raw = call_llm(system_prompt=system_prompt, user_prompt=user_prompt)
    raw = _clean_json(raw)

    try:
        data = safe_json_load(raw)
        if not isinstance(data, list):
            return []

        out: List[Dict[str, Any]] = []
        for r in data:
            if not isinstance(r, dict):
                continue
            rt = (r.get("risk_type") or "").strip()
            if not rt:
                continue
            if rt in existing_types:
                continue
            if rt in BLOCKLIST:
                continue

            lvl = str(r.get("risk_level", "Medium")).strip().title()
            if lvl not in {"Low", "Medium", "High"}:
                lvl = "Medium"

            citations = r.get("citations", [])
            if not isinstance(citations, list):
                citations = []

            out.append({
                "risk_type": rt,
                "risk_level": lvl,
                "explanation": (r.get("explanation") or "").strip(),
                "mitigation": (r.get("mitigation") or "").strip(),
                "citations": [c for c in citations if isinstance(c, int)],
            })

        return out[:6]

    except Exception:
        return []