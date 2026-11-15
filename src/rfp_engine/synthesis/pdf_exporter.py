from fpdf import FPDF

from rfp_engine.synthesis.generator import N7BiddingDossier


class N7PDFReport(FPDF):
    def header(self) -> None:
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(180, 15, 30)
        self.set_x(self.l_margin)
        self.cell(
            self.epw,
            8,
            "N7 CONSULTING | DOSSIER STRATEGIQUE D'AVANT-VENTE",
            new_x="LMARGIN",
            new_y="NEXT",
            align="R",
        )
        self.set_draw_color(180, 15, 30)
        self.set_line_width(0.4)
        self.line(self.l_margin, 15, self.w - self.r_margin, 15)
        self.ln(6)

    def footer(self) -> None:
        self.set_y(-15)
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(
            self.epw,
            10,
            f"Confidentiel - N7 Consulting (ENSEEIHT) | Page {self.page_no()}/{{nb}}",
            align="C",
        )

    def write_block(
        self,
        text: str,
        h: float = 5.5,
        bold: bool = False,
        color: tuple[int, int, int] = (40, 40, 40),
    ) -> None:
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "B" if bold else "", 10)
        self.set_text_color(*color)
        self.multi_cell(self.epw, h, _sanitize(text), new_x="LMARGIN", new_y="NEXT")

    def write_section_title(self, title: str) -> None:
        self.ln(3)
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(180, 15, 30)
        self.multi_cell(self.epw, 7, _sanitize(title), new_x="LMARGIN", new_y="NEXT")
        self.ln(1)


def _sanitize(text: str) -> str:
    replacements = {
        "’": "'",
        "“": '"',
        "”": '"',
        "–": "-",
        "—": "-",
        "…": "...",
        "•": "-",
        "€": "EUR",
        "é": "e",
        "è": "e",
        "ê": "e",
        "ë": "e",
        "à": "a",
        "â": "a",
        "ù": "u",
        "û": "u",
        "î": "i",
        "ï": "i",
        "ô": "o",
        "ç": "c",
        "É": "E",
        "È": "E",
        "À": "A",
        "Ç": "C",
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text.encode("latin-1", "replace").decode("latin-1")


def generate_n7_pdf(dossier: N7BiddingDossier) -> bytes:
    pdf = N7PDFReport()
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "B", 15)
    pdf.set_text_color(20, 30, 55)
    pdf.multi_cell(
        pdf.epw,
        7.5,
        _sanitize(f"Dossier d'Avant-Vente : {dossier.titre_marche}"),
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.ln(2)

    budget_estime = dossier.total_jeh_estime * 442
    pdf.write_block(
        f"Decision : {dossier.decision_gonogo}  |  Score : {dossier.score_opportunite}/100  |  Charge : {dossier.total_jeh_estime} JEH (~{budget_estime} EUR HT)",
        bold=True,
        color=(180, 15, 30),
    )
    pdf.write_block(
        f"Client / Acheteur : {dossier.client}", bold=True, color=(80, 80, 80)
    )

    pdf.write_section_title("1. Synthese Executive")
    pdf.write_block(dossier.synthese_executive)

    pdf.write_section_title("2. Positionnement & Argumentaire N7 Consulting")
    pdf.write_block(dossier.argumentaire_commercial_n7)

    pdf.write_section_title("3. Audit de Conformite CNJE")
    for item in dossier.conformite_cnje:
        pdf.write_block(f"- [{item.statut}] {item.critere}", bold=True)
        pdf.write_block(f"  {item.commentaire}")

    pdf.write_section_title("4. Staffing & Equipe Projet ENSEEIHT")
    for stf in dossier.staffing_enseeiht:
        comps = ", ".join(stf.competences_cles)
        pdf.write_block(
            f"- Filiere {stf.filiere} ({stf.niveau}) - {stf.nombre_etudiants} etudiant(s)",
            bold=True,
        )
        pdf.write_block(f"  Competences : {comps} | Role : {stf.role_dans_projet}")

    pdf.write_section_title(
        f"5. Ventilation Financiere ({dossier.total_jeh_estime} JEH)"
    )
    for ph in dossier.ventilation_financiere:
        pdf.write_block(
            f"- {ph.phase} ({ph.jeh_estimes} JEH - {ph.profil_associe})", bold=True
        )
        pdf.write_block(f"  {ph.description}")

    pdf.write_section_title("6. Matrice des Risques & Clauses a Renegocier")
    for r in dossier.matrice_risques:
        pdf.write_block(f"- [{r.impact}] {r.domaine} : {r.description}", bold=True)
        pdf.write_block(f"  Mitigation : {r.plan_mitigation}")

    if dossier.clauses_a_renegocier:
        pdf.ln(2)
        pdf.write_block(
            "Clauses prioritaires a renegocier avant signature :",
            bold=True,
            color=(180, 15, 30),
        )
        for cl in dossier.clauses_a_renegocier:
            pdf.write_block(f"- {cl}")

    if dossier.recommandations_commerciales:
        pdf.write_section_title("7. Recommandations Commerciales Avant-Vente")
        for rec in dossier.recommandations_commerciales:
            pdf.write_block(f"- {rec}")

    return bytes(pdf.output())
