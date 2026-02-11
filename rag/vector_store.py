import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

class VectorStore:
    def __init__(self,dim=384):
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.index = faiss.IndexFlatL2(dim)  ##stores all clause embeddings
        self.texts = []

    def add(self,texts:list[str]):
        embeddings = self.model.encode(texts)
        embeddings = np.array(embeddings).astype('float32')
        self.index.add(embeddings)
        self.texts.extend(texts)


    def search(self,query:str,k : int = 5):
        query_vec = self.model.encode([query])
        query_vec = np.array(query_vec).astype('float32')

        _,indices = self.index.search(query_vec,k)  ##compares clause embeddings to query vec for similarity
        return [self.texts[i] for i in indices[0] if i < len(self.texts)]

    