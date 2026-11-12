import os
from fpdf import FPDF


def create_sample_cctp(output_path: str = "data/test_cctp_airbus.pdf") -> None:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)
    content = (
        "APPEL D OFFRES - AIRBUS DEFENCE & SPACE TOULOUSE\n"
        "Projet : Plateforme de Vision par Ordinateur et Telemetrie Embarquee.\n\n"
        "1. Besoin Technique :\n"
        "Conception d un pipeline de detection d anomalies par Deep Learning (PyTorch, Computer Vision) "
        "couple a une carte d acquisition temps reel (FPGA / Traitement du signal).\n\n"
        "2. Contraintes Contractuelles :\n"
        "- Charge estimee : 25 Jours-Etude Homme (JEH).\n"
        "- Clause 4.2 : Astreinte telephonique et maintenance corrective 24/7 pendant 3 ans apres livraison.\n"
        "- Clause 4.3 : Mise a disposition de deux etudiants en regie horaire dans nos locaux a Blagnac.\n"
    )
    pdf.multi_cell(0, 7, content)
    pdf.output(output_path)
    print(f"CCTP de test généré avec succès : {output_path}")


if __name__ == "__main__":
    create_sample_cctp()
