import os
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Path as FPath
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

from api.schemas import UploadResponse, QueryRequest, QueryResponse, HistoryResponse
from api.db import get_db, engine, SessionLocal
from api.models import Base, User
from api.persistence import (
    create_contract,
    get_contract,
    set_last_result,
    get_last_result,
    add_run,
    get_history,
)

from api.auth import router as auth_router
from api.deps import get_current_user

from tools.contract_parser import load_contract, split_into_clauses
from tools.clause_classifier import classify_clauses_batch

from rag.contract_store import ContractStore
from rag.vector_store import VectorStore

from agents.planner import plan
from agents.executor import execute

from tools.logger import logger
from tools.metrics import time_it


app = FastAPI(title="Contract Analyzer API", version="1.0")

@app.on_event("startup")
def on_startup():
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("[startup] DB tables ensured")
    except Exception as e:
        logger.exception(f"[startup] DB init failed: {e}")
     

app.include_router(auth_router)

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = os.getenv("DATA_DIR", "data")
CONTRACTS_DIR = Path(DATA_DIR) / "contracts"
INDEX_DIR = Path(DATA_DIR) / "indexes"
CONTRACTS_DIR.mkdir(parents=True, exist_ok=True)
INDEX_DIR.mkdir(parents=True, exist_ok=True)

VALID_MODES = {
    "qa",
    "summary_only",
    "key_clauses_only",
    "risk_only",
    "structured_only",
    "unclear_only",
    "lawyer_questions_only",
    "full_report",
}


def build_contract_index_from_text(text_data: str):
    clauses = split_into_clauses(text_data)

    store = ContractStore()
    vector_store = VectorStore()

    clause_types = classify_clauses_batch(clauses)
    store.add_clauses_batch(clauses, clause_types)

    items = [(c["clause_id"], c["text"]) for c in store.clauses]
    vector_store.add(items)

    clause_rows = []
    for c in store.clauses:
        clause_rows.append((int(c["clause_id"]), c["text"], c.get("clause_type")))

    return store, vector_store, clause_rows


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/db/health")
def db_health():
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        return {"db": "ok"}
    finally:
        db.close()


@app.post("/contracts/upload", response_model=UploadResponse)
async def upload_contract(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    t0 = time.perf_counter()

    if not file.filename:
        raise HTTPException(status_code=400, detail="filename missing")

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only .pdf supported for now")

    contract_id = uuid.uuid4().hex

    pdf_path = CONTRACTS_DIR / f"{contract_id}_{file.filename}"
    index_path = INDEX_DIR / f"{contract_id}.faiss"

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    try:
        with open(pdf_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed saving file: {str(e)}")

    try:
        text_data = load_contract(str(pdf_path))
        store, vector_store, clause_rows = build_contract_index_from_text(text_data)

        vector_store.save(str(index_path))

        create_contract(
            db=db,
            user_id=user.id,
            contract_id=contract_id,
            filename=file.filename,
            pdf_path=str(pdf_path),
            index_path=str(index_path),
            clauses=clause_rows,
        )
    except Exception as e:
        logger.exception("Failed to parse/index contract")
        raise HTTPException(status_code=500, detail=f"Failed to parse/index: {str(e)}")

    dt = round((time.perf_counter() - t0) * 1000, 2)
    logger.info(f"[API] Uploaded contract_id={contract_id} user_id={user.id} indexed in {dt} ms")

    return UploadResponse(
        contract_id=contract_id,
        status="indexed",
        filename=file.filename,
        num_clauses=len(clause_rows),
        tmp_path=str(pdf_path),
    )


@app.post("/contracts/{contract_id}/query", response_model=QueryResponse)
def query_contract(
    contract_id: str,
    req: QueryRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    contract = get_contract(db, user.id, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="contract_id not found")

    query = (req.query or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="query is required")

    total_start = time.perf_counter()
    logger.info(f"[API] user_id={user.id} contract_id={contract_id} mode={req.mode} query={query[:200]}")

    try:
        # Load FAISS index from disk
        vector_store = VectorStore()
        vector_store.load(contract.index_path)

        # Build ContractStore from DB clauses
        store = ContractStore()
        clauses_sorted = sorted(contract.clauses, key=lambda c: c.clause_id)
        clause_texts = [c.text for c in clauses_sorted]
        clause_types = [c.clause_type for c in clauses_sorted]
        store.add_clauses_batch(clause_texts, clause_types)

        planner_ms = 0.0
        mode = req.mode

        if mode:
            if mode not in VALID_MODES:
                raise HTTPException(status_code=400, detail=f"Invalid mode: {mode}")

            tool_map = {
                "qa": "qa",
                "summary_only": "summarize_contract",
                "key_clauses_only": "extract_key_clauses",
                "structured_only": "structured_analysis",
                "risk_only": "analyze_full_contract_risk",
                "unclear_only": "find_unclear_or_missing",
                "lawyer_questions_only": "generate_legal_questions",
                "full_report": "build_full_report",
            }

            plan_obj = {
                "intent": mode,
                "k": req.k if req.k is not None else 3,
                "steps": [{"tool": tool_map[mode], "args": {}}],
                "notes": "mode_param_override",
            }
        else:
            plan_obj, planner_ms = time_it("Planner", plan, query)
            if req.k is not None:
                plan_obj["k"] = req.k

        result, exec_ms = time_it("Executor", execute, plan_obj, query, store, vector_store)

        total_ms = round((time.perf_counter() - total_start) * 1000, 2)
        run_perf = {"planner": round(planner_ms, 2), "executor": round(exec_ms, 2), "total": total_ms}

        set_last_result(db, user.id, contract_id, result)
        add_run(db, user.id, contract_id, query=query, plan=plan_obj, result=result, perf_ms=run_perf)

        logger.info(f"[API] Done user_id={user.id} contract_id={contract_id} intent={plan_obj.get('intent')} total_ms={total_ms}")

        return QueryResponse(
            contract_id=contract_id,
            plan=plan_obj,
            result=result,
            perf_ms=run_perf,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("API query execution error")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/contracts/{contract_id}/last_result")
def last_result_endpoint(
    contract_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    contract = get_contract(db, user.id, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="contract_id not found")

    res = get_last_result(db, user.id, contract_id)
    if res is None:
        return {"contract_id": contract_id, "last_result": None, "message": "No query executed yet."}
    return {"contract_id": contract_id, "last_result": res}


@app.get("/contracts/{contract_id}/history", response_model=HistoryResponse)
def history_endpoint(
    contract_id: str,
    limit: int = 10,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    contract = get_contract(db, user.id, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="contract_id not found")

    runs = get_history(db, user.id, contract_id, limit=max(1, min(limit, 50)))
    return {
        "contract_id": contract_id,
        "runs": [
            {
                "id": r.id,
                "created_at": r.created_at,
                "query": r.query,
                "plan": r.plan,
                "result": r.result,
                "perf_ms": r.perf_ms,
            }
            for r in runs
        ],
    }


@app.get("/contracts/{contract_id}/export_last_result")
def export_last_result_endpoint(
    contract_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    contract = get_contract(db, user.id, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="contract_id not found")

    res = get_last_result(db, user.id, contract_id)
    if res is None:
        raise HTTPException(status_code=400, detail="No result to export yet")

    return JSONResponse(content=res)


@app.get("/contracts/{contract_id}/clauses/{clause_id}")
def get_clause_endpoint(
    contract_id: str,
    clause_id: int = FPath(..., ge=1),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    contract = get_contract(db, user.id, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="contract_id not found")

    clause = next((c for c in contract.clauses if int(c.clause_id) == int(clause_id)), None)
    if not clause:
        raise HTTPException(status_code=404, detail="clause_id not found")

    return {
        "contract_id": contract_id,
        "clause_id": clause_id,
        "clause_type": clause.clause_type,
        "text": clause.text,
    }