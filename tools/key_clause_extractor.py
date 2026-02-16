from typing import Dict, List
from llm import call_llm
from tools.json_utils import safe_json_load

KEY_TOPICS = [
    ("termination", "Termination / exit / resignation / notice"),
    ("payment", "salary CTC compensation pay wages bonus allowance deduction PF ESI reimbursement"),
    ("confidentiality", "Confidentiality / NDA / trade secrets"),
    ("non_compete", "Non-compete / non-solicit / restraint"),
    ("ip", "Intellectual property / inventions / source code ownership"),
    ("dispute", "Dispute resolution / arbitration / jurisdiction"),
    ("liability", "Liability / damages / indemnity"),
    ("other_important", "Important obligations, penalties, restrictions, unusual terms, red flags"),
]


PAYMENT_KEYWORDS = [
    "salary", "ctc", "remuneration", "wage", "stipend", "payable",
    "allowance", "bonus", "deduction", "payslip", "inr", "₹", "rs.", "rupees"
]

def looks_like_payment(txt: str) -> bool:
    t = txt.lower()
    return any(k in t for k in PAYMENT_KEYWORDS)

# Tune this based on your distance scale (L2 distance for FAISS flat L2)
# Lower distance = closer match
DEFAULT_MAX_DIST = 1.20
PAYMENT_MAX_DIST = 1.10


def extract_key_clauses(store, vector_store, top_k: int = 3) -> Dict[str, List[dict]]:
    """
    Returns dict: topic -> list of {clause_id, clause_text}
    Assumes vector_store.search_with_scores(query,k) returns:
      List[ (clause_id, clause_text, dist) ]   OR
      List[ (clause_text, dist) ] (fallback supported)
    """

    results: Dict[str, List[dict]] = {}

    for key, query in KEY_TOPICS:
       
        hits = []
        if hasattr(vector_store, "search_with_scores"):
            hits = vector_store.search_with_scores(query, k=top_k * 5)
        else:
            # fallback
            raw_hits = vector_store.search(query, k=top_k)
            results[key] = [{"clause_id": None, "clause_text": h} for h in raw_hits]
            continue

        picked: List[dict] = []

        # Filtering rules
        max_dist = PAYMENT_MAX_DIST if key == "payment" else DEFAULT_MAX_DIST

        for h in hits:
            clause_id = None
            clause_text = None
            dist = None

            # Accept both formats:
            # (clause_id, clause_text, dist)
            # OR (clause_text, dist)
            if isinstance(h, tuple) and len(h) == 3:
                clause_id, clause_text, dist = h
            elif isinstance(h, tuple) and len(h) == 2:
                clause_text, dist = h
            else:
                # unknown format
                clause_text = str(h)
                dist = None

            if clause_text is None:
                continue

            # distance filter if dist exists
            if dist is not None and dist > max_dist:
                continue

            # extra strict validation for payment
            if key == "payment" and not looks_like_payment(clause_text):
                continue

            picked.append({
                "clause_id": clause_id,
                "clause_text": clause_text
            })

            if len(picked) >= top_k:
                break

        if not picked:
            picked = [{"clause_id": None, "clause_text": "Not found"}]

        results[key] = picked
    return results

#     # OPTIONAL LLM cleanup (you can remove this if you want max determinism)
#     system_prompt = """
# You are a legal clause organizer.

# Task:
# - Keep clause_id and clause_text unchanged
# - Do NOT add new keys
# - Return ONLY valid JSON (no markdown/code fences)

# Schema:
# {
#   "termination": [{"clause_id": 3, "clause_text": "..."}],
#   ...
# }
# """

#     user_prompt = f"""
# Return the following object as valid JSON, unchanged in content:
# {results}
# """

#     raw = call_llm(system_prompt=system_prompt, user_prompt=user_prompt)

#     try:
#         return safe_json_load(raw)
#     except Exception:
     