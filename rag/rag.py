from rag.contract_store import CONTRACTS
import numpy as np


def embed(text:str):
    np.random.seed(abs(hash(text))% (10**6))
    return np.random.rand(384)

def cosine_similarity(a,b):
    return np.dot(a,b)/(np.linalg.norm(a)*np.linalg.norm(b))

DOC_EMBEDDINGS = [(embed(doc),doc) for doc in CONTRACTS]

def retrieval(query:str,top_k = 2):
    q_emb = embed(query)
    scores = []

    for emb,doc in DOC_EMBEDDINGS:
        score = cosine_similarity(q_emb,emb)
        scores.append((score,doc))

    scores.sort(reverse=True)
    return [doc for _,doc in scores[:top_k]]