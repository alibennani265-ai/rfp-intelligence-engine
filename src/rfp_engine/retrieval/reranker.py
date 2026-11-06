from typing import Any, Dict, List
from loguru import logger
from sentence_transformers import CrossEncoder


class DocumentReranker:

    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
    ):
        logger.info(f"Chargement du Cross-Encoder Reranker ({model_name})...")
        self.model = CrossEncoder(model_name)

    def rerank(
        self, query: str, docs: List[Dict[str, Any]], top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Réordonne les documents hybrides (Vector + BM25) en calculant le score Cross-Encoder exact."""
        if not docs:
            return []

        pairs = [[query, doc.get("text", "")] for doc in docs]
        scores = self.model.predict(pairs)

        for doc, score in zip(docs, scores):
            doc["rerank_score"] = float(score)

        # Tri par score dégressif
        sorted_docs = sorted(
            docs, key=lambda x: x["rerank_score"], reverse=True
        )
        return sorted_docs[:top_k]