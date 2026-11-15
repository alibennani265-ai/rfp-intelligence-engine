import os
import uuid
from typing import Any

from loguru import logger
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, PointStruct, VectorParams
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder, SentenceTransformer


class HybridSearchEngine:
    _shared_client: QdrantClient | None = None

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

        if HybridSearchEngine._shared_client is None:
            HybridSearchEngine._shared_client = QdrantClient(path=self.db_path)
        self.client = HybridSearchEngine._shared_client

        self.encoder = SentenceTransformer(embedding_model)
        self.encoder.max_seq_length = 512
        self.vector_size: int = self.encoder.get_sentence_embedding_dimension() or 1024
        self.use_reranker = use_reranker
        self.reranker = CrossEncoder(reranker_model) if use_reranker else None
        self.bm25: BM25Okapi | None = None
        self.documents: list[dict[str, Any]] = []

        self._ensure_collection_exists()
        self._hydrate_lexical_index_from_qdrant()

    def _ensure_collection_exists(self) -> None:
        collections = [col.name for col in self.client.get_collections().collections]
        if self.collection_name not in collections:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size, distance=Distance.COSINE
                ),
            )

    def reset_collection(self) -> None:
        collections = [col.name for col in self.client.get_collections().collections]
        if self.collection_name in collections:
            self.client.delete_collection(collection_name=self.collection_name)
        self._ensure_collection_exists()
        self.documents = []
        self.bm25 = None

    def _hydrate_lexical_index_from_qdrant(self) -> None:
        records, _ = self.client.scroll(
            collection_name=self.collection_name,
            limit=2000,
            with_payload=True,
            with_vectors=False,
        )
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
            self.bm25 = BM25Okapi(
                [doc["text"].lower().split() for doc in self.documents]
            )

    def index_documents(self, docs: list[dict[str, Any]]) -> None:
        if not docs:
            return
        logger.info(f"Encodage de {len(docs)} blocs pour '{self.collection_name}'...")
        embeddings = self.encoder.encode(
            [doc["text"] for doc in docs],
            batch_size=16,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        points = [
            PointStruct(
                id=str(
                    uuid.uuid5(
                        uuid.NAMESPACE_DNS,
                        f"{self.collection_name}_{doc.get('id', idx)}_{doc['text'][:80]}",
                    )
                ),
                vector=vector.tolist(),
                payload={
                    "doc_id": str(doc.get("id", f"doc_{idx}")),
                    "section": doc.get("section", "N/A"),
                    "text": doc["text"],
                    "metadata": doc.get("metadata", {}),
                },
            )
            for idx, (doc, vector) in enumerate(zip(docs, embeddings, strict=True))
        ]
        self.client.upsert(collection_name=self.collection_name, points=points)
        self._hydrate_lexical_index_from_qdrant()

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        if not self.documents:
            return []
        candidate_k = max(top_k * 3, 15)
        query_vector = self.encoder.encode(query).tolist()

        response = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=candidate_k,
            with_payload=True,
        )
        raw_points = response.points if hasattr(response, "points") else response
        dense_hits = [
            {
                "id": (res.payload or {}).get("doc_id"),
                "section": (res.payload or {}).get("section"),
                "text": (res.payload or {}).get("text"),
                "score": float(getattr(res, "score", 0.0)),
                "metadata": (res.payload or {}).get("metadata", {}),
            }
            for res in raw_points
            if (res.payload or {}).get("text")
        ]

        lexical_hits: list[dict[str, Any]] = []
        if self.bm25:
            scores = self.bm25.get_scores(query.lower().split())
            for idx in sorted(
                range(len(scores)), key=lambda i: scores[i], reverse=True
            )[:candidate_k]:
                if scores[idx] > 0:
                    doc = self.documents[idx]
                    lexical_hits.append({**doc, "score": float(scores[idx])})

        rrf_scores: dict[str, float] = {}
        registry: dict[str, dict[str, Any]] = {}
        for rank, item in enumerate(dense_hits, start=1):
            k = str(item["id"] or item["text"][:60])
            registry[k] = item
            rrf_scores[k] = rrf_scores.get(k, 0.0) + 1.0 / (60 + rank)
        for rank, item in enumerate(lexical_hits, start=1):
            k = str(item["id"] or item["text"][:60])
            registry[k] = item
            rrf_scores[k] = rrf_scores.get(k, 0.0) + 1.0 / (60 + rank)

        fused = [
            {**registry[k], "rrf_score": s}
            for k, s in sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        ][:candidate_k]
        if self.use_reranker and self.reranker and fused:
            ce_scores = self.reranker.predict([(query, c["text"]) for c in fused])
            for c, s in zip(fused, ce_scores, strict=True):
                c["score"] = float(s)
            fused.sort(key=lambda x: x["score"], reverse=True)
        return fused[:top_k]

    def close(self) -> None:
        pass
