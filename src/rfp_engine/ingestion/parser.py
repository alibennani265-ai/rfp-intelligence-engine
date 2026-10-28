from pathlib import Path
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from pypdf import PdfReader
from loguru import logger


class RFPRequirement(BaseModel):
    requirement_id: str
    section: str
    text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RFPParser:
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"Fichier non trouvé : {file_path}")

    def parse(self) -> List[RFPRequirement]:
        logger.info(f"Début du parsing de {self.file_path.name}")
        reader = PdfReader(self.file_path)
        requirements: List[RFPRequirement] = []

        for page_idx, page in enumerate(reader.pages):
            text = page.extract_text()
            if not text:
                continue

            lines = text.split("\n")
            current_section = f"Page {page_idx + 1}"

            for line_idx, line in enumerate(lines):
                cleaned_line = line.strip()
                if len(cleaned_line) < 10:
                    continue

                req_id = f"REQ-P{page_idx + 1}-L{line_idx + 1}"
                requirements.append(
                    RFPRequirement(
                        requirement_id=req_id,
                        section=current_section,
                        text=cleaned_line,
                        metadata={
                            "source_file": self.file_path.name,
                            "page": page_idx + 1,
                        },
                    )
                )

        logger.info(f"Parsing terminé. {len(requirements)} exigences extraites.")
        return requirements