import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List, Tuple

class VectorStore:
    def __init__(self, dim: int = 384):
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.index = faiss.IndexFlatL2(dim)
        self.texts: List[str] = []
        self.ids: List[int] = []   # clause_ids aligned with texts

    def add(self, items: List[Tuple[int, str]]):
        """
        items = [(clause_id, clause_text), ...]
        """
        if not items:
            return

        clause_ids, texts = zip(*items)  # tuple of ids, tuple of texts

        embeddings = self.model.encode(list(texts))           # shape: (N, 384)
        embeddings = np.array(embeddings).astype("float32")   # faiss needs float32

        self.index.add(embeddings)

        self.texts.extend(list(texts))
        self.ids.extend(list(clause_ids))

    def search(self, query: str, k: int = 5) -> List[Tuple[int, str]]:
        query_vec = self.model.encode([query])               # shape: (1, 384)
        query_vec = np.array(query_vec).astype("float32")

        _, indices = self.index.search(query_vec, k)

        results: List[Tuple[int, str]] = []
        for i in indices[0]:
            if 0 <= i < len(self.texts):
                results.append((self.ids[i], self.texts[i]))

        return results
    
    def search_with_scores(self, query: str, k: int = 5):
        query_vec = self.model.encode([query])
        query_vec = np.array(query_vec).astype("float32")

        distances, indices = self.index.search(query_vec, k)

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if 0 <= idx < len(self.texts):
                results.append(
                    (self.ids[idx], self.texts[idx], float(dist))
                )

        results.sort(key=lambda x: x[2])

        return results
