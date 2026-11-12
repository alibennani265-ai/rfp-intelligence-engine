import json
from typing import Any

from loguru import logger

from rfp_engine.evaluation.metrics import (
    compute_hit_rate,
    compute_keyword_coverage,
    compute_mrr,
)
from rfp_engine.ingestion.study_ingestor import N7PastStudyIngestor
from rfp_engine.retrieval.vector_store import HybridSearchEngine
from rfp_engine.synthesis.generator import RFPSynthesizer


class RAGEvaluator:
    def __init__(self, dataset_path: str = "data/eval_dataset.json"):
        self.dataset_path = dataset_path

        self.engine = HybridSearchEngine(collection_name="n7_past_studies")

        logger.info("Vérification et ingestion du corpus d'études N7 dans Qdrant...")
        ingestor = N7PastStudyIngestor(
            collection_name="n7_past_studies", engine=self.engine
        )
        ingestor.ingest_all("data/past_studies")

        self.synthesizer = RFPSynthesizer()

    def load_dataset(self) -> list[dict[str, Any]]:
        with open(self.dataset_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def run_evaluation(self, top_k: int = 5) -> dict[str, float]:
        dataset = self.load_dataset()
        total_q = len(dataset)

        hit_rates = []
        mrrs = []
        coverages = []

        logger.info(f"Démarrage de l'évaluation RAG sur {total_q} requêtes de test...")

        for item in dataset:
            query = item["query"]
            keywords = item["expected_keywords"]

            # 1. Évaluation Vector Search / Retrieval
            retrieved = self.engine.search(query=query, top_k=top_k)
            logger.info(f"Query: '{query}' -> {len(retrieved)} extraits trouvés.")

            hr = compute_hit_rate(retrieved, keywords)
            mrr = compute_mrr(retrieved, keywords)

            hit_rates.append(hr)
            mrrs.append(mrr)

            # 2. Évaluation de la réponse générée
            if retrieved:
                ans = self.synthesizer.answer_question(query, retrieved)
                cov = compute_keyword_coverage(ans, keywords)
            else:
                cov = 0.0
            coverages.append(cov)

        mean_hit_rate = sum(hit_rates) / total_q if total_q > 0 else 0.0
        mean_mrr = sum(mrrs) / total_q if total_q > 0 else 0.0
        mean_coverage = sum(coverages) / total_q if total_q > 0 else 0.0

        results = {
            "hit_rate_at_k": round(mean_hit_rate, 4),
            "mrr": round(mean_mrr, 4),
            "answer_keyword_coverage": round(mean_coverage, 4),
            "total_queries_evaluated": total_q,
        }

        logger.info(f"Résultats de l'évaluation : {results}")
        return results


if __name__ == "__main__":
    evaluator = RAGEvaluator()
    try:
        res = evaluator.run_evaluation()
        print("\n" + "=" * 40)
        print("📊 RAPPORT D'ÉVALUATION RAG N7 ENGINE")
        print("=" * 40)
        for k, v in res.items():
            print(f"{k}: {v}")
        print("=" * 40)
    finally:
        evaluator.engine.close()
