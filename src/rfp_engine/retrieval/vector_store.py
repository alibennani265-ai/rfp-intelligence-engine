from typing import List, Dict, Any
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer
from loguru import logger
from rfp_engine.config import settings


class HybridSearchEngine:
    def __init__(self):
        logger.info(f"Chargement du modèle d'embedding : {settings.embedding_model_name}")
        self.encoder = SentenceTransformer(settings.embedding_model_name)
        self.documents: List[Dict[str, Any]] = []
        self.bm25: BM25Okapi | None = None

    def index_documents(self, docs: List[Dict[str, Any]]) -> None:
        self.documents = docs
        corpus_tokens = [doc["text"].lower().split() for doc in docs]
        self.bm25 = BM25Okapi(corpus_tokens)
        
        texts = [doc["text"] for doc in docs]
        embeddings = self.encoder.encode(texts, show_progress_bar=False)
        for i, emb in enumerate(embeddings):
            self.documents[i]["vector"] = emb.tolist()
        
        logger.info(f"{len(docs)} documents indexés avec succès.")

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        if not self.documents or not self.bm25:
            return []

        tokenized_query = query.lower().split()
        bm25_scores = self.bm25.get_scores(tokenized_query)

        top_indices = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)[:top_k]

        results = []
        for idx in top_indices:
            doc = self.documents[idx].copy()
            doc["score"] = float(bm25_scores[idx])
            doc.pop("vector", None)
            results.append(doc)

        return results