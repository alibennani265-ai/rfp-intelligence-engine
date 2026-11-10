import os
from typing import Any, Dict, List
from loguru import logger
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, PointStruct, VectorParams
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer


class HybridSearchEngine:

    def __init__(
        self,
        collection_name: str = "rfp_requirements",
        embedding_model: str = "BAAI/bge-m3",
    ):
        self.collection_name = collection_name
        self.db_path = "data/qdrant_db"
        os.makedirs(self.db_path, exist_ok=True)

        self.client = QdrantClient(path=self.db_path)
        logger.info(
            f"Initialisation de l'embedding model : {embedding_model} sur collection '{self.collection_name}'..."
        )
        self.encoder = SentenceTransformer(embedding_model)

        if hasattr(self.encoder, "get_embedding_dimension"):
            self.vector_size = self.encoder.get_embedding_dimension()
        else:
            self.vector_size = self.encoder.get_sentence_embedding_dimension()

        self.bm25 = None
        self.documents: List[Dict[str, Any]] = []
        self._ensure_collection_exists()

    def _ensure_collection_exists(self):
        collections = [
            col.name for col in self.client.get_collections().collections
        ]
        if self.collection_name not in collections:
            logger.info(
                f"Création de la collection Qdrant : '{self.collection_name}'..."
            )
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size, distance=Distance.COSINE
                ),
            )

    def index_documents(self, docs: List[Dict[str, Any]]):
        if not docs:
            logger.warning("Aucun document à indexer.")
            return

        self.documents = docs
        corpus = [doc["text"].lower().split() for doc in docs]
        self.bm25 = BM25Okapi(corpus)

        texts = [doc["text"] for doc in docs]
        embeddings = self.encoder.encode(
            texts, show_progress_bar=False, convert_to_numpy=True
        )

        points = []
        for idx, (doc, vector) in enumerate(zip(docs, embeddings)):
            points.append(
                PointStruct(
                    id=idx,
                    vector=vector.tolist(),
                    payload={
                        "doc_id": doc.get("id", f"doc_{idx}"),
                        "section": doc.get("section", "N/A"),
                        "text": doc["text"],
                        "metadata": doc.get("metadata", {}),
                    },
                )
            )

        self.client.upsert(
            collection_name=self.collection_name, points=points
        )
        logger.info(
            f"{len(docs)} documents indexés dans la collection Qdrant '{self.collection_name}'."
        )

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        query_vector = self.encoder.encode(query).tolist()
        results = []

        # 1. Recherche Vectorielle Qdrant
        try:
            if hasattr(self.client, "query_points"):
                response = self.client.query_points(
                    collection_name=self.collection_name,
                    query=query_vector,
                    limit=top_k,
                    with_payload=True,
                )
                search_result = (
                    response.points if hasattr(response, "points") else response
                )
            elif hasattr(self.client, "search"):
                search_result = self.client.search(
                    collection_name=self.collection_name,
                    query_vector=query_vector,
                    limit=top_k,
                    with_payload=True,
                )
            else:
                search_result = []

            for res in search_result:
                payload = getattr(res, "payload", {}) or {}
                text = payload.get("text", "")
                if text:
                    results.append(
                        {
                            "id": payload.get("doc_id"),
                            "section": payload.get("section"),
                            "text": text,
                            "score": float(getattr(res, "score", 0.0)),
                            "metadata": payload.get("metadata", {}),
                        }
                    )
        except Exception as e:
            logger.error(f"Erreur recherche Qdrant: {e}")

        # 2. Secours Hybride BM25 si la recherche vectorielle ne retourne rien
        if not results and self.bm25 and self.documents:
            tokenized_query = query.lower().split()
            bm25_scores = self.bm25.get_scores(tokenized_query)
            top_indices = sorted(
                range(len(bm25_scores)),
                key=lambda i: bm25_scores[i],
                reverse=True,
            )[:top_k]
            for idx in top_indices:
                if bm25_scores[idx] > 0:
                    doc = self.documents[idx]
                    results.append(
                        {
                            "id": doc.get("id"),
                            "section": doc.get("section"),
                            "text": doc.get("text"),
                            "score": float(bm25_scores[idx]),
                            "metadata": doc.get("metadata", {}),
                        }
                    )

        return results

    def close(self):
        try:
            if hasattr(self.client, "close"):
                self.client.close()
        except Exception:
            pass