from rag.rag import retrieval
from llm import call_llm

query = "Can this contract be terminated early?"

docs = retrieval(query)

system_prompt = "You are a legal contract analysis agent."

user_prompt = f"""
Contract clauses:
{docs}

Question:
{query}
"""

answer = call_llm(system_prompt=system_prompt,user_prompt=user_prompt)
print(answer)