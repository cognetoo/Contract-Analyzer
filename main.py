from tools.contract_parser import load_contract, split_into_clauses
from tools.clause_classifier import classify_clauses_batch
from rag.contract_store import ContractStore
from rag.vector_store import VectorStore

from agents.planner import plan
from agents.executor import execute

from tools.logger import logger
from tools.metrics import time_it

import time
import json
from datetime import datetime


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
    logger.info("Contract loaded and indexed successfully.")

    print("\n Contract Analyzer Ready!")
    print("Type your question")
    print("Commands:")
    print(" - 'report'       : full contract report")
    print(" - 'analyze risk' : full contract risk report")
    print(" - 'export json'  : export last result to json")
    print(" - 'exit'         : quit\n")

    last_result = None  

    while True:
        query = input(">> ").strip()
        if not query:
            continue

        qlow = query.lower()

        if qlow == "exit":
            logger.info("Session ended by the user.")
            print("Goodbye 👋")
            break

        logger.info(f"User Query: {query}")

        if qlow == "export json":
            if last_result is None:
                print("No result to export yet.")
                continue

            filename = f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

            payload = last_result
            if isinstance(last_result, str):
                payload = {"text": last_result}

            with open(filename, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=4, ensure_ascii=False)

            logger.info(f"Result exported to {filename}")
            print(f"Exported to {filename}")
            continue

        try:
            total_start = time.perf_counter()

            plan_obj, planner_time = time_it("Planner", plan, query)
            logger.info(f"Planner output: {plan_obj}")

            result, exec_time = time_it(
                "Executor",
                execute,
                plan_obj,
                query,
                store,
                vector_store
            )

            total_time = round((time.perf_counter() - total_start) * 1000, 2)
            logger.info(f"[PERF] Total request time: {total_time} ms")
            logger.info(f"Execution completed. Intent: {plan_obj.get('intent')}")

            last_result = result

            # print
            if isinstance(result, dict):
                print("\n" + json.dumps(result, indent=2, ensure_ascii=False))
            else:
                print("\n" + str(result))

            print("\n" + "-" * 50 + "\n")

        except Exception:
            logger.exception("Execution error")
            print("Something went wrong. Check logs.")