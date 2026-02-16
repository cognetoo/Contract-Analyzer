from tools.contract_parser import load_contract, split_into_clauses
from tools.clause_classifier import classify_clauses_batch
from rag.contract_store import ContractStore
from tools.rule_based_qa import can_terminate_early
from tools.question_router import route_question
from rag.vector_store import VectorStore
from tools.llm_qa import answer_with_llm
from tools.full_risk_engine import analyze_full_contract_risk
from tools.json_utils import safe_json_load



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

    clause_types = classify_clauses_batch(clauses)

    store.add_clauses_batch(clauses, clause_types) ##adding batch wise to our contract store

    items = [(c["clause_id"], c["text"]) for c in store.clauses]

    vector_store.add(items)

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

    print("\n Contract Analyzer Ready!")
    print("Type your question")
    print("Type 'analyze risk' for full contract risk report")
    print("Type 'report' for full contract report")
    print("Type 'exit' to quit\n")

    while True:
        query = input(">> ").strip()

        if query.lower() == "exit":
            print("Goodbye 👋")
            break

        # 🔍 Risk Analysis Mode
        if query.lower() == "analyze risk":
            risk_report = analyze_full_contract_risk(store)

            present = risk_report["present_risks"]
            missing = risk_report["missing_risks"]
            additional = risk_report["additional_risks"]

            print("\n FULL CONTRACT RISK REPORT\n")

    
            # Present Risks
   
            if present:
              print(" PRESENT RISKS DETECTED:\n")

              for r in present:
                print("Clause ID:", r["clause_id"])
                # print("Clause Text:", r["clause_text"][:300], "...")
                print("Risk Type:", r["risk_type"])
                print("Similarity Score:", r["similarity_score"])
                print("Risk Level:", r["risk_level"])
                print("Explanation:", r["explanation"])
                print("Mitigation:", r["mitigation"])
                print("-" * 50)

            else:
              print("No present clause risks detected.\n")

   
            # Missing Risks
            if missing:
               print("\n MISSING CRITICAL CLAUSES:\n")

               print("Risk Score:", missing["risk_score"])
               print("Risk Level:", missing["risk_level"])
               print("\nFindings:")

               for finding in missing["findings"]:
                  print("-", finding)
                  print("-" * 50)
            else:
               print("\nNo critical clauses missing.\n")

            if additional:
               print("\n ADDITIONAL RISKS DISCOVERED:\n")

               for r in additional:
                print("Risk Type:", r["risk_type"])
                print("Risk Level:", r["risk_level"])
                print("Explanation:", r["explanation"])
                print("Mitigation:", r["mitigation"])
                print("-" * 50)
            else:
                print("\nNo additional risks discovered.\n")

            continue

        if query.lower() == "report":
           from tools.report_builder import build_full_report

           report = build_full_report(store,vector_store)

           print("\n==== FULL CONTRACT REPORT ====\n")
           print("SUMMARY: \n",report['summary'])
           print("\nKEY CLAUSES:\n",report['key_clauses'])
           print("\nSTRUCTURED ANALYSIS:\n",report["structured_analysis"])
           print("\nUNCLEAR / MISSING: \n",report["unclear_or_missing"])
           print("\nQUESTIONS TO ASK A LAWYER:\n",report["questions_to_ask_lawyer"])
           print("\n"+"-" * 50 + "\n")
           continue
  
        # Normal Q&A Mode
        response = answer_query(query, vector_store)
        print("\n", response)
        print("\n" + "-" * 50 + "\n")





