"""
Application Flask – Traitement Numérique du Signal Vocal
ESP/UCAD – DIC2 – 2025-2026
Auteur : Fatoumata Barro
"""

import os
import sys
import json
import numpy as np

# ─────────────────────────────────────────────
# Configuration FFmpeg pour pydub (Windows)
# Ajuste ce chemin si besoin selon ton installation
# ─────────────────────────────────────────────
FFMPEG_CANDIDATES = [
    r"C:\Users\lenovo\Downloads\ffmpeg-8.1-essentials_build\ffmpeg-8.1-essentials_build\bin\ffmpeg.exe",
    r"C:\ffmpeg\bin\ffmpeg.exe",
    r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
]

def _configure_ffmpeg():
    """Détecte et configure automatiquement le chemin de ffmpeg pour pydub."""
    for path in FFMPEG_CANDIDATES:
        if os.path.isfile(path):
            try:
                from pydub import AudioSegment
                AudioSegment.converter = path
                ffmpeg_dir = os.path.dirname(path)
                if ffmpeg_dir not in os.environ.get("PATH", ""):
                    os.environ["PATH"] += os.pathsep + ffmpeg_dir
                print(f"[FFmpeg] Trouvé : {path}")
                return True
            except Exception as e:
                print(f"[FFmpeg] Erreur config : {e}")
    print("[FFmpeg] Non trouvé dans les chemins connus. Seuls les WAV seront supportés.")
    return False

_configure_ffmpeg()
from flask import Flask, render_template, request, jsonify, send_file
from modules.recorder import save_audio
from modules.segmenter import segment_audio
from modules.fft_filter import (
    load_and_convert_audio,
    compute_fft,
    apply_rectangular_filter,
    reconstruct_signal,
    generate_plots,
)

# ─────────────────────────────────────────────
# Configuration de l'application
# ─────────────────────────────────────────────
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB max upload

BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
DATABASE_DIR  = os.path.join(BASE_DIR, "database")
SEGMENTS_DIR  = os.path.join(BASE_DIR, "static", "segments")
UPLOAD_DIR    = os.path.join(BASE_DIR, "static", "uploads")
PLOTS_DIR     = os.path.join(BASE_DIR, "static", "plots")
FILTERED_DIR  = os.path.join(BASE_DIR, "static", "filtered")

for d in [DATABASE_DIR, SEGMENTS_DIR, UPLOAD_DIR, PLOTS_DIR, FILTERED_DIR]:
    os.makedirs(d, exist_ok=True)

# Valeurs autorisées (contrainte du sujet)
ALLOWED_SAMPLE_RATES = [16000, 22050, 44100]
ALLOWED_BIT_DEPTHS   = [16, 32]


# ─────────────────────────────────────────────
# Routes principales
# ─────────────────────────────────────────────

@app.route("/")
def index():
    """Page d'accueil – redirige vers la partie 1."""
    return render_template("index.html")


@app.route("/partie1")
def partie1():
    """Interface Partie 1 : Numérisation et Segmentation."""
    return render_template("partie1.html")


@app.route("/partie2")
def partie2():
    """Interface Partie 2 : Analyse FFT et Filtrage."""
    return render_template("partie2.html")


# ─────────────────────────────────────────────
# API – Partie 1 : Enregistrement
# ─────────────────────────────────────────────

@app.route("/api/save_audio", methods=["POST"])
def api_save_audio():
    """
    Reçoit un blob audio du navigateur et le sauvegarde en WAV.

    Paramètres JSON attendus :
        audio_data  : blob binaire (multipart)
        sample_rate : int  – fréquence d'échantillonnage
        bit_depth   : int  – profondeur de codage
        locuteur    : str  – identifiant du locuteur
        session     : str  – identifiant de session

    Retourne :
        JSON { success, filepath, filename }
    """
    try:
        # Validation des paramètres
        sample_rate = int(request.form.get("sample_rate", 0))
        bit_depth   = int(request.form.get("bit_depth", 0))
        locuteur    = request.form.get("locuteur", "locuteur_01").strip()
        session     = request.form.get("session",  "session_01").strip()

        if sample_rate not in ALLOWED_SAMPLE_RATES:
            return jsonify({"success": False,
                            "error": f"Fréquence invalide : {sample_rate} Hz. "
                                     f"Valeurs autorisées : {ALLOWED_SAMPLE_RATES}"}), 400
        if bit_depth not in ALLOWED_BIT_DEPTHS:
            return jsonify({"success": False,
                            "error": f"Codage invalide : {bit_depth} bits. "
                                     f"Valeurs autorisées : {ALLOWED_BIT_DEPTHS}"}), 400

        if "audio" not in request.files:
            return jsonify({"success": False, "error": "Aucun fichier audio reçu."}), 400

        audio_file = request.files["audio"]
        audio_bytes = audio_file.read()

        filepath, filename = save_audio(
            audio_bytes=audio_bytes,
            sample_rate=sample_rate,
            bit_depth=bit_depth,
            locuteur=locuteur,
            session=session,
            database_dir=DATABASE_DIR,
        )

        return jsonify({"success": True, "filepath": filepath, "filename": filename})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/list_recordings", methods=["GET"])
def api_list_recordings():
    """
    Liste tous les enregistrements de la base de données.

    Retourne :
        JSON { success, recordings: [ {locuteur, session, filename, path} ] }
    """
    recordings = []
    try:
        for locuteur in sorted(os.listdir(DATABASE_DIR)):
            loc_path = os.path.join(DATABASE_DIR, locuteur)
            if not os.path.isdir(loc_path):
                continue
            for session in sorted(os.listdir(loc_path)):
                ses_path = os.path.join(loc_path, session)
                if not os.path.isdir(ses_path):
                    continue
                for fname in sorted(os.listdir(ses_path)):
                    if fname.endswith(".wav"):
                        recordings.append({
                            "locuteur": locuteur,
                            "session":  session,
                            "filename": fname,
                            "path":     os.path.join(locuteur, session, fname),
                        })
        return jsonify({"success": True, "recordings": recordings})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ─────────────────────────────────────────────
# API – Partie 1 : Segmentation
# ─────────────────────────────────────────────

@app.route("/api/segment", methods=["POST"])
def api_segment():
    """
    Segmente un fichier WAV en retirant les silences.

    Paramètres JSON :
        filepath        : str   – chemin relatif dans database/
        threshold       : float – seuil d'amplitude (0.0 – 1.0)
        min_silence_ms  : int   – durée minimale de silence (ms)

    Retourne :
        JSON { success, segments: [ {filename, duration, url} ] }
    """
    try:
        data           = request.get_json()
        rel_path       = data.get("filepath", "")
        threshold      = float(data.get("threshold", 0.02))
        min_silence_ms = int(data.get("min_silence_ms", 300))

        full_path = os.path.join(DATABASE_DIR, rel_path)
        if not os.path.exists(full_path):
            return jsonify({"success": False, "error": "Fichier introuvable."}), 404

        segments = segment_audio(
            filepath=full_path,
            threshold=threshold,
            min_silence_ms=min_silence_ms,
            output_dir=SEGMENTS_DIR,
        )

        return jsonify({"success": True, "segments": segments})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/download_segment/<filename>")
def download_segment(filename):
    """Télécharge un segment audio."""
    path = os.path.join(SEGMENTS_DIR, filename)
    if not os.path.exists(path):
        return jsonify({"error": "Fichier introuvable"}), 404
    return send_file(path, as_attachment=True)


# ─────────────────────────────────────────────
# API – Partie 2 : FFT & Filtrage
# ─────────────────────────────────────────────

@app.route("/api/upload_audio", methods=["POST"])
def api_upload_audio():
    """
    Reçoit un fichier audio (WAV, MP3, OGG…), le convertit en WAV si besoin,
    calcule la FFT et retourne les données pour affichage.

    Retourne :
        JSON {
            success,
            filename,
            sample_rate,
            duration,
            time_data    : liste de temps (s),
            amplitude    : liste d'amplitudes,
            freqs        : liste de fréquences (Hz),
            fft_magnitude: liste de magnitudes FFT,
            plot_time    : chemin image signal temporel,
            plot_fft     : chemin image spectre FFT
        }
    """
    try:
        if "audio" not in request.files:
            return jsonify({"success": False, "error": "Aucun fichier reçu."}), 400

        audio_file  = request.files["audio"]
        filename    = audio_file.filename
        upload_path = os.path.join(UPLOAD_DIR, filename)
        audio_file.save(upload_path)

        # Chargement + conversion WAV si nécessaire
        wav_path, sample_rate, signal = load_and_convert_audio(upload_path, UPLOAD_DIR)

        # Calcul FFT
        freqs, fft_magnitude = compute_fft(signal, sample_rate)

        # Génération des graphiques
        plot_time_path, plot_fft_path = generate_plots(
            signal, sample_rate, freqs, fft_magnitude,
            prefix="original", output_dir=PLOTS_DIR
        )

        duration  = len(signal) / sample_rate
        time_data = np.linspace(0, duration, num=min(len(signal), 5000)).tolist()
        amp_data  = signal[::max(1, len(signal)//5000)].tolist()

        # On envoie un sous-échantillon pour l'affichage JS
        n_display = 2000
        step_f    = max(1, len(freqs) // n_display)

        return jsonify({
            "success":       True,
            "filename":      os.path.basename(wav_path),
            "wav_path":      wav_path.replace(BASE_DIR, "").replace("\\", "/"),
            "sample_rate":   int(sample_rate),
            "duration":      round(duration, 3),
            "time_data":     time_data[:n_display],
            "amplitude":     amp_data[:n_display],
            "freqs":         freqs[::step_f].tolist(),
            "fft_magnitude": fft_magnitude[::step_f].tolist(),
            "plot_time":     "/" + plot_time_path.replace(BASE_DIR + os.sep, "").replace("\\", "/"),
            "plot_fft":      "/" + plot_fft_path.replace(BASE_DIR + os.sep, "").replace("\\", "/"),
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/filter_audio", methods=["POST"])
def api_filter_audio():
    """
    Applique un filtre rectangulaire (passe-bande ou coupe-bande) sur le signal.

    Paramètres JSON :
        filename    : str   – nom du fichier WAV uploadé
        fmin        : float – borne inférieure du filtre (Hz)
        fmax        : float – borne supérieure du filtre (Hz)
        filter_type : str   – 'passband' ou 'stopband'

    Retourne :
        JSON {
            success,
            filtered_filename,
            plot_comparison,
            freqs_filtered, fft_filtered,
            time_filtered, amp_filtered
        }
    """
    try:
        data        = request.get_json()
        filename    = data.get("filename")
        fmin        = float(data.get("fmin", 0))
        fmax        = float(data.get("fmax", 8000))
        filter_type = data.get("filter_type", "passband")

        wav_path = os.path.join(UPLOAD_DIR, filename)
        if not os.path.exists(wav_path):
            return jsonify({"success": False, "error": "Fichier source introuvable."}), 404

        # Chargement
        _, sample_rate, signal = load_and_convert_audio(wav_path, UPLOAD_DIR)
        nyquist = sample_rate / 2.0

        if fmin < 0 or fmax > nyquist or fmin >= fmax:
            return jsonify({
                "success": False,
                "error": f"Bornes invalides. fmin doit être ≥ 0, fmax ≤ {nyquist} Hz, fmin < fmax."
            }), 400

        # Application du masque rectangulaire
        freqs, fft_mag_orig, filtered_signal, freqs_f, fft_mag_filtered = apply_rectangular_filter(
            signal, sample_rate, fmin, fmax, filter_type
        )

        # Sauvegarde du fichier filtré
        filtered_filename = f"filtered_{os.path.splitext(filename)[0]}_{filter_type}_{int(fmin)}-{int(fmax)}Hz.wav"
        filtered_path     = os.path.join(FILTERED_DIR, filtered_filename)
        reconstruct_signal(filtered_signal, sample_rate, filtered_path)

        # Graphiques comparatifs
        _, plot_fft_after = generate_plots(
            filtered_signal, sample_rate, freqs_f, fft_mag_filtered,
            prefix="filtered", output_dir=PLOTS_DIR
        )

        n = 2000
        step_f = max(1, len(freqs_f) // n)
        duration_f = len(filtered_signal) / sample_rate
        time_f     = np.linspace(0, duration_f, num=min(len(filtered_signal), n)).tolist()
        amp_f      = filtered_signal[::max(1, len(filtered_signal)//n)].tolist()

        return jsonify({
            "success":           True,
            "filtered_filename": filtered_filename,
            "filtered_url":      f"/static/filtered/{filtered_filename}",
            "plot_fft_filtered": "/" + plot_fft_after.replace(BASE_DIR + os.sep, "").replace("\\", "/"),
            "freqs_filtered":    freqs_f[::step_f].tolist(),
            "fft_filtered":      fft_mag_filtered[::step_f].tolist(),
            "time_filtered":     time_f[:n],
            "amp_filtered":      amp_f[:n],
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/download_filtered/<filename>")
def download_filtered(filename):
    """Télécharge le signal filtré."""
    path = os.path.join(FILTERED_DIR, filename)
    if not os.path.exists(path):
        return jsonify({"error": "Fichier introuvable"}), 404
    return send_file(path, as_attachment=True)


# ─────────────────────────────────────────────
# Lancement
# ─────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)