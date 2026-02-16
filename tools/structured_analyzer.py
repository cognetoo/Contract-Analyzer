from llm import call_llm
from tools.json_utils import safe_json_load
import re

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
    t = txt.lower()
    return any(k in t for k in COMP_KEYWORDS)


def structured_analysis(store, vector_store, k_per_section: int = 5):
    """
    Returns JSON analysis with citations.
    """
    retrieved = {}
    for key, query in SECTIONS:
        hits = vector_store.search(query, k=k_per_section)
        blocks = []

        for h in hits:
            if isinstance(h, tuple) and len(h) == 2:
                cid, txt = h

                if key == "compensation" and not looks_like_comp(txt):
                    continue

                blocks.append(f"[Clause {cid}] {txt[:1200]}")
            else:
                if key != "compensation":
                    blocks.append(f"[Clause ?] {str(h)[:1200]}")

        if key == "compensation" and not blocks:
            retrieved[key] = "Not found"
        else:
            retrieved[key] = "\n\n".join(blocks) if blocks else "Not found"

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
    return safe_json_load(raw)

    try:
        return safe_json_load(raw)
    except Exception:
        return {"parse_error": raw[:2000]}
