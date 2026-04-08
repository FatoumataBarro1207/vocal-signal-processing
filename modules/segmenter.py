"""
Module : segmenter.py
Rôle   : Segmentation automatique d'un fichier WAV en détectant les silences
         et en découpant le signal en segments vocaux utiles.
"""

import os
import numpy as np
import soundfile as sf


def detect_voice_segments(
    signal: np.ndarray,
    sample_rate: int,
    threshold: float,
    min_silence_ms: int,
) -> list[tuple[int, int]]:
    """
    Détecte les segments vocaux dans un signal audio en identifiant les silences.

    Algorithme :
        1. Calcul de l'énergie locale par fenêtre.
        2. Classification de chaque fenêtre : silence (énergie < seuil) ou voix.
        3. Fusion des segments vocaux séparés par des silences courts.
        4. Renvoi des indices de début/fin de chaque segment vocal.

    Paramètres :
        signal         : np.ndarray – signal audio normalisé [-1, 1]
        sample_rate    : int        – fréquence d'échantillonnage
        threshold      : float      – seuil d'amplitude (0.0 – 1.0)
        min_silence_ms : int        – durée minimale d'un silence réel (ms)

    Retourne :
        list de tuples (start_sample, end_sample)
    """
    min_silence_samples = int(min_silence_ms * sample_rate / 1000)
    frame_size = max(1, min_silence_samples // 4)

    segments    = []
    in_voice    = False
    seg_start   = 0
    silence_len = 0

    i = 0
    while i < len(signal):
        frame = signal[i : i + frame_size]
        energy = np.sqrt(np.mean(frame ** 2))  # RMS de la fenêtre

        if energy >= threshold:
            if not in_voice:
                seg_start = i
                in_voice  = True
            silence_len = 0
        else:
            if in_voice:
                silence_len += frame_size
                if silence_len >= min_silence_samples:
                    # Fin du segment vocal
                    end = i - silence_len + frame_size
                    segments.append((seg_start, end))
                    in_voice    = False
                    silence_len = 0

        i += frame_size

    # Dernier segment si le signal se termine en voix
    if in_voice:
        segments.append((seg_start, len(signal)))

    return segments


def segment_audio(
    filepath: str,
    threshold: float,
    min_silence_ms: int,
    output_dir: str,
) -> list[dict]:
    """
    Charge un fichier WAV, détecte les segments vocaux et les sauvegarde.

    Paramètres :
        filepath       : str   – chemin complet du fichier WAV source
        threshold      : float – seuil d'amplitude pour la détection des silences
        min_silence_ms : int   – durée minimale de silence (ms)
        output_dir     : str   – dossier de sortie pour les segments

    Retourne :
        list de dicts { filename, duration, url, start_s, end_s }
    """
    os.makedirs(output_dir, exist_ok=True)

    signal, sample_rate = sf.read(filepath, dtype="float32")

    # Conversion mono si stéréo
    if signal.ndim > 1:
        signal = signal.mean(axis=1)

    # Détection des segments
    voice_segs = detect_voice_segments(signal, sample_rate, threshold, min_silence_ms)

    base_name = os.path.splitext(os.path.basename(filepath))[0]
    results   = []

    for idx, (start, end) in enumerate(voice_segs, start=1):
        chunk    = signal[start:end]
        duration = len(chunk) / sample_rate

        # Ignorer les segments trop courts (< 100 ms)
        if duration < 0.1:
            continue

        seg_name = f"{base_name}_seg{str(idx).zfill(3)}.wav"
        seg_path = os.path.join(output_dir, seg_name)
        sf.write(seg_path, chunk, sample_rate, subtype="PCM_16")

        results.append({
            "filename": seg_name,
            "duration": round(duration, 3),
            "url":      f"/static/segments/{seg_name}",
            "start_s":  round(start / sample_rate, 3),
            "end_s":    round(end   / sample_rate, 3),
        })

    return results