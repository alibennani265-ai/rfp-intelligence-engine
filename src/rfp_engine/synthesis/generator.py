from typing import Any, Dict, List
from litellm import completion
from loguru import logger
from pydantic import BaseModel


class ENSEEIHTStaffing(BaseModel):
    filiere: str  # "SN (Sciences du Numérique)", "3EA", "MFEE"
    nombre_etudiants: int
    competences_cles: List[str]
    justification: str


class GoNoGoAnalysis(BaseModel):
    decision: str  # "GO", "NO-GO", "GO SOUS RÉSERVE"
    score_faisabilite: int  # Note sur 100
    conformite_cnje: str  # Validation du cadre légal Junior-Entreprise
    points_bloquants: List[str]  # Clauses rédhibitoires (pénalités, CA, assurance)
    risques_majeurs: List[str]
    staffing_recommande: List[ENSEEIHTStaffing]
    estimation_jeh: str  # Estimation globale de l'effort en Jours-Étude Homme


class N7BiddingDossier(BaseModel):
    titre_projet: str
    synthese_executive: str
    argumentaire_n7: str  # Pourquoi N7 Consulting doit remporter le marché
    analyse_go_nogo: GoNoGoAnalysis
    decoupage_lots: List[Dict[str, str]]  # Lot, Description, Profils ENSEEIHT
    recommandations_avant_vente: List[str]


class RFPSynthesizer:

    def __init__(self, model_name: str = "ollama/llama3.1:8b"):
        self.model_name = model_name

    def answer_question(
        self, query: str, requirements: List[Dict[str, Any]]
    ) -> str:
        """Chat RAG orienté Junior-Entreprise N7 Consulting."""
        context_text = "\n\n".join(
            [
                f"Exigence [{req['id']}] (Section: {req['section']}):\n{req['text']}"
                for req in requirements
            ]
        )

        prompt = f"""Tu es le Directeur Commercial virtuel de N7 Consulting, la Junior-Entreprise de l'ENSEEIHT (Centrale Toulouse).
Réponds à la question de l'équipe commerciale en analysant le Cahier des Charges ci-dessous sous l'angle métier Junior-Entreprise (cadre CNJE, profils étudiants SN/3EA/MFEE, tarifs JEH, pénalités).

EXTRAITS DU DOCUMENT :
{context_text}

QUESTION : {query}

CONSIGNES :
- Analyse l'impact direct pour N7 Consulting.
- Cite les exigences (ex: REQ-01) concernées.
- Sois direct, pragmatique et orienté décision commerciale.
"""
        try:
            response = completion(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Erreur Chat LLM: {e}")
            return "Erreur lors de la réponse. Vérifiez qu'Ollama tourne bien en local."

    def evaluate_go_nogo(
        self, requirements: List[Dict[str, Any]]
    ) -> GoNoGoAnalysis:
        """Évalue la faisabilité pour N7 Consulting et propose le staffing ENSEEIHT."""
        context_text = "\n".join(
            [
                f"[{req['id']}] ({req['section']}): {req['text']}"
                for req in requirements[:12]
            ]
        )

        prompt = f"""Tu es l'Expert Avant-Vente de N7 Consulting (Junior-Entreprise de l'ENSEEIHT).
Analyse les exigences suivantes pour déterminer si N7 Consulting peut postuler à cet appel d'offres.

EXIGENCES :
{context_text}

RÈGLES CNJE & ENSEEIHT :
1. Cadre CNJE : Réalisation d'études d'ingénierie à valeur pédagogique. Pas de régie pure, ni de maintenance pluriannuelle 24/7 post-diplôme.
2. Filières ENSEEIHT : SN (Informatique, IA, Data, Telecom, Dev), 3EA (Électronique, Automatique, Énergie), MFEE (Mécanique des Fluides, Hydraulique, Environnement).

Produis une réponse au format JSON respectant strictement cette structure :
{{
  "decision": "GO",
  "score_faisabilite": 85,
  "conformite_cnje": "Excellente. Projet d'ingénierie logicielle répondant au cadre pédagogique CNJE.",
  "points_bloquants": ["Aucun point rédhibitoire identifié."],
  "risques_majeurs": ["Clause de pénalité de retard de 1% par jour", "Obligation de propriété intellectuelle exclusive"],
  "staffing_recommande": [
    {{
      "filiere": "SN (Sciences du Numérique)",
      "nombre_etudiants": 2,
      "competences_cles": ["Python", "FastAPI", "RAG / LLM"],
      "justification": "Développement du moteur d'IA et de l'architecture logicielle."
    }}
  ],
  "estimation_jeh": "25 à 35 Jours-Étude Homme (JEH)"
}}
"""
        try:
            response = completion(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]

            return GoNoGoAnalysis.model_validate_json(content.strip())
        except Exception as e:
            logger.error(f"Erreur Go/No-Go: {e}")
            return self._fallback_gonogo(requirements)

    def generate_dossier(
        self, requirements: List[Dict[str, Any]]
    ) -> N7BiddingDossier:
        """Génère le dossier complet de stratégie de réponse pour l'équipe commerciale."""
        gonogo = self.evaluate_go_nogo(requirements)

        context_text = "\n".join(
            [f"[{req['id']}]: {req['text']}" for req in requirements[:8]]
        )

        prompt = f"""Tu es le Vice-Président Commercial de N7 Consulting.
Génère le plan d'action d'avant-vente et l'argumentaire stratégique pour emporter cet appel d'offres.

EXIGENCES CLES :
{context_text}

Produis un JSON valide suivant ce schéma :
{{
  "titre_projet": "Réponse Appel d'Offres - Ingénierie & Développement",
  "synthese_executive": "Synthèse des enjeux et opportunités du marché pour N7 Consulting.",
  "argumentaire_n7": "N7 Consulting combine l'excellence académique des élèves-ingénieurs de l'ENSEEIHT (Centrale Toulouse) avec la réactivité d'une structure certifiée ISO 9001.",
  "decoupage_lots": [
    {{
      "lot": "Lot 1 : Spécifications et Architecture",
      "description": "Analyse du besoin et conception de la solution.",
      "profils": "1 Élève-Ingénieur SN"
    }},
    {{
      "lot": "Lot 2 : Développement & Intégration",
      "description": "Implémentation technique et tests de recette.",
      "profils": "2 Élèves-Ingénieurs SN / Data"
    }}
  ],
  "recommandations_avant_vente": [
    "Planifier un rendez-vous de cadrage avec le client sous 48h.",
    "Négocier un plafonnement des pénalités de retard à 10% du montant total HT."
  ]
}}
"""
        try:
            response = completion(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]

            dossier_dict = json.loads(content.strip())
            return N7BiddingDossier(
                titre_projet=dossier_dict.get(
                    "titre_projet", "Dossier d'Avant-Vente N7"
                ),
                synthese_executive=dossier_dict.get(
                    "synthese_executive", ""
                ),
                argumentaire_n7=dossier_dict.get("argumentaire_n7", ""),
                analyse_go_nogo=gonogo,
                decoupage_lots=dossier_dict.get("decoupage_lots", []),
                recommandations_avant_vente=dossier_dict.get(
                    "recommandations_avant_vente", []
                ),
            )
        except Exception as e:
            logger.error(f"Erreur Dossier N7: {e}")
            return N7BiddingDossier(
                titre_projet="Dossier de Réponse N7 Consulting",
                synthese_executive="Analyse de l'appel d'offres pour l'ENSEEIHT.",
                argumentaire_n7="Force frappe d'ingénieurs ENSEEIHT qualifiés.",
                analyse_go_nogo=gonogo,
                decoupage_lots=[
                    {
                        "lot": "Lot Unique : Ingénierie & Réalisation",
                        "description": "Exécution globale par équipe projet N7.",
                        "profils": "Étudiants ENSEEIHT",
                    }
                ],
                recommandations_avant_vente=[
                    "Valider la conformité de la convention auprès de la CNJE."
                ],
            )

    def _fallback_gonogo(
        self, requirements: List[Dict[str, Any]]
    ) -> GoNoGoAnalysis:
        return GoNoGoAnalysis(
            decision="GO SOUS RÉSERVE",
            score_faisabilite=75,
            conformite_cnje="Conforme aux statuts d'étude d'ingénierie.",
            points_bloquants=["Vérifier les exigences d'assurance RCA."],
            risques_majeurs=["Délais de livraison serrés."],
            staffing_recommande=[
                ENSEEIHTStaffing(
                    filiere="SN (Sciences du Numérique)",
                    nombre_etudiants=2,
                    competences_cles=["Python", "Ingénierie Logicielle"],
                    justification="Réalisation de la prestation technique.",
                )
            ],
            estimation_jeh="15 à 25 JEH",
        )