from rfp_engine.ingestion.parser import RFPParser
from rfp_engine.retrieval.vector_store import HybridSearchEngine


def main():
    # 1. Extraction des exigences depuis le vrai PDF
    pdf_path = "data/sample_rfp.pdf"
    parser = RFPParser(pdf_path)
    requirements = parser.parse()

    # Transformer les objets RFPRequirement en dictionnaires pour le vector store
    docs = [
        {
            "id": req.requirement_id,
            "section": req.section,
            "text": req.text,
            "metadata": req.metadata,
        }
        for req in requirements
    ]

    # 2. Indexation dans le moteur hybride (BM25 + BGE-M3)
    engine = HybridSearchEngine()
    engine.index_documents(docs)

    # 3. Test de recherches métiers sur le marché réel
    queries = [
        "Quelles sont les clauses de propriété intellectuelle ?",
        "Pénalités de retard et résiliation du marché",
        "Profils ingénieur Full Stack et compétences requises",
    ]

    print("\n================ RÉSULTATS DE RECHERCHE HYBRIDE ================\n")
    for q in queries:
        print(f"🔍 REQUÊTE : \"{q}\"")
        results = engine.search(q, top_k=2)
        for res in results:
            print(f"  • [{res['id']}] (Score BM25: {res['score']:.2f})")
            print(f"    Text: {res['text']}\n")


if __name__ == "__main__":
    main()