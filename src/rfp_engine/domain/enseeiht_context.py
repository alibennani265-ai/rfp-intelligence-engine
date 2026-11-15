"""Référentiel Métier N7 Consulting & Filières ENSEEIHT."""

ENSEEIHT_DEPARTMENTS = {
    "SN": {
        "nom": "Sciences du Numérique",
        "specialites": [
            "Intelligence Artificielle & Machine Learning",
            "Data Science & Big Data",
            "Développement Full-Stack (Python, FastAPI, React, Node.js)",
            "Cloud, DevOps & Infrastructure",
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
        "profils_typique": "Consultant Simulation Numérique, Ingénieur Thermique & Fluides",
    },
}

CNJE_RULES = """
CADRE LÉGAL ET RÉGLEMENTAIRE CNJE (LIGNES ROUGES) :
1. PLUS-VALUE PÉDAGOGIQUE (PVP) OBLIGATOIRE : L'étude doit prolonger les enseignements sanctionnés par un examen à l'ENSEEIHT (interdiction des tâches sans valeur ajoutée intellectuelle, saisie brute ou licences étudiantes).
2. INTERDICTION DE RÉGIE & PRÊT DE MAIN-D'ŒUVRE : Engagement au forfait sur livrables uniquement. Interdiction de placer un étudiant en régie chez le client, sous subordination hiérarchique ou avec pointage de feuilles de temps. Interdiction de sous-traiter à un tiers externe.
3. OBLIGATION DE MOYENS & GARANTIE LIMITÉE : Obligation de moyens uniquement (jamais de résultat), pas d'astreinte 24/7 ni de maintenance pluriannuelle. Garantie de conformité limitée à 1 mois (rapport) ou 3 mois (livrable technique/logiciel) après PVRF.
4. PROPRIÉTÉ INTELLECTUELLE & JURIDICTION : Cession des droits patrimoniaux uniquement après paiement intégral de toutes les factures. Juridiction compétente : Tribunal judiciaire du siège de la J.E. (jamais Tribunal de commerce).
5. UNITÉ DE FACTURATION (JEH) : Nombre entier indivisible, facturé entre 80 € HT et 450 € HT / JEH (moyenne N7 : 442 € HT), soumis à TVA 20 %.
"""
