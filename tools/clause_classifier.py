import json
import re
from llm import call_llm

ALLOWED_CLAUSE_TYPES = [
    "confidentiality",
    "termination",
    "payment",
    "dispute_resolution",
    "non_compete",
    "intellectual_property",
    "liability",
    "governing_law",
    "employment_terms",
    "other"
]


def extract_json(text):
    """
    Extract JSON safely even if LLM wraps it in ```json blocks
    """
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if match:
        return match.group(0)
    return None


def classify_clauses_batch(clauses):
    """
    Classify clauses in batch using LLM with strict JSON enforcement.
    Returns list of clause types aligned with input order.
    """

    numbered_clauses = "\n\n".join(
        [f"{i+1}. {clause}" for i, clause in enumerate(clauses)]
    )

    system_prompt = f"""
You are a legal contract clause classifier.

Classify each clause into exactly ONE of these types:

{ALLOWED_CLAUSE_TYPES}

Return ONLY a JSON list of strings.
The list length MUST equal number of clauses.
No explanation.
No markdown.
No extra text.

Example output:
["confidentiality", "termination", "payment"]
"""

    user_prompt = f"""
Classify the following clauses:

{numbered_clauses}
"""

    response = call_llm(system_prompt=system_prompt, user_prompt=user_prompt)

    try:
        json_text = extract_json(response)
        classifications = json.loads(json_text)

        # Safety check
        if not isinstance(classifications, list):
            raise ValueError("Output is not list")

        if len(classifications) != len(clauses):
            raise ValueError("Length mismatch")

        # Clean + validate
        cleaned = []
        for label in classifications:
            label = label.strip().lower()
            if label not in ALLOWED_CLAUSE_TYPES:
                label = "other"
            cleaned.append(label)

        return cleaned

    except Exception as e:
        print("Classification parsing failed. Falling back to 'other'.")
        return ["other"] * len(clauses)
