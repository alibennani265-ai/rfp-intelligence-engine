import json
import re
from typing import Any

from litellm import completion
from loguru import logger
from pydantic import BaseModel, field_validator

from rfp_engine.domain.enseeiht_context import CNJE_RULES, ENSEEIHT_DEPARTMENTS


def _coerce_int(value: Any, default: int = 1) -> int:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, float):
        return round(value)
    if isinstance(value, str):
        m = re.search(r"-?\d+", value)
        if m:
            return int(m.group(0))
    return default


def _coerce_str(value: Any, default: str = "Non précisé") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _unwrap_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        for v in value.values():
            if isinstance(v, list):
                return v
        return [value]
    return []


class CNJECheckItem(BaseModel):
    critere: str
    statut: str
    commentaire: str

    @field_validator("critere", "statut", "commentaire", mode="before")
    @classmethod
    def clean_str(cls, v: Any) -> str:
        return _coerce_str(v)


class ENSEEIHTStaffing(BaseModel):
    filiere: str
    niveau: str
    nombre_etudiants: int
    competences_cles: list[str]
    role_dans_projet: str

    @field_validator("filiere", "niveau", "role_dans_projet", mode="before")
    @classmethod
    def clean_str(cls, v: Any) -> str:
        return _coerce_str(v)

    @field_validator("nombre_etudiants", mode="before")
    @classmethod
    def clean_int(cls, v: Any) -> int:
        return max(1, _coerce_int(v, 2))

    @field_validator("competences_cles", mode="before")
    @classmethod
    def clean_list(cls, v: Any) -> list[str]:
        if isinstance(v, list):
            return [str(x) for x in v if x]
        return [str(v)] if v else ["Ingénierie logicielle"]


class PhasePricing(BaseModel):
    phase: str
    description: str
    jeh_estimes: int
    profil_associe: str

    @field_validator("phase", "description", "profil_associe", mode="before")
    @classmethod
    def clean_str(cls, v: Any) -> str:
        return _coerce_str(v)

    @field_validator("jeh_estimes", mode="before")
    @classmethod
    def clean_int(cls, v: Any) -> int:
        return max(1, _coerce_int(v, 5))


class RiskItem(BaseModel):
    domaine: str
    description: str
    impact: str
    plan_mitigation: str

    @field_validator(
        "domaine", "description", "impact", "plan_mitigation", mode="before"
    )
    @classmethod
    def clean_str(cls, v: Any) -> str:
        return _coerce_str(v)


class N7BiddingDossier(BaseModel):
    raisonnement_auditeur: str = ""
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

    @field_validator(
        "raisonnement_auditeur",
        "titre_marche",
        "client",
        "decision_gonogo",
        "synthese_executive",
        "argumentaire_commercial_n7",
        mode="before",
    )
    @classmethod
    def clean_str(cls, v: Any) -> str:
        return _coerce_str(v, "")

    @field_validator("score_opportunite", mode="before")
    @classmethod
    def clean_score(cls, v: Any) -> int:
        return max(0, min(100, _coerce_int(v, 50)))

    @field_validator("total_jeh_estime", mode="before")
    @classmethod
    def clean_total_jeh(cls, v: Any) -> int:
        return max(1, _coerce_int(v, 20))

    @field_validator(
        "conformite_cnje",
        "staffing_enseeiht",
        "ventilation_financiere",
        "matrice_risques",
        mode="before",
    )
    @classmethod
    def clean_object_lists(cls, v: Any) -> list[Any]:
        return _unwrap_list(v)

    @field_validator(
        "clauses_a_renegocier", "recommandations_commerciales", mode="before"
    )
    @classmethod
    def clean_str_lists(cls, v: Any) -> list[str]:
        items = _unwrap_list(v)
        return [str(x).strip() for x in items if str(x).strip()]


class RFPSynthesizer:
    def __init__(self, model_name: str = "ollama/llama3.1:8b") -> None:
        self.model_name = model_name

    def answer_question(self, query: str, requirements: list[dict[str, Any]]) -> str:
        context_text = "\n\n".join(
            [
                f"Source [{req.get('id', idx)}] ({req.get('section', 'N/A')}):\n{req.get('text', '')}"
                for idx, req in enumerate(requirements)
            ]
        )
        dept_info = json.dumps(ENSEEIHT_DEPARTMENTS, ensure_ascii=False, indent=2)

        prompt = f"""Tu es le Vice-Président Commercial et Auditeur Légal CNJE de N7 Consulting (Junior-Entreprise de l'ENSEEIHT — Centrale Toulouse).
Réponds en croisant les clauses du CCTP client, les compétences ENSEEIHT / études passées N7, et le Cadre Légal CNJE.

FILIÈRES ENSEEIHT (RÈGLE DE ROUTAGE STRICT) :
{dept_info}
- Tout projet 100% logiciel, web, SaaS, plateforme, data, IA ou déploiement cloud/DevOps relève EXCLUSIVEMENT de la filière **SN (Sciences du Numérique)**. Ne mentionne jamais 3EA ou MFEE sauf s'il y a explicitement du matériel électronique/embarqué ou de la mécanique des fluides/thermique dans le CCTP.

EXTRAITS DOCUMENTAIRES (CCTP + ÉTUDES N7 + CLR CNJE) :
{context_text}

QUESTION : {query}

Structure ta réponse en 3 parties :
### 1. Avis Technique & Références N7 Consulting
### 2. Audit de Conformité Légale (CLR CNJE)
### 3. Recommandation Commerciale
"""
        response = completion(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        return str(response.choices[0].message.content)

    def generate_dossier(
        self,
        rfp_chunks: list[dict[str, Any]],
        legal_chunks: list[dict[str, Any]] | None = None,
    ) -> N7BiddingDossier:
        rfp_context = "\n\n".join(
            [
                f"[{r.get('id', i)}] ({r.get('section')}): {r.get('text')}"
                for i, r in enumerate(rfp_chunks)
            ]
        )
        legal_context = "\n\n".join(
            [
                f"[N7/CNJE - {r.get('section')}]: {r.get('text')}"
                for r in (legal_chunks or [])
            ]
        )
        dept_info = json.dumps(ENSEEIHT_DEPARTMENTS, ensure_ascii=False, indent=2)

        prompt = f"""Tu es l'Auditeur Légal CNJE et VP Commercial de N7 Consulting (Junior-Entreprise de l'ENSEEIHT).
Analyse le CCTP client ci-dessous et génère un dossier JSON complet.

FILIÈRES ENSEEIHT :
{dept_info}

CADRE LÉGAL CNJE & RÉFÉRENTIEL N7 :
{CNJE_RULES}
{legal_context}

EXTRAITS DU CCTP CLIENT À AUDITER :
{rfp_context}

RÈGLES MÉTIER IMPÉRATIVES :
1. "raisonnement_auditeur" : Rédige d'abord ton analyse libre en 4-5 phrases (nature technique exacte du projet, filière ENSEEIHT pertinente, clauses juridiques sensibles détectées dans le CCTP, estimation réaliste de charge en JEH).
2. ROUTAGE DES FILIÈRES ("staffing_enseeiht") :
   - Si le projet est 100% logiciel / plateforme web / IA / data / déploiement cloud, affecte **UNIQUEMENT la filière "SN"** (ex: 1 Chef de projet/Architecte IA SN + 2 Développeurs Full-Stack SN).
   - N'ajoute **JAMAIS** "3EA" (électronique) ou "MFEE" (fluides) pour du déploiement logiciel ou serveur !
3. INTERDICTION DE LAISSER LES TABLEAUX VIDES :
   - "conformite_cnje" : DOIT contenir 4 critères précis extraits du CCTP (Plus-Value Pédagogique, Régie vs Forfait, Pénalités de retard, Garantie/PI).
   - "staffing_enseeiht" : DOIT contenir 1 à 3 profils d'étudiants adaptés.
   - "ventilation_financiere" : DOIT contenir 3 à 5 phases réelles (ex: Cadrage & Architecture, Développement Backend/IA, Interface Frontend, Déploiement & Recette) avec des JEH entiers réalistes (total généralement entre 20 et 55 JEH pour une plateforme complète).
   - "matrice_risques" : DOIT contenir 2 à 4 risques concrets identifiés dans le CCTP.
   - "clauses_a_renegocier" : Cite précisément les articles/clauses problématiques du CCTP (sans formules vagues comme "clauses abusives").

Réponds UNIQUEMENT en JSON valide respectant exactement ce schéma :
{{
  "raisonnement_auditeur": "Analyse détaillée avant décision...",
  "titre_marche": "Titre exact extrait du CCTP",
  "client": "Nom exact du client extrait du CCTP",
  "decision_gonogo": "GO STRATÉGIQUE | GO SOUS RÉSERVE DE RENÉGOCIATION | NO-GO (BLOQUANT CNJE)",
  "score_opportunite": 65,
  "synthese_executive": "Synthèse précise du besoin et des enjeux...",
  "argumentaire_commercial_n7": "Pourquoi N7 Consulting et l'ENSEEIHT sont légitimes sur ce projet...",
  "conformite_cnje": [
    {{"critere": "Nom du critère", "statut": "CONFORME | À NÉGOCIER | NON CONFORME", "commentaire": "Analyse précise avec référence au CCTP"}}
  ],
  "staffing_enseeiht": [
    {{"filiere": "SN", "niveau": "2A / 3A ENSEEIHT", "nombre_etudiants": 2, "competences_cles": ["Python", "React"], "role_dans_projet": "Rôle exact"}}
  ],
  "ventilation_financiere": [
    {{"phase": "Phase 1 : Cadrage & Architecture", "description": "Livrables attendus", "jeh_estimes": 6, "profil_associe": "Architecte SN"}}
  ],
  "total_jeh_estime": 25,
  "matrice_risques": [
    {{"domaine": "Juridique / Technique", "description": "Description précise du risque", "impact": "Critique | Élevé | Moyen", "plan_mitigation": "Action concrète"}}
  ],
  "clauses_a_renegocier": ["Clause précise à modifier avant signature"],
  "recommandations_commerciales": ["Action concrète d'avant-vente"]
}}
"""
        logger.info(f"Génération audit N7 ({len(rfp_chunks)} blocs CCTP)...")
        response = completion(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=2500,
            response_format={"type": "json_object"},
        )
        content = str(response.choices[0].message.content).strip()
        match = re.search(r"\{.*\}", content, re.DOTALL)
        dossier = N7BiddingDossier.model_validate_json(
            match.group(0) if match else content
        )
        if dossier.ventilation_financiere:
            dossier.total_jeh_estime = sum(
                p.jeh_estimes for p in dossier.ventilation_financiere
            )
        return dossier
