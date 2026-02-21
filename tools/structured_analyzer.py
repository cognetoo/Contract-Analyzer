from llm import call_llm
from tools.json_utils import safe_json_load
import re
from tools.confidence import average_confidence

SECTIONS = [
    ("parties", "Identify parties (Employer / Employee), roles, and relationship"),
    ("term", "Contract term / duration / start date / probation"),
    ("compensation", "salary CTC compensation wages bonus allowance deduction PF ESI reimbursement"),
    ("penalties", "penalty liquidated damages bond 2 lakhs compensation clause damages section 73 74"),
    ("termination", "Termination rights, notice, severance, penalties"),
    ("confidentiality", "Confidentiality scope, duration, exceptions"),
    ("non_compete", "Non-compete / non-solicit restrictions (scope/duration/geo)"),
    ("ip", "IP assignment, inventions, source code ownership"),
    ("disputes", "Dispute resolution, arbitration, governing law, jurisdiction"),
    ("other_red_flags", "Any other obligations that look risky/unfair"),
]

COMP_KEYWORDS = [
    "salary", "ctc", "remuneration", "wage", "stipend", "pay", "payable",
    "allowance", "bonus", "deduction", "payslip", "inr", "₹", "rs", "rupees",
    "pf", "esi", "tds", "hra", "lta", "reimbursement"
]


def looks_like_comp(txt: str) -> bool:
    t = (txt or "").lower()
    return any(k in t for k in COMP_KEYWORDS)


def structured_analysis(store, vector_store, k_per_section: int = 5):
    retrieved = {}
    section_conf_map = {}

    for key, query in SECTIONS:
        hits = vector_store.search_with_scores(query, k=k_per_section)  # [(cid, txt, dist), ...]
        distances = [dist for _, _, dist in hits] if hits else []
        section_conf = average_confidence(distances)  # 0..1
        section_conf_map[key] = round(float(section_conf), 3)

        blocks = []
        for cid, txt, dist in hits:
            if key == "compensation" and not looks_like_comp(txt):
                continue
            blocks.append(f"[Clause {cid}] {txt[:1200]}")

        evidence = "\n\n".join(blocks) if blocks else "Not found"

        if key == "compensation" and not blocks:
            evidence = "Not found"

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

Important mapping rules:
- "non_compete" section MUST be based only on clauses that mention competing / restraint (e.g., non-compete).
- "client / customer contact / solicitation" MUST go under penalties or liability (or a separate "non_solicit" section) and cite Clause 11.
- Do not cite a clause unless that clause text directly supports the sentence.

Schema:
{
  "parties": {"answer": "...", "citations": [1,2]},
  ...
  "other_red_flags": [
    {"issue": "...", "citations": [4]},
    {"issue": "...", "citations": [13]}
  ]
}
"""

    user_prompt = f"""
Retrieved evidence per section:
{retrieved}

Create a structured contract analysis following the schema.
"""

    raw = call_llm(system_prompt=system_prompt, user_prompt=user_prompt)
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw).strip()

    obj = safe_json_load(raw)

    overall_conf = round(sum(section_conf_map.values()) / max(1, len(section_conf_map)), 3)

    if isinstance(obj, dict):
        obj["_meta"] = {
            "section_confidence": section_conf_map,
            "overall_confidence": overall_conf
        }

    return obj