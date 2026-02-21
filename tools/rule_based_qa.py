import re
from typing import List, Tuple, Union, Optional

ClauseHit = Union[str, Tuple[int, str]]

def _texts(hits: List[ClauseHit]) -> List[str]:
    out = []
    for h in hits:
        if isinstance(h, tuple) and len(h) == 2:
            _, txt = h
            out.append(txt)
        else:
            out.append(str(h))
    return out

def _find_first(patterns: List[str], texts: List[str]) -> Optional[str]:
    for t in texts:
        low = t.lower()
        for p in patterns:
            if re.search(p, low):
                return t
    return None

def _extract_number_like(text: str) -> Optional[str]:
    """
    Improved amount extractor:
    - Prefers "Rs. 2 lakhs" / "2 lakhs" over "rs. 2"
    - Falls back to generic currency/number if no lakh/lakhs found
    """
    t = text.lower()

    # Prefer lakh/lakhs patterns first (more informative)
    m = re.search(
        r"(₹\s*\d[\d,\.]*\s*lakhs?)|"
        r"(rs\.?\s*\d[\d,\.]*\s*lakhs?)|"
        r"(\d[\d,\.]*\s*lakhs?)|"
        r"(\d[\d,\.]*\s*lakh)",
        t
    )
    if m:
        return m.group(0)

    # Fallback patterns (plain currency/number)
    m = re.search(
        r"(₹\s*\d[\d,\.]*)|"
        r"(rs\.?\s*\d[\d,\.]*)|"
        r"(\d[\d,\.]*\s*inr)|"
        r"(\brupees\s*\d[\d,\.]*)",
        t
    )
    return m.group(0) if m else None


def can_terminate_early(hits: List[ClauseHit]) -> str:
    texts = _texts(hits)
    t = _find_first(
        patterns=[
            r"\bterminate\b",
            r"\btermination\b",
            r"\bnotice\b",
            r"\bresign\b",
            r"\bprior notice\b",
        ],
        texts=texts,
    )
    if not t:
        return "NO_RULE_MATCH: no termination language found in retrieved clauses"
    return "Possible termination language found:\n\n" + t

def find_notice_period(hits: List[ClauseHit]) -> str:
    texts = _texts(hits)
    t = _find_first(
        patterns=[r"\bnotice period\b", r"\b\d+\s*(day|days|month|months)\b.*\bnotice\b", r"\bprior notice\b"],
        texts=texts,
    )
    if not t:
        return "NO_RULE_MATCH: no notice period found"
    return "Notice / resignation related clause:\n\n" + t

def find_payment_terms(hits: List[ClauseHit]) -> str:
    texts = _texts(hits)
    t = _find_first(
        patterns=[
            r"\bsalary\b", r"\bctc\b", r"\bremuneration\b", r"\bstipend\b",
            r"\bwages?\b", r"\bpayable\b", r"\ballowance\b", r"\bbonus\b",
            r"\bdeduction\b", r"\bpf\b", r"\besi\b", r"\btds\b", r"\breimbursement\b"
        ],
        texts=texts,
    )
    if not t:
        return "NO_RULE_MATCH: no payment terms found"
    return "Payment/compensation related clause:\n\n" + t

def find_penalty_or_bond(hits: List[ClauseHit]) -> str:
    texts = _texts(hits)
    t = _find_first(
        patterns=[
            r"\bpenalt(y|ies)\b",
            r"\bliquidated damages\b",
            r"\bdamages\b",
            r"\bsection\s*73\b",
            r"\bsection\s*74\b",
            r"\b2\s*lakhs?\b",
            r"\blakh\b"
        ],
        texts=texts,
    )
    if not t:
        return "NO_RULE_MATCH: no penalty/bond language found"
    amt = _extract_number_like(t)
    extra = f"\n\n(Detected amount-like phrase: {amt})" if amt else ""
    return "Penalty / damages related clause:\n\n" + t + extra

def find_arbitration_or_jurisdiction(hits: List[ClauseHit]) -> str:
    texts = _texts(hits)
    t = _find_first(
        patterns=[r"\barbitration\b", r"\barbitration and conciliation act\b", r"\bjurisdiction\b", r"\bgoverning law\b", r"\bjaipur\b"],
        texts=texts,
    )
    if not t:
        return "NO_RULE_MATCH: no arbitration/jurisdiction language found"
    return "Dispute resolution / jurisdiction clause:\n\n" + t

def find_confidentiality(hits: List[ClauseHit]) -> str:
    texts = _texts(hits)
    t = _find_first(
        patterns=[r"\bconfidential\b", r"\btrade secret\b", r"\bnon[- ]disclosure\b"],
        texts=texts,
    )
    if not t:
        return "NO_RULE_MATCH: no confidentiality language found"
    return "Confidentiality related clause:\n\n" + t

def find_ip_ownership(hits: List[ClauseHit]) -> str:
    texts = _texts(hits)
    t = _find_first(
        patterns=[r"\bintellectual property\b", r"\bip\b", r"\bsource code\b", r"\binvention\b", r"\bexclusive property\b"],
        texts=texts,
    )
    if not t:
        return "NO_RULE_MATCH: no IP language found"
    return "IP ownership related clause:\n\n" + t

def find_non_compete(hits: List[ClauseHit]) -> str:
    texts = _texts(hits)
    t = _find_first(
        patterns=[r"\bnon[- ]compete\b", r"\bcompete\b", r"\brestraint\b"],
        texts=texts,
    )
    if not t:
        return "NO_RULE_MATCH: no non-compete language found"
    return "Non-compete related clause:\n\n" + t

def find_return_of_property(hits: List[ClauseHit]) -> str:
    texts = _texts(hits)
    t = _find_first(
        patterns=[r"\breturn\b.*\b(laptop|books|mobile|papers|assets|property)\b", r"\bcompany property\b"],
        texts=texts,
    )
    if not t:
        return "NO_RULE_MATCH: no return-of-property clause found"
    return "Return of company property clause:\n\n" + t


def rule_based_answer(user_query: str, hits: List[ClauseHit]) -> str:
    q = user_query.lower()

    if any(w in q for w in ["salary", "ctc", "payment", "pay", "wages", "stipend", "pf", "esi", "deduction", "bonus", "allowance", "reimbursement"]):
        ans = find_payment_terms(hits)
        if not ans.startswith("NO_RULE_MATCH"):
            return ans

    if any(w in q for w in ["penalty", "bond", "2 lakh", "2 lakhs", "damages", "section 73", "section 74", "liquidated"]):
        ans = find_penalty_or_bond(hits)
        if not ans.startswith("NO_RULE_MATCH"):
            return ans

    if any(w in q for w in ["terminate", "termination", "resign", "resignation", "notice"]):
        ans = find_notice_period(hits)
        if not ans.startswith("NO_RULE_MATCH"):
            return ans
        ans = can_terminate_early(hits)
        if not ans.startswith("NO_RULE_MATCH"):
            return ans

    if any(w in q for w in ["confidential", "nda", "trade secret", "non disclosure"]):
        ans = find_confidentiality(hits)
        if not ans.startswith("NO_RULE_MATCH"):
            return ans

    if any(w in q for w in ["ip", "intellectual", "invention", "source code"]):
        ans = find_ip_ownership(hits)
        if not ans.startswith("NO_RULE_MATCH"):
            return ans

    if any(w in q for w in ["non compete", "noncompete", "compete", "restraint"]):
        ans = find_non_compete(hits)
        if not ans.startswith("NO_RULE_MATCH"):
            return ans

    if any(w in q for w in ["arbitration", "dispute", "jurisdiction", "governing law", "court"]):
        ans = find_arbitration_or_jurisdiction(hits)
        if not ans.startswith("NO_RULE_MATCH"):
            return ans

    if any(w in q for w in ["return", "laptop", "company property", "assets"]):
        ans = find_return_of_property(hits)
        if not ans.startswith("NO_RULE_MATCH"):
            return ans

    return "NO_RULE_MATCH: no applicable rule"