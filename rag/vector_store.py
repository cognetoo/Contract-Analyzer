import os
import json
from typing import List, Tuple, Optional

import faiss
import numpy as np


# ---- Lazy model loader  ----
_MODEL: Optional[object] = None

def _get_model():
    """
    Loads SentenceTransformer only when needed.
    This prevents Render from timing out during startup/import.
    """
    global _MODEL
    if _MODEL is None:
        from sentence_transformers import SentenceTransformer
        _MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    return _MODEL


class VectorStore:
    def __init__(self, dim: int = 384, load_model_on_init: bool = False):
        self.dim = dim
        self.index = faiss.IndexFlatL2(dim)
        self.texts: List[str] = []
        self.ids: List[int] = []  # clause_ids aligned with texts

        # Load only when embeddings are needed.
        self._model = None
        if load_model_on_init:
            self._model = _get_model()

    def _encode(self, texts: List[str]) -> np.ndarray:
        model = self._model or _get_model()
        emb = model.encode(texts, normalize_embeddings=True)
        return np.asarray(emb, dtype="float32")

    def add(self, items: List[Tuple[int, str]]):
        """
        items = [(clause_id, clause_text), ...]
        """
        if not items:
            return

        clause_ids, texts = zip(*items)
        embeddings = self._encode(list(texts))
        self.index.add(embeddings)

        self.texts.extend(list(texts))
        self.ids.extend(list(clause_ids))

    def search(self, query: str, k: int = 5) -> List[Tuple[int, str]]:
        query_vec = self._encode([query])
        _, indices = self.index.search(query_vec, k)

        results: List[Tuple[int, str]] = []
        for i in indices[0]:
            if 0 <= i < len(self.texts):
                results.append((self.ids[i], self.texts[i]))
        return results

    def search_with_scores(self, query: str, k: int = 5) -> List[Tuple[int, str, float]]:
        query_vec = self._encode([query])
        distances, indices = self.index.search(query_vec, k)

        results: List[Tuple[int, str, float]] = []
        for dist, idx in zip(distances[0], indices[0]):
            if 0 <= idx < len(self.texts):
                results.append((self.ids[idx], self.texts[idx], float(dist)))

        # smaller L2 dist = better
        results.sort(key=lambda x: x[2])
        return results

    def save(self, index_path: str):
        """
        Saves FAISS index + ids/texts mapping.
        """
        os.makedirs(os.path.dirname(index_path), exist_ok=True)
        faiss.write_index(self.index, index_path)

        meta_path = index_path + ".meta.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump({"ids": self.ids, "texts": self.texts}, f, ensure_ascii=False)

    def load(self, index_path: str):
        """
        Loads FAISS index + ids/texts mapping.
        Note: does NOT require embedding model.
        """
        self.index = faiss.read_index(index_path)

        meta_path = index_path + ".meta.json"
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        self.ids = meta.get("ids", [])
        self.texts = meta.get("texts", [])