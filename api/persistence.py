from datetime import datetime
from typing import List, Optional, Tuple, Any

from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select

from api.models import Contract, Clause, ContractResult,ContractRun


# clause_rows: List[(clause_id:int, text:str, clause_type:str|None)]
ClauseRow = Tuple[int, str, Optional[str]]


def create_contract(
    db: Session,
    contract_id: str,
    filename: str,
    pdf_path: str,
    index_path: str,
    clauses: List[ClauseRow],
):
    # create contract
    c = Contract(
        contract_id=contract_id,
        filename=filename,
        pdf_path=pdf_path,
        index_path=index_path,
        num_clauses=len(clauses),
    )
    db.add(c)

    # create clause rows
    for clause_id, text, clause_type in clauses:
        db.add(
            Clause(
                contract_id=contract_id,
                clause_id=int(clause_id),
                text=text,
                clause_type=clause_type,
            )
        )

    # create last_result row
    db.add(ContractResult(contract_id=contract_id, last_result=None, updated_at=datetime.utcnow()))

    db.commit()


def get_contract(db: Session, contract_id: str) -> Optional[Contract]:
    stmt = (
        select(Contract)
        .where(Contract.contract_id == contract_id)
        .options(selectinload(Contract.clauses))
    )
    return db.execute(stmt).scalars().first()


def set_last_result(db: Session, contract_id: str, result: Any):
    # store dict for JSON
    if not isinstance(result, dict):
        result = {"text": str(result)}

    r = db.get(ContractResult, contract_id)
    if not r:
        r = ContractResult(contract_id=contract_id, last_result=result, updated_at=datetime.utcnow())
        db.add(r)
    else:
        r.last_result = result
        r.updated_at = datetime.utcnow()

    db.commit()


def get_last_result(db: Session, contract_id: str):
    r = db.get(ContractResult, contract_id)
    return None if not r else r.last_result

def add_run(
    db: Session,
    contract_id: str,
    query: str,
    plan: Any,
    result: Any,
    perf_ms: Any,
):
    # store dict for JSON safety
    if not isinstance(plan, dict):
        plan = {"text": str(plan)}
    if not isinstance(result, dict):
        result = {"text": str(result)}
    if not isinstance(perf_ms, dict):
        perf_ms = {"text": str(perf_ms)}

    db.add(
        ContractRun(
            contract_id=contract_id,
            query=query,
            plan=plan,
            result=result,
            perf_ms=perf_ms,
        )
    )
    db.commit()


def get_history(db: Session, contract_id: str, limit: int = 10):
    stmt = (
        select(ContractRun)
        .where(ContractRun.contract_id == contract_id)
        .order_by(ContractRun.created_at.desc())
        .limit(limit)
    )
    return db.execute(stmt).scalars().all()