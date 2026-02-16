from llm import call_llm
def answer_with_llm(question: str, clauses):
    # clauses can be list[str] OR list[tuple[int,str]]
    formatted = []
    for c in clauses:
        if isinstance(c, tuple) and len(c) == 2:
            cid, txt = c
            formatted.append(f"[Clause {cid}] {txt}")
        else:
            formatted.append(str(c))

    context = "\n\n".join(formatted)

    system_prompt = """You are a helpful contract QA assistant.
Use ONLY the provided clauses. If not found, say Not found.
Always cite as [Clause N]. Return plain text."""
    user_prompt = f"Question: {question}\n\nClauses:\n{context}"

    return call_llm(system_prompt=system_prompt, user_prompt=user_prompt)