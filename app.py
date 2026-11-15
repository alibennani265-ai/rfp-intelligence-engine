import re

import pandas as pd
import requests
import streamlit as st

from rfp_engine.synthesis.generator import N7BiddingDossier
from rfp_engine.synthesis.pdf_exporter import generate_n7_pdf

API_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="N7 Consulting — RFP Copilot", page_icon="🔴", layout="wide"
)
st.markdown(
    "<h1 style='color:#B40F22;margin-bottom:0;'>🔴 N7 Consulting — RFP Strategy Copilot</h1>",
    unsafe_allow_html=True,
)
st.caption(
    "Auditeur Légal CNJE, RAG Hybride & Générateur de Dossiers d'Avant-Vente (ENSEEIHT)"
)

with st.sidebar:
    st.header("1. Appel d'Offres Client")
    uploaded_file = st.file_uploader("Déposer un CCTP / CCAP (PDF)", type=["pdf"])
    if uploaded_file is not None and st.button(
        "🚀 Charger & Parser le Marché", use_container_width=True
    ):
        with st.spinner("Découpage sémantique & indexation Qdrant + BM25..."):
            files = {
                "file": (
                    uploaded_file.name,
                    uploaded_file.getvalue(),
                    "application/pdf",
                )
            }
            res = requests.post(f"{API_URL}/upload", files=files, timeout=300)
            if res.status_code == 200:
                st.session_state.pop("dossier_cache", None)
                st.success(
                    f"✅ Marché indexé ({res.json()['total_requirements']} blocs contextuels)."
                )
            else:
                st.error(res.text)

    st.markdown("---")
    st.header("2. Cadre Légal CNJE & N7")
    if st.button("🔄 Synchroniser Cadre Légal CNJE & Études", use_container_width=True):
        with st.spinner("Indexation du cadre légal CNJE..."):
            res = requests.post(f"{API_URL}/ingest-past-studies", timeout=300)
            if res.status_code == 200:
                st.success(f"✅ {res.json()['message']}")

    st.markdown("---")
    try:
        h = requests.get(f"{API_URL}/health", timeout=2).json()
        st.success(
            f"🟢 API En ligne | CCTP: {h.get('rfp_chunks', 0)} blocs | CNJE/N7: {h.get('knowledge_chunks', 0)} blocs"
        )
    except requests.RequestException:
        st.error("🔴 API Hors-ligne")

tab1, tab2 = st.tabs(
    [
        "💬 Assistant RAG Commercial & Légal",
        "📄 Audit CNJE, Dossier d'Avant-Vente & PDF",
    ]
)

with tab1:
    st.subheader("Interroger le CCTP, les compétences N7 et la conformité CNJE")
    if "messages" not in st.session_state:
        st.session_state.messages = []
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input(
        "Ex: Est-ce que N7 Consulting peut répondre à cet appel d'offres ? Quelles clauses bloquent ?"
    ):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with (
            st.chat_message("assistant"),
            st.spinner("Analyse croisée CCTP + Expérience N7 + CLR CNJE..."),
        ):
            res = requests.post(
                f"{API_URL}/chat",
                json={"question": prompt, "top_k": 6},
                timeout=180,
            )
            if res.status_code == 200:
                data = res.json()
                st.markdown(data["answer"])
                with st.expander("🔍 Extraits mobilisés (CCTP + N7 + CLR CNJE)"):
                    for src in data["sources"]:
                        st.write(
                            f"**[{src['id']}]** {src['section']} — *Score: {src.get('score', 0):.2f}*"
                        )
                        st.caption(src["text"])
                st.session_state.messages.append(
                    {"role": "assistant", "content": data["answer"]}
                )

with tab2:
    st.subheader("Rapport d'Avant-Vente & Audit de Conformité CNJE")
    if st.button("📊 Lancer l'Audit Complet & Générer le PDF", type="primary"):
        with st.spinner(
            "Analyse approfondie des clauses du CCTP et génération du dossier..."
        ):
            res = requests.get(f"{API_URL}/dossier-n7", timeout=240)
            if res.status_code == 200:
                st.session_state["dossier_cache"] = res.json()
            else:
                detail = (
                    res.json().get("detail", res.text)
                    if res.headers.get("content-type", "").startswith(
                        "application/json"
                    )
                    else f"Erreur serveur ({res.status_code}) : {res.text}"
                )
                st.error(detail)

    if "dossier_cache" in st.session_state:
        dossier = N7BiddingDossier.model_validate(st.session_state["dossier_cache"])
        col1, col2, col3 = st.columns(3)
        with col1:
            dec = dossier.decision_gonogo.upper()
            if "NO-GO" in dec:
                st.error(f"### {dossier.decision_gonogo}")
            elif "RÉSERVE" in dec or "RESERVE" in dec:
                st.warning(f"### {dossier.decision_gonogo}")
            else:
                st.success(f"### {dossier.decision_gonogo}")
        col2.metric("Score d'Opportunité", f"{dossier.score_opportunite} / 100")
        col3.metric(
            "Volume Estimé",
            f"{dossier.total_jeh_estime} JEH (~{dossier.total_jeh_estime * 442:,} € HT)".replace(
                ",", " "
            ),
        )

        st.markdown(f"## 📌 {dossier.titre_marche}")
        st.caption(f"Client : {dossier.client}")

        if dossier.raisonnement_auditeur:
            with st.expander(
                "🧠 Raisonnement Technique & Juridique de l'Auditeur", expanded=True
            ):
                st.write(dossier.raisonnement_auditeur)

        st.info(dossier.synthese_executive)
        st.success(dossier.argumentaire_commercial_n7)

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### 🏛️ Audit de Conformité CNJE")
            st.dataframe(
                pd.DataFrame([i.model_dump() for i in dossier.conformite_cnje]),
                use_container_width=True,
            )
        with c2:
            st.markdown("### 🎓 Staffing ENSEEIHT")
            st.dataframe(
                pd.DataFrame([i.model_dump() for i in dossier.staffing_enseeiht]),
                use_container_width=True,
            )

        st.markdown("### 💰 Ventilation Financière (JEH)")
        st.dataframe(
            pd.DataFrame([i.model_dump() for i in dossier.ventilation_financiere]),
            use_container_width=True,
        )

        st.markdown("### ⚠️ Matrice des Risques")
        st.dataframe(
            pd.DataFrame([i.model_dump() for i in dossier.matrice_risques]),
            use_container_width=True,
        )

        if dossier.clauses_a_renegocier:
            st.markdown("### 🛑 Clauses Bloquantes / À Renégocier")
            for cl in dossier.clauses_a_renegocier:
                st.warning(f"• {cl}")

        pdf_bytes = generate_n7_pdf(dossier)
        safe_client = re.sub(r"[^a-zA-Z0-9_-]", "_", dossier.client)[:40] or "Client"
        st.download_button(
            label="📥 Télécharger le Dossier d'Avant-Vente Officiel (.PDF)",
            data=pdf_bytes,
            file_name=f"Dossier_Avant_Vente_N7_{safe_client}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
