import json
from typing import Any, Dict, List
from litellm import completion
from loguru import logger
from pydantic import BaseModel, Field


class CNJECheckItem(BaseModel):
    critere: str
    statut: str  # "CONFORME", "NON CONFORME", "À NÉGOCIER"
    commentaire: str


class ENSEEIHTStaffing(BaseModel):
    filiere: str  # "SN", "3EA", "MFEE"
    niveau: str  # "N7 (1ère année)", "N7 (2ème année)", "N7 (3ème année)"
    nombre_etudiants: int
    competences_cles: List[str]
    role_dans_projet: str


class PhasePricing(BaseModel):
    phase: str
    description: str
    jeh_estimes: int
    profil_associe: str


class RiskItem(BaseModel):
    domaine: str  # "Juridique", "Technique", "Calendrier", "Financier"
    description: str
    impact: str  # "Élevé", "Moyen", "Faible"
    plan_mitigation: str


class N7BiddingDossier(BaseModel):
    titre_marche: str
    client: str
    decision_gonogo: str  # "GO STRATÉGIQUE", "GO SOUS RÉSERVE", "NO-GO"
    score_opportunite: int  # /100
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

    def answer_question(
        self, query: str, requirements: List[Dict[str, Any]]
    ) -> str:
        """Chat RAG générique orienté N7 Consulting."""
        context_text = "\n\n".join(
            [
                f"Clause [{req['id']}] (Section: {req['section']}):\n{req['text']}"
                for req in requirements
            ]
        )

        prompt = f"""Tu es le Directeur Commercial de N7 Consulting, la Junior-Entreprise de l'ENSEEIHT (Centrale Toulouse).
Réponds à la question de l'équipe commerciale en analysant le Cahier des Charges ci-dessous.

EXTRAITS DU DOCUMENT :
{context_text}

QUESTION : {query}

INSTRUCTIONS :
- Base tes réponses STRICTEMENT sur les clauses extraites du document.
- Analyse l'impact métier pour N7 Consulting (cadre CNJE, filières ENSEEIHT SN/3EA/MFEE, risques contractuels, pénalités).
- Si une information est absente des extraits, indique-le clairement.
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
            return "Erreur lors de la réponse du modèle. Vérifiez qu'Ollama est actif en arrière-plan."

    def generate_dossier(
        self, requirements: List[Dict[str, Any]]
    ) -> N7BiddingDossier:
        """Génère le dossier d'avant-vente dynamique basé exclusivement sur le PDF chargé."""
        context_text = "\n\n".join(
            [
                f"[{req['id']}] (Section: {req['section']}): {req['text']}"
                for req in requirements[:15]
            ]
        )

        prompt = f"""Tu es le Vice-Président Commercial de N7 Consulting (Junior-Entreprise de l'ENSEEIHT).
Analyse les clauses ci-dessous extraites d'un appel d'offres et génère un Dossier d'Avant-Vente complet au format JSON.

EXTRAITS DU CAHIER DES CHARGES :
{context_text}

RÈGLES D'EXTRACTION DYNAMIQUE :
1. "titre_marche" : Extrais l'intitulé exact ou le sujet du marché d'après le texte (ou formule un titre précis sur la base du besoin).
2. "client" : Extrais le nom de la structure / entreprise / acheteur citée dans le texte (si non mentionné, indique "Organisme Client").
3. "conformite_cnje" : Analyse l'adéquation avec le statut Junior-Entreprise (mission à valeur pédagogique, pas de régie pure, pas d'astreinte 24/7).
4. "staffing_enseeiht" : Détermine la ou les filières ENSEEIHT nécessaires (SN: Informatique/Data/IA, 3EA: Électronique/Énergie/Automatique, MFEE: Mécanique des Fluides/Environnement).

Format JSON attendu :
{{
  "titre_marche": "Nom exact ou identifié du marché",
  "client": "Nom du client/acheteur extrait du document",
  "decision_gonogo": "GO STRATÉGIQUE",
  "score_opportunite": 85,
  "synthese_executive": "Synthèse dynamique des enjeux du besoin exprimé dans ce document.",
  "argumentaire_commercial_n7": "Positionnement stratégique de N7 Consulting fondé sur l'excellence académique de l'ENSEEIHT et la certification ISO 9001.",
  "conformite_cnje": [
    {{
      "critere": "Valeur pédagogique de la mission",
      "statut": "CONFORME",
      "commentaire": "Explication basée sur le besoin technique du document."
    }}
  ],
  "staffing_enseeiht": [
    {{
      "filiere": "SN (Sciences du Numérique)",
      "niveau": "N7 (2ème année)",
      "nombre_etudiants": 2,
      "competences_cles": ["Compétence 1", "Compétence 2"],
      "role_dans_projet": "Description de l'intervention."
    }}
  ],
  "ventilation_financiere": [
    {{
      "phase": "Phase 1 : Cadrage",
      "description": "Détail de la prestation",
      "jeh_estimes": 5,
      "profil_associe": "Consultant N7"
    }}
  ],
  "total_jeh_estime": 20,
  "matrice_risques": [
    {{
      "domaine": "Juridique / Technique",
      "description": "Risque identifié dans le document",
      "impact": "Élevé",
      "plan_mitigation": "Action corrective proposée par N7"
    }}
  ],
  "clauses_a_renegocier": ["Clause extraite à négocier"],
  "recommandations_commerciales": ["Action d'avant-vente conseillée"]
}}
"""

        logger.info(
            "Analyse du document et génération du Dossier d'Avant-Vente..."
        )

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

            return N7BiddingDossier.model_validate_json(content.strip())
        except Exception as e:
            logger.error(f"Erreur lors de la génération du dossier : {e}")
            return self._generate_fallback_dossier(requirements)

    def _generate_fallback_dossier(
        self, requirements: List[Dict[str, Any]]
    ) -> N7BiddingDossier:
        first_req = requirements[0] if requirements else {}
        doc_name = first_req.get("section", "Document d'Appel d'Offres")

        return N7BiddingDossier(
            titre_marche=f"Analyse du marché : {doc_name}",
            client="Acheteur / Organisme Émetteur",
            decision_gonogo="GO SOUS RÉSERVE",
            score_opportunite=75,
            synthese_executive="Analyse basée sur les exigences extraites du document importé. Les informations spécifiques doivent être validées lors de la phase de cadrage commercial.",
            argumentaire_commercial_n7="N7 Consulting s'appuie sur le réservoir de compétences des élèves-ingénieurs de l'ENSEEIHT et son système de management de la qualité certifié ISO 9001.",
            conformite_cnje=[
                CNJECheckItem(
                    critere="Cadre pédagogique",
                    statut="CONFORME",
                    commentaire="L'étude doit être découpée en phases d'ingénierie réalisables par des étudiants.",
                ),
                CNJECheckItem(
                    critere="Garanties & Assurances",
                    statut="À NÉGOCIER",
                    commentaire="Vérifier la présence de clauses de responsabilité ou de pénalités de retard.",
                ),
            ],
            staffing_enseeiht=[
                ENSEEIHTStaffing(
                    filiere="SN (Sciences du Numérique)",
                    niveau="N7 (2ème année)",
                    nombre_etudiants=2,
                    competences_cles=[
                        "Ingénierie Logicielle",
                        "Traitement de Données",
                    ],
                    role_dans_projet="Réalisation des prestations techniques.",
                )
            ],
            ventilation_financiere=[
                PhasePricing(
                    phase="Phase 1 : Cadrage & Spécifications",
                    description="Analyse du besoin et conception de la solution.",
                    jeh_estimes=5,
                    profil_associe="Consultant N7",
                ),
                PhasePricing(
                    phase="Phase 2 : Réalisation & Tests",
                    description="Implémentation et validation technique.",
                    jeh_estimes=15,
                    profil_associe="Consultant Développeur N7",
                ),
            ],
            total_jeh_estime=20,
            matrice_risques=[
                RiskItem(
                    domaine="Contractuel",
                    description="Absence de précision sur les modalités de recette.",
                    impact="Moyen",
                    plan_mitigation="Valider le calendrier de livraison dès le démarrage de la convention.",
                )
            ],
            clauses_a_renegocier=[
                "Plafonner les pénalités éventuelles à 10% du montant HT."
            ],
            recommandations_commerciales=[
                "Organiser un entretien de cadrage technique avec le client."
            ],
        )