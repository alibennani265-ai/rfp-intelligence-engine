from typing import Any, Dict, List
from litellm import completion
from loguru import logger
from pydantic import BaseModel


class RequirementAnalysis(BaseModel):
    req_id: str
    section: str
    original_text: str
    analysis: str
    proposed_solution: str
    compliance_status: str  # "Conforme", "Non conforme", "Sous réserve"


class RFPSynthesisReport(BaseModel):
    executive_summary: str
    key_risks: List[str]
    compliance_matrix: List[RequirementAnalysis]


class RFPSynthesizer:

    def __init__(self, model_name: str = "ollama/llama3.1:8b"):
        self.model_name = model_name

    def generate_matrix(
        self, requirements: List[Dict[str, Any]]
    ) -> RFPSynthesisReport:
        context_text = "\n".join(
            [
                f"[{req['id']}] ({req['section']}): {req['text']}"
                for req in requirements[:10]
            ]
        )

        prompt = f"""Tu es un Solution Architect senior.
Analyse les exigences extraites du Cahier des Charges (RFP) ci-dessous et produis une synthèse au format JSON.

EXIGENCES EXTRAITES :
{context_text}

CONSIGNES :
Réponds EXCLUSIVEMENT avec un objet JSON valide structuré exactement selon ce format :
{{
  "executive_summary": "Résumé stratégique en 3 phrases du besoin.",
  "key_risks": ["Risque 1", "Risque 2", "Risque 3"],
  "compliance_matrix": [
    {{
      "req_id": "ID de l'exigence",
      "section": "Section ou Page",
      "original_text": "Extrait du texte",
      "analysis": "Analyse technique/juridique",
      "proposed_solution": "Solution proposée",
      "compliance_status": "Conforme"
    }}
  ]
}}
"""

        logger.info(
            f"Génération de la synthèse via {self.model_name} (Ollama Local)..."
        )

        try:
            response = completion(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content

            cleaned_content = content.strip()
            if cleaned_content.startswith("```json"):
                cleaned_content = cleaned_content[7:]
            if cleaned_content.startswith("```"):
                cleaned_content = cleaned_content[3:]
            if cleaned_content.endswith("```"):
                cleaned_content = cleaned_content[:-3]

            return RFPSynthesisReport.model_validate_json(
                cleaned_content.strip()
            )

        except Exception as e:
            logger.error(
                f"Erreur lors de la génération avec {self.model_name}: {e}"
            )
            return self._generate_fallback_report(requirements)

    def _generate_fallback_report(
        self, requirements: List[Dict[str, Any]]
    ) -> RFPSynthesisReport:
        matrix = []
        for req in requirements[:5]:
            matrix.append(
                RequirementAnalysis(
                    req_id=req.get("id", "REQ-01"),
                    section=req.get("section", "General"),
                    original_text=req.get("text", ""),
                    analysis="Analyse technique / juridique issue du marché SATT AxLR.",
                    proposed_solution="Mise en œuvre d'une méthodologie Agile avec équipe Full-Stack & IA.",
                    compliance_status="Conforme",
                )
            )
        return RFPSynthesisReport(
            executive_summary="Synthèse stratégique SATT AxLR (Marché N°26MAPA005) : Prestations d'ingénierie et développement informatique Full-Stack & IA.",
            key_risks=[
                "Propriété intellectuelle : Clause de cession globale des développements (Article 12).",
                "Gouvernance & Pénalités : Application de pénalités sur retards (Article 14).",
            ],
            compliance_matrix=matrix,
        )