import os
import json
from typing import List, Tuple, Optional

import faiss
import numpy as np

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

_MODEL: Optional[object] = None


def get_model():
    """
    Singleton: load SentenceTransformer only once per worker process.
    """
    global _MODEL
    if _MODEL is None:
        from sentence_transformers import SentenceTransformer
        _MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    return _MODEL


class VectorStore:
    def __init__(self, dim: int = 384):
        self.dim = dim
        self.index = faiss.IndexFlatL2(dim)
        self.texts: List[str] = []
        self.ids: List[int] = []

    def add(self, items: List[Tuple[int, str]], batch_size: int = 16):
        """
        items = [(clause_id, clause_text), ...]
        """
        if not items:
            return

        clause_ids, texts = zip(*items)
        model = get_model()

        embeddings = model.encode(
            list(texts),
            batch_size=batch_size,
            show_progress_bar=False,
        )
        embeddings = np.asarray(embeddings, dtype="float32")

        self.index.add(embeddings)
        self.texts.extend(list(texts))
        self.ids.extend(list(clause_ids))

    def search(self, query: str, k: int = 5) -> List[Tuple[int, str]]:
        model = get_model()
        query_vec = model.encode([query], show_progress_bar=False)
        query_vec = np.asarray(query_vec, dtype="float32")

        _, indices = self.index.search(query_vec, k)

        results: List[Tuple[int, str]] = []
        for i in indices[0]:
            if 0 <= i < len(self.texts):
                results.append((self.ids[i], self.texts[i]))
        return results

    def search_with_scores(self, query: str, k: int = 5) -> List[Tuple[int, str, float]]:
        model = get_model()
        query_vec = model.encode([query], show_progress_bar=False)
        query_vec = np.asarray(query_vec, dtype="float32")

        distances, indices = self.index.search(query_vec, k)

        results: List[Tuple[int, str, float]] = []
        for dist, idx in zip(distances[0], indices[0]):
            if 0 <= idx < len(self.texts):
                results.append((self.ids[idx], self.texts[idx], float(dist)))

        # smaller L2 distance = better match
        results.sort(key=lambda x: x[2])
        return results

    def save(self, index_path: str):
        os.makedirs(os.path.dirname(index_path), exist_ok=True)

        faiss.write_index(self.index, index_path)

        meta_path = index_path + ".meta.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump({"ids": self.ids, "texts": self.texts}, f, ensure_ascii=False)

    def load(self, index_path: str):
        self.index = faiss.read_index(index_path)

        meta_path = index_path + ".meta.json"
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        self.ids = meta.get("ids", [])
        self.texts = meta.get("texts", [])