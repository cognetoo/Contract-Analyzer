import re
from typing import List, Dict

VAGUE_PATTERNS = [
    r"\breasonable\b",
    r"\bas decided by\b",
    r"\bat the discretion of\b",
    r"\bfrom time to time\b",
    r"\bmay be amended\b",
    r"\bsubject to\b",
    r"\bas per company policy\b",
]

BLANK_PATTERNS = [
    r"_{3,}",          # _______
    r"\bTBD\b",
    r"\bto be decided\b",
    r"\bto be determined\b",
    r"\bN/?A\b"
]

def find_unclear_or_missing(store) -> List[Dict]:
    """
    Returns list of issues:
    [{clause_id, issue_type, snippet}]
    """
    issues = []

    for c in store.clauses:
        text = c["text"]
        low = text.lower()

        # blanks / missing fields
        for pat in BLANK_PATTERNS:
            if re.search(pat, text, flags=re.IGNORECASE):
                issues.append({
                    "clause_id": c["clause_id"],
                    "issue_type": "missing_value",
                    "snippet": text[:500]
                })
                break

        # vague language
        for pat in VAGUE_PATTERNS:
            if re.search(pat, low):
                issues.append({
                    "clause_id": c["clause_id"],
                    "issue_type": "vague_language",
                    "snippet": text[:500]
                })
                break

    return issues