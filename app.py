import json
import pandas as pd
import requests
import streamlit as st

API_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="N7 Consulting — Copilot RFP", page_icon="🔴", layout="wide"
)

# Custom Banner N7
st.title("🔴 N7 Consulting — RFP Strategy & Bidding Copilot")
st.caption(
    "Assistant d'Analyse d'Appels d'Offres, Go/No-Go CNJE & Staffing ENSEEIHT (Local Llama 3.1 8B)"
)

# Sidebar
with st.sidebar:
    st.image(
        "https://raw.githubusercontent.com/twitter/twemoji/master/assets/72x72/1f4d8.png",
        width=50,
    )
    st.header("1. Dépôt de l'Appel d'Offres")
    uploaded_file = st.file_uploader("CCTP / CCAP (Format PDF)", type=["pdf"])

    if uploaded_file is not None:
        if st.button(
            "🚀 Analyser le marché pour N7", use_container_width=True
        ):
            with st.spinner("Indexation Qdrant & Analyse des clauses..."):
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
                        f"Marché analysé ! {data['total_requirements']} exigences extraites."
                    )
                else:
                    st.error(f"Erreur d'indexation: {res.text}")

    st.markdown("---")
    try:
        h = requests.get(f"{API_URL}/health", timeout=2)
        if h.status_code == 200:
            st.success("API N7 Engine: En ligne")
    except Exception:
        st.error("API N7 Engine: Hors-ligne (lance uvicorn)")

# Navigation en 3 Onglets
tab1, tab2, tab3 = st.tabs(
    [
        "💬 Chat RAG N7",
        "🛑 Évaluation Go / No-Go & Staffing",
        "📄 Dossier d'Avant-Vente Exportable",
    ]
)

# TAB 1: Chat RAG Métier
with tab1:
    st.subheader("Posez vos questions à l'assistant commercial N7")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input(
        "Ex: Quel profil ENSEEIHT faut-il prévoir ? Y a-t-il une clause de pénalité bloquante ?"
    ):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Analyse du Cahier des Charges..."):
                res = requests.post(
                    f"{API_URL}/chat", json={"question": prompt, "top_k": 5}
                )
                if res.status_code == 200:
                    data = res.json()
                    ans = data["answer"]
                    st.markdown(ans)

                    with st.expander("🔍 Extraits contractuels Qdrant"):
                        for src in data["sources"]:
                            st.write(
                                f"**[{src['id']}]** ({src['section']}) — *Score: {src.get('score', 0):.2f}*"
                            )
                            st.caption(src["text"])

                    st.session_state.messages.append(
                        {"role": "assistant", "content": ans}
                    )
                else:
                    st.error("Index vide ou backend indisponible.")

# TAB 2: Go/No-Go & Staffing ENSEEIHT
with tab2:
    st.subheader("Analyse de Faisabilité & Alignement Cadre CNJE")

    if st.button(
        "⚡ Lancer l'Évaluation Go / No-Go", type="primary"
    ):
        with st.spinner("Évaluation des clauses contractuelles et RH..."):
            res = requests.get(f"{API_URL}/gonogo")
            if res.status_code == 200:
                gonogo = res.json()

                # Visualisation Décision
                col1, col2, col3 = st.columns(3)
                with col1:
                    dec = gonogo["decision"]
                    if dec == "GO":
                        st.success(f"### Décision : {dec}")
                    elif dec == "GO SOUS RÉSERVE":
                        st.warning(f"### Décision : {dec}")
                    else:
                        st.error(f"### Décision : {dec}")

                with col2:
                    st.metric(
                        "Score de Faisabilité",
                        f"{gonogo['score_faisabilite']} / 100",
                    )
                with col3:
                    st.metric(
                        "Charge Estimée", gonogo.get("estimation_jeh", "N/A")
                    )

                st.markdown("---")
                st.markdown("### 🏛️ Validation Cadre CNJE & Risques")
                st.info(f"**Conformité CNJE :** {gonogo['conformite_cnje']}")

                c_left, c_right = st.columns(2)
                with c_left:
                    st.markdown("**🛑 Points Rédhibitoires / Bloquants :**")
                    for p in gonogo["points_bloquants"]:
                        st.write(f"• {p}")
                with c_right:
                    st.markdown("**⚠️ Risques Contractuels :**")
                    for r in gonogo["risques_majeurs"]:
                        st.write(f"• {r}")

                st.markdown("---")
                st.markdown(
                    "### 🎓 Staffing Recommandé (Filières ENSEEIHT)"
                )
                df_staffing = pd.DataFrame(gonogo["staffing_recommande"])
                st.dataframe(df_staffing, use_container_width=True)
            else:
                st.error("Uploadez d'abord un fichier PDF d'appel d'offres.")

# TAB 3: Dossier Stratégique de Réponse Exportable
with tab3:
    st.subheader("Générateur de Dossier Stratégique de Réponse N7")

    if st.button("📄 Générer le Dossier Complet d'Avant-Vente"):
        with st.spinner("Rédaction du dossier stratégique par Llama 3.1..."):
            res = requests.get(f"{API_URL}/dossier-n7")
            if res.status_code == 200:
                dossier = res.json()

                st.markdown(f"## {dossier['titre_projet']}")
                st.markdown("---")

                st.markdown("### 📌 Synthèse Éxécutive & Opportunité")
                st.write(dossier["synthese_executive"])

                st.markdown("### 🎯 Argumentaire Stratégique N7 Consulting")
                st.success(dossier["argumentaire_n7"])

                st.markdown(
                    "### 🛠️ Proposition de Découpage du Projet (Lots)"
                )
                df_lots = pd.DataFrame(dossier["decoupage_lots"])
                st.dataframe(df_lots, use_container_width=True)

                st.markdown(
                    "### 💡 Recommandations de l'Équipe Avant-Vente"
                )
                for rec in dossier["recommandations_avant_vente"]:
                    st.write(f"✔ {rec}")

                # Génération du contenu Markdown téléchargeable
                md_content = f"""# {dossier['titre_projet']}
*Document préparatoire d'Avant-Vente — N7 Consulting (ENSEEIHT)*

---

## 1. Synthèse Exécutive
{dossier['synthese_executive']}

## 2. Argumentaire Commercial N7 Consulting
{dossier['argumentaire_n7']}

## 3. Découpage en Lots & Profils Recommandés
"""
                for lot in dossier["decoupage_lots"]:
                    md_content += f"- **{lot.get('lot')}** : {lot.get('description')} *(Profils: {lot.get('profils')})*\n"

                md_content += "\n## 4. Recommandations Négociation & Cadrage\n"
                for rec in dossier["recommandations_avant_vente"]:
                    md_content += f"- {rec}\n"

                st.markdown("---")
                st.download_button(
                    label="📥 Télécharger le Dossier d'Avant-Vente (.md)",
                    data=md_content,
                    file_name="Dossier_Avant_Vente_N7_Consulting.md",
                    mime="text/markdown",
                )
            else:
                st.error("Impossible de générer le dossier.")