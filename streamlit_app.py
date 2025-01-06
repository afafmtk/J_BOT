import streamlit as st
import logging
from time import time
from load_and_prepare import clear_database, load_documents, split_documents, add_to_chroma
from retrieve import query_rag

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Initialisation des états nécessaires
if "query_history" not in st.session_state:
    st.session_state["query_history"] = []  # Historique des requêtes
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []  # Historique des conversations (requêtes et réponses)

def process_request(query_text):
    """Traitement d'une requête utilisateur."""
    start_time = time()

    # Réinitialisation et préparation des données en arrière-plan
    clear_database()
    documents = load_documents()

    # Gestion de la progression
    progress_bar = st.progress(0)
    total_steps = len(documents) + len(documents) * 10  # Approximativement
    current_step = 0

    chunks = []
    for doc in documents:
        current_step += 1
        progress_percentage = int((current_step / total_steps) * 100)
        progress_bar.progress(progress_percentage)
        chunks.extend(split_documents([doc]))

    for chunk in chunks:
        current_step += 1
        progress_percentage = int((current_step / total_steps) * 100)
        progress_bar.progress(progress_percentage)
        add_to_chroma([chunk])

    # Recherche dans la base de données
    result = query_rag(query_text)
    progress_bar.progress(100)  # Finalisation de la progression

    end_time = time()
    elapsed_time = end_time - start_time

    return result, elapsed_time

def main():
    # Titre principal avec style
    st.markdown("<h1 style='color: purple;'>Juridique_Chat</h1>", unsafe_allow_html=True)

    # Barre latérale avec logo et historique
    st.sidebar.image("logo_dxc.jpg", use_container_width=True)
    st.sidebar.markdown("<h2 style='color: purple;'>Query History</h2>", unsafe_allow_html=True)

    if st.session_state["query_history"]:
        for i, query in enumerate(st.session_state["query_history"], 1):
            st.sidebar.write(f"{i}. {query}")
    else:
        st.sidebar.info("No queries submitted yet.")

    # Champ de texte pour la requête utilisateur
    query_text = st.text_input(
        "Enter your query:",
        key="query_input",
        placeholder="Type your request here...",
    )
    # Bouton sous le champ de texte
    run_button = st.button("Run")

    # Gestion de l'événement du bouton
    if run_button and query_text.strip():
        # Ajouter la requête à l'historique
        st.session_state["query_history"].append(query_text)

        with st.spinner("Processing your request..."):
            # Exécution du traitement et récupération des résultats
            result, elapsed_time = process_request(query_text)

        # Ajouter la conversation au chat_history
        st.session_state["chat_history"].append((query_text, result))

        # Rafraîchir la page pour réinitialiser le champ de saisie
        st.rerun()

    # Affichage style conversation
    st.markdown("<h2 style='color: purple;'>Conversation</h2>", unsafe_allow_html=True)
    for query, response in st.session_state["chat_history"]:
        # Affichage en style conversation
        st.markdown(f"""
        <div style="background-color: #e9ecef; padding: 10px; border-radius: 10px; margin: 5px 0; text-align: left;">
            <strong>User:</strong> {query}
        </div>
        <div style="background-color: #f8f9fa; padding: 10px; border-radius: 10px; margin: 5px 0 10px; text-align: right;">
            <strong>Result:</strong> {response}
        </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
