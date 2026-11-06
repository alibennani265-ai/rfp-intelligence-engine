from typing import Any, Dict, List
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from rfp_engine.config import settings
from rfp_engine.ingestion.parser import RFPParser
from rfp_engine.retrieval.vector_store import HybridSearchEngine
from rfp_engine.synthesis.generator import RFPSynthesizer, RFPSynthesisReport

app = FastAPI(
    title=settings.app_name,
    description="Moteur d'analyse d'appels d'offres, recherche hybride & synthèse LLM (Llama 3.1 Local)",
    version="0.1.0",
)

engine = HybridSearchEngine()
synthesizer = RFPSynthesizer(model_name="ollama/llama3.1:8b")


class IngestResponse(BaseModel):
    message: str
    total_requirements: int


class SearchResponse(BaseModel):
    query: str
    count: int
    results: List[Dict[str, Any]]


@app.get("/health")
def health_check():
    return {"status": "ok", "app": settings.app_name}


@app.post("/index", response_model=IngestResponse)
def index_rfp(pdf_path: str = "data/sample_rfp.pdf"):
    try:
        parser = RFPParser(pdf_path)
        requirements = parser.parse()
        docs = [
            {
                "id": req.requirement_id,
                "section": req.section,
                "text": req.text,
                "metadata": req.metadata,
            }
            for req in requirements
        ]
        engine.index_documents(docs)
        return IngestResponse(
            message=f"Document {pdf_path} indexé avec succès.",
            total_requirements=len(docs),
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Fichier PDF non trouvé.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/search", response_model=SearchResponse)
def search_requirements(
    q: str = Query(..., description="Requête en langage naturel"),
    top_k: int = Query(3, ge=1, le=20),
):
    results = engine.search(query=q, top_k=top_k)
    return SearchResponse(query=q, count=len(results), results=results)


@app.post("/synthesize", response_model=RFPSynthesisReport)
def synthesize_rfp(
    query: str = Query(
        "Propriété intellectuelle et ingénieur Full Stack",
        description="Sujet ou thématique à analyser",
    ),
    top_k: int = Query(5, ge=1, le=20),
):
    """
    Récupère les exigences via la recherche hybride (BM25 + Qdrant BGE-M3)
    puis génère une Matrice de Conformité par LLM Llama 3.1 (8B) local.
    """
    retrieved_docs = engine.search(query=query, top_k=top_k)
    if not retrieved_docs:
        raise HTTPException(
            status_code=404, detail="Aucune exigence trouvée."
        )

    return synthesizer.generate_matrix(retrieved_docs)