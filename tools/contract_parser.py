import re
from pypdf import PdfReader
import re
from pypdf import PdfReader


def load_contract(pdf_path: str) -> str:
    """
    Loads PDF and converts to raw text.
    """
    reader = PdfReader(pdf_path)
    full_text = ""

    for page in reader.pages:
        text = page.extract_text()
        if text:
            full_text += text + "\n"

    return full_text


def clean_raw_text(text: str) -> str:
    """
    Removes signature blocks and obvious garbage.
    """

    # Remove signature lines like _________
    text = re.sub(r'_{3,}', '', text)



    # Remove lines with mostly uppercase and very short (often headers)
    lines = text.split("\n")
    cleaned_lines = []

    for line in lines:
        stripped = line.strip()

        # Skip empty lines
        if not stripped:
            continue

        # Remove page numbers like "Page 1 of 5"
        if re.search(r'page\s*\d+', stripped.lower()):
            continue

        # Remove director / signature labels
        if any(word in stripped.lower() for word in ["director", "employee", "signature"]):
            continue

        cleaned_lines.append(stripped)

    return "\n".join(cleaned_lines)


def split_into_clauses(contract_text: str):
    """
    Splits contract into clean clauses using legal numbering patterns.
    """

    contract_text = clean_raw_text(contract_text)

    # Match:
    # 1
    # 1.
    # 1)
    # 1.1
    # 2.3.4
    # (1)
    pattern = r'\n\s*\(?\d+(?:\.\d+)*\)?[\.\)]?\s+'


    clauses = re.split(pattern, contract_text)

    cleaned = []

    for clause in clauses:
        clause = clause.strip()

        # Remove tiny fragments
        if len(clause.split()) < 15:
            continue

        cleaned.append(clause)

    return cleaned
