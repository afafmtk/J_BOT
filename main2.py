import logging
import os
import shutil
import re
from PyPDF2 import PdfReader
import fitz  # PyMuPDF
from tqdm import tqdm
from time import time
from langchain.schema import Document
from load_and_prepare import clear_database, split_documents, add_to_chroma
from load_and_prepare2 import extract_text_simple, detect_pdf_format, extract_f_double
from retrieve import query_rag

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def save_file_to_data_directory():
    """
    Demande à l'utilisateur d'entrer un fichier et le sauvegarde dans le répertoire 'data'.
    """
    while True:
        file_path = input("📂 Entrez le chemin complet du fichier PDF : ").strip()

        # Vérifie si le fichier existe
        if not os.path.isfile(file_path):
            logger.error("❌ Le fichier spécifié n'existe pas. Veuillez réessayer.")
            continue

        # Vérifie si c'est un fichier PDF
        if not file_path.lower().endswith(".pdf"):
            logger.error("❌ Seuls les fichiers PDF sont acceptés.")
            continue

        # Crée le dossier 'data' s'il n'existe pas
        data_dir = os.path.join(os.getcwd(), 'data')
        os.makedirs(data_dir, exist_ok=True)

        # Sauvegarde dans 'data'
        destination = os.path.join(data_dir, os.path.basename(file_path))
        if os.path.exists(destination):
            logger.warning("⚠️ Le fichier existe déjà dans le dossier 'data'. Passage direct à la génération de réponse.")
            return destination, True
        else:
            shutil.copy2(file_path, destination)
            logger.info(f"✅ Fichier sauvegardé dans : {destination}")
            return destination, False

def main():
    """
    Fonction principale pour gérer le traitement du document et répondre aux questions.
    """
    # Chronomètre le temps d'exécution
    start_time = time()

    # Étape 1 : Sauvegarder et charger le fichier
    pdf_path, already_processed = save_file_to_data_directory()

    # Étape 2 : Si le fichier n'est pas encore traité, effectuer l'extraction et l'ajouter à la base de données
    if not already_processed:
        # Détection du format du document
        format_type = detect_pdf_format(pdf_path)
        logger.info(f"📝 Format détecté : {format_type}")

        # Extraction du texte
        logger.info("📄 Extraction du texte en cours...")
        if format_type == "double":
            text = extract_f_double(pdf_path)  # Format double colonne
        else:
            text = extract_text_simple(pdf_path)  # Format simple colonne

        # Ajout du document extrait dans la base de données
        logger.info("📄 Ajout du document extrait dans la base de données.")
        documents = [Document(page_content=text)]

        logger.info("🔍 Découpage des documents en sections...")
        chunks = []
        for doc in tqdm(documents, desc="Découpage des documents", unit="doc"):
            chunks.extend(split_documents([doc]))

        logger.info("🗄️ Ajout des sections dans la base de données.")
        for chunk in tqdm(chunks, desc="Ajout dans Chroma", unit="chunk"):
            add_to_chroma([chunk])

    # Étape 3 : Poser une question et effectuer une recherche
    while True:
        query_text = input("❓ Entrez votre question juridique (ou tapez 'exit' pour quitter) : ").strip()
        if query_text.lower() == "exit":
            logger.info("🚪 Fin de la session. Merci d'avoir utilisé l'application.")
            break
        elif not query_text:
            logger.error("❌ Question vide. Veuillez poser une question valide.")
            continue

        logger.info(f"🔎 Recherche dans la base de données pour la question : '{query_text}'")
        query_rag(query_text)

    # Temps d'exécution
    end_time = time()
    elapsed_time = end_time - start_time
    logger.info(f"⏱️ Temps d'exécution total : {elapsed_time:.2f} secondes")

if __name__ == "__main__":
    main()
