import json
import re
from typing import Any, Dict, List
from litellm import completion
from loguru import logger
from pydantic import BaseModel
from rfp_engine.domain.enseeiht_context import CNJE_RULES, ENSEEIHT_DEPARTMENTS


class CNJECheckItem(BaseModel):
    critere: str
    statut: str
    commentaire: str


class ENSEEIHTStaffing(BaseModel):
    filiere: str  # SN, 3EA ou MFEE
    niveau: str
    nombre_etudiants: int
    competences_cles: List[str]
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
    conformite_cnje: List[CNJECheckItem]
    staffing_enseeiht: List[ENSEEIHTStaffing]
    ventilation_financiere: List[PhasePricing]
    total_jeh_estime: int
    matrice_risques: List[RiskItem]
    clauses_a_renegocier: List[str]
    recommandations_commerciales: List[str]


class RFPSynthesizer:

    def __init__(self, model_name: str = "ollama/llama3.1:8b"):
        self.model_name = model_name

    def generate_dossier(
        self, requirements: List[Dict[str, Any]]
    ) -> N7BiddingDossier:
        """Génère un dossier d'avant-vente éclairé par la base de connaissances ENSEEIHT/CNJE."""
        context_text = "\n\n".join(
            [
                f"[{req['id']}] (Section: {req.get('section', 'N/A')}): {req['text']}"
                for req in requirements
            ]
        )

        dept_info = json.dumps(ENSEEIHT_DEPARTMENTS, ensure_ascii=False, indent=2)

        prompt = f"""Tu es le Vice-Président Commercial de N7 Consulting, la Junior-Entreprise de l'ENSEEIHT (Centrale Toulouse).

CONNAISSANCES DOMAINE OBLIGATOIRES :
1. FILIÈRES ET COMPÉTENCES ENSEEIHT :
{dept_info}

2. RÈGLES DE CONFORMITÉ CNJE :
{CNJE_RULES}

DOCUMENT D'APPEL D me D'OFFRES À ANALYSER :
{context_text}

INSTRUCTIONS DE GÉNÉRATION JSON :
- "titre_marche" : Intitulé exact du projet extrait du document.
- "client" : Nom de l'acheteur/client extrait du document.
- "staffing_enseeiht" : Choisis STRICTEMENT parmi les filières ENSEEIHT ("SN", "3EA" ou "MFEE") en fonction des besoins techniques réels identifiés dans le document.
- "conformite_cnje" : Évalue le projet au regard des règles CNJE fournies ci-dessus.
- Tous les textes doivent être détaillés et s'appuyer sur les faits et chiffres du document.

Format JSON attendu (réponds uniquement avec l'objet JSON) :
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
        logger.info(f"Appel du LLM ({self.model_name}) avec contexte domaine ENSEEIHT...")
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
            logger.error(f"Erreur de validation JSON: {e}")
            raise e