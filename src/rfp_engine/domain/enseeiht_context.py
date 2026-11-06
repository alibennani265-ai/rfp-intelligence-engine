"""Référentiel Métier N7 Consulting & Filières ENSEEIHT."""

ENSEEIHT_DEPARTMENTS = {
    "SN": {
        "nom": "Sciences du Numérique",
        "specialites": [
            "Intelligence Artificielle & Machine Learning",
            "Data Science & Big Data",
            "Développement Full-Stack (Python, FastAPI, React, Node.js)",
            "Cloud, DevOps & Substrate Infrastructure",
            "Cybersécurité & Réseaux",
            "Calcul Bas Niveau & Calcul Intensif (C/C++, OCaml, Ada, Système)",
        ],
        "profils_typique": "Consultant Data/IA, Ingénieur Logiciel Full-Stack, Architecte Système",
    },
    "3EA": {
        "nom": "Électronique, Énergie Électrique, Automatique",
        "specialites": [
            "Systèmes Embarqués & Microélectronique",
            "Automatique, Signal & Traitement d'Images",
            "Électronique de Puissance & Réseaux Électriques",
            "Automatisme & Métrologie",
        ],
        "profils_typique": "Ingénieur Embarqué, Consultant Automatique & Signal",
    },
    "MFEE": {
        "nom": "Mécanique des Fluides, Énergie & Environnement",
        "specialites": [
            "Simulation Numérique CFD (Computational Fluid Dynamics)",
            "Modélisation Thermique & Énergétique",
            "Hydraulique & Mécanique des structures",
            "Ingénierie Environnementale & Transition Énergétique",
        ],
        "profils_typique": "Consultant Simulation Numerique, Ingénieur Thermique & Fluides",
    },
}

CNJE_RULES = """
CADRE RÉGLEMENTAIRE CONFE'DE'RATION NATIONALE DES JUNIOR-ENTREPRISES (CNJE) :
1. VALEUR PÉDAGOGIQUE OBLIGATOIRE : Toute étude confiée à N7 Consulting doit comporter une part d'analyse, de conception ou de développement d'ingénierie correspondant directement au cursus de l'ENSEEIHT.
2. INTERDICTION DE RÉGIE PURE : N7 Consulting vend des prestations au FORFAIT (engagements sur livrables), jamais de mise à disposition d'étudiants en régie horaire dans les locaux clients.
3. PAS DE MAINTENANCE 24/7 POST-DIPLÔME : Pas d'astreinte ni de contrat de support pluriannuel post-livraison.
4. UNITÉ DE FACTURATION : Jours-Étude Homme (JEH), tarif compris entre 80€ et 450€ HT / JEH selon la technicité.
"""