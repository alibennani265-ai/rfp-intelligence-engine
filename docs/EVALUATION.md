# Protocole Scientifique d'Évaluation RAG

## 1. Corpus de Connaissances Métier (`data/past_studies/`)
La base documentaire de référence comprend **4 documents structurés (31 chunks uniques indexés par UUID déterministes)** :
- `SYNTHESE_40_ETUDES.md` (11 blocs) : Historique financier, tarif moyen JEH (442 € HT) et répartition par filière.
- `REFERENTIEL_CNJE_CONFORMITE.md` (7 blocs) : Articles du Mémento CNJE (valeur pédagogique, art. L.8241-1 sur la régie, plafonnement des pénalités, propriété intellectuelle).
- `CATALOGUE_FILIERES_ENSEEIHT.md` (8 blocs) : Compétences techniques détaillées des départements **SN**, **3EA** et **MFEE**.
- `PLAYBOOK_CLAUSES_CONTRACTUELLES.md` (5 blocs) : Stratégies de renégociation face aux clauses d'astreinte 24/7, de régie sur site et de confidentialité aéronautique/spatiale.

## 2. Résultats du Benchmark (10 Requêtes Multi-Domaines)
| Métrique | Score | Interprétation |
| :--- | :---: | :--- |
| **HitRate@5** | `1.0000` | Rappel parfait dans le Top-5 après fusion RRF + Cross-Encoder. |
| **MRR** | `0.9500` | Quasi-totalité des sources exactes classées en 1ère position. |
| **Answer Keyword Coverage** | `0.8833` | Fidélité factuelle élevée de `Llama-3.1-8B` sans hallucination de chiffres. |
