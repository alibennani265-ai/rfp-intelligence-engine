import os
from typing import Any

from loguru import logger
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, PointStruct, VectorParams
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder, SentenceTransformer


class HybridSearchEngine:
    """Moteur de recherche hybride 2-Tier : Dense (BGE-M3) + Lexical (BM25) avec RRF et Cross-Encoder."""

    def __init__(
        self,
        collection_name: str = "rfp_requirements",
        embedding_model: str = "BAAI/bge-m3",
        reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        use_reranker: bool = True,
    ) -> None:
        self.collection_name = collection_name
        self.db_path = "data/qdrant_db"
        os.makedirs(self.db_path, exist_ok=True)

        self.client = QdrantClient(path=self.db_path)
        logger.info(
            f"Chargement du modèle d'embedding '{embedding_model}' ({self.collection_name})..."
        )
        self.encoder = SentenceTransformer(embedding_model)

        if hasattr(self.encoder, "get_embedding_dimension"):
            self.vector_size = self.encoder.get_embedding_dimension() or 1024
        else:
            self.vector_size = self.encoder.get_sentence_embedding_dimension() or 1024

        self.use_reranker = use_reranker
        self.reranker = CrossEncoder(reranker_model) if use_reranker else None

        self.bm25: BM25Okapi | None = None
        self.documents: list[dict[str, Any]] = []

        self._ensure_collection_exists()
        self._hydrate_lexical_index_from_qdrant()

    def _ensure_collection_exists(self) -> None:
        collections = [col.name for col in self.client.get_collections().collections]
        if self.collection_name not in collections:
            logger.info(f"Création de la collection Qdrant : '{self.collection_name}'")
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size, distance=Distance.COSINE
                ),
            )

    def _hydrate_lexical_index_from_qdrant(self) -> None:
        """Reconstruit l'index BM25 en mémoire à partir des payloads persistés dans Qdrant."""
        try:
            records, _ = self.client.scroll(
                collection_name=self.collection_name,
                limit=1000,
                with_payload=True,
                with_vectors=False,
            )
            if records:
                self.documents = [
                    {
                        "id": (rec.payload or {}).get("doc_id", str(rec.id)),
                        "section": (rec.payload or {}).get("section", "N/A"),
                        "text": (rec.payload or {}).get("text", ""),
                        "metadata": (rec.payload or {}).get("metadata", {}),
                    }
                    for rec in records
                    if (rec.payload or {}).get("text")
                ]
                if self.documents:
                    corpus = [doc["text"].lower().split() for doc in self.documents]
                    self.bm25 = BM25Okapi(corpus)
                    logger.info(
                        f"Index lexical BM25 restauré ({len(self.documents)} chunks)."
                    )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                f"Impossible de restaurer l'index BM25 depuis Qdrant : {exc}"
            )

    def index_documents(self, docs: list[dict[str, Any]]) -> None:
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

        points = [
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
            for idx, (doc, vector) in enumerate(zip(docs, embeddings, strict=True))
        ]

        self.client.upsert(collection_name=self.collection_name, points=points)
        logger.info(
            f"{len(docs)} chunks indexés dans Qdrant ('{self.collection_name}')."
        )

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Exécute une recherche hybride (Dense + BM25 via RRF) suivie d'un Cross-Encoder Reranking."""
        candidate_k = max(top_k * 3, 15)
        query_vector = self.encoder.encode(query).tolist()

        
        # 1. Tier 1A : Recherche Dense (Qdrant)
        dense_hits: list[dict[str, Any]] = []
        try:
            response = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                limit=candidate_k,
                with_payload=True,
            )
            raw_points = response.points if hasattr(response, "points") else response

            for res in raw_points:
                payload = getattr(res, "payload", {}) or {}
                if payload.get("text"):
                    dense_hits.append(
                        {
                            "id": payload.get("doc_id"),
                            "section": payload.get("section"),
                            "text": payload.get("text"),
                            "score": float(getattr(res, "score", 0.0)),
                            "metadata": payload.get("metadata", {}),
                        }
                    )
        except Exception as exc:  # noqa: BLE001
            logger.error(f"Erreur recherche vectorielle Qdrant : {exc}")

        # 2. Tier 1B : Recherche Lexicale (BM25)
        lexical_hits: list[dict[str, Any]] = []
        if self.bm25 and self.documents:
            tokenized_query = query.lower().split()
            bm25_scores = self.bm25.get_scores(tokenized_query)
            top_indices = sorted(
                range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True
            )[:candidate_k]
            for idx in top_indices:
                if bm25_scores[idx] > 0:
                    doc = self.documents[idx]
                    lexical_hits.append(
                        {
                            "id": doc.get("id"),
                            "section": doc.get("section"),
                            "text": doc.get("text"),
                            "score": float(bm25_scores[idx]),
                            "metadata": doc.get("metadata", {}),
                        }
                    )

        # 3. Fusion Reciprocal Rank Fusion (RRF)
        rrf_scores: dict[str, float] = {}
        doc_registry: dict[str, dict[str, Any]] = {}
        rrf_k = 60

        for rank, item in enumerate(dense_hits, start=1):
            doc_key = str(item["id"] or item["text"][:60])
            doc_registry[doc_key] = item
            rrf_scores[doc_key] = rrf_scores.get(doc_key, 0.0) + (1.0 / (rrf_k + rank))

        for rank, item in enumerate(lexical_hits, start=1):
            doc_key = str(item["id"] or item["text"][:60])
            doc_registry[doc_key] = item
            rrf_scores[doc_key] = rrf_scores.get(doc_key, 0.0) + (1.0 / (rrf_k + rank))

        fused_candidates = [
            {**doc_registry[key], "rrf_score": score}
            for key, score in sorted(
                rrf_scores.items(), key=lambda x: x[1], reverse=True
            )
        ][:candidate_k]

        # 4. Tier 2 : Cross-Encoder Reranking
        if self.use_reranker and self.reranker and fused_candidates:
            pairs = [(query, cand["text"]) for cand in fused_candidates]
            ce_scores = self.reranker.predict(pairs)
            for cand, ce_score in zip(fused_candidates, ce_scores, strict=True):
                cand["score"] = float(ce_score)
            fused_candidates.sort(key=lambda x: x["score"], reverse=True)

        return fused_candidates[:top_k]

    def close(self) -> None:
        try:
            if hasattr(self.client, "close"):
                self.client.close()
        except Exception as exc:  # noqa: BLE001
            logger.debug(f"Fermeture client Qdrant : {exc}")
