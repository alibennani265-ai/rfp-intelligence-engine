import os
from glob import glob
from typing import Any, Dict, List, Optional
from loguru import logger
from pypdf import PdfReader
from rfp_engine.retrieval.vector_store import HybridSearchEngine


class N7PastStudyIngestor:

    def __init__(
        self,
        collection_name: str = "n7_past_studies",
        engine: Optional[HybridSearchEngine] = None,
    ):
        self.collection_name = collection_name
        self.engine = (
            engine
            if engine is not None
            else HybridSearchEngine(collection_name=collection_name)
        )

    def ingest_all(self, folder_path: str = "data/past_studies") -> int:
        pdf_files = glob(os.path.join(folder_path, "*.pdf"))
        md_files = glob(os.path.join(folder_path, "*.md"))

        if not pdf_files and not md_files:
            logger.warning(
                f"Aucun fichier PDF ou Markdown trouvé dans {folder_path}"
            )
            return 0

        documents = []

        # 1. Ingestion Markdown (.md)
        for md_path in md_files:
            filename = os.path.basename(md_path)
            try:
                with open(md_path, "r", encoding="utf-8", errors="ignore") as f:
                    full_text = f.read()

                chunks = [
                    p.strip()
                    for p in full_text.split("\n\n")
                    if len(p.strip()) > 40
                ]
                for i, chunk in enumerate(chunks):
                    documents.append(
                        {
                            "id": f"{filename}_chunk_{i}",
                            "section": f"Synthèse Historique N7: {filename}",
                            "text": chunk,
                            "metadata": {
                                "source_file": filename,
                                "type": "past_study_synthesis",
                            },
                        }
                    )
                logger.info(
                    f"Extraction Markdown réussie pour '{filename}' : {len(chunks)} blocs."
                )
            except Exception as e:
                logger.error(
                    f"Erreur d'extraction sur le fichier Markdown '{filename}': {e}"
                )

        # 2. Ingestion PDF (.pdf)
        for pdf_path in pdf_files:
            filename = os.path.basename(pdf_path)
            try:
                reader = PdfReader(pdf_path)
                full_text = ""
                for idx, page in enumerate(reader.pages):
                    txt = page.extract_text() or ""
                    if txt.strip():
                        full_text += f"\n--- Page {idx + 1} ---\n" + txt

                chunks = [
                    p.strip()
                    for p in full_text.split("\n\n")
                    if len(p.strip()) > 80
                ]
                for i, chunk in enumerate(chunks):
                    documents.append(
                        {
                            "id": f"{filename}_chunk_{i}",
                            "section": f"Étude N7: {filename}",
                            "text": chunk,
                            "metadata": {
                                "source_file": filename,
                                "type": "past_study_pdf",
                            },
                        }
                    )
                logger.info(
                    f"Extraction PDF réussie pour '{filename}' : {len(chunks)} blocs."
                )
            except Exception as e:
                logger.error(
                    f"Erreur d'extraction sur le PDF '{filename}': {e}"
                )

        if documents:
            self.engine.index_documents(documents)
            logger.info(
                f"Indexation réussie : {len(documents)} blocs d'historique N7 intégrés dans Qdrant ({self.collection_name})."
            )

        return len(documents)