import streamlit as st
import logging
import os
import shutil
from time import time
from langchain.schema import Document
from load_and_prepare import split_documents, add_to_chroma
from load_and_prepare2 import extract_text_simple, detect_pdf_format, extract_f_double
from retrieve import query_rag

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Initialisation des états nécessaires
if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "file_processed" not in st.session_state:
    st.session_state["file_processed"] = False
if "uploaded_file" not in st.session_state:
    st.session_state["uploaded_file"] = None

# Gestion des fichiers PDF
def save_uploaded_file(uploaded_file):
    """Sauvegarde un fichier PDF téléchargé dans le répertoire 'data'."""
    data_dir = os.path.join(os.getcwd(), 'data')
    os.makedirs(data_dir, exist_ok=True)

    file_path = os.path.join(data_dir, uploaded_file.name)
    if not os.path.exists(file_path):
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
    return file_path

# Traitement des documents PDF
def process_pdf_file(file_path):
    """Traite un fichier PDF (extraction et ajout à la base de données)."""
    format_type = detect_pdf_format(file_path)
    logger.info(f"📝 Format détecté : {format_type}")

    # Extraction du texte
    if format_type == "double":
        text = extract_f_double(file_path)
    else:
        text = extract_text_simple(file_path)

    # Découpage et ajout dans la base de données
    documents = [Document(page_content=text)]
    chunks = []
    for doc in documents:
        chunks.extend(split_documents([doc]))
    for chunk in chunks:
        add_to_chroma([chunk])

    return True

# Traitement de la requête utilisateur
def process_request(query_text):
    """Recherche la réponse basée sur la base de données Chroma."""
    start_time = time()
    result = query_rag(query_text)
    elapsed_time = time() - start_time
    return result, elapsed_time

# Interface principale
def main():
    st.title("💬 Juridique_Bot")

    # Barre latérale avec logo et historique
    st.sidebar.image("static\logo_dxc.jpg", use_container_width=True)
    st.sidebar.markdown("<h2 style='color: purple;'>Query History</h2>", unsafe_allow_html=True)

    if st.session_state["messages"]:
        for i, msg in enumerate(st.session_state["messages"], 1):
            if msg["role"] == "user":
                st.sidebar.write(f"{i}. {msg['content']}")
    else:
        st.sidebar.info("No queries submitted yet.")

    # Téléchargement de fichiers PDF
    if not st.session_state["file_processed"]:
        uploaded_file = st.file_uploader("Téléchargez un fichier PDF", type=["pdf"])
        if uploaded_file is not None:
            st.success("✅ Fichier téléchargé avec succès!")
            file_path = save_uploaded_file(uploaded_file)
            with st.spinner("Traitement du fichier PDF en cours..."):
                process_pdf_file(file_path)
            st.session_state["file_processed"] = True
            st.success("📄 Fichier traité et ajouté à la base de données!")
            st.rerun()

    # Affichage du chat après traitement du fichier
    if st.session_state["file_processed"]:
        for msg in st.session_state["messages"]:
            st.chat_message(msg["role"]).write(msg["content"])

        # Zone d'entrée utilisateur avec icône d'envoi ou touche Entrée
        if prompt := st.chat_input("Posez votre question juridique ici..."):
            # Ajouter la question
            st.session_state["messages"].append({"role": "user", "content": prompt})
            st.chat_message("user").write(prompt)

            # Générer et ajouter la réponse
            with st.spinner("Recherche en cours..."):
                result, _ = process_request(prompt)
            st.session_state["messages"].append({"role": "assistant", "content": result})
            st.chat_message("assistant").write(result)

if __name__ == "__main__":
    main()
