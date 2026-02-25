from pydantic import BaseModel
from typing import Any, Dict, Optional,List
from datetime import datetime

class UploadResponse(BaseModel):
    contract_id: str
    status: str = "indexed"
    filename: str
    num_clauses: int
    tmp_path: Optional[str] = None

class QueryRequest(BaseModel):
    query: str
    k: Optional[int] = None
    mode: Optional[str] = None 

class QueryResponse(BaseModel):
    contract_id: str
    plan: Dict[str, Any]
    result: Any
    perf_ms: Dict[str, float]

class HistoryItem(BaseModel):
    id:int
    created_at: datetime
    query: str
    plan: Dict[str, Any]
    result: Any
    perf_ms: Dict[str, Any]

class HistoryResponse(BaseModel):
    contract_id: str
    runs: List[HistoryItem]