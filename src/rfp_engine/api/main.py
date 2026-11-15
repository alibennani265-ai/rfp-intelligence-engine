import asyncio
import os
from pathlib import Path
from typing import Annotated, Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from loguru import logger
from pydantic import BaseModel

from rfp_engine.ingestion.parser import RFPParser
from rfp_engine.ingestion.study_ingestor import N7PastStudyIngestor
from rfp_engine.retrieval.vector_store import HybridSearchEngine
from rfp_engine.synthesis.generator import N7BiddingDossier, RFPSynthesizer

app = FastAPI(title="N7 Strategic Bidding Engine", version="1.3.0")

rfp_search_engine = HybridSearchEngine(collection_name="rfp_requirements")
knowledge_engine = HybridSearchEngine(collection_name="n7_past_studies")
if not knowledge_engine.documents and os.path.exists("data/past_studies"):
    N7PastStudyIngestor(
        collection_name="n7_past_studies", engine=knowledge_engine
    ).ingest_all("data/past_studies")

synthesizer = RFPSynthesizer()


class IngestResponse(BaseModel):
    status: str
    filename: str
    total_requirements: int
    message: str = "Document indexé avec succès."


class ChatRequest(BaseModel):
    question: str
    top_k: int = 6


class ChatResponse(BaseModel):
    question: str
    answer: str
    sources: list[dict[str, Any]]


@app.get("/health")
def health_check() -> dict[str, Any]:
    return {
        "status": "ok",
        "rfp_chunks": len(rfp_search_engine.documents),
        "knowledge_chunks": len(knowledge_engine.documents),
    }


@app.post("/upload", response_model=IngestResponse)
async def upload_pdf(file: Annotated[UploadFile, File(...)]):
    if not file.filename or not file.filename.endswith(".pdf"):
        raise HTTPException(
            status_code=400, detail="Seuls les fichiers PDF sont acceptés."
        )
    os.makedirs("data", exist_ok=True)
    save_path = os.path.join("data", file.filename)
    content = await file.read()
    await asyncio.to_thread(Path(save_path).write_bytes, content)

    rfp_search_engine.reset_collection()
    requirements = RFPParser(save_path).parse()
    docs = [
        {
            "id": r.requirement_id,
            "section": f"[CCTP CLIENT] {r.section}",
            "text": r.text,
            "metadata": r.metadata,
        }
        for r in requirements
    ]
    rfp_search_engine.index_documents(docs)
    return IngestResponse(
        status="ok", filename=file.filename, total_requirements=len(docs)
    )


@app.post("/ingest-past-studies")
def ingest_past_studies() -> dict[str, Any]:
    knowledge_engine.reset_collection()
    count = N7PastStudyIngestor(
        collection_name="n7_past_studies", engine=knowledge_engine
    ).ingest_all("data/past_studies")
    return {
        "status": "ok",
        "total_chunks": count,
        "message": f"{count} blocs CNJE & N7 indexés.",
    }


@app.post("/chat", response_model=ChatResponse)
def chat_with_rfp(request: ChatRequest) -> ChatResponse:
    rfp_docs = rfp_search_engine.search(query=request.question, top_k=request.top_k)

    # 1. Recherche ciblée sur l'expérience N7 Consulting et les filières ENSEEIHT
    n7_docs = knowledge_engine.search(
        query=f"{request.question} études réalisées N7 Consulting compétences filières ENSEEIHT SN 3EA MFEE tarif JEH",
        top_k=4,
    )
    for d in n7_docs:
        d["section"] = f"[EXPÉRIENCE & COMPÉTENCES N7] {d.get('section', 'N7')}"

    # 2. Recherche ciblée sur le Cadre Légal CNJE
    legal_docs = knowledge_engine.search(
        query=f"{request.question} cadre légal CLR CNJE régie pénalités de retard garantie propriété intellectuelle",
        top_k=4,
    )
    for d in legal_docs:
        d["section"] = f"[CADRE LÉGAL CNJE] {d.get('section', 'CLR CNJE')}"

    seen: set[str] = set()
    combined: list[dict[str, Any]] = []
    for doc in rfp_docs + n7_docs + legal_docs:
        key = str(doc.get("id", doc["text"][:50]))
        if key not in seen:
            seen.add(key)
            combined.append(doc)

    answer = synthesizer.answer_question(request.question, combined)
    return ChatResponse(question=request.question, answer=answer, sources=combined)


@app.get("/dossier-n7", response_model=N7BiddingDossier)
def generate_n7_dossier() -> N7BiddingDossier:
    if not rfp_search_engine.documents:
        raise HTTPException(
            status_code=400,
            detail="Aucun document indexé. Déposez d'abord un CCTP PDF.",
        )

    queries = [
        "objet du marché acheteur client contexte besoins techniques architecture livrables",
        "pénalités de retard déplafonnées responsabilité garantie maintenance astreinte",
        "régie intégration équipe feuille de temps horaires sous-traitance propriété intellectuelle",
        "budget chiffrage délais planning durée réalisation jours homme",
    ]
    seen: set[str] = set()
    aggregated: list[dict[str, Any]] = []
    for q in queries:
        for doc in rfp_search_engine.search(query=q, top_k=4):
            did = str(doc.get("id", doc["text"][:40]))
            if did not in seen:
                seen.add(did)
                aggregated.append(doc)

    n7_and_legal = knowledge_engine.search(
        query="filières ENSEEIHT études passées N7 Consulting tarif JEH règles CNJE pénalités régie garantie PI",
        top_k=5,
    )

    try:
        return synthesizer.generate_dossier(aggregated[:14], legal_chunks=n7_and_legal)
    except Exception as exc:
        logger.exception("Erreur lors de la génération du dossier N7")
        raise HTTPException(
            status_code=500, detail=f"Erreur génération dossier : {exc}"
        ) from exc
