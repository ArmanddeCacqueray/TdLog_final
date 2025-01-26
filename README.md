# Projet de Compte Rendu Automatique

Ce projet utilise des technologies modernes comme Flask, Whisper, et OpenAI pour générer automatiquement des comptes rendus de réunions à partir de fichiers vidéo ou texte. Voici un guide pour configurer et exécuter le projet.

---

## Prérequis

1. **Clé OpenAI** :
   - Créez un fichier `.venv/APIKEY.txt`.
   - Ajoutez-y votre clé API OpenAI.

2. **Python** : Assurez-vous que Python (version 3.8 ou supérieure) est installé sur votre machine.

3. **FFmpeg** : Téléchargez et configurez FFmpeg pour traiter les fichiers multimédias.

---

## Étapes d'installation

### 1. Créer un environnement Python
```bash
python -m venv .venv
source .venv/bin/activate # Sur Linux/Mac
env\Scripts\activate    # Sur Windows
```

### 2. Installer les dépendances

#### Installer les modules requis :
```bash
pip install -r requirements.txt
pip install -r modules_armand.txt
```
⚠️ *L'installation peut prendre environ 10 minutes, en particulier à cause du module `torch`.(1 Giga)

### 3. Configurer FFmpeg

#### Téléchargement et installation :
1. Rendez-vous sur [le site officiel de FFmpeg](https://ffmpeg.org/) ou [gyan.dev](https://www.gyan.dev/).
2. Téléchargez une version "Essential Builds" ou "Full Builds".
3. Décompressez l'archive dans un dossier, par exemple : `C:\ffmpeg`.

#### Ajouter FFmpeg à la variable PATH (Windows) :
1. Appuyez sur `Win + S` et recherchez "Variables d'environnement".
2. Dans la fenêtre **Propriétés système**, cliquez sur **Variables d'environnement...**.
3. Dans la section **Variables système**, sélectionnez la variable `Path` et cliquez sur **Modifier**.
4. Ajoutez un nouveau chemin : `C:\ffmpeg\bin`.
5. Cliquez sur **OK** pour valider.

Vérifiez l'installation :
```bash
ffmpeg -version
```

### 4. Lancer le projet
le projet se lance avec la commande flask dans le powershell:
```bash
flask run
```

---

## Utilisation

1. Une fois le projet lancé,  vous accédez à :
   - [http://127.0.0.1:5000/index](http://127.0.0.1:5000/)

2. Suivez les étapes pour :
   - Charger des fichiers vidéo ou texte.
   - Obtenir un compte rendu structuré de la réunion.

### Remarque importante
- Après avoir cliqué sur le bouton pour valider la video selectionnée, la page affichera un message JSON.
- Pour continuer à naviguer, revenez simplement à la page précédente dans votre navigateur.

---

## Dépannage

### Erreurs courantes :
1. **FFmpeg non trouvé** :
   - Assurez-vous que le chemin `C:\ffmpeg\bin` est ajouté à votre variable PATH.

2. **Modules manquants** :
   - Vérifiez que toutes les dépendances sont bien installées avec `pip install -r requirements.txt` et `modules_armand.txt`.

3. **Erreur OpenAI API** :
   - Assurez-vous que votre clé OpenAI est correctement placée dans `.venv/APIKEY.txt`.

---

## Contributeurs

- **Armand** : Créateur principal du projet.

Pour toute question ou amélioration, n'hésitez pas à proposer une issue ou une pull request.

