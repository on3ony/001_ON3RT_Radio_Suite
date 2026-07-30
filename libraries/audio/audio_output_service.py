"""
ON3RT Radio Suite
libraries/audio/audio_output_service.py

Service audio partagé de la Suite : énumère les périphériques de
sortie disponibles et joue des fichiers WAV sur le périphérique
choisi. Aucune dépendance à un module applicatif ni à PTT/CAT — c'est
la première brique de l'infrastructure Voix (architecture validée
avec l'utilisateur : AudioOutputService / VoiceService /
TransmissionService). TransmissionService orchestrera PTT + lecture
audio + sécurité ; les autres sources sonores futures de la Suite
(alertes DX Cluster, propagation, etc.) consommeront ce même service,
jamais une lecture audio dupliquée ailleurs.

Sélection du périphérique : mémorisée par NOM, jamais par index — les
index sounddevice/PortAudio ne sont pas stables d'une session à
l'autre (un périphérique débranché/rebranché, ou l'ajout d'un autre
périphérique, réordonne la liste). Le nom est résolu vers un index
réel à chaque lecture, jamais mis en cache.

Un même périphérique physique apparaît généralement plusieurs fois sur
Windows, une entrée par API audio (MME, DirectSound, WASAPI, WDM-KS) —
confirmé avec le matériel réel de l'utilisateur (IC-7300 en USB Audio
CODEC, visible 3 fois : MME et DirectSound à 44100 Hz, WASAPI à
48000 Hz). Quand plusieurs entrées partagent le même nom, WASAPI est
préférée (API Windows moderne, latence plus faible) ; sans entrée
WASAPI, la première trouvée.

Ré-échantillonnage : mesuré sur le matériel réel, l'entrée WASAPI d'un
périphérique refuse tout débit différent de son débit natif (mode
partagé) — jouer un WAV à 44100 Hz dessus alors qu'elle exige 48000 Hz
échoue avec PaErrorCode -9997 "Invalid sample rate". MME/DirectSound,
elles, rééchantillonnent en silence via le mixeur Windows. Plutôt que
de dépendre d'un comportement implicite qui varie selon l'API retenue,
ce service ré-échantillonne lui-même (interpolation linéaire simple,
libraries/audio/audio_output_service.py::_resample_linear — aucune
dépendance supplémentaire type scipy) chaque fois que le débit du
fichier ne correspond pas à celui du périphérique choisi. Suffisant
pour de la voix/phonie ; pas pensé pour un usage audiophile.

Lecture non bloquante : sounddevice.play() démarre la lecture sur un
flux PortAudio interne et rend la main immédiatement (aucun
sounddevice.wait() n'est appelé ici). sounddevice.play() n'accepte pas
de finished_callback ; la fin de lecture est donc détectée par un
QTimer qui interroge périodiquement sounddevice.get_stream().active —
même logique de sondage que RadioService/PropagationService, plutôt
que d'introduire un callback invoqué depuis le thread interne de
PortAudio. Précision de détection : de l'ordre de l'intervalle de
sondage, plus une marge propre au périphérique par défaut observée
lors des essais (~0.6s de queue au-delà de la durée réelle sur le
périphérique par défaut de la machine de développement, cause exacte
non caractérisée) — à affiner si nécessaire au moment de
TransmissionService, où la précision du relâchement du PTT devient
réellement critique ; sans impact pour cette étape.

Format audio : uniquement WAV PCM (8/16/32 bits), lu via le module
standard `wave` + numpy, sans dépendance supplémentaire type
soundfile — suffisant car toute la chaîne Voix prévue (pyttsx3, puis
XTTS en option) produit du WAV.

stop() est un arrêt immédiat et silencieux (n'émet pas
playback_finished) : utilisé aussi bien en interne (annuler une
lecture précédente avant d'en démarrer une nouvelle) que par un futur
bouton STOP ou la sécurité PTT de TransmissionService, qui savent déjà
qu'ils ont eux-mêmes interrompu la lecture.
"""

from __future__ import annotations

import json
import wave
from pathlib import Path

import numpy as np
import sounddevice as sd
from PySide6.QtCore import QObject, QTimer, Signal

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "data" / "audio_output.json"

_PREFERRED_HOSTAPI_SUBSTRING = "WASAPI"
_POLL_INTERVAL_MS = 50

_WAV_DTYPES = {1: np.uint8, 2: np.int16, 4: np.int32}


def _resample_linear(data: np.ndarray, src_rate: float, dst_rate: float) -> np.ndarray:
    """
    Ré-échantillonnage par interpolation linéaire, sans dépendance
    supplémentaire — voir docstring du module pour pourquoi c'est
    nécessaire (mode partagé WASAPI). No-op si les débits correspondent
    déjà.
    """

    if src_rate == dst_rate:
        return data

    n_src = data.shape[0]
    n_dst = int(round(n_src * dst_rate / src_rate))

    x_src = np.linspace(0, 1, n_src, endpoint=False)
    x_dst = np.linspace(0, 1, n_dst, endpoint=False)

    out = np.zeros((n_dst, data.shape[1]), dtype=np.float64)
    for channel in range(data.shape[1]):
        out[:, channel] = np.interp(x_dst, x_src, data[:, channel].astype(np.float64))

    return out.astype(data.dtype)


def _read_wav(path: Path) -> tuple[np.ndarray, int]:
    """Lit un fichier WAV PCM en tableau numpy (frames, canaux) + fréquence d'échantillonnage."""

    with wave.open(str(path), "rb") as f:
        n_channels = f.getnchannels()
        samplerate = f.getframerate()
        sample_width = f.getsampwidth()
        n_frames = f.getnframes()
        raw = f.readframes(n_frames)

    dtype = _WAV_DTYPES.get(sample_width)
    if dtype is None:
        raise wave.Error(f"Largeur d'échantillon WAV non prise en charge : {sample_width * 8} bits")

    data = np.frombuffer(raw, dtype=dtype).reshape(-1, n_channels)

    return data, samplerate


class AudioOutputService(QObject):
    """
    Périphérique de sortie sélectionné et lecture de fichiers WAV. Ne
    connaît rien du PTT ni de la synthèse vocale : TransmissionService
    orchestre ces briques séparément, jamais l'inverse.
    """

    playback_finished = Signal()
    playback_error = Signal(str)

    def __init__(self, config_path=None, parent=None):
        super().__init__(parent)

        self._path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH

        self.device_name: str | None = None

        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(_POLL_INTERVAL_MS)
        self._poll_timer.timeout.connect(self._poll_playback)

        if self._path.exists():
            self.load()

    # ------------------------------------------------------------------
    # Persistance
    # ------------------------------------------------------------------

    def load(self) -> None:
        """
        Charge le périphérique mémorisé. Si le fichier est absent, vide,
        illisible ou mal formé, l'état par défaut (périphérique système)
        est conservé : aucune donnée n'est inventée.
        """

        try:
            raw = self._path.read_text(encoding="utf-8")
            data = json.loads(raw)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return

        if not isinstance(data, dict):
            return

        device_name = data.get("device_name")
        if device_name is None or isinstance(device_name, str):
            self.device_name = device_name

    def save(self) -> None:
        """Écrit l'état courant, en écriture atomique (fichier temporaire puis remplacement)."""

        self._path.parent.mkdir(parents=True, exist_ok=True)

        tmp_path = self._path.with_suffix(".tmp")
        tmp_path.write_text(
            json.dumps({"device_name": self.device_name}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp_path.replace(self._path)

    # ------------------------------------------------------------------
    # Périphériques
    # ------------------------------------------------------------------

    @staticmethod
    def list_output_devices() -> list[dict]:
        """
        Retourne les périphériques de sortie réels (au moins un canal de
        sortie), avec leur nom, leur API audio et leur nombre de canaux.
        Un même périphérique physique peut apparaître plusieurs fois
        (une entrée par API audio) — voir docstring du module.
        """

        hostapis = sd.query_hostapis()
        devices = []

        for device in sd.query_devices():
            if device["max_output_channels"] <= 0:
                continue

            devices.append({
                "name": device["name"],
                "hostapi": hostapis[device["hostapi"]]["name"],
                "channels": device["max_output_channels"],
                "default_samplerate": device["default_samplerate"],
            })

        return devices

    def set_output_device(self, name: str | None) -> None:
        """`None` = périphérique système par défaut."""

        self.device_name = name
        self.save()

    def _resolve_device(self) -> tuple[int | None, float | None]:
        """
        Résout self.device_name vers (index, fréquence d'échantillonnage
        par défaut du périphérique), au moment de l'utilisation — jamais
        mis en cache, voir docstring du module. (None, None) = nom non
        défini ou introuvable, sounddevice utilisera alors le
        périphérique système par défaut sans ré-échantillonnage forcé.
        """

        if self.device_name is None:
            return None, None

        hostapis = sd.query_hostapis()
        candidates = [
            (index, device)
            for index, device in enumerate(sd.query_devices())
            if device["name"] == self.device_name and device["max_output_channels"] > 0
        ]

        if not candidates:
            return None, None

        for index, device in candidates:
            if _PREFERRED_HOSTAPI_SUBSTRING in hostapis[device["hostapi"]]["name"]:
                return index, device["default_samplerate"]

        index, device = candidates[0]
        return index, device["default_samplerate"]

    # ------------------------------------------------------------------
    # Lecture
    # ------------------------------------------------------------------

    def is_playing(self) -> bool:
        stream = sd.get_stream()
        return stream is not None and stream.active

    def play_file(self, path) -> None:
        """
        Charge un fichier WAV PCM et le joue sur le périphérique
        sélectionné, sans bloquer. Émet playback_finished à la fin de
        la lecture, ou playback_error si le fichier est illisible ou si
        l'ouverture du flux audio échoue. Une lecture déjà en cours est
        arrêtée avant de démarrer la nouvelle (jamais deux lectures
        superposées).
        """

        self.stop()

        try:
            data, samplerate = _read_wav(Path(path))
        except (OSError, wave.Error) as exc:
            self.playback_error.emit(str(exc))
            return

        device_index, device_samplerate = self._resolve_device()

        if device_samplerate is not None:
            data = _resample_linear(data, samplerate, device_samplerate)
            samplerate = device_samplerate

        try:
            sd.play(data, samplerate, device=device_index)
        except sd.PortAudioError as exc:
            self.playback_error.emit(str(exc))
            return

        self._poll_timer.start()

    def stop(self) -> None:
        """Arrête immédiatement toute lecture en cours — voir docstring du module."""

        self._poll_timer.stop()
        sd.stop()

    def _poll_playback(self) -> None:
        if not self.is_playing():
            self._poll_timer.stop()
            self.playback_finished.emit()
