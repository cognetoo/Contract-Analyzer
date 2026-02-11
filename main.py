from llm import call_llm
from tools.contract_parser import load_contract, split_into_clauses
from tools.clause_classifier import classify_clause
from rag.contract_store import ContractStore
from tools.rule_based_qa import can_terminate_early
from tools.question_router import route_question
from rag.vector_store import VectorStore
from tools.llm_qa import answer_with_llm
from tools.risk_analyzer import analyze_contract_risk
from tools.hybrid_risk_engine import analyze_risks_hybrid


def build_contract_index(pdf_path):
    """
    Loads contract,classifies clauses, builds vector store and contract store
    """
    text = load_contract(pdf_path)
    clauses = split_into_clauses(text)
    # print("\n---- DEBUG: First 5 Clauses ----")
    # for i, clause in enumerate(clauses[:5]):
    #     print(f"\n--- Clause {i+1} ---\n")
    #     print(clause)
    store = ContractStore()
    vector_store = VectorStore()

    for clause in clauses:
        clause_type = classify_clause(clause)
        store.add_clause(clause_text=clause,clause_type=clause_type)

    all_clause_texts = [c["text"] for c in store.clauses]
    vector_store.add(all_clause_texts)

    return store,vector_store


def answer_query(query,vector_store):
    """
    Answers user query using semantic retrieval + hybrid QA.
    """
    

    relevant_clauses = vector_store.search(query, k=5)
    route = route_question(query)

    if route == "termination":
       answer = can_terminate_early(relevant_clauses)

       if "No explicit" in answer:
        answer = answer_with_llm(query, relevant_clauses)

    else:
      answer = answer_with_llm(query, relevant_clauses)

    return answer

if __name__ == "__main__":
    store, vector_store = build_contract_index("EMPLOYMENT-AGREEMENT.pdf")

    print("\n📄 Contract Analyzer Ready!")
    print("Type your question")
    print("Type 'analyze risk' for full contract risk report")
    print("Type 'exit' to quit\n")

    while True:
        query = input(">> ").strip()

        if query.lower() == "exit":
            print("Goodbye 👋")
            break

        # 🔍 Risk Analysis Mode
        if query.lower() == "analyze risk":
            risks = analyze_risks_hybrid(store)

            if not risks:
              print("\nNo significant risks detected.\n")
            else:
              print("\nRisk Analysis Report:\n")

            for r in risks:
               print("Risk Type:", r["risk_type"])
               print("Similarity Score:", r["similarity_score"])
               print("LLM Analysis:\n", r["llm_analysis"])
               print("-" * 50)

            continue
  
        # 💬 Normal Q&A Mode
        response = answer_query(query, vector_store)
        print("\n", response)
        print("\n" + "-" * 50 + "\n")





