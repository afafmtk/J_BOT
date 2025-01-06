from pypdf import PdfReader
import re
import os
import fitz
import spacy
from spacy.lang.fr.stop_words import STOP_WORDS
import PyPDF2
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama.llms import OllamaLLM


nlp = spacy.load("fr_core_news_sm")


def extract_text_simple(pdf_path):
    with open(pdf_path, "rb") as file:
        reader = PyPDF2.PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
            textt = clean_text(text)
    return textt

"""
def extract_text_simple(pdf_path):
    reader = PdfReader(pdf_path)
    all_text = []

    for page in reader.pages:
        text = page.extract_text()
        if text:
            all_text.append(text.strip())

    return '\n'.join(all_text)
"""


def detect_pdf_format(pdf_path):
    try:
        doc = fitz.open(pdf_path)
        page = doc.load_page(0)
        blocs = page.get_text("dict")["blocks"]
        left_count = 0
        right_count = 0
        middle_x = page.rect.width / 2

        for block in blocs:
            if "bbox" in block:
                x0, _, x1, _ = block["bbox"]
                if x1 <= middle_x:
                    left_count += 1
                elif x0 >= middle_x:
                    right_count += 1

        doc.close()

        if left_count > 0 and right_count > 0:
            return "double"
        else:
            return "simple"
    except Exception as e:
        return f"Erreur lors de la détection : {e}"
    
   
def extract_f_double(pdf_path):
    reader = PdfReader(pdf_path)
    all_pages_text = []
    
    for page in reader.pages:
        text = page.extract_text()
        if text:  # Vérifie que le texte est valide
            text = clean_text(text)
            structured_text = analyze_page_structure(text)
            all_pages_text.append(structured_text)

    # Forcer la sortie en chaîne de caractères
    return '\n'.join(all_pages_text)


def clean_text(text):
    """
    Nettoie et normalise le texte extrait
    """
    text = re.sub(r'\s+', ' ', text)  
    text = re.sub(r'\n+', '\n', text)  
    text = re.sub(r'[^\w\s.,;:!?()\[\]\'"-]', '', text)
    text = re.sub(r'\s+([.,;:!?])', r'\1', text)  
    text = re.sub(r'([.,;:!?])\s+', r'\1 ', text)  
    text = re.sub(r'\s{2,}', ' ', text)

    # Normalisation 
    text = text.lower()

    # Lemmatisation et suppression des mots vides avec spaCy
    doc = nlp(text)
    cleaned_tokens = []
    for token in doc:
        if token.lemma_ not in STOP_WORDS and not token.is_punct:
            cleaned_tokens.append(token.lemma_)

    cleaned_text = ' '.join(cleaned_tokens)

    return cleaned_text.strip()


def analyze_page_structure(text):
    column_markers = identify_column_markers(text)
    structured_text = reorganize_columns(text, column_markers)
    return structured_text

def identify_column_markers(text):
    markers = []
    space_sequences = re.finditer(r'\s{4,}', text)
    for match in space_sequences:
        markers.append(match.start())
    return markers

def reorganize_columns(text, markers):
    if not markers:
        return text
    columns = []
    start = 0
    for marker in markers:
        columns.append(text[start:marker].strip())
        start = marker
    columns.append(text[start:].strip())
    return '\n'.join(columns)   