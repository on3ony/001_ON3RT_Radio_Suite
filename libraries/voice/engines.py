"""
ON3RT Radio Suite
libraries/voice/engines.py

Moteurs de synthèse vocale — contrat commun minimal, duck-type, aucun
héritage imposé :
    name: str
    is_available() -> bool
    synthesize(text, params: VoiceParams, output_path: Path) -> None   # écrit un WAV

Pyttsx3Engine (étape 4b) — toujours disponible en pratique sous
Windows (SAPI5 fait partie de l'OS) — et PiperEngine (étape 4f, second
moteur, optionnel) suivent ce même contrat. Un futur moteur (XTTS,
étape ultérieure) suivra le même schéma, sans jamais toucher à
VoiceService.synthesize().

PiperEngine — entièrement optionnel, "auto" ne l'utilise jamais
(params.engine=None reste Pyttsx3Engine) : uniquement sélectionné via
VoiceParams(engine="piper"). Le paquet pip "piper-tts" n'est jamais
importé au niveau du module (voir plus bas, comme pyttsx3 pour
Pyttsx3Engine) : s'il n'est pas installé, is_available() retourne
simplement False, et cette absence ne lève jamais d'exception qui
empêcherait le démarrage de la Suite — même garantie que pour
Pyttsx3Engine.

Modèles de voix : jamais téléchargés automatiquement. is_available()
exige à la fois que le paquet "piper" s'importe ET qu'au moins un
fichier *.onnx soit présent dans data/piper_voices/ — un modèle
manquant doit être installé manuellement là (fichiers .onnx + .onnx.json
appairés, comme produits par "python -m piper.download_voices"), jamais
récupéré silencieusement par le code.

Sélection du modèle : voice_profile nomme directement le modèle
(nom de fichier sans extension, ex. "fr_FR-siwis-medium") ; si absent,
une correspondance par langue par défaut (_DEFAULT_MODEL_BY_LANGUAGE)
sert de repli. Contrairement à Pyttsx3Engine (voix système énumérables
via getProperty("voices")), Piper n'a pas de "voix installées" à
lister : seuls les fichiers présents dans data/piper_voices/ existent.

Mise en cache des modèles chargés (self._voices, par instance de
PiperEngine) : PiperVoice.load() charge un modèle ONNX de plusieurs
dizaines de Mo, contrairement à pyttsx3.init() qui est quasi instantané
— un rechargement à chaque synthèse serait inacceptable en pratique.
Un modèle déjà chargé une fois reste en mémoire pour toute la durée de
vie du moteur (partagé par VoiceService, donc par toute la Suite).

rate/volume : SynthesisConfig.volume (piper) correspond directement à
VoiceParams.volume. VoiceParams.rate n'a PAS de correspondance mappée
(SynthesisConfig.length_scale est un multiplicateur de durée, échelle
et sens différents du "rate" en mots/minute de pyttsx3 -- aucune
conversion naturelle) : ignoré par PiperEngine, comme documenté pour
tout champ VoiceParams non pertinent pour un moteur donné.

Débit par défaut (_DEFAULT_LENGTH_SCALE) : le débit natif de Piper
(length_scale=1.0) a été jugé trop rapide pour une phonie radio
(contest/DX) -- DEFAULT_LENGTH_SCALE=1.25 (25% plus lent) appliqué par
défaut à CHAQUE synthèse Piper, choisi par écoute comparative réelle de
plusieurs échantillons (1.0/1.2/1.25) sur le modèle fr_FR-tom-medium,
puis confirmé sur matériel réel via le bouton "Annoncer" de Contest
Assistant. Non exposé via VoiceParams (voir paragraphe ci-dessus,
aucune correspondance rate->length_scale) : c'est la définition même du
"comportement par défaut du moteur" pour Piper, pas une valeur
demandée par l'appelant.

CoInitialize()/CoUninitialize() : SAPI5 (via pyttsx3/comtypes) repose
sur COM, dont les objets sont liés à l'appartement du thread qui les
crée. VoiceService exécute chaque synthèse sur un thread du
QThreadPool global, potentiellement réutilisé entre plusieurs appels.
Vérifié empiriquement sur la machine de développement : la synthèse
fonctionne même sans initialisation COM explicite sur un thread du
pool — mais l'apartment threading COM est documenté comme fragile
selon le contexte d'exécution (version de pyttsx3/pywin32, ordre des
appels). CoInitialize()/CoUninitialize() explicites autour de chaque
synthèse restent une précaution défensive peu coûteuse, pas la
correction d'un bug observé ici.

Sélection de la voix par langue : pyttsx3 n'a pas de notion FR/EN
directe — chaque voix SAPI5 expose voice.languages (vérifié sur la
machine de développement : ["fr-FR"], déjà en str, pas en bytes, mais
ce champ est documenté ailleurs comme parfois encodé en bytes selon la
version de pyttsx3/pywin32 — décodage défensif ci-dessous).
_find_voice_for_language() cherche la première voix dont un code de
langue commence par le préfixe demandé ("fr"/"en"), sans jamais
supposer un identifiant de voix fixe (les identifiants SAPI5 varient
d'une machine à l'autre — vérifié : "HKEY_LOCAL_MACHINE\\...\\TTS_MS_FR-FR_HORTENSE_11.0"
sur la machine de développement, une chaîne opaque propre à cette
installation Windows).
"""

from __future__ import annotations

from pathlib import Path

from libraries.voice.voice_params import VoiceParams


class Pyttsx3Engine:

    name = "pyttsx3"

    @staticmethod
    def is_available() -> bool:
        try:
            import pyttsx3  # noqa: F401
        except ImportError:
            return False
        return True

    def synthesize(self, text: str, params: VoiceParams, output_path: Path) -> None:
        import pyttsx3

        try:
            import pythoncom
        except ImportError:
            pythoncom = None

        if pythoncom is not None:
            pythoncom.CoInitialize()

        try:
            engine = pyttsx3.init()

            if params.rate is not None:
                engine.setProperty("rate", params.rate)
            if params.volume is not None:
                engine.setProperty("volume", params.volume)

            voice_id = _find_voice_for_language(engine, params.language)
            if voice_id is not None:
                engine.setProperty("voice", voice_id)

            output_path.parent.mkdir(parents=True, exist_ok=True)

            engine.save_to_file(text, str(output_path))
            engine.runAndWait()
        finally:
            if pythoncom is not None:
                pythoncom.CoUninitialize()


def _find_voice_for_language(engine, language: str) -> str | None:
    prefix = (language or "").strip().lower()[:2]
    if not prefix:
        return None

    for voice in engine.getProperty("voices"):
        for lang_code in getattr(voice, "languages", None) or []:
            if isinstance(lang_code, bytes):
                lang_code = lang_code.decode("utf-8", errors="ignore")
            if str(lang_code).strip().lower().startswith(prefix):
                return voice.id

    return None


DEFAULT_PIPER_VOICES_DIR = Path(__file__).resolve().parents[2] / "data" / "piper_voices"

# Modele par defaut si voice_profile n'est pas fourni -- voir docstring
# du module. Prefixe de langue (2 lettres), meme convention que
# _find_voice_for_language ci-dessus.
_DEFAULT_MODEL_BY_LANGUAGE = {
    "fr": "fr_FR-siwis-medium",
    "en": "en_US-lessac-medium",
}

# Debit par defaut de Piper (voir docstring du module) -- choisi par
# ecoute comparative reelle (1.0/1.2/1.25) puis confirme sur materiel
# reel, jamais expose via VoiceParams.rate.
_DEFAULT_LENGTH_SCALE = 1.25


class PiperEngine:
    """Second moteur de VoiceService (étape 4f), optionnel — voir docstring du module pour l'ensemble des garanties."""

    name = "piper"

    def __init__(self, voices_dir: Path | None = None):
        self._voices_dir = Path(voices_dir) if voices_dir else DEFAULT_PIPER_VOICES_DIR

        # Modeles ONNX deja charges (PiperVoice), par chemin de modele
        # -- voir docstring du module, section "Mise en cache".
        self._voices: dict[str, "PiperVoice"] = {}

    def is_available(self) -> bool:
        try:
            import piper  # noqa: F401
        except ImportError:
            return False

        if not self._voices_dir.is_dir():
            return False

        return any(self._voices_dir.glob("*.onnx"))

    def synthesize(self, text: str, params: VoiceParams, output_path: Path) -> None:
        import wave

        from piper import PiperVoice, SynthesisConfig

        model_path = self._resolve_model_path(params)

        voice = self._voices.get(str(model_path))
        if voice is None:
            voice = PiperVoice.load(str(model_path))
            self._voices[str(model_path)] = voice

        if params.volume is not None:
            syn_config = SynthesisConfig(length_scale=_DEFAULT_LENGTH_SCALE, volume=params.volume)
        else:
            syn_config = SynthesisConfig(length_scale=_DEFAULT_LENGTH_SCALE)

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with wave.open(str(output_path), "wb") as wav_file:
            voice.synthesize_wav(text, wav_file, syn_config=syn_config)

    def _resolve_model_path(self, params: VoiceParams) -> Path:
        """
        voice_profile nomme directement le modèle (nom de fichier sans
        extension) ; sinon, repli sur _DEFAULT_MODEL_BY_LANGUAGE. Aucun
        téléchargement : le modèle doit déjà exister dans
        data/piper_voices/, installé manuellement — voir docstring du
        module.
        """

        prefix = (params.language or "").strip().lower()[:2]
        profile = params.voice_profile or _DEFAULT_MODEL_BY_LANGUAGE.get(prefix)

        if not profile:
            raise ValueError(
                f"Aucun modele Piper par defaut pour la langue '{params.language}' et aucun "
                "voice_profile fourni -- preciser VoiceParams(voice_profile=...)."
            )

        model_path = self._voices_dir / f"{profile}.onnx"

        if not model_path.exists():
            raise FileNotFoundError(
                f"Modele Piper introuvable : {model_path} -- a installer manuellement dans "
                f"{self._voices_dir} (jamais telecharge automatiquement par la Suite)."
            )

        return model_path
