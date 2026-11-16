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
        return [str(v)] if v else ["Ingénierie ENSEEIHT"]


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
Réponds en croisant les clauses du CCTP/CCAP client, les compétences ENSEEIHT / études passées N7, et le Cadre Légal CNJE.

FILIÈRES ENSEEIHT (RÈGLE DE ROUTAGE STRICT) :
{dept_info}
- Tout projet 100% logiciel, web, SaaS, plateforme, data, IA ou déploiement cloud/DevOps relève EXCLUSIVEMENT de la filière **SN (Sciences du Numérique)**. Ne mentionne jamais 3EA ou MFEE sauf s'il y a explicitement du matériel électronique/embarqué ou de la mécanique des fluides/thermique dans le marché.

EXTRAITS DOCUMENTAIRES (MARCHÉ CLIENT + ÉTUDES N7 + CLR CNJE) :
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

    def _deep_audit_reasoning(
        self, rfp_context: str, legal_context: str, dept_info: str
    ) -> str:
        """Passe 1 : Réflexion libre approfondie (sans contrainte JSON) pour détecter toutes les clauses et bâtir le chiffrage."""
        reasoning_prompt = f"""Tu es le Vice-Président Commercial et Auditeur Légal CNJE de N7 Consulting (Junior-Entreprise de l'ENSEEIHT — Centrale Toulouse).
Lis attentivement l'intégralité des extraits du marché client ci-dessous et rédige une note d'analyse stratégique interne complète avant décision.

FILIÈRES ENSEEIHT :
{dept_info}

CADRE LÉGAL CNJE (LIGNES ROUGES) :
{CNJE_RULES}
{legal_context}

EXTRAITS DU MARCHÉ CLIENT (CCTP / CCAP / RC) :
{rfp_context}

ANALYSE EN PROFONDEUR LES 5 POINTS SUIVANTS (SOIS CRITIQUE ET FACTUEL) :
1. **Objet réel du marché & Client** : Quel est le nom exact de l'acheteur et quelle est la prestation technique concrète demandée (et NON "mettre en place un accord-cadre") ?
2. **Audit Juridique CNJE (Chasse aux clauses bloquantes)** :
   - Y a-t-il des **pénalités ou indemnités de retard déplafonnées**, journalières, automatiques ou sans mise en demeure ? (Si oui : RISQUE MAJEUR CNJE).
   - Y a-t-il une obligation de **régie**, d'intégration dans l'équipe client, de **feuilles de temps / pointage horaire**, d'**astreinte**, de **sous-traitance**, ou une **obligation de résultat** / garantie > 3 mois ?
   - La Plus-Value Pédagogique (PVP) pour les étudiants ENSEEIHT est-elle réelle ou s'agit-il d'exécution répétitive sans valeur intellectuelle ?
3. **Verdict Go / No-Go & Score** :
   - Si présence de régie, feuilles de temps, astreintes, sous-traitance ou absence de PVP -> **NO-GO (BLOQUANT CNJE)** (Score < 40/100).
   - Si présence de pénalités/indemnités de retard déplafonnées, prix fermes risqués, garantie excessive ou clauses abusives -> **GO SOUS RÉSERVE DE RENÉGOCIATION** (Score entre 40 et 65/100).
   - Uniquement si 100% conforme CNJE sans clause bloquante -> **GO STRATÉGIQUE** (Score > 75/100).
4. **Staffing ENSEEIHT adapté** : Quels profils étudiants précis (SN pour logiciel/data/IA/web ; 3EA uniquement si électronique/embarqué ; MFEE uniquement si fluides/thermique) ?
5. **Découpage complet en 3 à 5 phases avec chiffrage réaliste en JEH** : Détaille chaque phase du projet (ex: Phase 1 Cadrage & Spécifications, Phase 2 Développement / Conception cœur, Phase 3 Intégration / Tests / Sécurité, Phase 4 Recette & Documentation) avec un nombre de JEH cohérent avec l'ampleur du marché (jamais une seule phase de 6 JEH).
"""
        logger.info("Passe 1/2 : Réflexion critique approfondie sur le marché...")
        res = completion(
            model=self.model_name,
            messages=[{"role": "user", "content": reasoning_prompt}],
            temperature=0.2,
            max_tokens=2200,
        )
        return str(res.choices[0].message.content).strip()

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

        # Passe 1 : Raisonnement critique libre
        audit_notes = self._deep_audit_reasoning(rfp_context, legal_context, dept_info)

        # Passe 2 : Conversion fidèle de l'analyse en JSON structuré
        json_prompt = f"""Transforme la note d'analyse stratégique ci-dessous en un objet JSON strictement conforme au schéma demandé.
Ne perds AUCUNE clause critique, AUCUN risque (notamment les pénalités/indemnités de retard déplafonnées) et conserve l'intégralité des phases de chiffrage (minimum 3 à 5 phases).

NOTE D'ANALYSE STRATÉGIQUE :
{audit_notes}

RÈGLES DE MAPPING JSON :
- "decision_gonogo" : reprend exactement le verdict de l'analyse ("NO-GO (BLOQUANT CNJE)", "GO SOUS RÉSERVE DE RENÉGOCIATION" ou "GO STRATÉGIQUE").
- "argumentaire_commercial_n7" : explique la légitimité technique des filières ENSEEIHT et les études similaires réalisées par N7 Consulting sur le cœur technique du projet (jamais "expertise dans la mise en place d'accords-cadres").
- "conformite_cnje" : au moins 4 critères précis (Plus-Value Pédagogique, Régie / Forfait, Pénalités & Indemnités de retard, Garantie & Propriété Intellectuelle).
- "ventilation_financiere" : au moins 3 à 5 phases distinctes et détaillées avec des JEH entiers réalistes.
- "clauses_a_renegocier" : liste toutes les clauses problématiques identifiées (pénalités déplafonnées, durée, garantie, etc.).

Réponds UNIQUEMENT avec un objet JSON valide respectant ces clés exactes :
{{
  "raisonnement_auditeur": "Résumé structuré du raisonnement critique (4-6 phrases)",
  "titre_marche": "Objet technique réel du marché",
  "client": "Nom exact de l'acheteur",
  "decision_gonogo": "NO-GO (BLOQUANT CNJE) | GO SOUS RÉSERVE DE RENÉGOCIATION | GO STRATÉGIQUE",
  "score_opportunite": 55,
  "synthese_executive": "Synthèse complète du périmètre technique, financier et juridique",
  "argumentaire_commercial_n7": "Argumentaire technique ENSEEIHT + références N7 Consulting",
  "conformite_cnje": [
    {{"critere": "string", "statut": "CONFORME | À NÉGOCIER | NON CONFORME", "commentaire": "string"}}
  ],
  "staffing_enseeiht": [
    {{"filiere": "SN", "niveau": "2A / 3A ENSEEIHT", "nombre_etudiants": 2, "competences_cles": ["string"], "role_dans_projet": "string"}}
  ],
  "ventilation_financiere": [
    {{"phase": "Phase 1 : ...", "description": "string", "jeh_estimes": 8, "profil_associe": "string"}}
  ],
  "total_jeh_estime": 30,
  "matrice_risques": [
    {{"domaine": "Juridique | Technique | Financier", "description": "string", "impact": "Critique | Élevé | Moyen", "plan_mitigation": "string"}}
  ],
  "clauses_a_renegocier": ["string"],
  "recommandations_commerciales": ["string"]
}}
"""
        logger.info("Passe 2/2 : Structuration JSON du dossier N7...")
        response = completion(
            model=self.model_name,
            messages=[{"role": "user", "content": json_prompt}],
            temperature=0.1,
            max_tokens=2800,
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
