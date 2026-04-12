# 🎙️ TNS — Signal Vocal

### Application web de Numérisation, Segmentation et Filtrage de Signal Vocal

*Mini-Projet · Traitement Numérique du Signal · DIC2 · ESP/UCAD · 2025–2026*

![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.x-000000?style=for-the-badge&logo=flask&logoColor=white)
![NumPy](https://img.shields.io/badge/NumPy-FFT-013243?style=for-the-badge&logo=numpy&logoColor=white)
![SciPy](https://img.shields.io/badge/SciPy-Signal-8CAAE6?style=for-the-badge&logo=scipy&logoColor=white)

> **Encadrant :** Dr. Moustapha MBAYE — Département de Génie Informatique, ESP/UCAD

---

## 📌 Présentation

Ce projet implémente une application web complète de traitement numérique du signal vocal, structurée en deux modules complémentaires :

| Module | Fonctionnalités |
|--------|----------------|
| **Partie 1 — Numérisation & Segmentation** | Enregistrement configurable (16/22/44 kHz · 16/32 bits), base de données audio organisée, découpage automatique des silences par analyse RMS |
| **Partie 2 — Analyse FFT & Filtrage** | Spectre fréquentiel par FFT, identification visuelle du bruit, filtre rectangulaire H(f) passe-bande ou coupe-bande, reconstruction par IFFT |

---

## ⚡ Démarrage rapide

### Prérequis

- Python **3.10+**
- Navigateur **Chrome** ou **Edge** (requis pour l'accès microphone)
- **FFmpeg** — uniquement pour les formats MP3/OGG ([télécharger ici](https://www.gyan.dev/ffmpeg/builds/))

### Installation (Windows)

```powershell
# 1. Cloner le dépôt
git clone https://github.com/FatoumataBarro1207/vocal-signal-processing.git
cd vocal-signal-processing

# 2. Créer et activer l'environnement virtuel
python -m venv venv
venv\Scripts\activate

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Lancer l'application
python app.py
```

Ouvrir dans le navigateur : **http://127.0.0.1:5000**

> 💡 L'application crée automatiquement tous les dossiers nécessaires au premier lancement.

---

## 🗂️ Structure du projet

```
vocal-signal-processing/
│
├── app.py                     # Application Flask — routes & API REST
├── requirements.txt           # Dépendances Python
│
├── modules/
│   ├── recorder.py            # Réception blob audio → sauvegarde WAV
│   ├── segmenter.py           # Détection silences (RMS) → segments
│   └── fft_filter.py         # FFT · masque H(f) · IFFT · graphiques
│
├── templates/
│   ├── base.html              # Layout commun (navbar, footer, toasts)
│   ├── index.html             # Page d'accueil
│   ├── partie1.html           # Interface Numérisation / Segmentation
│   └── partie2.html           # Interface FFT / Filtrage
│
├── static/
│   ├── css/style.css          # Thème clair/beige — design dashboard
│   └── js/
│       ├── utils.js           # Fonctions partagées (toast, formatTime)
│       ├── partie1.js         # Web Audio API, MediaRecorder, segmentation
│       └── partie2.js         # Upload, FFT, filtrage, comparaison
│
└── database/                  # Créé automatiquement au premier lancement
    └── locuteur_XX/
        └── session_XX/
            └── enreg_001_44kHz_16b.wav
```

---

## 🔬 Fondements scientifiques

### Théorème de Shannon-Nyquist

La fréquence d'échantillonnage `Fe` doit satisfaire :

```
Fe >= 2 x f_max
```

| Fe choisie | Fréquence de Nyquist | Application |
|-----------|---------------------|-------------|
| 16 000 Hz | 8 000 Hz | Téléphonie numérique |
| 22 050 Hz | 11 025 Hz | Radio numérique |
| 44 100 Hz | 22 050 Hz | Audio CD — plage auditive complète |

### Filtre rectangulaire — Contrainte sujet §3.3

Le filtrage est réalisé **exclusivement** par masque fréquentiel rectangulaire :

```
Passe-bande : H(f) = 1   si f_min <= |f| <= f_max  ,  0 sinon
Coupe-bande : H_bar(f) = 1 - H(f)
```

**Implémentation Python :**

```python
# FFT du signal
X = scipy.fft.fft(signal)
freqs = scipy.fft.fftfreq(N, d=1.0/sample_rate)

# Construction du masque rectangulaire
mask = ((np.abs(freqs) >= fmin) & (np.abs(freqs) <= fmax)).astype(float)
# Pour coupe-bande : mask = 1.0 - mask

# Application + reconstruction IFFT
X_filtre = X * mask
signal_filtre = np.real(scipy.fft.ifft(X_filtre))
```

---

## 📦 Dépendances

| Package | Version | Rôle |
|---------|---------|------|
| `flask` | >= 3.0 | Serveur web et routage |
| `numpy` | >= 1.26 | Calculs numériques |
| `scipy` | >= 1.12 | FFT / IFFT |
| `soundfile` | >= 0.12 | Lecture / écriture WAV (PCM_16, PCM_32) |
| `matplotlib` | >= 3.8 | Génération graphiques (mode serveur Agg) |
| `pydub` | >= 0.25 | Conversion formats audio (MP3, OGG vers WAV) |

---

## 🖥️ Aperçu des interfaces

### Partie 1 — Numérisation & Segmentation

- Sélection fréquence (16 / 22 / 44 kHz) et codage (16 / 32 bits)
- Enregistrement microphone avec visualisation waveform en temps réel
- Sauvegarde WAV dans base de données organisée `locuteur/session/fichier`
- Segmentation automatique avec paramètres ajustables (seuil RMS, silence min.)
- Tableau des segments avec lecteur audio et téléchargement

### Partie 2 — FFT & Filtrage

- Upload par drag & drop (WAV, MP3, OGG — conversion automatique)
- Affichage signal temporel x(t) et spectre d'amplitude |X(f)|
- Filtre rectangulaire configurable (fmin, fmax, type passe/coupe-bande)
- Visualisation du masque H(f) en temps réel
- Comparaison avant/après filtrage (spectres + signaux temporels)
- Lecteur audio intégré + export WAV filtré

---

## 👥 Auteurs

**Fatoumata BARRO** & **Mouhamed DRAME**— DIC2 TR, Département de Génie Informatique, ESP/UCAD

> Encadrant : **Dr. Moustapha MBAYE** · Année universitaire 2025–2026

---

## 📚 Références

- Oppenheim A.V. & Schafer R.W., *Discrete-Time Signal Processing*, Pearson, 2010
- [Documentation Flask](https://flask.palletsprojects.com)
- [SciPy FFT Reference](https://docs.scipy.org/doc/scipy/reference/fft.html)
- [Web Audio API — MDN](https://developer.mozilla.org/fr/docs/Web/API/Web_Audio_API)
- Cours TNS — Dr. Moustapha MBAYE, ESP/UCAD, 2025–2026
