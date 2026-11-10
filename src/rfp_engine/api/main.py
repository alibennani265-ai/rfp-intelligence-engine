import os
from typing import Any, Dict, List
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from rfp_engine.config import settings
from rfp_engine.ingestion.parser import RFPParser
from rfp_engine.ingestion.study_ingestor import N7PastStudyIngestor
from rfp_engine.retrieval.vector_store import HybridSearchEngine
from rfp_engine.synthesis.generator import N7BiddingDossier, RFPSynthesizer

app = FastAPI(
    title="N7 Consulting — Strategic Bidding Engine",
    description="Assistant de Décision et d'Avant-Vente RAG pour N7 Consulting (ENSEEIHT)",
    version="0.6.0",
)

engine = HybridSearchEngine()
synthesizer = RFPSynthesizer(model_name="ollama/llama3.1:8b")


class IngestResponse(BaseModel):
    message: str
    filename: str
    total_requirements: int


class ChatRequest(BaseModel):
    question: str
    top_k: int = 5


class ChatResponse(BaseModel):
    question: str
    answer: str
    sources: List[Dict[str, Any]]


@app.get("/health")
def health_check():
    return {"status": "ok", "app": "N7 Strategic Bidding Engine"}


@app.post("/upload", response_model=IngestResponse)
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(
            status_code=400, detail="Seuls les fichiers PDF sont acceptés."
        )

    os.makedirs("data", exist_ok=True)
    save_path = os.path.join("data", file.filename)

    with open(save_path, "wb") as f:
        content = await file.read()
        f.write(content)

    try:
        global engine
        engine = HybridSearchEngine()

        parser = RFPParser(save_path)
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
            message="Nouveau document indexé avec succès.",
            filename=file.filename,
            total_requirements=len(docs),
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Erreur d'indexation: {str(e)}"
        )


@app.post("/ingest-past-studies")
def ingest_past_studies():
    """Ingère et vectorise tous les fichiers d'anciennes études placés dans data/past_studies."""
    ingestor = N7PastStudyIngestor()
    total_chunks = ingestor.ingest_all("data/past_studies")
    return {
        "status": "ok",
        "message": f"{total_chunks} blocs d'anciennes études N7 indexés dans Qdrant.",
    }


@app.post("/chat", response_model=ChatResponse)
def chat_n7(body: ChatRequest):
    retrieved_docs = engine.search(query=body.question, top_k=body.top_k)
    if not retrieved_docs:
        raise HTTPException(
            status_code=404, detail="Index vide. Veuillez uploader un PDF."
        )

    answer = synthesizer.answer_question(body.question, retrieved_docs)
    return ChatResponse(
        question=body.question, answer=answer, sources=retrieved_docs
    )


@app.get("/dossier-n7", response_model=N7BiddingDossier)
def generate_full_dossier():
    retrieved_docs = engine.search(
        query="objet prestation besoin profil compétences pénalités propriété intellectuelle prix livrables planning",
        top_k=25,
    )
    if not retrieved_docs:
        raise HTTPException(
            status_code=404, detail="Index vide. Veuillez uploader un PDF."
        )

    return synthesizer.generate_dossier(retrieved_docs)
    