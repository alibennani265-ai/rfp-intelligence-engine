import asyncio
import os
from pathlib import Path
from typing import Annotated, Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

from rfp_engine.ingestion.parser import RFPParser
from rfp_engine.ingestion.study_ingestor import N7PastStudyIngestor
from rfp_engine.retrieval.vector_store import HybridSearchEngine
from rfp_engine.synthesis.generator import N7BiddingDossier, RFPSynthesizer

app = FastAPI(
    title="N7 Strategic Bidding Engine",
    description="RAG Hybride & Copilot d'Avant-Vente pour N7 Consulting (ENSEEIHT)",
    version="1.0.0",
)

search_engine = HybridSearchEngine(collection_name="rfp_requirements")
synthesizer = RFPSynthesizer()


class IngestResponse(BaseModel):
    status: str
    filename: str
    total_requirements: int
    message: str = "Document indexé avec succès."


class ChatRequest(BaseModel):
    question: str
    top_k: int = 5


class ChatResponse(BaseModel):
    question: str
    answer: str
    sources: list[dict[str, Any]]


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "app": "N7 Strategic Bidding Engine"}


@app.post("/upload", response_model=IngestResponse)
async def upload_pdf(file: Annotated[UploadFile, File(...)]):
    if not file.filename or not file.filename.endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Seuls les fichiers PDF sont acceptés.",
        )

    os.makedirs("data", exist_ok=True)
    save_path = os.path.join("data", file.filename)

    content = await file.read()
    await asyncio.to_thread(Path(save_path).write_bytes, content)

    try:
        parser = RFPParser(save_path)
        requirements = parser.parse()

        docs = [
            {
                "id": getattr(req, "id", f"req_{idx}"),
                "section": req.section,
                "text": req.text,
                "metadata": req.metadata,
            }
            for idx, req in enumerate(requirements)
        ]
        search_engine.index_documents(docs)

        return IngestResponse(
            status="ok",
            filename=file.filename,
            total_requirements=len(docs),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur d'indexation: {e!s}") from e


@app.post("/ingest-past-studies")
def ingest_past_studies() -> dict[str, str]:
    ingestor = N7PastStudyIngestor(
        collection_name=search_engine.collection_name,
        engine=search_engine,
    )
    count = ingestor.ingest_all("data/past_studies")
    return {
        "status": "ok",
        "message": f"{count} blocs d'anciennes études N7 indexés dans Qdrant.",
    }


@app.post("/chat", response_model=ChatResponse)
def chat_with_rfp(request: ChatRequest) -> ChatResponse:
    docs = search_engine.search(query=request.question, top_k=request.top_k)
    answer = synthesizer.answer_question(request.question, docs)
    return ChatResponse(
        question=request.question,
        answer=answer,
        sources=docs,
    )


@app.get("/dossier-n7", response_model=N7BiddingDossier)
def generate_n7_dossier() -> N7BiddingDossier:
    docs = search_engine.search(
        query="cahier des charges objectifs techniques budget délais contraintes",
        top_k=25,
    )
    if not docs:
        raise HTTPException(
            status_code=400,
            detail="Aucun document indexé. Veuillez d'abord uploader un CCTP/CCAP.",
        )
    try:
        return synthesizer.generate_dossier(docs)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur génération dossier: {e!s}") from e