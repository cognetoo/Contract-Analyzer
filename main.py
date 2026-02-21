from tools.contract_parser import load_contract, split_into_clauses
from tools.clause_classifier import classify_clauses_batch
from rag.contract_store import ContractStore
from rag.vector_store import VectorStore

from tools.full_risk_engine import analyze_full_contract_risk
from tools.report_builder import build_full_report

from agents.planner import plan
from agents.executor import execute


def build_contract_index(pdf_path):
    text = load_contract(pdf_path)
    clauses = split_into_clauses(text)

    store = ContractStore()
    vector_store = VectorStore()

    clause_types = classify_clauses_batch(clauses)
    store.add_clauses_batch(clauses, clause_types)

    items = [(c["clause_id"], c["text"]) for c in store.clauses]
    vector_store.add(items)

    return store, vector_store


if __name__ == "__main__":
    store, vector_store = build_contract_index("EMPLOYMENT-AGREEMENT.pdf")

    print("\n Contract Analyzer Ready!")
    print("Type your question")
    print("Commands:")
    print(" - 'analyze risk' : full contract risk report")
    print(" - 'report'       : full contract report")
    print(" - 'exit'         : quit\n")

    while True:
        query = input(">> ").strip()
        if not query:
            continue

        if query.lower() == "exit":
            print("Goodbye 👋")
            break

        # Keep these commands exactly as your current behavior
        if query.lower() == "analyze risk":
            risk_report = analyze_full_contract_risk(store)

            present = risk_report["present_risks"]
            missing = risk_report["missing_risks"]
            additional = risk_report["additional_risks"]

            print("\n FULL CONTRACT RISK REPORT\n")

            if present:
                print(" PRESENT RISKS DETECTED:\n")
                for r in present:
                    print("Clause ID:", r.get("clause_id"))
                    print("Risk Type:", r.get("risk_type"))
                    print("Similarity Score:", r.get("similarity_score"))
                    print("Risk Level:", r.get("risk_level"))
                    print("Explanation:", r.get("explanation"))
                    print("Mitigation:", r.get("mitigation"))
                    print("-" * 50)
            else:
                print("No present clause risks detected.\n")

            if missing:
                print("\n MISSING CRITICAL CLAUSES:\n")
                print("Risk Score:", missing.get("risk_score"))
                print("Risk Level:", missing.get("risk_level"))
                print("\nFindings:")
                for finding in missing.get("findings", []):
                    print("-", finding)
                    print("-" * 50)
            else:
                print("\nNo critical clauses missing.\n")

            if additional:
                print("\n ADDITIONAL RISKS DISCOVERED:\n")
                for r in additional:
                    print("Risk Type:", r.get("risk_type"))
                    print("Risk Level:", r.get("risk_level"))
                    print("Explanation:", r.get("explanation"))
                    print("Mitigation:", r.get("mitigation"))
                    print("-" * 50)
            else:
                print("\nNo additional risks discovered.\n")

            continue

        if query.lower() == "report":
            report = build_full_report(store, vector_store)

            print("\n==== FULL CONTRACT REPORT ====\n")
            print("SUMMARY: \n", report["summary"])
            print("\nKEY CLAUSES:\n", report["key_clauses"])
            print("\nSTRUCTURED ANALYSIS:\n", report["structured_analysis"])
            print("\nUNCLEAR / MISSING: \n", report["unclear_or_missing"])
            print("\nQUESTIONS TO ASK A LAWYER:\n", report["questions_to_ask_lawyer"])
            print("\n" + "-" * 50 + "\n")
            continue

        # NEW routing
        plan_obj = plan(query)
        result = execute(plan_obj, query, store, vector_store)

        # result can be dict (summary/report/risk) or text (qa)
        print("\n", result)
        print("\n" + "-" * 50 + "\n")