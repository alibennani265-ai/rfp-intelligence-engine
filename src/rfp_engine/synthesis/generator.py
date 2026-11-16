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

    def _call_llm(
        self,
        prompt: str,
        temperature: float = 0.15,
        max_tokens: int = 2500,
        json_mode: bool = False,
    ) -> str:
        kwargs: dict[str, Any] = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "extra_body": {"options": {"num_ctx": 16384}},
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
        return self._call_llm(prompt, temperature=0.2, max_tokens=2000)

    def _agent_legal_audit(self, rfp_context: str, legal_context: str) -> str:
        """Agent 1 : Auditeur Légal CNJE spécialisé — extrait uniquement les faits juridiques sourcés du marché."""
        prompt = f"""Tu es l'Auditeur Légal CNJE de N7 Consulting.
Lis TOUS les extraits du marché client ci-dessous et relève chaque fait contractuel avec sa référence d'article/page exacte.
Ne devine rien : si une clause est absente, écris "Non mentionné dans les extraits".

CADRE LÉGAL CNJE :
{CNJE_RULES}
{legal_context}

EXTRAITS DU MARCHÉ CLIENT :
{rfp_context}

Rédige un constat juridique factuel en répondant point par point :
1. **Acheteur & Objet exact** : Nom de l'organisme acheteur et nature technique réelle des prestations demandées.
2. **Mode d'exécution (Forfait vs Régie)** : Le marché impose-t-il une présence sur site, une intégration dans l'équipe client, des feuilles de temps/pointage, ou un engagement au forfait sur livrables ? (Cite le texte exact).
3. **Pénalités & Indemnités de retard** : Y a-t-il des pénalités ou indemnités de retard ? Sont-elles plafonnées ou **déplafonnées** / journalières / sans mise en demeure ? (Cite le texte et l'article exact).
4. **Garanties, Maintenance, Astreintes & PI** : Durée de garantie demandée, astreintes éventuelles, sous-traitance, cession de propriété intellectuelle.
5. **Verdict Juridique CNJE** :
   - Si régie/subordination, feuilles de temps, astreintes ou sous-traitance obligatoire -> **NO-GO (BLOQUANT CNJE)**.
   - Si pénalités/indemnités de retard déplafonnées, garantie > 3 mois ou clauses financières déséquilibrées -> **GO SOUS RÉSERVE DE RENÉGOCIATION**.
   - Si aucune clause problématique trouvée dans le texte -> **GO STRATÉGIQUE**.
"""
        logger.info("Agent 1/3 : Audit juridique factuel CNJE...")
        return self._call_llm(prompt, temperature=0.1, max_tokens=1600)

    def _agent_technical_scoping(
        self, rfp_context: str, legal_audit: str, dept_info: str
    ) -> str:
        """Agent 2 : Architecte ENSEEIHT & Chiffrage — dimensionne les compétences et phases uniquement d'après le besoin technique."""
        prompt = f"""Tu es le Directeur Technique (CTO) de N7 Consulting (ENSEEIHT).
À partir des extraits du marché et de l'audit juridique, dimensionne l'équipe étudiante et le découpage financier en JEH.

FILIÈRES ENSEEIHT :
{dept_info}

RÈGLE ABSOLUE DE ROUTAGE DES FILIÈRES :
- Si le marché concerne du logiciel, développement web/mobile, plateforme, data, IA, SI ou cloud -> utilise **UNIQUEMENT la filière SN**. Interdiction absolue d'inclure 3EA ou MFEE.
- N'inclus **3EA** que si le texte mentionne des cartes électroniques, capteurs, FPGA, systèmes embarqués ou automatisme.
- N'inclus **MFEE** que si le texte mentionne de la mécanique des fluides (CFD), thermique, hydraulique ou énergie.

CONSTAT JURIDIQUE DÉJÀ ÉTABLI :
{legal_audit}

EXTRAITS TECHNIQUES DU MARCHÉ :
{rfp_context}

Rédige le dimensionnement technique en 3 points :
1. **Filière(s) ENSEEIHT strictement requise(s)** et profils étudiants (ex: Chef de projet / Architecte SN + Développeurs SN).
2. **Découpage en 3 à 5 phases cohérentes** avec l'ampleur réelle du marché (ex: Phase 1 Cadrage & Spécifications, Phase 2 Développement / Conception, Phase 3 Tests & Intégration, Phase 4 Recette & Documentation) et estimation réaliste en JEH entiers.
3. **Argumentaire technique N7 Consulting** basé sur les compétences de la filière retenue et les études passées similaires.
"""
        logger.info("Agent 2/3 : Dimensionnement technique & chiffrage JEH...")
        return self._call_llm(prompt, temperature=0.15, max_tokens=1600)

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

        # Vérification stricte de cohérence entre les statuts CNJE / clauses à renégocier et le verdict Go/No-Go
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

        legal_audit = self._agent_legal_audit(rfp_context, legal_context)
        tech_scoping = self._agent_technical_scoping(
            rfp_context, legal_audit, dept_info
        )

        json_prompt = f"""Assemble le dossier final d'avant-vente N7 Consulting au format JSON en synthétisant FIDÈLEMENT les deux rapports d'experts ci-dessous.
RÈGLE DE COHÉRENCE ABSOLUE :
- Chaque ligne du tableau "conformite_cnje" DOIT être 100 % cohérente avec "clauses_a_renegocier" et "decision_gonogo" (ne jamais écrire qu'une clause est conforme si elle apparaît dans les clauses à renégocier).
- N'invente aucune clause absente du rapport juridique.

=== RAPPORT AGENT 1 : AUDIT JURIDIQUE CNJE ===
{legal_audit}

=== RAPPORT AGENT 2 : DIMENSIONNEMENT TECHNIQUE & CHIFFRAGE ===
{tech_scoping}

Réponds UNIQUEMENT avec un objet JSON valide respectant exactement ce schéma :
{{
  "raisonnement_auditeur": "Synthèse fidèle des constats juridiques et techniques des 2 agents",
  "titre_marche": "Objet technique réel du marché",
  "client": "Nom exact de l'acheteur",
  "decision_gonogo": "NO-GO (BLOQUANT CNJE) | GO SOUS RÉSERVE DE RENÉGOCIATION | GO STRATÉGIQUE",
  "score_opportunite": 55,
  "synthese_executive": "Synthèse complète du périmètre technique, juridique et financier",
  "argumentaire_commercial_n7": "Argumentaire technique ENSEEIHT basé sur le rapport de l'Agent 2",
  "conformite_cnje": [
    {{"critere": "Critère audité", "statut": "CONFORME | À NÉGOCIER | NON CONFORME", "commentaire": "Constat exact avec référence article/page"}}
  ],
  "staffing_enseeiht": [
    {{"filiere": "SN", "niveau": "2A / 3A ENSEEIHT", "nombre_etudiants": 2, "competences_cles": ["string"], "role_dans_projet": "string"}}
  ],
  "ventilation_financiere": [
    {{"phase": "Phase 1 : ...", "description": "Livrables précis", "jeh_estimes": 8, "profil_associe": "string"}}
  ],
  "total_jeh_estime": 30,
  "matrice_risques": [
    {{"domaine": "Juridique | Technique | Financier", "description": "Risque réel identifié", "impact": "Critique | Élevé | Moyen", "plan_mitigation": "Action concrète"}}
  ],
  "clauses_a_renegocier": ["Uniquement les clauses réellement problématiques relevées par l'Agent 1"],
  "recommandations_commerciales": ["Action concrète d'avant-vente"]
}}
"""
        logger.info("Agent 3/3 : Assemblage JSON cohérent du dossier N7...")
        content = self._call_llm(
            json_prompt, temperature=0.1, max_tokens=2800, json_mode=True
        )
        match = re.search(r"\{.*\}", content, re.DOTALL)
        dossier = N7BiddingDossier.model_validate_json(
            match.group(0) if match else content
        )
        return self._enforce_consistency(dossier, rfp_context.lower())
