from flask import Flask, render_template, Markup, request, jsonify
import openai
from io import StringIO
import fitz  # PyMuPDF
from dotenv import load_dotenv
from nltk.tokenize import sent_tokenize
import os
import subprocess
import whisper

# Initialisation de l'application Flask
from app import app

# Chargement de la clé OpenAI
openai.api_key_path = ".venv/APIKEY.txt"

# Liste pour stocker l'historique des messages
message_history = []

# Fonction pour lire un fichier PDF
def read_pdf(filename):
    """
    Lit le contenu textuel d'un fichier PDF et retourne le texte concaténé de toutes les pages.

    :param filename: Chemin du fichier PDF à lire.
    :return: Texte extrait du PDF.
    """
    context = ""
    try:
        with fitz.Document(filename) as pdf_file:
            for page_num in range(pdf_file.page_count):
                page = pdf_file.load_page(page_num)
                page_text = page.get_text().replace("\n", "")
                context += page_text
    except Exception as e:
        print(f"Erreur lors de la lecture du PDF : {e}")
    return context

# Fonction pour lire un fichier texte
def read_txt(filename):
    """
    Lit le contenu d'un fichier texte et retourne son contenu.

    :param filename: Chemin du fichier texte.
    :return: Contenu du fichier texte.
    """
    try:
        with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except Exception as e:
        raise ValueError(f"Erreur lors de la lecture du fichier texte {filename}: {e}")

# Fonction pour diviser un texte en chunks
def split_text(text, chunk_size=5000):
    """
    Divise un texte en morceaux de taille spécifiée.

    :param text: Texte à diviser.
    :param chunk_size: Taille maximale d'un chunk.
    :return: Liste de chunks.
    """
    chunks = []
    current_chunk = StringIO()
    current_size = 0
    sentences = sent_tokenize(text)
    
    for sentence in sentences:
        sentence_size = len(sentence)
        if sentence_size > chunk_size:
            while sentence_size > chunk_size:
                chunk = sentence[:chunk_size]
                chunks.append(chunk)
                sentence = sentence[chunk_size:]
                sentence_size -= chunk_size
                current_chunk = StringIO()
                current_size = 0
        if current_size + sentence_size < chunk_size:
            current_chunk.write(sentence)
            current_size += sentence_size
        else:
            chunks.append(current_chunk.getvalue())
            current_chunk = StringIO()
            current_chunk.write(sentence)
            current_size = sentence_size
    
    if current_chunk:
        chunks.append(current_chunk.getvalue())
    return chunks

# Fonction pour transcrire une vidéo en texte
def transcribe_video(video_path, language="fr", model_name="tiny", save=True):
    """
    Transcrit l'audio d'une vidéo en texte en utilisant Whisper.

    :param video_path: Chemin de la vidéo.
    :param language: Langue de transcription.
    :param model_name: Modèle Whisper à utiliser.
    :param save: Sauvegarder ou non la transcription.
    :return: Transcription texte.
    """
    audio_path = "sample-3.mp3"
    if os.path.exists(audio_path):
        os.remove(audio_path)
    
    command = [
        'ffmpeg',
        '-i', video_path,  # Fichier vidéo d'entrée
        '-q:a', '0',       # Qualité audio
        '-map', 'a',       # Extraire uniquement la piste audio
        audio_path         # Fichier audio de sortie
    ]
    subprocess.run(command, check=True)

    model = whisper.load_model(model_name)
    result = model.transcribe(audio_path, language=language)

    if save:
        with open("transcription.txt", "w", encoding="utf-8") as f:
            f.write(result["text"])

    return result["text"]

# Fonction pour générer un compte rendu à partir d'un texte de réunion
def generer_compte_rendu(dialogue, length=1):
    """
    Génère un compte rendu professionnel à partir d'un dialogue de réunion.

    :param dialogue: Texte du dialogue.
    :param length: Multiplicateur pour la longueur du compte rendu.
    :return: Compte rendu généré.
    """
    try:
        messages = [
            {"role": "system", "content": "Vous êtes un assistant chargé de rédiger des comptes rendus professionnels."},
            {"role": "user", "content": f"Voici le texte d'un dialogue :\n\n{dialogue}\n\nRédigez un compte rendu professionnel et structuré."}
        ]

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=length * len(dialogue),
            temperature=0.5
        )

        return response['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"Erreur lors de la génération du compte rendu : {e}")
        return None

# Fonction principale pour gérer les fichiers et générer des comptes rendus
def compterendu():
    """
    Lit des fichiers, génère un compte rendu et le sauvegarde.

    :return: Compte rendu généré.
    """
    try:
        filename = os.path.join(os.path.dirname(__file__), "filename.pdf")
        document = read_pdf(filename)
        chunks = split_text(document)

        filename2 = os.path.join(os.path.dirname(__file__), "transcription.txt")
        document2 = read_txt(filename2)
        chunks2 = split_text(document2)

        message_history.clear()
        message_history.append({"role": "user", "content": chunks[0]})
        message_history.append({"role": "user", "content": chunks2[0]})
        message_history.append({"role": "user", "content": "Utilisez le modèle pour rédiger un compte rendu structuré."})

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=message_history,
            max_tokens=450
        )

        summary = response.choices[0].message['content']
        text_file_path = filename2.replace('.txt', '_resume.txt')

        with open(text_file_path, 'w', encoding='utf-8') as text_file:
            text_file.write(summary)

        print(f"Résumé sauvegardé dans {text_file_path}")
        return summary
    except Exception as e:
        print(f"Erreur lors du traitement : {e}")
        return None

# Fonction pour traiter les vidéos téléchargées
def traiter_video():
    """
    Parcourt les vidéos téléchargées et les traite.
    """
    video_dir = os.path.join(os.getcwd(), 'app', 'static', 'uploads')
    fichiers = os.listdir(video_dir)

    if fichiers:
        for fichier in fichiers:
            print(f"Traitement de la vidéo : {fichier}")
    else:
        print("Aucune vidéo à traiter")

# Fonction pour traiter les données d'une vidéo
def process(gdata):
    """
    Traite une vidéo et génère un compte rendu.

    :param gdata: Dictionnaire contenant les données de la vidéo.
    :return: Résultat du traitement.
    """
    file_path = gdata.get('file_path')

    if not file_path or not os.path.exists(file_path):
        return {"error": "Fichier non trouvé"}

    file_size = os.path.getsize(file_path)
    print("Fichier trouvé, traitement en cours...")

    result = compterendu()

    return {
        "status": "completed",
        "file_size": file_size,
        "file_name": os.path.basename(file_path),
        "file_resume": result
    }
