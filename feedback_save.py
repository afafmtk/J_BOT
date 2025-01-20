import streamlit as st
from streamlit_feedback import streamlit_feedback
import csv
import datetime
import uuid
from pathlib import Path
from load_and_prepare import split_documents, add_to_chroma
from load_and_prepare2 import extract_text_simple, process_pdf_file
from retrieve import query_rag
from langchain.schema import Document
import logging
import os
from time import time


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Initialisation 
def initialize_session_state():
    if 'session_id' not in st.session_state:
        st.session_state.session_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    if 'messages' not in st.session_state:
        st.session_state.messages = []

    if 'feedback_history' not in st.session_state:
        st.session_state.feedback_history = []

    if 'fbk' not in st.session_state:
        st.session_state.fbk = str(uuid.uuid4())

    if 'file_processed' not in st.session_state:
        st.session_state.file_processed = False


def save_uploaded_file(uploaded_file):
    data_dir = os.path.join(os.getcwd(), 'data')
    os.makedirs(data_dir, exist_ok=True)

    file_path = os.path.join(data_dir, uploaded_file.name)
    if not os.path.exists(file_path):
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
    return file_path

# Sauvegarde du feedback in CSV file
def save_feedback():
    feedback_dir = Path('feedbacks')
    feedback_dir.mkdir(exist_ok=True)
    filepath = feedback_dir / f'{st.session_state.session_id}.csv'

    file_exists = filepath.exists()

    with open(filepath, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(["Question", "Answer", "Score", "Valeur", "Commentaire"])

        for feedback in st.session_state.feedback_history:
            writer.writerow([
                feedback['Question'],
                feedback['Réponse'],
                feedback['feedback']['score'],
                feedback['feedback']['valeur'],
                feedback['feedback']['text']
            ])

# Gestion des feedbacks
def fbcb(response):
    if not st.session_state.feedback_history:
        st.warning("Aucune interaction disponible pour ajouter un feedback.")
        return

    last_entry = st.session_state.feedback_history[-1]
    #Structuration du feedback
    feedback = {
        "score": response.get("score"),
        "valeur": "Positif" if response.get("score") == "👍" else ("Négatif" if response.get("score") == "👎" else "NaN"),
        "text": response.get("text", "").strip() if response.get("text") else "NAN"
    }

    last_entry.update({'feedback': feedback})
    save_feedback()
    st.success("Feedback enregistré avec succès !") #confirmation que tous est bon

# invoke the model to generate the responce
def process_request(query_text):
    start_time = time()
    result = query_rag(query_text)
    elapsed_time = time() - start_time
    logger.info(f"Requête traitée en {elapsed_time:.2f} secondes")
    return result

# Main application
def main():
    
    initialize_session_state()

    st.markdown("""
    <head>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css">
    </head>
    """, unsafe_allow_html=True)

    st.markdown("<h1 style='color: purple;'><i class='fas fa-balance-scale'></i> Juridique_Bot</h1>", unsafe_allow_html=True)

    # si l'utilisateur veux faire entrer nouveau fichier / avoir une nouvelle conversation
    if st.sidebar.button("🔄 Nouveau fichier // Nouvelle conversation"):
        initialize_session_state()
        st.session_state.messages = []
        st.session_state.feedback_history = []
        st.session_state.file_processed = False
        st.rerun()

    # Gestion des fichiers uploadés
    uploaded_file = st.file_uploader("", type=["pdf"], label_visibility="collapsed")
    if uploaded_file is not None:
        if not st.session_state.file_processed:
            st.success("✅ Fichier téléchargé avec succès!")
            file_path = save_uploaded_file(uploaded_file)
            with st.spinner("Traitement du fichier PDF en cours..."):
                process_pdf_file(file_path)
            st.session_state["messages"].append({"role": "assistant", "content": "Fichier traité avec succès !"})
            st.session_state.file_processed = True
        else:
            st.info("⚠️ Le fichier a déjà été traité.") # dans le cas où il est déjà dans notre bd

    # Affichage des messages précédents (conversations)
    for msg in st.session_state.get("messages", []):
        st.chat_message(msg["role"]).write(msg["content"])

    # Boîte de saisie pour poser une question
    if user_input := st.chat_input("Posez votre question juridique..."):
        if not user_input.strip():
            st.warning("❌ Veuillez poser une question valide.")
            return

        st.session_state["messages"].append({"role": "user", "content": user_input})
        st.chat_message("user").write(user_input)

        with st.spinner("Recherche en cours..."):
            result = process_request(user_input)

        st.session_state["messages"].append({"role": "assistant", "content": result})
        st.chat_message("assistant").write(result)

        # Ajouter à l'historique des interactions
        st.session_state.feedback_history.append({
            'Timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'Session_ID': st.session_state.session_id,
            'Question': user_input,
            'Réponse': result,
        })

    # Gestion du feedback aprés la generation de la réponse 
    if len(st.session_state.feedback_history) > 0:
        feedback_response = streamlit_feedback(
            feedback_type="thumbs",
            optional_text_label="[Optionnel] Expliquez votre choix",
            key=f"fb_{len(st.session_state.feedback_history)}",
        )
        if feedback_response:
            fbcb(feedback_response)

if __name__ == "__main__":
    main()
