"""
Module : recorder.py
Role   : Sauvegarde d'un enregistrement audio recu du navigateur en fichier WAV
         avec la frequence d'echantillonnage et la profondeur de codage choisies.
"""

import os
import io
import numpy as np
import soundfile as sf
from pydub import AudioSegment

# Configurer ffmpeg pour Windows
_FFMPEG_CANDIDATES = [
    r"C:\Users\lenovo\Downloads\ffmpeg-8.1-essentials_build\ffmpeg-8.1-essentials_build\bin\ffmpeg.exe",
    r"C:\ffmpeg\bin\ffmpeg.exe",
    r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
]
for _p in _FFMPEG_CANDIDATES:
    if os.path.isfile(_p):
        AudioSegment.converter = _p
        break


def _next_index(session_dir: str) -> str:
    """
    Calcule le prochain indice d'enregistrement dans un repertoire de session.

    Parametre :
        session_dir : str – chemin du repertoire de session

    Retourne :
        str – indice formate sur 3 chiffres, ex. '003'
    """
    existing = [f for f in os.listdir(session_dir) if f.endswith(".wav")]
    return str(len(existing) + 1).zfill(3)


def save_audio(
    audio_bytes: bytes,
    sample_rate: int,
    bit_depth: int,
    locuteur: str,
    session: str,
    database_dir: str,
) -> tuple:
    """
    Sauvegarde un enregistrement audio (blob binaire du navigateur) en fichier WAV.

    Essaie plusieurs methodes de decodage dans l'ordre :
    1. pydub avec detection automatique du format
    2. soundfile direct (si le format est supporté)
    3. Sauvegarde brute des bytes

    Parametres :
        audio_bytes  : bytes – donnees brutes audio (WebM/OGG/MP4 du navigateur)
        sample_rate  : int   – frequence d'echantillonnage cible
        bit_depth    : int   – profondeur de codage cible (16 ou 32)
        locuteur     : str   – identifiant du locuteur
        session      : str   – identifiant de session
        database_dir : str   – repertoire racine de la base de donnees

    Retourne :
        tuple (filepath_relatif: str, filename: str)
    """
    # Creation de l'arborescence
    session_dir = os.path.join(database_dir, locuteur, session)
    os.makedirs(session_dir, exist_ok=True)

    idx = _next_index(session_dir)
    sr_label  = {16000: "16kHz", 22050: "22kHz", 44100: "44kHz"}.get(sample_rate, f"{sample_rate}Hz")
    subtype   = {16: "PCM_16", 32: "PCM_32"}.get(bit_depth, "PCM_16")
    filename  = f"enreg_{idx}_{sr_label}_{bit_depth}b.wav"
    filepath  = os.path.join(session_dir, filename)

    # Methode 1 : pydub (supporte WebM, OGG, MP4, WAV...)
    samples = None
    try:
        audio_segment = AudioSegment.from_file(io.BytesIO(audio_bytes))
        audio_segment = audio_segment.set_frame_rate(sample_rate).set_channels(1)
        raw = np.array(audio_segment.get_array_of_samples(), dtype=np.float32)
        max_val = float(2 ** (audio_segment.sample_width * 8 - 1))
        samples = raw / max_val
        print(f"[Recorder] pydub OK – {len(samples)} samples, sr={sample_rate}")
    except Exception as e1:
        print(f"[Recorder] pydub echec : {e1}")

        # Methode 2 : soundfile direct
        try:
            samples, sr_orig = sf.read(io.BytesIO(audio_bytes), dtype="float32")
            if samples.ndim > 1:
                samples = samples.mean(axis=1)
            # Pas de reeechantillonnage ici (scipy.signal.resample pourrait l'être)
            print(f"[Recorder] soundfile OK – sr={sr_orig}")
        except Exception as e2:
            print(f"[Recorder] soundfile echec : {e2}")

            # Methode 3 : sauvegarder en brut puis relire
            try:
                tmp_path = filepath.replace(".wav", "_raw.bin")
                with open(tmp_path, "wb") as f:
                    f.write(audio_bytes)
                samples, _ = sf.read(tmp_path, dtype="float32")
                if samples.ndim > 1:
                    samples = samples.mean(axis=1)
                os.remove(tmp_path)
                print(f"[Recorder] methode brute OK")
            except Exception as e3:
                raise RuntimeError(
                    f"Impossible de decoder l'audio. "
                    f"pydub: {e1} | soundfile: {e2} | brut: {e3}"
                )

    # Sauvegarde WAV
    sf.write(filepath, samples, sample_rate, subtype=subtype)
    print(f"[Recorder] Sauvegarde OK : {filepath}")

    rel_path = os.path.join(locuteur, session, filename).replace("\\", "/")
    return rel_path, filename