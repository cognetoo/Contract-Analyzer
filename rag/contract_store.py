from typing import List, Optional, Dict

class ContractStore:
    def __init__(self):
        self.clauses: List[Dict] = []

    def add_clause(self, clause_text: str, clause_type: str, metadata: Optional[dict] = None) -> int:
        clause_id = len(self.clauses) + 1  # 1-based ID
        self.clauses.append({
            "clause_id": clause_id,
            "text": clause_text,
            "type": clause_type,
            "metadata": metadata or {}
        })
        return clause_id

    def add_clauses_batch(self, clauses: List[str], clause_types: List[str], metadatas: Optional[List[dict]] = None):
        """
        Batch insert clauses safely.
        Ensures each clause has clause_id, type, and metadata.
        """
        if len(clauses) != len(clause_types):
            raise ValueError("clauses and clause_types must have the same length")

        if metadatas is None:
            metadatas = [None] * len(clauses)
        elif len(metadatas) != len(clauses):
            raise ValueError("metadatas must be same length as clauses (or None)")

        for clause_text, clause_type, md in zip(clauses, clause_types, metadatas):
            self.add_clause(clause_text=clause_text, clause_type=clause_type, metadata=md)

    def get_by_type(self, clause_type: str):
        return [c for c in self.clauses if c["type"] == clause_type]
