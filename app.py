from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, Markup, g
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
import os
import fitz  # PyMuPDF
import yt_dlp   
import utils
import subprocess
import whisper
from datetime import datetime
import openai
import re
from dotenv import load_dotenv

# Génération d'une clé secrète
secret_key = secrets.token_hex(16)  # Génère une clé secrète hexadécimale de 32 caractères
print(secret_key)
print( "print")

# Création de l'application Flask
app = Flask(__name__)
app.secret_key = secret_key

# Configuration de la base de données
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ddatabase.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


def download_video_from_url(url):
    ydl_opts = {
        'format': 'best',
        'outtmpl': 'downloads/%(id)s.%(ext)s',  # Dossier de téléchargement
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info_dict)


# Modèle pour les utilisateurs
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    videos = db.relationship('Video', backref='owner', lazy=True)

    def __init__(self, name, email, password):
        self.name = name
        self.email = email
        self.password = password

# Modèle pour les vidéos
class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    video_url = db.Column(db.String(255), nullable=False)
    video_length = db.Column(db.Integer, nullable=False)  # Longueur de la vidéo en secondes
    transcription = db.Column(db.Text, nullable=True) 
    compterendu = db.Column(db.Text, nullable=True) 
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


# Créer les tables dans la base de données
with app.app_context():
    db.create_all()

# Route pour afficher la page de connexion
@app.route('/')
def home():
    user_name = session.get('user_name')  # Récupérer le nom de l'utilisateur connecté
    if user_name:
        return render_template('home.html', user_name=user_name)
    else:
        return redirect(url_for('login'))  # Rediriger si l'utilisateur n'est pas connecté

@app.route('/logout')
def logout():
    session.clear()  # Supprime toutes les données de session
    flash('Vous êtes déconnecté.', 'info')
    return redirect(url_for('login'))

@app.route('/ajouter_transcription', methods=['POST'])
def ajouter_transcription():
    user_id = session.get('user_id')
    if not user_id:
        flash("Veuillez vous connecter pour accéder à cette page.", "danger")
        return redirect(url_for('login'))

    if request.method == 'POST':
        transcription_text = request.form.get('transcription_text')  # Récupère le texte de la transcription
        video_name = request.form.get('video_url')

        if not transcription_text:
            flash("Veuillez fournir une transcription.", 'danger')
            return redirect(request.url)

        try:
            # Créer un nouvel enregistrement avec juste du texte (transcription)
            new_video = Video(
                video_url=video_name, 
                video_length=0,
                compterendu=None,
                user_id=user_id,
                transcription=transcription_text
            )

            db.session.add(new_video)
            db.session.commit()

            flash('Transcription ajoutée avec succès.', 'success')
            return render_template('upload_video.html')


        except Exception as e:
            flash(f"Une erreur s'est produite lors de l'ajout de la transcription : {e}", 'danger')
            return redirect(request.url)

    return render_template('upload_video.html')


@app.route('/ajouter_video', methods=['POST'])
def ajouter_video():
    user_id = session.get('user_id')
    if not user_id:
        flash("Veuillez vous connecter pour accéder à cette page.", "danger")
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Récupérer l'URL ou le fichier de la vidéo
        video_url = request.form.get('video_url')
        videolength = request.form.get('video_length')
        if video_url:
            try:
                print(f"Téléchargement de la vidéo depuis l'URL : {video_url}")
                video_path = download_video_from_url(video_url)
                print(f"Vidéo téléchargée avec succès à : {video_path}")
            except Exception as e:
                flash(f"Erreur lors du téléchargement de la vidéo : {e}", 'danger')
                print(f"Erreur lors du téléchargement de la vidéo : {e}")
                return redirect(request.url)
        else:
            if 'video_file' not in request.files:
                flash('Aucun fichier vidéo sélectionné.', 'danger')
                print("Aucun fichier vidéo sélectionné.")
                return redirect(request.url)

            video_file = request.files['video_file']
            if video_file.filename == '':
                flash('Veuillez sélectionner un fichier vidéo valide.', 'danger')
                print("Aucun fichier vidéo valide sélectionné.")
                return redirect(request.url)

            video_path = os.path.join('uploads', video_file.filename)
            video_file.save(video_path)
            print(f"Fichier vidéo enregistré à : {video_path}")

        try:
            # Transcrire la vidéo avec Whisper
            print(f"Chargement du modèle Whisper...")
            transcription =  utils.transcribe_video(video_path, save=False)

            # Vérifier la transcription
            print(f"Transcription de la vidéo : {transcription[:100]}...")  # Afficher les 100 premiers caractères de la transcription

            # Créer un nouvel enregistrement de vidéo avec la transcription
            new_video = Video(
                video_url=video_path,
                video_length=videolength,  # Longueur basée sur le nombre de mots
                user_id=user_id,
                transcription=transcription,
                compterendu=None
            )
            print(f"Ajout de la vidéo à la base de données : {new_video.video_url}, longueur : {new_video.video_length} mots")
            db.session.add(new_video)
            db.session.commit()

            flash('Vidéo et transcription ajoutées avec succès.', 'success')
            print("Vidéo et transcription ajoutées avec succès.")
            return render_template('upload_video.html')

        except Exception as e:
            flash(f"Une erreur s'est produite lors du traitement de la vidéo : {e}", 'danger')
            print(f"Erreur lors du traitement de la vidéo : {e}")
            return redirect(request.url)
        finally:
            # Supprimer la vidéo après traitement pour économiser de l'espace disque
            if os.path.exists(video_path):
                os.remove(video_path)
                print(f"Vidéo supprimée après traitement : {video_path}")

    return render_template('upload_video.html')






def download_video_from_url(url):
    ydl_opts = {
        'format': 'best',
        'outtmpl': 'uploads/%(id)s.%(ext)s',  # Dossier de téléchargement
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info_dict)



# Route pour traiter les informations du formulaire de connexion
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    
    email = request.form['email']
    password = request.form['password']

    # Vérifier si l'utilisateur existe
    user = User.query.filter_by(email=email).first()

    if user and check_password_hash(user.password, password):
        # Enregistrer l'utilisateur dans la session
        session['user_id'] = user.id
        session['user_name'] = user.name
        flash('Connexion réussie !', 'success')
        return redirect(url_for('upload_video'))
    else:
        flash('Email ou mot de passe incorrect.', 'danger')
        return redirect(url_for('login'))

@app.route('/upload_video', methods=['GET', 'POST'])
def upload_video():
    if request.method == 'GET':
        return render_template('upload_video.html')  # Affiche la page d'upload de vidéo
    else:
        # Traitement du formulaire POST (ajout de la vidéo)
        video_url = request.form['video_url']
        video_length = request.form['video_length']
        # Ajouter la vidéo à la base de données ou effectuer l'upload
        return render_template('upload_video.html')   # Redirige après l'ajout

# Route pour ajouter une vidéo
@app.route('/add_video', methods=['POST'])
def add_video():
    if 'user_id' not in session:
        flash('Veuillez vous connecter pour ajouter une vidéo.', 'danger')
        return redirect(url_for('login'))

    email = request.form['email']  # Email de l'utilisateur pour identifier le propriétaire
    video_url = request.form['video_url']
    video_length = int(request.form['video_length'])  # Longueur de la vidéo (en secondes)

    # Trouver l'utilisateur correspondant à l'email
    user = User.query.filter_by(email=email).first()
    if not user:
        flash('Utilisateur non trouvé. Veuillez vérifier l\'email.', 'danger')
        return redirect(url_for('home'))

    # Ajouter la vidéo dans la base de données
    new_video = Video(video_url=video_url, video_length=video_length, user_id=user.id)
    db.session.add(new_video)
    db.session.commit()

    flash('Vidéo ajoutée avec succès !', 'success')
    return redirect(url_for('home'))

# Route pour afficher les vidéos d'un utilisateur
@app.route('/videos')
def videos():
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Rediriger vers la page de login si l'utilisateur n'est pas connecté

    # Récupérer l'utilisateur actuellement connecté
    user = User.query.get(session['user_id'])
    # Récupérer toutes les transcriptions de l'utilisateur
    videos = Video.query.filter_by(user_id=user.id).all() # Supposez que "Video" est votre modèle SQLAlchemy
    return render_template('videos.html', videos=videos)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        hashed_password = generate_password_hash(password, method='sha256')

        # Vérifier si l'utilisateur existe déjà
        if User.query.filter_by(email=email).first():
            flash('Un utilisateur avec cet email existe déjà.', 'danger')
            return redirect(url_for('signup'))

        # Créer un nouvel utilisateur
        new_user = User(name=name, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        flash('Compte créé avec succès ! Connectez-vous.', 'success')
        return redirect(url_for('login'))

    return render_template('signup.html')

@app.route('/index')
def index():
     # Assurez-vous que l'utilisateur est connecté
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Rediriger vers la page de login si l'utilisateur n'est pas connecté

    # Récupérer l'utilisateur actuellement connecté
    user = User.query.get(session['user_id'])
    # Récupérer toutes les transcriptions de l'utilisateur
    videos = Video.query.filter_by(user_id=user.id).all() # Supposez que "Video" est votre modèle SQLAlchemy
    return render_template('index.html', videos=videos)



@app.route('/update_transcription', methods=['POST'])
def update_transcription():
    data = request.get_json()
    video_id = data.get('video_id')
    
    # Récupérer la vidéo depuis la base de données
    video = Video.query.get(video_id)
    if not video:
        return "Vidéo non trouvée", 404

    # Chemin vers le fichier transcription.txt
    transcription_path = os.path.join(app.root_path, 'transcription.txt')
    try:
        # Écrire la transcription dans le fichier transcription.txt
        with open(transcription_path, 'w', encoding='utf-8') as file:
            file.write(video.transcription or "Aucune transcription disponible.")
        return f"Fichier transcription.txt mis à jour avec succès pour la vidéo ID {video_id}.", 200
    except Exception as e:
        return f"Erreur lors de la mise à jour : {e}", 500

# Chargement des variables d'environnement
load_dotenv()


# Configuration des répertoires et des tailles de fichiers
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # Taille maximale des fichiers (50 Mo)


#############
message_history = []

# Extensions autorisées pour les fichiers
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv'}

# Fonction pour vérifier les extensions de fichiers
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Route de la page d'accueil
@app.route("/home2")
def new_home():
    return render_template("index.html")

# Préparation des données avant chaque requête
@app.before_request
def before_request():
    g.dynamic_data = {"status": "processing"}

# Route pour télécharger des fichiers
@app.route('/upload', methods=['POST'])
def upload_file():
    user_id = session.get('user_id')
    mon_resume=utils.compterendu()
    video = Video.query.get(user_id)
    video.compterendu = mon_resume
    db.session.commit()
    return render_template("upload.html", dynamic_message=Markup(mon_resume))


# Fonction pour effectuer la complétion GPT-3.5
filename = os.path.join(os.path.dirname(__file__), "transcription.txt")
document = utils.read_txt(filename)
chunks = utils.split_text(document)  
message_history = []
def gpt3_completion(prompt_user, model="gpt-3.5-turbo", max_tokens=450):
    global message_history
    message_history.append({"role": "user", "content": prompt_user})
    response = openai.ChatCompletion.create(
        model=model, messages=message_history, max_tokens=max_tokens
    )
    model_response = response.choices[0].message["content"].strip()
    message_history.append({"role": "assistant", "content": model_response})
    return model_response

# Route pour afficher la page de conversation
@app.route("/conversation", methods=["GET", "POST"])
def conversation():
    message_history.clear()  # Réinitialise la liste à vide
    message_history.append({"role": "user", "content": chunks[0]})
    return render_template("index_conversation.html")

# Route pour envoyer un prompt et recevoir une réponse
@app.route("/prompt", methods=["POST", "GET"])
def prompt():
    if request.method == "POST":
        prompt = request.form["prompt"]
        ans = gpt3_completion(prompt)
        return jsonify({"answer": ans})


@app.route('/generate_cr', methods=['POST'])
def generate_cr():
    # Vérifiez si l'utilisateur est connecté
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Redirige si l'utilisateur n'est pas connecté
    # Récupération de l'ID de la vidéo sélectionnée depuis le formulaire
    video_id = request.form.get('video_select')

    # Vérification si une vidéo a été sélectionnée
    if not video_id:
        flash("Veuillez sélectionner une vidéo pour générer le compte rendu.")
        return redirect(url_for('index'))

    # Rechercher la vidéo dans la base de données
    video = Video.query.get(video_id)
    if not video:
        flash("La vidéo sélectionnée est introuvable.")
        return redirect(url_for('index'))

    # Vérification si la transcription est disponible pour la vidéo
    if not video.transcription:
        flash("Aucune transcription disponible pour cette vidéo.")
        return redirect(url_for('index'))

    # Remplacement du contenu de `transcription.txt` par la transcription de la vidéo
    transcription_path = "transcription.txt"
    try:
        with open(transcription_path, 'w', encoding='utf-8') as f:
            f.write(video.transcription)
        flash("Le compte rendu a été généré avec succès.")
    except Exception as e:
        flash(f"Une erreur s'est produite lors de la génération du compte rendu : {str(e)}")
        return redirect(url_for('index'))
     return jsonify({'message': 'transcription chargée dans transcription.txt, vous pouvez maintenant generer un compte rendu'}), 200


# Route pour poser une question prédéfinie
@app.route("/question", methods=["GET"])
def question():
    ans = gpt3_completion("tu es un assistant gpt qui réponds aux questions sur les réunions, présentes toi très rapidement et propose ton aide")
    return jsonify({"answer": ans})

# Route pour générer une réponse basée sur un prompt
@app.route("/answer", methods=["POST", "GET"])
def answer():
    prompt = request.form["prompt"]
    prompt = f"{prompt}\nRéponds à la requête de l'utilisateur"
    ans = gpt3_completion(prompt)
    return jsonify({"answer": ans})

@app.route('/animation', methods=['GET', 'POST'])
# Fonction pour générer un compte rendu animé
def compterendu_anime():
    model_path = os.path.join(os.path.dirname(__file__), "modele_animation_js.txt")
    transcription_path = os.path.join(os.path.dirname(__file__), "transcription.txt")
    
    # Lecture des fichiers
    model_text = utils.read_txt(model_path)
    transcription_text = utils.read_txt(transcription_path)
    
    # Découper le texte en morceaux
    model_chunks = utils.split_text(model_text)
    transcription_chunks = utils.split_text(transcription_text)

    # Ajouter les morceaux dans l'historique des messages
    message_history.clear()
    message_history.append({"role": "user", "content": model_chunks[0]})
    message_history.append({"role": "user", "content": transcription_chunks[0]})
    message_history.append({"role": "user", "content": "Génère un scénario animé en format Javascript, où chaque bot (bot1, bot2, etc.) représente un intervenant en respectant le modele que je t'ai donné"})

    # Appel à l'API OpenAI pour générer le scénario
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo", messages=message_history, max_tokens=1500
    )
    scenario = response.choices[0].message["content"]

    # Sauvegarder le scénario dans un fichier JS
    js_folder = os.path.join(os.getcwd(), "static", "js")
    output_js_path = os.path.join(js_folder, "prompt_anime.js")
    with open(output_js_path, "w", encoding="utf-8") as js_file:
        js_file.write(scenario)
        js_file.write('''
function displayScenario(scenario) {
    const chatContainer = document.getElementById('chat-container');
    scenario.forEach((entry, index) => {
        setTimeout(() => {
            const messageDiv = document.createElement('div');
            messageDiv.classList.add('chat-message');
            const avatarImg = document.createElement('img');
            avatarImg.src = entry.avatar;
            avatarImg.alt = `${entry.bot} avatar`;
            avatarImg.classList.add('chat-avatar');
            const textDiv = document.createElement('div');
            textDiv.classList.add('chat-text');
            textDiv.innerHTML = `<strong>${entry.bot}:</strong> ${entry.message}`;
            messageDiv.appendChild(avatarImg);
            messageDiv.appendChild(textDiv);
            chatContainer.appendChild(messageDiv);
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }, index * 3000); // Affiche chaque message avec un délai de 3 secondes
    });
}
window.onload = () => { displayScenario(meetingScenario); };
''')
    print(f"Scénario animé sauvegardé dans {output_js_path}")
    if request.method == 'POST':
        # Traitement de la vidéo uploadée pour l'animation
        # Ajoutez ici le code pour traiter l'upload
          return render_template('index_anime.html')
    return render_template('index_anime.html')



# Fonction pour générer un compte rendu basé sur une base de données
def compterendu_basededonnee():
    model_path = os.path.join(os.path.dirname(__file__), "modele_basededonnee.txt")
    transcription_path = os.path.join(os.path.dirname(__file__), "transcription.txt")
    
    # Lecture des fichiers
    model_text = utils.read_txt(model_path)
    transcription_text = utils.read_txt(transcription_path)

    # Découper le texte en morceaux
    model_chunks = utils.split_text(model_text)
    transcription_chunks = utils.split_text(transcription_text)

    # Ajouter les morceaux dans l'historique des messages
    message_history.clear()
    message_history.append({"role": "user", "content": model_chunks[0]})
    message_history.append({"role": "user", "content": transcription_chunks[0]})
    message_history.append({"role": "user", "content": "Génère un texte formaté en base de données à partir de la transcription de réunion, avec des titres en gras et des sauts de ligne."})

    # Appel à l'API OpenAI pour générer le résumé
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo", messages=message_history, max_tokens=450
    )

    summary = response.choices[0].message['content']
    
    # Sauvegarde du résumé dans un fichier
    text_file_path = transcription_path.replace('.txt', '_resume.txt')
    with open(text_file_path, 'w') as text_file:
        text_file.write(summary)
    print(f"Résumé sauvegardé dans {text_file_path}")

    return summary


def format_text_for_html(text):
    # Conversion de Markdown **gras** en balises <strong>
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    
    # Si vous avez des puces dans votre texte, les convertir en <ul> et <li>
    text = re.sub(r'(?m)^- (.+)$', r'<li>\1</li>', text)  # - en <li> (ajoutez cette ligne pour les puces)
    text = re.sub(r'(<li>.*?</li>)', r'<ul>\1</ul>', text, flags=re.DOTALL)  # <ul> autour des <li>
    
    # Remplacer les retours à la ligne par des balises <br>
    text = text.replace('\n', '<br>')
    
    return text

# Route pour afficher le résumé en base de données
@app.route('/basededonnee', methods=['GET', 'POST'])
def basededonnee():
    if request.method == 'POST':
        # Traitement de la vidéo uploadée pour la base de données
        # Ajoutez ici le code pour traiter l'upload
        result=compterendu_basededonnee()
        return render_template("upload_safe.html", dynamic_message=format_text_for_html(Markup(result)))

@app.route('/videos/<int:video_id>/transcription')
def view_transcription(video_id):
    video = Video.query.get(video_id)
    if not video or not video.transcription:
        flash("Transcription introuvable ou vidéo inexistante.", "danger")
        return redirect(url_for('videos', email=session.get('user_email')))  # Redirection à la liste des vidéos
    
    return render_template('transcription.html', transcription=video.transcription, video=video)

@app.route('/videos/<int:video_id>/compterendu')
def view_compterendu(video_id):
    video = Video.query.get(video_id)
    if not video or not video.compterendu:
        flash("Compte rendu introuvable ou vidéo inexistante.", "danger")
        return redirect(url_for('videos', email=session.get('user_email')))  # Redirection à la liste des vidéos
    
    return render_template('compterendu.html', compterendu=video.compterendu, video=video)

if __name__ == "__main__":
    app.run(debug=True)

