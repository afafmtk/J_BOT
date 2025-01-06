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
if "file_uploader_key" not in st.session_state:
    st.session_state["file_uploader_key"] = 0

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

def reset_file_and_chat():
    """Réinitialise l'état de l'application et force la désélection du fichier."""
    st.session_state.clear()
    # Incrémente la clé pour forcer le rechargement du file_uploader
    st.session_state["file_uploader_key"] = (st.session_state.get("file_uploader_key", 0) + 1)

# Interface principale
def main():
    st.markdown("""
    <head>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css">
    </head>
    """, unsafe_allow_html=True)
    
    st.markdown("<h1 style='color: purple;'><i class='fas fa-balance-scale'></i> Juridique_Bot</h1>", unsafe_allow_html=True)
    
    # Barre latérale avec logo
    #st.sidebar.image("static/logo_dxc.jpg", use_container_width=True)
    #st.sidebar.markdown("<h2 style='color: purple;'>Query History</h2>", unsafe_allow_html=True)

    if st.sidebar.button("🔄  Nouveau fichier"):
        reset_file_and_chat()
        st.rerun()

    # Interface de chat unifiée
    
    # Zone de téléchargement de fichier intégrée avec clé dynamique
    uploaded_file = st.file_uploader(
        "", 
        type=["pdf"], 
        label_visibility="collapsed",
        key=f"file_uploader_{st.session_state.get('file_uploader_key', 0)}"
    )
    
    # Traitement du fichier si téléchargé
    if uploaded_file is not None and uploaded_file != st.session_state.get("last_processed_file"):
        st.success("✅ Fichier téléchargé avec succès!")
        file_path = save_uploaded_file(uploaded_file)
        with st.spinner("Traitement du fichier PDF en cours..."):
            process_pdf_file(file_path)
        st.session_state["file_processed"] = True
        st.session_state["last_processed_file"] = uploaded_file
        st.session_state["messages"].append({"role": "assistant", "content": "Fichier traité avec succès ! Vous pouvez maintenant poser vos questions."})
        st.rerun()

    # Affichage de l'historique des messages
    for msg in st.session_state["messages"]:
        st.chat_message(msg["role"]).write(msg["content"])

    # Zone de chat avec instruction claire
    if user_input := st.chat_input("Posez votre question juridique..."):
        # Ajouter la question à l'historique
        st.session_state["messages"].append({"role": "user", "content": user_input})
        st.chat_message("user").write(user_input)

        # Générer et ajouter la réponse
        with st.spinner("Recherche en cours..."):
            result, _ = process_request(user_input)
        st.session_state["messages"].append({"role": "assistant", "content": result})
        st.chat_message("assistant").write(result)

if __name__ == "__main__":
    main()