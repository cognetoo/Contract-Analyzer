import os
import time
import uuid
from pathlib import Path

from fastapi import (
    FastAPI,
    UploadFile,
    File,
    HTTPException,
    Depends,
    Path as FPath,
    BackgroundTasks,
)
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy.orm import Session
from sqlalchemy import text

from api.schemas import (
    UploadResponse,
    UploadStatusResponse,
    QueryRequest,
    QueryResponse,
    HistoryResponse,
)
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
from rag.vector_store import VectorStore, get_model

from agents.planner import plan
from agents.executor import execute

from tools.logger import logger
from tools.metrics import time_it


app = FastAPI(title="Contract Analyzer API", version="1.0")


# ---------------- Startup ----------------
@app.on_event("startup")
def on_startup():
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("[startup] DB tables ensured")

        get_model()
        logger.info("[startup] Embedding model loaded")

    except Exception as e:
        logger.exception(f"[startup] init failed: {e}")


app.include_router(auth_router)


# ---------------- CORS ----------------
ALLOW_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
frontend_origin = os.getenv("FRONTEND_ORIGIN")
if frontend_origin:
    ALLOW_ORIGINS.append(frontend_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------- Data dirs ----------------
DATA_DIR = os.getenv("DATA_DIR", "/tmp/data")
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
    # Hard limits to avoid Render timeouts / memory issues
    MAX_CHARS = int(os.getenv("MAX_CONTRACT_CHARS", "200000"))
    if len(text_data) > MAX_CHARS:
        text_data = text_data[:MAX_CHARS]

    clauses = split_into_clauses(text_data)

    MAX_CLAUSES = int(os.getenv("MAX_CLAUSES", "250"))
    if len(clauses) > MAX_CLAUSES:
        clauses = clauses[:MAX_CLAUSES]

    store = ContractStore()
    vector_store = VectorStore()

    clause_types = classify_clauses_batch(clauses)
    store.add_clauses_batch(clauses, clause_types)

    items = [(c["clause_id"], c["text"]) for c in store.clauses]

    embed_batch = int(os.getenv("EMBED_BATCH_SIZE", "16"))
    try:
        vector_store.add(items, batch_size=embed_batch)
    except TypeError:
        vector_store.add(items)

    clause_rows = [(int(c["clause_id"]), c["text"], c.get("clause_type")) for c in store.clauses]
    return store, vector_store, clause_rows


UPLOAD_STATUS = {}


def process_contract_background(
    contract_id: str,
    filename: str,
    pdf_path: str,
    index_path: str,
    user_id: int,
):
    """
    Heavy parse+index happens here so /contracts/upload returns fast (no gateway timeout).
    """
    db = SessionLocal()
    try:
        UPLOAD_STATUS[contract_id] = {"status": "processing", "error": None, "num_clauses": 0}

        text_data = load_contract(pdf_path)
        store, vector_store, clause_rows = build_contract_index_from_text(text_data)

        vector_store.save(index_path)

        create_contract(
            db=db,
            user_id=user_id,
            contract_id=contract_id,
            filename=filename,
            pdf_path=pdf_path,
            index_path=index_path,
            clauses=clause_rows,
        )

        UPLOAD_STATUS[contract_id] = {
            "status": "indexed",
            "error": None,
            "num_clauses": len(clause_rows),
        }

        logger.info(f"[BG] Indexed contract_id={contract_id} user_id={user_id} clauses={len(clause_rows)}")

    except Exception as e:
        logger.exception("[BG] Failed to process contract")
        UPLOAD_STATUS[contract_id] = {"status": "failed", "error": str(e), "num_clauses": 0}
    finally:
        db.close()


# ---------------- Routes ----------------
@app.get("/")
def root():
    return {"status": "ok", "service": "contract-analyzer-api"}


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
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),  # kept for auth/consistency
    user: User = Depends(get_current_user),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="filename missing")
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only .pdf supported for now")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    MAX_FILE_MB = int(os.getenv("MAX_PDF_MB", "5"))
    if len(content) > MAX_FILE_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"PDF too large. Max {MAX_FILE_MB}MB.")

    contract_id = uuid.uuid4().hex
    pdf_path = str(CONTRACTS_DIR / f"{contract_id}_{file.filename}")
    index_path = str(INDEX_DIR / f"{contract_id}.faiss")

    try:
        with open(pdf_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed saving file: {str(e)}")

    UPLOAD_STATUS[contract_id] = {"status": "queued", "error": None, "num_clauses": 0}
    background_tasks.add_task(
        process_contract_background,
        contract_id,
        file.filename,
        pdf_path,
        index_path,
        user.id,
    )

    return UploadResponse(
        contract_id=contract_id,
        status="processing",
        filename=file.filename,
        num_clauses=0,
        tmp_path=pdf_path,
    )


@app.get("/contracts/{contract_id}/upload_status", response_model=UploadStatusResponse)
def upload_status(
    contract_id: str,
    user: User = Depends(get_current_user),
):
    s = UPLOAD_STATUS.get(contract_id)
    if not s:
        return UploadStatusResponse(contract_id=contract_id, status="unknown", error=None, num_clauses=0)
    return UploadStatusResponse(contract_id=contract_id, **s)


@app.post("/contracts/{contract_id}/query", response_model=QueryResponse)
def query_contract(
    contract_id: str,
    req: QueryRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    contract = get_contract(db, user.id, contract_id)

    if not contract:
        s = UPLOAD_STATUS.get(contract_id)

        if s and s.get("status") in {"queued", "processing"}:
            raise HTTPException(status_code=409, detail=f"Contract still {s['status']}. Retry after a few seconds.")

        if s and s.get("status") == "failed":
            raise HTTPException(status_code=400, detail=f"Contract processing failed: {s.get('error')}")

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

        logger.info(
            f"[API] Done user_id={user.id} contract_id={contract_id} intent={plan_obj.get('intent')} total_ms={total_ms}"
        )

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