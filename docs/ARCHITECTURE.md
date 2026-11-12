# Architecture Système & Choix d'Ingénierie

## 1. Recherche Hybride 2-Tier (Dense + Lexical + Cross-Encoder)
La recherche vectorielle pure souffre d'un angle mort sur les acronymes réglementaires et techniques propres aux Junior-Entreprises et à l'ENSEEIHT (`CNJE`, `JEH`, `3EA`, `MFEE`, `CCTP`).
- **Tier 1A (Dense) :** Embeddings `BAAI/bge-m3` (1024D) stockés dans Qdrant avec similarité cosinus.
- **Tier 1B (Lexical) :** Index `BM25Okapi` reconstruit automatiquement au démarrage depuis les payloads Qdrant (`_hydrate_lexical_index_from_qdrant`).
- **Fusion RRF :** Combinaison sans hyperparamètres sensibles via $RRF(d) = \sum_{r \in R} \frac{1}{60 + \text{rang}_r(d)}$.
- **Tier 2 (Reranking) :** `cross-encoder/ms-marco-MiniLM-L-6-v2` évalue conjointement la paire `(query, passage)` sur les 15 meilleurs candidats pour isoler le Top-5 final.

## 2. Contraintes Apple Silicon (moins de 10B Paramètres)
Le système cible une exécution locale souveraine sur MacBook Air sans transfert de documents clients vers des API externes. Le choix de `llama3.1:8b` quantifié en 4-bit (~4.9 Go VRAM/RAM unifiée) permet de conserver une marge mémoire suffisante pour `BAAI/bge-m3` (~2.2 Go) et le Cross-Encoder (~90 Mo) sans déclencher de swap disque.
