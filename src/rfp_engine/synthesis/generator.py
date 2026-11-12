import json
import re
from typing import Any

from litellm import completion
from loguru import logger
from pydantic import BaseModel

from rfp_engine.domain.enseeiht_context import CNJE_RULES, ENSEEIHT_DEPARTMENTS


class CNJECheckItem(BaseModel):
    critere: str
    statut: str  # "CONFORME", "NON CONFORME", "À NÉGOCIER"
    commentaire: str


class ENSEEIHTStaffing(BaseModel):
    filiere: str  # "SN", "3EA" ou "MFEE"
    niveau: str
    nombre_etudiants: int
    competences_cles: list[str]
    role_dans_projet: str


class PhasePricing(BaseModel):
    phase: str
    description: str
    jeh_estimes: int
    profil_associe: str


class RiskItem(BaseModel):
    domaine: str
    description: str
    impact: str
    plan_mitigation: str


class N7BiddingDossier(BaseModel):
    titre_marche: str
    client: str
    decision_gonogo: str
    score_opportunite: int
    synthese_executive: str
    argumentaire_commercial_n7: str
    conformite_cnje: list[CNJECheckItem]
    staffing_enseeiht: list[ENSEEIHTStaffing]
    ventilation_financiere: list[PhasePricing]
    total_jeh_estime: int
    matrice_risques: list[RiskItem]
    clauses_a_renegocier: list[str]
    recommandations_commerciales: list[str]


class RFPSynthesizer:
    def __init__(self, model_name: str = "ollama/llama3.1:8b"):
        self.model_name = model_name

    def answer_question(self, query: str, requirements: list[dict[str, Any]]) -> str:
        """Génère une réponse concise et factuelle à partir des extraits récupérés."""
        context_text = "\n\n".join(
            [
                f"Extrait [{req.get('id', idx)}] (Section: {req.get('section', 'N/A')}):\n{req.get('text', '')}"
                for idx, req in enumerate(requirements)
            ]
        )

        prompt = f"""Tu es le Directeur Commercial de N7 Consulting (Junior-Entreprise de l'ENSEEIHT, Centrale Toulouse).
Réponds à la question suivante en t'appuyant STRICTEMENT sur les extraits ci-dessous.

EXTRAITS DOCUMENTAIRES :
{context_text}

QUESTION : {query}

INSTRUCTIONS :
- Cite les faits, chiffres, montants, volumes et filières exacts figurant dans les extraits.
- Sois très concis, factuel et précis (style cabinet de conseil).
"""
        try:
            response = completion(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )
            return response.choices[0].message.content
        except Exception as e:  # noqa: BLE001
            logger.error(f"Erreur Chat LLM: {e}")
            return "Erreur lors de la réponse du modèle. Vérifiez qu'Ollama est actif."

    def generate_dossier(self, requirements: list[dict[str, Any]]) -> N7BiddingDossier:
        """Génère un dossier d'avant-vente éclairé par le référentiel ENSEEIHT et les règles CNJE."""
        context_text = "\n\n".join(
            [
                f"[{req.get('id', idx)}] (Section: {req.get('section', 'N/A')}): {req.get('text', '')}"
                for idx, req in enumerate(requirements[:25])
            ]
        )

        dept_info = json.dumps(ENSEEIHT_DEPARTMENTS, ensure_ascii=False, indent=2)

        prompt = f"""Tu es le Vice-Président Commercial de N7 Consulting, la Junior-Entreprise de l'ENSEEIHT (Centrale Toulouse).

CONNAISSANCES DOMAINE OBLIGATOIRES :
1. FILIÈRES ET COMPÉTENCES ENSEEIHT :
{dept_info}

2. RÈGLES DE CONFORMITÉ CNJE :
{CNJE_RULES}

DOCUMENT D'APPEL D'OFFRES À ANALYSER :
{context_text}

INSTRUCTIONS DE GÉNÉRATION JSON :
- "titre_marche" : Intitulé exact du projet extrait du document.
- "client" : Nom de l'acheteur/client extrait du document.
- "staffing_enseeiht" : Choisis STRICTEMENT parmi les filières ENSEEIHT ("SN", "3EA" ou "MFEE") en fonction des besoins techniques réels identifiés dans le document.
- "conformite_cnje" : Évalue le projet au regard des règles CNJE fournies ci-dessus.
- Remplis TOUS les champs du JSON sans utiliser de placeholders.

Format JSON attendu :
{{
  "titre_marche": "...",
  "client": "...",
  "decision_gonogo": "GO STRATÉGIQUE",
  "score_opportunite": 85,
  "synthese_executive": "...",
  "argumentaire_commercial_n7": "...",
  "conformite_cnje": [
    {{"critere": "Valeur Pédagogique", "statut": "CONFORME", "commentaire": "..."}}
  ],
  "staffing_enseeiht": [
    {{
      "filiere": "SN",
      "niveau": "N7 (2ème année)",
      "nombre_etudiants": 2,
      "competences_cles": ["Python", "FastAPI"],
      "role_dans_projet": "..."
    }}
  ],
  "ventilation_financiere": [
    {{"phase": "Phase 1 : Cadrage", "description": "...", "jeh_estimes": 5, "profil_associe": "Consultant SN"}}
  ],
  "total_jeh_estime": 20,
  "matrice_risques": [
    {{"domaine": "Technique", "description": "...", "impact": "Moyen", "plan_mitigation": "..."}}
  ],
  "clauses_a_renegocier": ["..."],
  "recommandations_commerciales": ["..."]
}}
"""
        logger.info(
            f"Appel du LLM ({self.model_name}) avec contexte domaine ENSEEIHT..."
        )
        try:
            response = completion(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )
            content = response.choices[0].message.content.strip()
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            raw_json = json_match.group(0) if json_match else content
            return N7BiddingDossier.model_validate_json(raw_json)
        except Exception as e:
            logger.error(f"Erreur de génération JSON: {e}")
            raise
