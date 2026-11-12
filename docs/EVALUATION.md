# Protocole Scientifique d'Évaluation RAG

## Métriques Implémentées (`src/rfp_engine/evaluation/metrics.py`)
1. **HitRate@K :** Mesure binaire vérifiant si au moins un extrait contenant les mots-clés de la vérité terrain apparaît dans les `K` premiers résultats.
2. **Mean Reciprocal Rank (MRR) :** Évalue la précision du classement en pénalisant les sources pertinentes reléguées en bas de liste ($\frac{1}{\text{rang}}$).
3. **Answer Keyword Coverage :** Vérifie que le LLM restitue fidèlement les entités chiffrées et réglementaires présentes dans le contexte sans hallucination.

## Limites & Perspectives
- Ajout prévu d'une évaluation par juge LLM (*Faithfulness* et *Answer Relevance*) sur un jeu élargi de 50 CCTP anonymisés.
