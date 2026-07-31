"""
ON3RT Radio Suite
libraries/voice/engines.py

Moteurs de synthèse vocale — contrat commun minimal, duck-type, aucun
héritage imposé :
    name: str
    is_available() -> bool
    synthesize(text, params: VoiceParams, output_path: Path) -> None   # écrit un WAV

Pyttsx3Engine est le seul moteur de cette étape (4b) — toujours
disponible en pratique sous Windows (SAPI5 fait partie de l'OS).
L'ajout d'un futur moteur (XTTS, étape ultérieure) suit ce même
contrat, sans jamais toucher à VoiceService.synthesize().

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
