class ContractStore:
    def __init__(self):
        self.clauses = []

    def add_clause(self, clause_text, clause_type, metadata=None):
        self.clauses.append({
            "text": clause_text,
            "type": clause_type,
            "metadata": metadata or {}
        })

    def get_by_type(self, clause_type):
        return [c for c in self.clauses if c["type"] == clause_type]
