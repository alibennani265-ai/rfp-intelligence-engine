<div align="center">

# 🔴 RFP Intelligence Engine — N7 Consulting

**Assistant de Décision, Audit CNJE & Copilot d'Avant-Vente pour Junior-Entreprise (ENSEEIHT / Centrale Toulouse)**

[![CI/CD Pipeline](https://github.com/alibennani265-ai/rfp-intelligence-engine/actions/workflows/ci.yml/badge.svg)](https://github.com/alibennani265-ai/rfp-intelligence-engine/actions)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110.0-009688.svg)](https://fastapi.tiangolo.com/)
[![Qdrant](https://img.shields.io/badge/Qdrant-v1.9.2-red.svg)](https://qdrant.tech/)
[![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[Architecture](#-architecture-syst%C3%A8me) • [Fonctionnalit%C3%A9s](#-fonctionnalit%C3%A9s-cl%C3%A9s) • [Installation](#-d%C3%A9marrage-rapide) • [Benchmarks](#-m%C3%A9triques--%C3%A9valuation-rag) • [Docker & K8s](#-industrialisation--d%C3%A9ploiement)

---

</div>

## 📌 Vision & Problématique Métier

**N7 Consulting**, la Junior-Entreprise de l'ENSEEIHT (Centrale Toulouse), analyse chaque mois des dizaines de Cahiers des Charges (CCTP/CCAP). La qualification et la réponse à ces marchés nécessitent une analyse précise :
1. **Conformité CNJE :** Audit systématique du cadre réglementaire de la Confédération Nationale des Junior-Entreprises (valeur pédagogique obligatoire, interdiction stricte de la régie pure et absence d'astreinte ou de maintenance 24/7 post-diplôme).
2. **Matching d'Équipe ENSEEIHT :** Recommandation d'étudiants issus des 3 filières d'ingénierie de l'école :
   - **SN (Sciences du Numérique) :** IA, Data Science, Software Engineering, Cloud, Cybersécurité.
   - **3EA (Électronique, Énergie Électrique, Automatique) :** Systèmes Embarqués, Signal, Automatisme, Microélectronique.
   - **MFEE (Mécanique des Fluides, Énergie & Environnement) :** Simulation CFD, Thermique, Ingénierie Hydraulique.
3. **Rédaction d'Avant-Vente :** Chiffrage estimatif en Jours-Étude Homme (JEH), analyse des risques contractuels et génération d'un rapport de synthèse décisionnelle téléchargeable au format **PDF Executive**.

---

## 🚀 Architecture Système

```mermaid
flowchart TD
    subgraph Ingestion ["1. Ingestion & Search Engine"]
        A[Appel d'Offres PDF / MD] --> B[RFP Parser & Chunking]
        C[Historique 40 Études N7] --> D[Study Ingestor]
        B --> E[BAAI/bge-m3 Dense Embeddings]
        D --> E
        B --> F[BM25 Lexical Index]
        E --> G[(Qdrant Vector DB Local)]
        F --> G
    end

    subgraph Reranking ["2. Re-Ranking & Context Engine"]
        G --> H[Hybrid Candidates Top-25]
        H --> I[Cross-Encoder Reranker\n'ms-marco-MiniLM-L-6-v2']
        I --> J[Top-5 Chunks Pertinents]
        K[Référentiel CNJE & Filières ENSEEIHT] --> L[Domain Context Engine]
    end

    subgraph Synthesis ["3. LLM Inference & Reporting"]
        J --> M[Synthesis Engine\n'Llama 3.1 8B via LiteLLM']
        L --> M
        M --> N{Validation Pydantic v2}
        N --> O[FastAPI Endpoints]
        O --> P[Dashboard Streamlit Executive]
        O --> Q[Export PDF FPDF2]
    end


✨ Fonctionnalités Clés

Recherche Hybride 2-Tier : Combinaison de la recherche sémantique dense (BAAI/bge-m3) et lexicale (rank-bm25), réordonnée par un Cross-Encoder (ms-marco-MiniLM-L-6-v2).Audit de Conformité CNJE : Détection automatique des risques légaux (absence de valeur pédagogique, clauses de régie, pénalités non plafonnées).Matching d'Équipe ENSEEIHT : Recommandation de profils d'élèves-ingénieurs (SN, 3EA, MFEE) selon les compétences exigées par le marché.RAG Evaluation Framework : Évaluation automatisée calculant les métriques HitRate@K, MRR (Mean Reciprocal Rank) et Answer Keyword Coverage.Rapport Exécutif PDF : Génération dynamique d'un document d'avant-vente téléchargeable, mis en page aux couleurs de N7 Consulting.📊 Métriques & Évaluation RAGLe projet inclut un banc d'évaluation scientifique (rfp_engine.evaluation.evaluator) mesurant les performances du pipeline sur la base de connaissances historique :MétriqueScore ObtenuDescriptionHitRate@51.000Proportion de requêtes où au moins une source pertinente figure dans le Top-5.MRR (Mean Reciprocal Rank)1.000Précision du positionnement du premier extrait pertinent dans les résultats.Answer Coverage1.000Taux de présence des informations clés attendues dans la réponse du LLM.📁 Structure du ProjetPlaintextrfp-intelligence-engine/
├── .github/
│   └── workflows/
│       └── ci.yml                 # Pipeline CI/CD GitHub Actions
├── app.py                         # Interface utilisateur Streamlit
├── data/
│   ├── eval_dataset.json          # Jeu de données d'évaluation RAG
│   ├── past_studies/              # Synthèse & documents des 40 études N7
│   └── qdrant_db/                 # Base de données vectorielle locale
├── docker-compose.yml             # Orchestration Multi-Services
├── Dockerfile                     # Multi-stage Dockerfile sécurisé
├── k8s/
│   └── deployment.yaml            # Manifestes Kubernetes (Deployments, PVC, Probes)
├── pyproject.toml                 # Configuration du projet & dépendances uv
├── src/
│   └── rfp_engine/
│       ├── api/
│       │   └── main.py            # Endpoints FastAPI
│       ├── domain/
│       │   └── enseeiht_context.py# Référentiel Filières ENSEEIHT & Règles CNJE
│       ├── evaluation/
│       │   ├── evaluator.py       # Moteur d'évaluation RAG
│       │   └── metrics.py         # Métriques HitRate, MRR, Coverage
│       ├── ingestion/
│       │   ├── parser.py          # Parsing PDF des Cahiers des Charges
│       │   └── study_ingestor.py   # Ingestion des études passées (PDF & MD)
│       ├── retrieval/
│       │   ├── reranker.py        # Cross-Encoder Reranker
│       │   └── vector_store.py    # Dual Search Qdrant + BM25
│       └── synthesis/
│           ├── generator.py       # Génération structurée JSON Llama 3.1
│           └── pdf_exporter.py    # Exportateur PDF FPDF2
└── README.md
🛠️ Stack TechniqueLangage & Tooling : Python 3.11, uv (Fast Package Manager), Pydantic v2.Vector DB & Search : Qdrant (Persistent Local Store), sentence-transformers (BAAI/bge-m3), rank-bm25.LLM Orchestration : Ollama (llama3.1:8b), LiteLLM.API & UI : FastAPI, Streamlit, fpdf2.DevOps & Infra : Docker (Multi-stage), Docker Compose, Kubernetes, GitHub Actions (Ruff, Mypy, Pytest).⚡ Démarrage RapidePrérequisPython 3.11+uv (Gestionnaire de paquets)Ollama exécutant llama3.1:8b (ollama run llama3.1:8b)1. InstallationBashgit clone [https://github.com/alibennani265-ai/rfp-intelligence-engine.git](https://github.com/alibennani265-ai/rfp-intelligence-engine.git)
cd rfp-intelligence-engine
uv venv && source .venv/bin/activate
uv pip install -e .
2. Lancement des ServicesBackend FastAPI (Terminal 1) :Bashuv run uvicorn rfp_engine.api.main:app --reload --port 8000
Frontend Streamlit (Terminal 2) :Bashuv run streamlit run app.py
Accès à l'application : http://localhost:8501.🐳 Industrialisation & DéploiementDocker Compose StackBashdocker-compose up --build -d
Manifestes KubernetesBashkubectl apply -f k8s/deployment.yaml
📄 LicenceProjet développé pour N7 Consulting (Junior-Entreprise de l'ENSEEIHT). Sous licence MIT.
---

### Étape 3 : Pousser les Modifications sur GitHub

Exécute la séquence de commandes dans ton terminal :

```bash
# 1. Vérifier le statut des fichiers
git status

# 2. Ajouter l'ensemble du projet propre
git add .

# 3. Commit d'industrialisation et de documentation
git commit -m "feat(rag): fix evaluation auto-ingest, add HitRate/MRR metrics, add Docker/K8s infra, and release executive README"

# 4. Push sur la branche main
git push origin main