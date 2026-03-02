from llm import call_llm
from tools.json_utils import safe_json_load
import re
from tools.confidence import average_confidence

SECTIONS = [
    ("parties", "Identify parties (Employer / Employee), roles, and relationship"),
    ("term", "Contract term / duration / start date / probation"),
    ("compensation", "salary CTC compensation wages bonus allowance deduction PF ESI reimbursement"),
    ("penalties", "penalty liquidated damages bond compensation clause damages section 73 74"),
    ("termination", "Termination rights, notice, severance, penalties"),
    ("confidentiality", "Confidentiality scope, duration, exceptions"),
    ("non_compete", "Non-compete / non-solicit restrictions (scope/duration/geo)"),
    ("ip", "IP assignment, inventions, source code ownership"),
    ("disputes", "Dispute resolution, arbitration, governing law, jurisdiction"),
    ("other_red_flags", "Any other obligations that look risky/unfair"),
]

COMP_KEYWORDS = [
    "salary","ctc","remuneration","wage","stipend","pay","payable",
    "allowance","bonus","deduction","payslip","inr","₹","rs","rupees",
    "pf","esi","tds","hra","lta","reimbursement"
]

def looks_like_comp(txt: str) -> bool:
    t = (txt or "").lower()
    return any(k in t for k in COMP_KEYWORDS)

def _clean(raw: str) -> str:
    raw = (raw or "").strip()
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw).strip()
    return raw

def structured_analysis(store, vector_store, k_per_section: int = 3):
    retrieved = {}
    section_conf_map = {}

    for key, query in SECTIONS:
        hits = vector_store.search_with_scores(query, k=k_per_section)  # [(cid, txt, dist), ...]
        distances = [dist for _, _, dist in hits] if hits else []
        section_conf = average_confidence(distances) if distances else 0.0
        section_conf_map[key] = round(float(section_conf), 3)

        blocks = []
        for cid, txt, dist in hits:
            if key == "compensation" and not looks_like_comp(txt):
                continue
            blocks.append(f"[Clause {cid}] {txt[:600]}")

        evidence = "\n\n".join(blocks) if blocks else "Not found"
        retrieved[key] = evidence

    system_prompt = """
You are a legal structured analyst.

Rules:
- Use ONLY provided retrieved clauses
- If info not found, write "Not found"
- Always cite with [Clause N]
- Return ONLY valid JSON (no markdown)
- If a section is "Not found", output:
  {"answer":"Not found","citations":[]}
- Do NOT cite clauses unless they directly contain the information.

Schema:
{
  "parties": {"answer": "...", "citations": [1,2]},
  ...
  "other_red_flags": [
    {"issue": "...", "citations": [4]}
  ]
}
"""

    user_prompt = f"""
Retrieved evidence per section:
{retrieved}

Create a structured contract analysis following the schema.
Keep answers concise.
"""

    raw = call_llm(system_prompt=system_prompt, user_prompt=user_prompt)
    raw = _clean(raw)

    obj = safe_json_load(raw)

    overall_conf = round(sum(section_conf_map.values()) / max(1, len(section_conf_map)), 3)
    if isinstance(obj, dict):
        obj["_meta"] = {"section_confidence": section_conf_map, "overall_confidence": overall_conf}

    return obj