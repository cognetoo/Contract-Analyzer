from llm import call_llm

def answer_with_llm(question, clauses):
    """
    Uses LLM when rule-based logic is insufficient.
    """
    system_prompt = """
You are a legal contract analysis assistant.
Answer strictly using the provided clauses.
Do not hallucinate.
"""

    context = "\n\n".join([c for c in clauses])

    user_prompt = f"""
Contract clauses:
{context}

Question:
{question}
"""

    return call_llm(
        system_prompt=system_prompt,
        user_prompt=user_prompt
    )
