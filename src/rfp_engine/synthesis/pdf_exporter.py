from fpdf import FPDF
from rfp_engine.synthesis.generator import N7BiddingDossier


class N7PDFReport(FPDF):

    def header(self):
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(190, 15, 30)  # Rouge N7
        self.cell(
            0,
            10,
            "N7 CONSULTING | DOSSIER STRATEGIQUE D'AVANT-VENTE",
            new_x="LMARGIN",
            new_y="NEXT",
            align="R",
        )
        self.set_draw_color(220, 220, 220)
        self.line(10, 17, 200, 17)
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(
            0,
            10,
            f"Document Confidentiel - N7 Consulting (ENSEEIHT) | Page {self.page_no()}/{{nb}}",
            align="C",
        )


def _sanitize(text: str) -> str:
    """Encode proprement les caractères spéciaux pour le rendu FPDF Standard."""
    replacements = {
        "’": "'",
        "“": '"',
        "”": '"',
        "–": "-",
        "—": "-",
        "…": "...",
        "•": "-",
        "✔": "[OK]",
        "🛑": "[NO-GO]",
        "⚠️": "[RISQUE]",
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text.encode("latin-1", "replace").decode("latin-1")


def generate_n7_pdf(dossier: N7BiddingDossier) -> bytes:
    pdf = N7PDFReport()
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Titre du Marché & En-tête
    pdf.set_font("Helvetica", "B", 15)
    pdf.set_text_color(20, 30, 55)
    pdf.multi_cell(
        0, 7, _sanitize(f"Dossier de Réponse : {dossier.titre_marche}")
    )
    pdf.ln(2)

    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(
        0,
        6,
        _sanitize(
            f"Client : {dossier.client} | Decision : {dossier.decision_gonogo} | Score Opportunite : {dossier.score_opportunite}/100"
        ),
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.ln(4)

    # 1. Synthèse Exécutive
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(190, 15, 30)
    pdf.cell(
        0, 7, _sanitize("1. Synthese Executive"), new_x="LMARGIN", new_y="NEXT"
    )
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(40, 40, 40)
    pdf.multi_cell(0, 5, _sanitize(dossier.synthese_executive))
    pdf.ln(3)

    # 2. Argumentaire Commercial N7
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(190, 15, 30)
    pdf.cell(
        0,
        7,
        _sanitize("2. Argumentaire Commercial N7 Consulting"),
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(40, 40, 40)
    pdf.multi_cell(0, 5, _sanitize(dossier.argumentaire_commercial_n7))
    pdf.ln(3)

    # 3. Conformité CNJE
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(190, 15, 30)
    pdf.cell(
        0,
        7,
        _sanitize("3. Audit de Conformite CNJE"),
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.set_font("Helvetica", "", 10)
    for cnje in dossier.conformite_cnje:
        pdf.multi_cell(
            0,
            5,
            _sanitize(
                f"- [{cnje.statut}] {cnje.critere} : {cnje.commentaire}"
            ),
        )
    pdf.ln(3)

    # 4. Staffing ENSEEIHT
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(190, 15, 30)
    pdf.cell(
        0,
        7,
        _sanitize("4. Staffing & Equipe Projet ENSEEIHT"),
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.set_font("Helvetica", "", 10)
    for stf in dossier.staffing_enseeiht:
        competences = ", ".join(stf.competences_cles)
        pdf.multi_cell(
            0,
            5,
            _sanitize(
                f"- Filiere {stf.filiere} ({stf.niveau}) : {stf.nombre_etudiants} etudiant(s) [{competences}] - {stf.role_dans_projet}"
            ),
        )
    pdf.ln(3)

    # 5. Ventilation Financière
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(190, 15, 30)
    pdf.cell(
        0,
        7,
        _sanitize(
            f"5. Ventilation Financiere ({dossier.total_jeh_estime} JEH au total)"
        ),
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.set_font("Helvetica", "", 10)
    for ph in dossier.ventilation_financiere:
        pdf.multi_cell(
            0,
            5,
            _sanitize(
                f"- {ph.phase} ({ph.jeh_estimes} JEH - {ph.profil_associe}) : {ph.description}"
            ),
        )
    pdf.ln(3)

    # 6. Matrice des Risques & Négociation
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(190, 15, 30)
    pdf.cell(
        0,
        7,
        _sanitize("6. Matrice des Risques & Clauses a Renegocier"),
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.set_font("Helvetica", "", 10)
    for r in dossier.matrice_risques:
        pdf.multi_cell(
            0,
            5,
            _sanitize(
                f"- Risque [{r.domaine} / Impact {r.impact}] : {r.description} -> Mitigation : {r.plan_mitigation}"
            ),
        )
    pdf.ln(2)
    for cl in dossier.clauses_a_renegocier:
        pdf.multi_cell(0, 5, _sanitize(f"- [A RENEGOCIER] {cl}"))
    pdf.ln(3)

    # 7. Recommandations Commerciales
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(190, 15, 30)
    pdf.cell(
        0,
        7,
        _sanitize("7. Recommandations Commerciales Avant-Vente"),
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.set_font("Helvetica", "", 10)
    for rec in dossier.recommandations_commerciales:
        pdf.multi_cell(0, 5, _sanitize(f"- {rec}"))

    return bytes(pdf.output())