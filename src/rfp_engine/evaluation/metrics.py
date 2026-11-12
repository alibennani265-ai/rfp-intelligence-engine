from typing import Any


def compute_hit_rate(
    retrieved_docs: list[dict[str, Any]], expected_keywords: list[str]
) -> float:
    """Calcule si au moins un document extrait contient l'un des mots-clés attendus."""
    if not retrieved_docs or not expected_keywords:
        return 0.0

    combined_text = " ".join([doc.get("text", "").lower() for doc in retrieved_docs])
    for kw in expected_keywords:
        if kw.lower() in combined_text:
            return 1.0
    return 0.0


def compute_mrr(
    retrieved_docs: list[dict[str, Any]], expected_keywords: list[str]
) -> float:
    """Calcule le Mean Reciprocal Rank (MRR) de la première occurrence d'un document pertinent."""
    if not retrieved_docs or not expected_keywords:
        return 0.0

    for rank, doc in enumerate(retrieved_docs, start=1):
        text = doc.get("text", "").lower()
        if any(kw.lower() in text for kw in expected_keywords):
            return 1.0 / rank
    return 0.0


def compute_keyword_coverage(answer: str, expected_keywords: list[str]) -> float:
    """Calcule le taux de couverture des mots-clés attendus dans la réponse générée."""
    if not answer or not expected_keywords:
        return 0.0

    answer_lower = answer.lower()
    matches = sum(1 for kw in expected_keywords if kw.lower() in answer_lower)
    return matches / len(expected_keywords)
