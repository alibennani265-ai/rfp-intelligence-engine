import pandas as pd
import requests
import streamlit as st
from rfp_engine.synthesis.generator import N7BiddingDossier
from rfp_engine.synthesis.pdf_exporter import generate_n7_pdf

API_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="N7 Consulting — RFP Copilot",
    page_icon="🔴",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS — Theme N7 Consulting Executive
st.markdown(
    """
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 800;
        color: #B40F22;
        margin-bottom: 0rem;
    }
    .sub-header {
        font-size: 1rem;
        color: #4A5568;
        margin-bottom: 1.5rem;
    }
    .card-metric {
        background-color: #F8FAFC;
        border-radius: 10px;
        padding: 1.2rem;
        border-left: 5px solid #B40F22;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
    }
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    "<div class='main-header'>🔴 N7 Consulting — RFP Strategy Copilot</div>",
    unsafe_allow_html=True,
)
st.markdown(
    "<div class='sub-header'>Plateforme d'Avant-Vente, Audit CNJE & Générateur de Dossiers PDF (ENSEEIHT)</div>",
    unsafe_allow_html=True,
)

# Sidebar
with st.sidebar:
    st.image(
        "https://img.icons8.com/isometric-folders/100/pdf-2.png", width=60
    )
    st.header("1. Document RFP")
    uploaded_file = st.file_uploader(
        "Déposer un CCTP / CCAP (PDF)", type=["pdf"]
    )

    if uploaded_file is not None:
        if st.button(
            "🚀 Charger & Parser le Marché", use_container_width=True
        ):
            with st.spinner("Extraction Qdrant & BM25..."):
                files = {
                    "file": (
                        uploaded_file.name,
                        uploaded_file.getvalue(),
                        "application/pdf",
                    )
                }
                res = requests.post(f"{API_URL}/upload", files=files)
                if res.status_code == 200:
                    data = res.json()
                    st.success(
                        f"✅ Indexé ! {data['total_requirements']} exigences extraites."
                    )
                else:
                    st.error(f"Erreur backend: {res.text}")

    st.markdown("---")
    try:
        h = requests.get(f"{API_URL}/health", timeout=2)
        if h.status_code == 200:
            st.success("🟢 API Backend: En ligne")
    except Exception:
        st.error("🔴 API Backend: Hors-ligne (lance uvicorn)")

# Tab Layout
tab1, tab2 = st.tabs(
    [
        "💬 Assistant RAG Commercial",
        "📄 Dossier d'Avant-Vente & Export PDF Executive",
    ]
)

# TAB 1: Chat RAG
with tab1:
    st.subheader("Posez vos questions sur le document d'appel d'offres")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input(
        "Ex: Quels sont les profils ENSEEIHT exigés et les pénalités contractuelles ?"
    ):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Analyse sémantique par Llama 3.1..."):
                res = requests.post(
                    f"{API_URL}/chat", json={"question": prompt, "top_k": 5}
                )
                if res.status_code == 200:
                    data = res.json()
                    ans = data["answer"]
                    st.markdown(ans)

                    with st.expander("🔍 Clauses du document (Qdrant)"):
                        for src in data["sources"]:
                            st.write(
                                f"**[{src['id']}]** ({src['section']}) — *Score: {src.get('score', 0):.2f}*"
                            )
                            st.caption(src["text"])

                    st.session_state.messages.append(
                        {"role": "assistant", "content": ans}
                    )
                else:
                    st.error("Document non indexé. Veuillez charger un PDF.")

# TAB 2: Synthèse Executive & Export PDF
with tab2:
    st.subheader("Rapport d'Avant-Vente & Décision Commerciale N7")

    if st.button("📊 Générer la Synthèse & le Rapport PDF", type="primary"):
        with st.spinner("Génération du dossier stratégique par Llama 3.1..."):
            res = requests.get(f"{API_URL}/dossier-n7")
            if res.status_code == 200:
                dossier_data = res.json()
                dossier = N7BiddingDossier.model_validate(dossier_data)

                # Dashboard Métriques
                col1, col2, col3 = st.columns(3)
                with col1:
                    dec = dossier.decision_gonogo
                    if "GO STRATÉGIQUE" in dec or dec == "GO":
                        st.success(f"### Décision : {dec}")
                    elif "RÉSERVE" in dec:
                        st.warning(f"### Décision : {dec}")
                    else:
                        st.error(f"### Décision : {dec}")

                with col2:
                    st.metric(
                        "Score d'Opportunité",
                        f"{dossier.score_opportunite} / 100",
                    )
                with col3:
                    st.metric(
                        "Volume Estimé", f"{dossier.total_jeh_estime} JEH"
                    )

                st.markdown("---")
                st.markdown(f"## 📌 {dossier.titre_marche}")
                st.caption(f"Acheteur / Client : {dossier.client}")

                # Synthèse & Positionnement
                st.markdown("### 📝 Synthèse Exécutive")
                st.info(dossier.synthese_executive)

                st.markdown("### 🎯 Argumentaire Commercial N7 Consulting")
                st.success(dossier.argumentaire_commercial_n7)

                # CNJE & Staffing
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("### 🏛️ Audit CNJE")
                    df_cnje = pd.DataFrame(
                        [item.model_dump() for item in dossier.conformite_cnje]
                    )
                    st.dataframe(df_cnje, use_container_width=True)

                with c2:
                    st.markdown("### 🎓 Equipe ENSEEIHT")
                    df_stf = pd.DataFrame(
                        [
                            item.model_dump()
                            for item in dossier.staffing_enseeiht
                        ]
                    )
                    st.dataframe(df_stf, use_container_width=True)

                # Ventilation & Risques
                st.markdown("### 💰 Breakdown Financier (JEH)")
                df_fin = pd.DataFrame(
                    [
                        item.model_dump()
                        for item in dossier.ventilation_financiere
                    ]
                )
                st.dataframe(df_fin, use_container_width=True)

                st.markdown("### ⚠️ Matrice des Risques")
                df_r = pd.DataFrame(
                    [item.model_dump() for item in dossier.matrice_risques]
                )
                st.dataframe(df_r, use_container_width=True)

                # Exportation PDF
                pdf_bytes = generate_n7_pdf(dossier)

                st.markdown("---")
                st.download_button(
                    label="📥 Télécharger le Dossier d'Avant-Vente Officiel (.PDF)",
                    data=pdf_bytes,
                    file_name=f"Dossier_Avant_Vente_N7_{dossier.client.replace(' ', '_')}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
            else:
                st.error("Uploadez d'abord un fichier PDF.")