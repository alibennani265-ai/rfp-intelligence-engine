import re
from collections import Counter
from pathlib import Path
from typing import Any

from loguru import logger
from pydantic import BaseModel, Field
from pypdf import PdfReader

HEADING_PATTERN = re.compile(
    r"(?m)^((?:ARTICLE|CHAPITRE|SECTION|TITRE|LOT|ANNEXE|PARTIE|\d+(?:\.\d+){0,3}|[IVX]+\.)\s*[:\-\.]?\s*[^\n]{3,90})$",
    re.IGNORECASE,
)


class RFPRequirement(BaseModel):
    requirement_id: str
    section: str
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class RFPParser:
    """Parseur généraliste et adaptatif pour tout type d'appel d'offres PDF (CCTP, CCAP, RC, AE)."""

    def __init__(
        self,
        file_path: str,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ) -> None:
        self.file_path = Path(file_path)
        self.custom_chunk_size = chunk_size
        self.custom_chunk_overlap = chunk_overlap
        if not self.file_path.exists():
            raise FileNotFoundError(f"Fichier non trouvé : {file_path}")

    @staticmethod
    def _strip_repeated_headers_footers(
        pages_lines: list[list[str]],
    ) -> list[list[str]]:
        if len(pages_lines) < 3:
            return pages_lines
        edge_counts: Counter[str] = Counter()
        for lines in pages_lines:
            candidates = set(lines[:2] + lines[-2:])
            for line in candidates:
                cleaned = re.sub(r"\d+", "#", line.strip())
                if 5 <= len(cleaned) <= 100:
                    edge_counts[cleaned] += 1

        threshold = max(3, int(len(pages_lines) * 0.5))
        repeated = {pat for pat, count in edge_counts.items() if count >= threshold}
        if not repeated:
            return pages_lines

        cleaned_pages: list[list[str]] = []
        for lines in pages_lines:
            filtered = [
                ln for ln in lines if re.sub(r"\d+", "#", ln.strip()) not in repeated
            ]
            cleaned_pages.append(filtered)
        return cleaned_pages

    def parse(self) -> list[RFPRequirement]:
        reader = PdfReader(self.file_path)
        raw_pages_lines: list[list[str]] = []

        for page in reader.pages:
            text = page.extract_text() or ""
            if len(text.strip()) < 40:
                try:
                    text = page.extract_text(extraction_mode="layout") or text
                except Exception as exc:  # noqa: BLE001
                    logger.debug(f"Extraction layout ignorée : {exc}")
            lines = [
                re.sub(r"[ \t]+", " ", ln).strip()
                for ln in text.splitlines()
                if ln.strip()
            ]
            raw_pages_lines.append(lines)

        clean_pages_lines = self._strip_repeated_headers_footers(raw_pages_lines)

        # Assemblage continu inter-pages avec repérage exact des numéros de page
        full_parts: list[str] = []
        page_spans: list[tuple[int, int, int]] = []
        cursor = 0
        for page_idx, lines in enumerate(clean_pages_lines):
            page_text = "\n".join(lines).strip()
            if not page_text:
                continue
            start_pos = cursor
            full_parts.append(page_text)
            cursor += len(page_text) + 2
            page_spans.append((start_pos, cursor, page_idx + 1))

        full_text = "\n\n".join(full_parts)
        total_len = len(full_text)
        if total_len == 0:
            logger.warning(
                f"Aucun texte extractible dans {self.file_path.name} (PDF scanné ?)."
            )
            return []

        # Taille de découpage adaptative selon la longueur réelle du marché
        if self.custom_chunk_size is not None:
            chunk_size = self.custom_chunk_size
            overlap = self.custom_chunk_overlap or int(chunk_size * 0.18)
        elif total_len < 12_000:
            chunk_size, overlap = 600, 120
        elif total_len < 60_000:
            chunk_size, overlap = 950, 160
        else:
            chunk_size, overlap = 1300, 220

        def _page_at(offset: int) -> int:
            for s, e, p in page_spans:
                if s <= offset < e:
                    return p
            return page_spans[-1][2] if page_spans else 1

        requirements: list[RFPRequirement] = []
        current_section = "Introduction / Préambule"
        start = 0
        idx = 1

        while start < total_len:
            end = min(start + chunk_size, total_len)
            if end < total_len:
                min_cut = start + int(chunk_size * 0.45)
                heading_cut = HEADING_PATTERN.search(full_text, min_cut, end)
                if heading_cut and heading_cut.start() > min_cut:
                    end = heading_cut.start()
                else:
                    split_pos = max(
                        full_text.rfind("\n\n", min_cut, end),
                        full_text.rfind(". ", min_cut, end),
                        full_text.rfind("\n", min_cut, end),
                    )
                    if split_pos != -1:
                        end = split_pos + 1

            chunk_text = full_text[start:end].strip()
            headings_in_chunk = HEADING_PATTERN.findall(chunk_text)
            if headings_in_chunk:
                current_section = headings_in_chunk[0].strip()[:85]

            if len(chunk_text) >= 40:
                p_start = _page_at(start)
                p_end = _page_at(max(start, end - 1))
                page_tag = (
                    f"Page {p_start}"
                    if p_start == p_end
                    else f"Pages {p_start}-{p_end}"
                )
                requirements.append(
                    RFPRequirement(
                        requirement_id=f"RFP-{idx:03d}",
                        section=f"{page_tag} | {current_section}",
                        text=chunk_text,
                        metadata={
                            "source_file": self.file_path.name,
                            "page_start": p_start,
                            "page_end": p_end,
                        },
                    )
                )
                idx += 1

            if end >= total_len:
                break
            start = max(end - overlap, start + 1)

        logger.info(f"Parsing terminé : {len(requirements)} blocs.")
        return requirements
