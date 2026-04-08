"""
Module : fft_filter.py
Rôle   : Chargement audio, calcul FFT, application du masque rectangulaire,
         reconstruction IFFT et génération des graphiques.
Auteur : Fatoumata Barro
"""

import os
import numpy as np
import soundfile as sf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.fft import fft, ifft, fftfreq

try:
    from pydub import AudioSegment
    # Chercher ffmpeg automatiquement sur Windows
    _candidates = [
        r"C:\Users\lenovo\Downloads\ffmpeg-8.1-essentials_build\ffmpeg-8.1-essentials_build\bin\ffmpeg.exe",
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
    ]
    for _p in _candidates:
        if os.path.isfile(_p):
            AudioSegment.converter = _p
            break
    PYDUB_AVAILABLE = True
except Exception:
    PYDUB_AVAILABLE = False

DARK_BG     = "#FAF8F5"
GRID_COLOR  = "#DDD8CE"
LINE_COLOR  = "#6D28D9"
LINE2_COLOR = "#0891B2"
TEXT_COLOR  = "#1C1917"


def _setup_dark_axes(ax, title, xlabel, ylabel):
    ax.set_facecolor(DARK_BG)
    ax.set_title(title, color=TEXT_COLOR, fontsize=11, fontweight="bold", pad=10)
    ax.set_xlabel(xlabel, color=TEXT_COLOR, fontsize=9)
    ax.set_ylabel(ylabel, color=TEXT_COLOR, fontsize=9)
    ax.tick_params(colors=TEXT_COLOR, labelsize=8)
    ax.spines[:].set_color(GRID_COLOR)
    ax.grid(True, color=GRID_COLOR, linestyle="--", linewidth=0.5, alpha=0.7)
    for spine in ax.spines.values():
        spine.set_edgecolor(GRID_COLOR)


def load_and_convert_audio(filepath: str, output_dir: str):
    """
    Charge un fichier audio et le convertit en WAV mono si nécessaire.

    Paramètres :
        filepath   : str – chemin du fichier source (WAV, MP3, OGG…)
        output_dir : str – dossier de sortie pour le WAV converti

    Retourne :
        tuple (wav_path: str, sample_rate: int, signal: np.ndarray)
    """
    os.makedirs(output_dir, exist_ok=True)
    ext = os.path.splitext(filepath)[1].lower()
    wav_path = filepath

    if ext != ".wav":
        wav_name = os.path.splitext(os.path.basename(filepath))[0] + "_converted.wav"
        wav_path = os.path.join(output_dir, wav_name)
        if PYDUB_AVAILABLE:
            try:
                audio = AudioSegment.from_file(filepath)
                audio = audio.set_channels(1)
                audio.export(wav_path, format="wav")
            except Exception as e:
                raise RuntimeError(f"Conversion impossible : {e}. Installez FFmpeg.")
        else:
            raise RuntimeError("pydub non disponible. Utilisez un fichier WAV.")

    signal, sample_rate = sf.read(wav_path, dtype="float32")
    if signal.ndim > 1:
        signal = signal.mean(axis=1)

    return wav_path, int(sample_rate), signal


def compute_fft(signal: np.ndarray, sample_rate: int):
    """
    Calcule la FFT du signal et retourne le spectre unilatéral.

    Paramètres :
        signal      : np.ndarray – signal temporel
        sample_rate : int        – fréquence d'échantillonnage (Hz)

    Retourne :
        tuple (freqs: np.ndarray, magnitude: np.ndarray)
    """
    N      = len(signal)
    X      = fft(signal)
    freqs  = fftfreq(N, d=1.0 / sample_rate)
    half_N = N // 2
    return freqs[:half_N], (2.0 / N) * np.abs(X[:half_N])


def apply_rectangular_filter(signal, sample_rate, fmin, fmax, filter_type):
    """
    Applique un masque rectangulaire H(f) sur le spectre FFT du signal.

    Masque (sujet §3.3) :
        Passe-bande : H(f) = 1 si fmin <= |f| <= fmax, 0 sinon
        Coupe-bande : H_bar(f) = 1 - H(f)

    Paramètres :
        signal      : np.ndarray – signal temporel
        sample_rate : int        – fréquence d'échantillonnage
        fmin        : float      – borne basse (Hz)
        fmax        : float      – borne haute (Hz)
        filter_type : str        – 'passband' ou 'stopband'

    Retourne :
        tuple (freqs_pos, mag_orig, filtered_signal, freqs_pos, mag_filtered)
    """
    N     = len(signal)
    X     = fft(signal)
    freqs = fftfreq(N, d=1.0 / sample_rate)
    abs_f = np.abs(freqs)

    if filter_type == "passband":
        mask = ((abs_f >= fmin) & (abs_f <= fmax)).astype(float)
    else:
        mask = 1.0 - ((abs_f >= fmin) & (abs_f <= fmax)).astype(float)

    X_filtered      = X * mask
    filtered_signal = np.real(ifft(X_filtered)).astype(np.float32)

    half_N       = N // 2
    freqs_pos    = freqs[:half_N]
    mag_orig     = (2.0 / N) * np.abs(X[:half_N])
    mag_filtered = (2.0 / N) * np.abs(X_filtered[:half_N])

    return freqs_pos, mag_orig, filtered_signal, freqs_pos, mag_filtered


def generate_plots(signal, sample_rate, freqs, fft_magnitude, prefix, output_dir):
    """
    Génère les graphiques dark mode du signal temporel et du spectre FFT.

    Paramètres :
        signal        : np.ndarray – signal temporel
        sample_rate   : int        – fréquence d'échantillonnage
        freqs         : np.ndarray – fréquences (Hz)
        fft_magnitude : np.ndarray – magnitudes FFT
        prefix        : str        – 'original' ou 'filtered'
        output_dir    : str        – dossier de sortie

    Retourne :
        tuple (plot_time_path: str, plot_fft_path: str)
    """
    os.makedirs(output_dir, exist_ok=True)
    duration  = len(signal) / sample_rate
    time_axis = np.linspace(0, duration, num=len(signal))

    fig_t, ax_t = plt.subplots(figsize=(10, 3), facecolor=DARK_BG)
    ax_t.plot(time_axis, signal, color=LINE_COLOR, linewidth=0.6, alpha=0.9)
    _setup_dark_axes(ax_t, f"Signal temporel ({prefix})", "Temps (s)", "Amplitude")
    ax_t.set_xlim(0, duration)
    fig_t.tight_layout(pad=1.5)
    plot_time_path = os.path.join(output_dir, f"{prefix}_time.png")
    fig_t.savefig(plot_time_path, dpi=120, facecolor=DARK_BG, bbox_inches="tight")
    plt.close(fig_t)

    fig_f, ax_f = plt.subplots(figsize=(10, 3), facecolor=DARK_BG)
    ax_f.plot(freqs, fft_magnitude, color=LINE2_COLOR, linewidth=0.7, alpha=0.9)
    ax_f.fill_between(freqs, fft_magnitude, alpha=0.15, color=LINE2_COLOR)
    _setup_dark_axes(ax_f, f"Spectre FFT – |X(f)| ({prefix})", "Fréquence (Hz)", "Amplitude")
    if len(freqs) > 0:
        ax_f.set_xlim(0, freqs[-1])
    fig_f.tight_layout(pad=1.5)
    plot_fft_path = os.path.join(output_dir, f"{prefix}_fft.png")
    fig_f.savefig(plot_fft_path, dpi=120, facecolor=DARK_BG, bbox_inches="tight")
    plt.close(fig_f)

    return plot_time_path, plot_fft_path


def reconstruct_signal(signal: np.ndarray, sample_rate: int, output_path: str) -> None:
    """
    Sauvegarde un signal numpy en fichier WAV PCM 16 bits.

    Paramètres :
        signal      : np.ndarray – signal filtré (float32)
        sample_rate : int        – fréquence d'échantillonnage
        output_path : str        – chemin du fichier WAV de sortie
    """
    sf.write(output_path, np.clip(signal, -1.0, 1.0), sample_rate, subtype="PCM_16")