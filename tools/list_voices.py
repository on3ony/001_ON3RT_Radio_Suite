#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
tools/list_voices.py
-------------------------------------------------
ON3RT Radio Suite - Diagnostic des voix pyttsx3 disponibles

Outil de diagnostic autonome, SANS dependance a libraries/voice/* :
liste directement les voix installees telles que pyttsx3 les expose
(SAPI5 sous Windows), independamment de la logique de selection de
VoiceService/Pyttsx3Engine (_find_voice_for_language, voir
libraries/voice/engines.py) -- utile pour explorer TOUTES les voix
presentes sur la machine, y compris celles que la Suite ne
selectionnerait jamais automatiquement aujourd'hui (aucune langue
FR/EN ne matche, par exemple).

Ne modifie et ne cree aucun autre fichier du projet : lecture seule,
aucune ecriture sur disque. Le test optionnel (--test/--voice) parle
directement a travers le peripherique audio par defaut de pyttsx3
(engine.say()/runAndWait()), sans jamais passer par AudioOutputService
ni ecrire de fichier WAV -- diagnostic pyttsx3 pur, pas un test de la
chaine VoiceService.

age/genre : SAPI5 (le seul moteur de la Suite a ce jour) ne fournit ces
deux attributs de facon fiable -- souvent None selon la voix installee.
Affiches "inconnu" quand pyttsx3 ne les fournit pas, jamais devines.

CoInitialize()/CoUninitialize() : meme precaution defensive peu
couteuse que libraries/voice/engines.py (Pyttsx3Engine), pour la meme
raison (voir sa docstring) -- ce script tourne sur le thread principal
(pas de QThreadPool ici), donc moins expose, mais la precaution ne
coute rien.

Les messages affiches a l'ecran evitent volontairement les caracteres
accentues -- meme convention que les scripts validate_*.py de ce
depot (mojibake possible sur certaines pages de code Windows).

Usage :
    python tools/list_voices.py
    python tools/list_voices.py --test "Bonjour, ceci est un test." --voice 2

--voice accepte soit un index (position affichee dans la liste,
a partir de 0), soit un identifiant de voix litteral (id SAPI5 complet,
tel qu'affiche dans la colonne "id" de la liste).
"""

from __future__ import annotations

import argparse


def _decode_language(raw) -> str:
    """Meme decodage defensif que engines.py::_find_voice_for_language -- languages peut etre bytes selon la version pyttsx3/pywin32."""

    if isinstance(raw, bytes):
        return raw.decode("utf-8", errors="ignore")
    return str(raw)


def _format_languages(languages) -> str:
    if not languages:
        return "inconnu"

    decoded = [_decode_language(lang) for lang in languages]
    return ", ".join(decoded) if decoded else "inconnu"


def _format_optional(value) -> str:
    return str(value) if value not in (None, "") else "inconnu"


def _list_voices(engine) -> list:
    return engine.getProperty("voices") or []


def _print_voice_table(engine) -> None:
    voices = _list_voices(engine)
    current_id = engine.getProperty("voice")

    if not voices:
        print("Aucune voix trouvee via pyttsx3.")
        return

    print(f"{len(voices)} voix trouvee(s) :\n")

    for index, voice in enumerate(voices):
        is_current = voice.id == current_id
        marker = "-> " if is_current else "   "

        print(f"{marker}[{index}] {voice.name}")
        print(f"       id       : {voice.id}")
        print(f"       langue(s): {_format_languages(getattr(voice, 'languages', None))}")
        print(f"       age      : {_format_optional(getattr(voice, 'age', None))}")
        print(f"       genre    : {_format_optional(getattr(voice, 'gender', None))}")
        if is_current:
            print("       (voix selectionnee par defaut)")
        print()


def _resolve_voice_id(engine, voice_arg: str) -> str | None:
    """Accepte un index (position affichee) ou un id litteral. Retourne None si introuvable."""

    voices = _list_voices(engine)

    try:
        index = int(voice_arg)
    except ValueError:
        index = None

    if index is not None:
        if 0 <= index < len(voices):
            return voices[index].id
        return None

    for voice in voices:
        if voice.id == voice_arg:
            return voice.id

    return None


def _run_test(engine, text: str, voice_arg: str) -> int:
    voice_id = _resolve_voice_id(engine, voice_arg)

    if voice_id is None:
        print(f"ERREUR : voix introuvable pour --voice {voice_arg!r} (index ou id invalide).")
        return 1

    print(f"Test avec la voix : {voice_id}")
    print(f"Texte : {text}")

    engine.setProperty("voice", voice_id)
    engine.say(text)
    engine.runAndWait()

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnostic des voix pyttsx3 disponibles (ON3RT Radio Suite).")
    parser.add_argument("--test", metavar="TEXTE", help="Phrase courte a synthetiser et jouer immediatement.")
    parser.add_argument(
        "--voice",
        metavar="INDEX_OU_ID",
        help="Voix a utiliser pour --test : index affiche dans la liste (ex: 2) ou id litteral SAPI5.",
    )
    args = parser.parse_args()

    if args.test and not args.voice:
        parser.error("--test necessite --voice (index ou id de la voix a utiliser).")

    try:
        import pyttsx3
    except ImportError:
        print("ERREUR : pyttsx3 n'est pas installe (voir requirements.txt : pyttsx3>=2.99).")
        return 1

    try:
        import pythoncom
    except ImportError:
        pythoncom = None

    if pythoncom is not None:
        pythoncom.CoInitialize()

    try:
        engine = pyttsx3.init()

        _print_voice_table(engine)

        if args.test:
            return _run_test(engine, args.test, args.voice)

        return 0
    finally:
        if pythoncom is not None:
            pythoncom.CoUninitialize()


if __name__ == "__main__":
    raise SystemExit(main())
