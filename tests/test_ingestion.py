import pytest
from rfp_engine.retrieval.vector_store import HybridSearchEngine


def test_hybrid_search_indexing_and_retrieval():
    engine = HybridSearchEngine()
    docs = [
        {"id": "1", "text": "L'architecture doit respecter la norme ISO 27001 pour la sécurité."},
        {"id": "2", "text": "Le temps de réponse de l'API doit être inférieur à 200ms."},
    ]
    engine.index_documents(docs)

    results = engine.search("ISO 27001 sécurité", top_k=1)
    assert len(results) == 1
    assert results[0]["id"] == "1"