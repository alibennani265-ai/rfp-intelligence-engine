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
    critere: str = "Conformité générale"
    statut: str = "À NÉGOCIER"
    commentaire: str = "À vérifier dans la Convention d'Étude"

    @field_validator("critere", "statut", "commentaire", mode="before")
    @classmethod
    def clean_str(cls, v: Any) -> str:
        return _coerce_str(v)


class ENSEEIHTStaffing(BaseModel):
    filiere: str = "SN"
    niveau: str = "2A / 3A ENSEEIHT"
    nombre_etudiants: int = 2
    competences_cles: list[str] = ["Développement Logiciel", "Data & IA"]
    role_dans_projet: str = "Réalisation des livrables techniques"

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
    phase: str = "Phase d'étude"
    description: str = "Conception et livraison des modules attendus"
    jeh_estimes: int = 6
    profil_associe: str = "Consultant ENSEEIHT SN"

    @field_validator("phase", "description", "profil_associe", mode="before")
    @classmethod
    def clean_str(cls, v: Any) -> str:
        return _coerce_str(v)

    @field_validator("jeh_estimes", mode="before")
    @classmethod
    def clean_int(cls, v: Any) -> int:
        val = max(1, _coerce_int(v, 6))
        # Si le LLM a mis un montant en euros (>= 150) au lieu d'un nombre de JEH, conversion automatique (442 EUR/JEH)
        return max(2, round(val / 442)) if val >= 150 else val


class RiskItem(BaseModel):
    domaine: str = "Juridique / Technique"
    description: str = "Point de vigilance identifié dans le CCTP"
    impact: str = "Moyen"
    plan_mitigation: str = "Encadrement contractuel dans la Convention d'Étude"

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

    def _call_llm(
        self,
        prompt: str,
        temperature: float = 0.15,
        max_tokens: int = 1600,
        num_ctx: int = 8192,
        json_mode: bool = False,
    ) -> str:
        kwargs: dict[str, Any] = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "extra_body": {"options": {"num_ctx": num_ctx}},
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        response = completion(**kwargs)
        return str(response.choices[0].message.content).strip()

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
- Tout projet logiciel, web, SaaS, plateforme, data, IA ou déploiement cloud relève EXCLUSIVEMENT de la filière **SN (Sciences du Numérique)**. Ne cite 3EA ou MFEE que si le texte mentionne explicitement du matériel électronique/embarqué ou de la mécanique des fluides/thermique.

EXTRAITS DOCUMENTAIRES (MARCHÉ CLIENT + ÉTUDES N7 + CLR CNJE) :
{context_text}

QUESTION : {query}

Structure ta réponse en 3 parties :
### 1. Avis Technique & Références N7 Consulting
### 2. Audit de Conformité Légale (CLR CNJE)
### 3. Recommandation Commerciale
"""
        return self._call_llm(prompt, temperature=0.2, max_tokens=1600, num_ctx=8192)

    @staticmethod
    def _enforce_consistency(
        dossier: N7BiddingDossier, rfp_text_lower: str
    ) -> N7BiddingDossier:
        """Verrou déterministe anti-contradiction entre l'audit juridique, le staffing et la décision finale."""
        has_hardware = any(
            k in rfp_text_lower
            for k in (
                "électronique",
                "embarqué",
                "fpga",
                "microcontrôleur",
                "capteur",
                "automatisme",
                "signal",
            )
        )
        has_fluids = any(
            k in rfp_text_lower
            for k in (
                "mécanique des fluides",
                "cfd",
                "thermique",
                "hydraulique",
                "aérodynamique",
            )
        )

        filtered_staffing = []
        for s in dossier.staffing_enseeiht:
            fil = s.filiere.upper()
            if "3EA" in fil and not has_hardware:
                continue
            if "MFEE" in fil and not has_fluids:
                continue
            filtered_staffing.append(s)

        if not filtered_staffing:
            filtered_staffing = [
                ENSEEIHTStaffing(
                    filiere="SN",
                    niveau="2A / 3A ENSEEIHT",
                    nombre_etudiants=2,
                    competences_cles=[
                        "Architecture Logicielle",
                        "Développement Full-Stack",
                        "Data & IA",
                    ],
                    role_dans_projet="Conception, développement et recette des livrables numériques",
                )
            ]
        dossier.staffing_enseeiht = filtered_staffing

        statuses = [c.statut.upper() for c in dossier.conformite_cnje]
        comments_blob = " ".join(
            [c.commentaire.lower() for c in dossier.conformite_cnje]
            + [cl.lower() for cl in dossier.clauses_a_renegocier]
            + [dossier.raisonnement_auditeur.lower()]
        )
        has_non_conforme = any("NON CONFORME" in s or "BLOQUANT" in s for s in statuses)
        has_to_negotiate = (
            any("NÉGOCIER" in s or "NEGOCIER" in s for s in statuses)
            or len(dossier.clauses_a_renegocier) > 0
        )
        has_deplafonne = "déplafonn" in comments_blob or "deplafonn" in comments_blob
        has_regie = any(
            w in comments_blob
            for w in (
                "prêt de main",
                "régie",
                "feuille de temps",
                "subordination",
                "astreinte 24",
            )
        )

        if has_non_conforme or has_regie:
            dossier.decision_gonogo = "NO-GO (BLOQUANT CNJE)"
            dossier.score_opportunite = min(dossier.score_opportunite, 38)
        elif has_to_negotiate or has_deplafonne:
            if "GO STRAT" in dossier.decision_gonogo.upper():
                dossier.decision_gonogo = "GO SOUS RÉSERVE DE RENÉGOCIATION"
            dossier.score_opportunite = min(max(dossier.score_opportunite, 42), 68)

        if dossier.ventilation_financiere:
            dossier.total_jeh_estime = sum(
                p.jeh_estimes for p in dossier.ventilation_financiere
            )
        return dossier

    def generate_dossier(
        self,
        rfp_chunks: list[dict[str, Any]],
        legal_chunks: list[dict[str, Any]] | None = None,
    ) -> N7BiddingDossier:
        # On garde les 16 extraits les plus pertinents pour tenir confortablement dans num_ctx=8192 et répondre en < 45s
        selected_chunks = rfp_chunks[:16]
        rfp_context = "\n\n".join(
            [
                f"[{r.get('id', i)}] ({r.get('section')}): {r.get('text')}"
                for i, r in enumerate(selected_chunks)
            ]
        )
        legal_context = "\n\n".join(
            [f"[N7/CNJE]: {r.get('text')}" for r in (legal_chunks or [])[:3]]
        )
        dept_info = json.dumps(ENSEEIHT_DEPARTMENTS, ensure_ascii=False, indent=2)

        # Passe 1 : Diagnostic juridique & technique synthétique et chirurgical (~20s)
        audit_prompt = f"""Tu es l'Auditeur Légal CNJE et CTO de N7 Consulting (ENSEEIHT).
Analyse ces extraits du marché client et rédige une fiche de diagnostic factuelle en 6 points concis (cite les articles/pages exacts) :

RÈGLES CNJE :
{CNJE_RULES}
{legal_context}

FILIÈRES ENSEEIHT (SN uniquement pour logiciel/web/data/IA ; 3EA uniquement si matériel électronique ; MFEE uniquement si fluides/thermique) :
{dept_info}

EXTRAITS DU MARCHÉ CLIENT :
{rfp_context}

Rédige les 6 points (sois factuel, concis et sans contradiction) :
1. ACHETEUR & OBJET TECHNIQUE RÉEL :
2. CONFORMITÉ CNJE & CLAUSES BLOQUANTES (pénalités/indemnités de retard déplafonnées ? régie/feuilles de temps ? astreintes ? sous-traitance ? garantie > 3 mois ?) :
3. VERDICT GO/NO-GO & SCORE (/100) :
4. FILIÈRE(S) ENSEEIHT & PROFILS ÉTUDIANTS :
5. PHASES DU PROJET & CHIFFRAGE EN JEH (3 à 4 phases réalistes — ATTENTION : 1 JEH = 1 jour-homme à 442 € HT, donc entre 3 et 20 JEH par phase, jamais un montant en euros) :
6. RISQUES MAJEURS & CLAUSES À RENÉGOCIER :
"""
        logger.info(
            f"Passe 1/2 : Diagnostic juridique et technique ({len(selected_chunks)} blocs)..."
        )
        diagnostic = self._call_llm(
            audit_prompt, temperature=0.1, max_tokens=900, num_ctx=8192
        )

        # Passe 2 : Conversion JSON rapide (~20s)
        json_prompt = f"""Convertis ce diagnostic en JSON valide sans aucune contradiction entre le tableau "conformite_cnje", "clauses_a_renegocier" et "decision_gonogo".

DIAGNOSTIC :
{diagnostic}

Schéma JSON attendu :
{{
  "raisonnement_auditeur": "Résumé en 4 phrases des constats juridiques et techniques",
  "titre_marche": "Titre technique réel du marché",
  "client": "Nom exact de l'acheteur",
  "decision_gonogo": "NO-GO (BLOQUANT CNJE) | GO SOUS RÉSERVE DE RENÉGOCIATION | GO STRATÉGIQUE",
  "score_opportunite": 55,
  "synthese_executive": "Synthèse du périmètre technique, financier et juridique",
  "argumentaire_commercial_n7": "Légitimité technique ENSEEIHT et références N7 Consulting",
  "conformite_cnje": [
    {{"critere": "Critère audité", "statut": "CONFORME | À NÉGOCIER | NON CONFORME", "commentaire": "Constat précis avec citation du marché"}}
  ],
  "staffing_enseeiht": [
    {{"filiere": "SN", "niveau": "2A / 3A ENSEEIHT", "nombre_etudiants": 2, "competences_cles": ["string"], "role_dans_projet": "string"}}
  ],
  "ventilation_financiere": [
    {{"phase": "Phase 1 : ...", "description": "Livrables", "jeh_estimes": 8, "profil_associe": "string"}}
  ],
  "total_jeh_estime": 30,
  "matrice_risques": [
    {{"domaine": "Juridique | Technique | Financier", "description": "Risque identifié", "impact": "Critique | Élevé | Moyen", "plan_mitigation": "Action concrète"}}
  ],
  "clauses_a_renegocier": ["Clause précise à renégocier"],
  "recommandations_commerciales": ["Action avant-vente"]
}}
"""
        logger.info("Passe 2/2 : Structuration JSON du dossier N7...")
        content = self._call_llm(
            json_prompt, temperature=0.1, max_tokens=1600, num_ctx=6144, json_mode=True
        )
        match = re.search(r"\{.*\}", content, re.DOTALL)
        dossier = N7BiddingDossier.model_validate_json(
            match.group(0) if match else content
        )
        return self._enforce_consistency(dossier, rfp_context.lower())
