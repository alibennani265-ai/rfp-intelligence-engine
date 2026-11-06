# 🔴 RFP Intelligence Engine — N7 Consulting

> Assistant d'Avant-Vente, Audit CNJE, Vector Search & Copilot de Décision pour **N7 Consulting** (Junior-Entreprise de l'ENSEEIHT, Centrale Toulouse).

## 🚀 Architecture RAG & Pipeline Hybride

```text
┌────────────────────────────────┐      ┌────────────────────────────────┐
│   Appel d'Offres CCTP (PDF)    │      │   Base d'Études N7 (PDFs)      │
└───────────────┬────────────────┘      └───────────────┬────────────────┘
                │                                       │
                ▼                                       ▼
    [ RFP Parser & Chunking ]               [ Study Ingestor & Metadata ]
                │                                       │
                └───────────────────┬───────────────────┘
                                    │
                                    ▼
                 [ Embeddings BAAI/bge-m3 + Index BM25 ]
                                    │
                                    ▼
                [ Vector Store Locale Qdrant (Persistent) ]
                ├── Collection: `rfp_requirements`
                └── Collection: `n7_past_studies`
                                    │
                                    ▼
                 [ Cross-Encoder Reranker (MiniLM-L6) ]
                                    │
                                    ▼
                 [ Domain Engine (Filières SN / 3EA / MFEE & CNJE) ]
                                    │
                                    ▼
                 [ Synthesis Engine (Ollama Llama 3.1 8B) ]
                                    │
                                    ▼
                 [ Dashboard Streamlit & Export PDF FPDF2 ]