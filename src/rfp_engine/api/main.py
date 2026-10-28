from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from rfp_engine.config import settings
from rfp_engine.retrieval.vector_store import HybridSearchEngine

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="API d'analyse et de recherche d'exigences dans les Appels d'Offres (RFP)",
)

search_engine = HybridSearchEngine()


class IndexRequest(BaseModel):
    documents: List[Dict[str, Any]]


class SearchQuery(BaseModel):
    query: str
    top_k: int = 3


@app.get("/")
def health_check():
    return {"status": "ok", "app": settings.app_name, "env": settings.env}


@app.post("/index")
def index_documents(payload: IndexRequest):
    if not payload.documents:
        raise HTTPException(status_code=400, detail="La liste de documents est vide.")
    search_engine.index_documents(payload.documents)
    return {"message": f"{len(payload.documents)} documents indexés."}


@app.post("/search")
def search_requirements(query: SearchQuery):
    results = search_engine.search(query.query, top_k=query.top_k)
    return {"query": query.query, "results": results}