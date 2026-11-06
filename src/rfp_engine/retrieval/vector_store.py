from typing import Any, Dict, List
from loguru import logger
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

from rfp_engine.config import settings


class HybridSearchEngine:

    def __init__(self, storage_path: str = "data/qdrant_db"):
        logger.info(
            f"Chargement du modèle d'embedding : {settings.embedding_model_name}"
        )
        self.encoder = SentenceTransformer(settings.embedding_model_name)

        self.client = QdrantClient(path=storage_path)
        self.collection_name = "rfp_requirements"
        self.documents: List[Dict[str, Any]] = []
        self.bm25: BM25Okapi | None = None

        self._ensure_collection()
        self._load_from_qdrant()

    def _ensure_collection(self) -> None:
        collections = [
            c.name for c in self.client.get_collections().collections
        ]
        if self.collection_name not in collections:
            embedding_dim = self.encoder.get_embedding_dimension()
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=embedding_dim, distance=Distance.COSINE
                ),
            )
            logger.info(f"Collection Qdrant '{self.collection_name}' créée.")

    def _load_from_qdrant(self) -> None:
        """Restaure les documents et réindexe BM25 depuis Qdrant au démarrage."""
        try:
            records, _ = self.client.scroll(
                collection_name=self.collection_name,
                limit=10000,
                with_payload=True,
                with_vectors=True,
            )
            if records:
                self.documents = []
                for r in records:
                    self.documents.append(
                        {
                            "id": r.payload.get("req_id"),
                            "section": r.payload.get("section"),
                            "text": r.payload.get("text"),
                            "metadata": r.payload.get("metadata", {}),
                            "vector": r.vector,
                        }
                    )
                corpus_tokens = [
                    doc["text"].lower().split() for doc in self.documents
                ]
                self.bm25 = BM25Okapi(corpus_tokens)
                logger.info(
                    f"{len(self.documents)} documents restaurés depuis Qdrant."
                )
        except Exception as e:
            logger.warning(
                f"Impossible de charger les données existantes : {e}"
            )

    def index_documents(self, docs: List[Dict[str, Any]]) -> None:
        self.documents = docs
        corpus_tokens = [doc["text"].lower().split() for doc in docs]
        self.bm25 = BM25Okapi(corpus_tokens)

        texts = [doc["text"] for doc in docs]
        embeddings = self.encoder.encode(texts, show_progress_bar=False)

        points = []
        for idx, (doc, emb) in enumerate(zip(docs, embeddings)):
            doc["vector"] = emb.tolist()
            points.append(
                PointStruct(
                    id=idx,
                    vector=emb.tolist(),
                    payload={
                        "req_id": doc["id"],
                        "section": doc["section"],
                        "text": doc["text"],
                        "metadata": doc.get("metadata", {}),
                    },
                )
            )

        self.client.upsert(collection_name=self.collection_name, points=points)
        logger.info(f"{len(docs)} documents indexés et stockés dans Qdrant.")

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        if not self.documents or not self.bm25:
            return []

        tokenized_query = query.lower().split()
        bm25_scores = self.bm25.get_scores(tokenized_query)

        top_indices = sorted(
            range(len(bm25_scores)),
            key=lambda i: bm25_scores[i],
            reverse=True,
        )[:top_k]

        results = []
        for idx in top_indices:
            doc = self.documents[idx].copy()
            doc["score"] = float(bm25_scores[idx])
            doc.pop("vector", None)
            results.append(doc)

        return results

