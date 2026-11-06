from fpdf import FPDF
from rfp_engine.synthesis.generator import N7BiddingDossier


class N7PDFReport(FPDF):

    def header(self):
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(180, 15, 30)  # Rouge N7
        self.cell(
            0,
            8,
            "N7 CONSULTING | DOSSIER STRATEGIQUE D'AVANT-VENTE",
            new_x="LMARGIN",
            new_y="NEXT",
            align="R",
        )
        self.set_draw_color(180, 15, 30)
        self.set_linewidth(0.4)
        self.line(10, 15, 200, 15)
        self.ln(6)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(
            0,
            10,
            f"Confidentiel - N7 Consulting (Junior-Entreprise de l'ENSEEIHT) | Page {self.page_no()}/{{nb}}",
            align="C",
        )


def _sanitize(text: str) -> str:
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
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text.encode("latin-1", "replace").decode("latin-1")


def generate_n7_pdf(dossier: N7BiddingDossier) -> bytes:
    pdf = N7PDFReport()
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Titre du Rapport
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(20, 30, 55)
    pdf.multi_cell(
        0, 7, _sanitize(f"Dossier d'Avant-Vente : {dossier.titre_marche}")
    )
    pdf.ln(2)

    # Cartouche Métriques
    pdf.set_fill_color(245, 247, 250)
    pdf.set_draw_color(200, 200, 200)
    pdf.rect(10, pdf.get_y(), 190, 16, style="FD")

    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(180, 15, 30)
    pdf.cell(
        60,
        16,
        _sanitize(f"  Decision : {dossier.decision_gonogo}"),
        new_x="RIGHT",
    )
    pdf.set_text_color(40, 40, 40)
    pdf.cell(
        65,
        16,
        _sanitize(f"Score Opportunite : {dossier.score_opportunite}/100"),
        new_x="RIGHT",
    )
    pdf.cell(
        65,
        16,
        _sanitize(f"Volume : {dossier.total_jeh_estime} JEH"),
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.ln(6)

    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 5, _sanitize(f"Client / Acheteur : {dossier.client}"))
    pdf.ln(6)

    # Section 1 : Synthèse Exécutive
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(180, 15, 30)
    pdf.cell(
        0, 7, _sanitize("1. Synthese Executive"), new_x="LMARGIN", new_y="NEXT"
    )
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(40, 40, 40)
    pdf.multi_cell(0, 5, _sanitize(dossier.synthese_executive))
    pdf.ln(4)

    # Section 2 : Argumentaire Commercial N7
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(180, 15, 30)
    pdf.cell(
        0,
        7,
        _sanitize("2. Positionnement & Argumentaire N7 Consulting"),
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 5, _sanitize(dossier.argumentaire_commercial_n7))
    pdf.ln(4)

    # Section 3 : Audit CNJE
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(180, 15, 30)
    pdf.cell(
        0,
        7,
        _sanitize("3. Audit de Conformite CNJE"),
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.set_font("Helvetica", "", 10)
    for item in dossier.conformite_cnje:
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(
            0,
            5,
            _sanitize(f"• [{item.statut}] {item.critere}"),
            new_x="LMARGIN",
            new_y="NEXT",
        )
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 5, _sanitize(f"   {item.commentaire}"))
        pdf.ln(1)
    pdf.ln(3)

    # Section 4 : Staffing ENSEEIHT
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(180, 15, 30)
    pdf.cell(
        0,
        7,
        _sanitize("4. Staffing & Equipe Projet ENSEEIHT"),
        new_x="LMARGIN",
        new_y="NEXT",
    )
    for stf in dossier.staffing_enseeiht:
        comps = ", ".join(stf.competences_cles)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(
            0,
            5,
            _sanitize(
                f"• Filiere {stf.filiere} ({stf.niveau}) - {stf.nombre_etudiants} etudiant(s)"
            ),
            new_x="LMARGIN",
            new_y="NEXT",
        )
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(
            0,
            5,
            _sanitize(
                f"   Competences : {comps}\n   Role : {stf.role_dans_projet}"
            ),
        )
        pdf.ln(1)
    pdf.ln(3)

    # Section 5 : Breakdown Financier
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(180, 15, 30)
    pdf.cell(
        0,
        7,
        _sanitize(
            f"5. Ventilation Financiere & Planning ({dossier.total_jeh_estime} JEH)"
        ),
        new_x="LMARGIN",
        new_y="NEXT",
    )
    for ph in dossier.ventilation_financiere:
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(
            0,
            5,
            _sanitize(f"• {ph.phase} ({ph.jeh_estimes} JEH - {ph.profil_associe})"),
            new_x="LMARGIN",
            new_y="NEXT",
        )
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 5, _sanitize(f"   Description : {ph.description}"))
        pdf.ln(1)
    pdf.ln(3)

    # Section 6 : Risques & Négociation
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(180, 15, 30)
    pdf.cell(
        0,
        7,
        _sanitize("6. Matrice des Risques & Clauses a Renegocier"),
        new_x="LMARGIN",
        new_y="NEXT",
    )
    for r in dossier.matrice_risques:
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(
            0,
            5,
            _sanitize(f"• Risque [{r.domaine} - Impact {r.impact}]"),
            new_x="LMARGIN",
            new_y="NEXT",
        )
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(
            0,
            5,
            _sanitize(
                f"   Analyse : {r.description}\n   Plan de mitigation : {r.plan_mitigation}"
            ),
        )
        pdf.ln(1)

    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(
        0,
        5,
        _sanitize("Clauses prioritaires a renegocier :"),
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.set_font("Helvetica", "", 10)
    for cl in dossier.clauses_a_renegocier:
        pdf.multi_cell(0, 5, _sanitize(f"  - [A RENEGOCIER] {cl}"))
    pdf.ln(3)

    # Section 7 : Recommandations
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(180, 15, 30)
    pdf.cell(
        0,
        7,
        _sanitize("7. Recommandations Commerciales Avant-Vente"),
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.set_font("Helvetica", "", 10)
    for rec in dossier.recommandations_commerciales:
        pdf.multi_cell(0, 5, _sanitize(f"  ✔ {rec}"))

    return bytes(pdf.output())