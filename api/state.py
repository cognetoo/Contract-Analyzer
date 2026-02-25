from dataclasses import dataclass
from typing import Any, Dict, Optional
from threading import Lock

@dataclass
class ContractSession:
    store: Any
    vector_store: Any

_sessions: Dict[str, ContractSession] = {}
_lock = Lock()

def set_session(contract_id: str, session: ContractSession):
    with _lock:
        _sessions[contract_id] = session

def get_session(contract_id: str) -> Optional[ContractSession]:
    with _lock:
        return _sessions.get(contract_id)