import numpy as np
from llm import call_llm
from sentence_transformers import SentenceTransformer
from rag.vector_store import VectorStore

#Load the embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")


#Define risk templates
RISK_TEMPLATES = {
    "Unilateral Termination": "Clause allows one party to terminate without cause or at will.",
    "Broad Confidentiality": "Confidentiality clause applies indefinitely or worldwide.",
    "Mandatory Arbitration": "Disputes must be resolved through arbitration instead of court.",
    "Non-Compete": "Employee restricted from working with competitors after employment.",
    "Unlimited Liability": "One party bears unlimited liability without cap."
}

def embed(text):
    return model.encode(text)

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


# Pre-embed risk templates
TEMPLATE_EMBEDDINGS = {
    risk: embed(description)
    for risk, description in RISK_TEMPLATES.items()
}


##Hybrid risk analyzer

def analyze_risks_hybrid(store, similarity_threshold=0.55):
    """
    Hybrid Risk Engine:
    - Semantic similarity for candidate detection
    - LLM for structured risk reasoning
    """

    risk_report = []

    for clause in store.clauses:
        clause_text = clause["text"]
        clause_embedding = embed(clause_text)

        # Step 1: Semantic filtering
        for risk_type, template_embedding in TEMPLATE_EMBEDDINGS.items():

            score = cosine_similarity(clause_embedding, template_embedding)

            if score > similarity_threshold:

                # Step 2: LLM Risk Evaluation
                llm_response = evaluate_clause_with_llm(clause_text, risk_type)

                risk_report.append({
                    "risk_type": risk_type,
                    "similarity_score": round(float(score), 3),
                    "llm_analysis": llm_response,
                    "clause_text": clause_text
                })

    return risk_report


#LLM structured evaluation

def evaluate_clause_with_llm(clause_text, predicted_risk_type):

    system_prompt = """
You are a legal risk analysis assistant.

Analyze the clause and determine:
- Is the predicted risk type valid?
- Risk Level (Low / Medium / High)
- Short Explanation (2-3 sentences)
- Confidence (0-100%)

Respond in this structured format:

Risk Valid: Yes/No
Risk Level:
Explanation:
Confidence:
"""

    user_prompt = f"""
Predicted Risk Type: {predicted_risk_type}

Clause:
{clause_text}
"""

    return call_llm(system_prompt=system_prompt, user_prompt=user_prompt)