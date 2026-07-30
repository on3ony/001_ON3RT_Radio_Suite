#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
validate_transmission_service.py
-------------------------------------------------
ON3RT Radio Suite - Validation matérielle de TransmissionService

Outil de validation autonome pour apps/cat_server/transmission_service.py
(TransmissionService), sur matériel CAT/CI-V réel (IC-7300). Construit
la chaîne complète RadioService -> PTTGuard -> AudioOutputService ->
TransmissionService, exactement comme un futur module Voix le fera, et
déroule les scénarios définis lors de l'étude de conception de
l'étape 3 : transmission complète, arrêt manuel (STOP) en cours de
lecture, fichier audio invalide.

Volontairement SANS :
    - synthèse vocale (pyttsx3, Coqui/XTTS)
    - VoiceService (n'existe pas encore)
    - tout code spécifique au futur module Voix

Ce script génère lui-même de courts fichiers WAV (tonalité pure, sans
dépendance à un fichier audio externe) : outil complètement autonome,
comme validate_ptt_guard.py.

data/live.json n'est jamais touché (redirigé vers un fichier de pont
jetable). Journalisation : ce script réutilise le logger CAT_SERVER
réel (apps/cat_server/logger.py), déjà utilisé par
RadioService/PTTGuard/TransmissionService.

Interruption immédiate : Ctrl+C à tout moment appelle
TransmissionService.stop() (relâche le PTT ET arrête l'audio) avant de
quitter. Entre chaque scénario, une invite permet aussi de s'arrêter
proprement (taper "q").

Mêmes garde-fous qu'avant tout essai matériel (voir aussi
validate_ptt_guard.py) : charge/antenne, puissance minimale,
confirmation explicite avant toute émission.

Les messages affichés à l'écran évitent volontairement les caractères
accentués (même convention que civ_diagnostic.py/validate_ptt_guard.py) ;
logs/cat_server.log, lui, reste en UTF-8 avec les accents normaux.

Usage :
    python validate_transmission_service.py [PORT] [BAUDRATE]

Par défaut : COM3, 19200 bauds.
"""

from __future__ import annotations

import math
import shutil
import signal
import struct
import sys
import tempfile
import wave
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

from apps.cat_server.ptt_guard import PTTGuard
from apps.cat_server.radio_service import RadioService
from apps.cat_server.transmission_service import TransmissionService
from libraries.audio.audio_output_service import AudioOutputService

_LIVE_DATA_PATH = Path(__file__).resolve().parent / "logs" / "validate_transmission_service_live.json"

# Référence au TransmissionService actif, utilisée par _emergency_stop()
# (Ctrl+C) : stop() relâche le PTT ET coupe l'audio, quel que soit
# l'état exact du scénario en cours.
_active_service: TransmissionService | None = None


def _wait(seconds: float) -> None:
    """Attend `seconds` secondes en laissant tourner la boucle d'evenements Qt."""

    loop = QEventLoop()
    QTimer.singleShot(int(seconds * 1000), loop.quit)
    loop.exec()


def _ask(question: str) -> bool:
    answer = input(f"{question} [o/n] : ").strip().lower()
    return answer in ("o", "oui", "y", "yes")


def _pause_or_quit(step_name: str) -> bool:
    answer = input(f"\n-- Entree pour continuer vers [{step_name}], ou 'q' pour arreter -- ").strip().lower()
    return answer != "q"


def _generate_tone_wav(path: Path, duration_s: float, freq_hz: float = 440.0, samplerate: int = 44100) -> None:
    """Genere un WAV mono PCM 16 bits, tonalite pure -- aucun fichier audio externe requis."""

    n_frames = int(samplerate * duration_s)

    with wave.open(str(path), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(samplerate)

        frames = bytearray()
        for i in range(n_frames):
            value = int(32767 * 0.3 * math.sin(2 * math.pi * freq_hz * i / samplerate))
            frames += struct.pack("<h", value)

        f.writeframes(bytes(frames))


def _emergency_stop(signum, frame) -> None:
    print("\n\n*** INTERRUPTION (Ctrl+C) : arret d'urgence ***")

    if _active_service is not None and _active_service.is_transmitting:
        print("Transmission active detectee -> arret force (PTT + audio)...")
        _active_service.stop()
        print(f"Arrete : is_transmitting = {_active_service.is_transmitting}")
    else:
        print("Aucune transmission active.")

    sys.exit(1)


# ----------------------------------------------------------------------
# Scenarios
# ----------------------------------------------------------------------

def _scenario_1_full_transmission(service: TransmissionService, tone_short: Path, tone_long: Path, errors_seen: list) -> bool:
    print("Transmission complete d'un court fichier WAV (~1.5s), via TransmissionService.transmit().")

    finished = []
    service.transmission_finished.connect(lambda: finished.append(True))

    ok = service.transmit(str(tone_short), owner="validate_transmission_service")
    print(f"  -> transmit() = {ok} (attendu : True)")
    if not ok:
        return False

    print(f"  -> is_transmitting = {service.is_transmitting} (attendu : True)")

    print("  -> Ecoutez le son et observez le voyant TX pendant la lecture...")
    for _ in range(40):  # jusqu'a 4s, tick de 0.1s
        _wait(0.1)
        if finished:
            break

    print(f"  -> transmission_finished recu = {bool(finished)} (attendu : True)")
    print(f"  -> is_transmitting = {service.is_transmitting} (attendu : False)")

    audio_and_tx_matched = _ask("Le son a-t-il ete audible et le voyant TX allume pendant toute la duree, puis eteint a la fin ?")

    return bool(finished) and not service.is_transmitting and audio_and_tx_matched


def _scenario_2_manual_stop(service: TransmissionService, tone_short: Path, tone_long: Path, errors_seen: list) -> bool:
    print("Arret manuel (STOP) en plein milieu d'une lecture plus longue (~6s).")

    stopped = []
    service.transmission_stopped.connect(lambda: stopped.append(True))

    ok = service.transmit(str(tone_long), owner="validate_transmission_service")
    print(f"  -> transmit() = {ok} (attendu : True)")
    if not ok:
        return False

    print("  -> Lecture en cours, attente de ~2s avant l'arret manuel...")
    _wait(2.0)

    print(f"  -> is_transmitting avant stop() = {service.is_transmitting} (attendu : True)")
    print("  -> TransmissionService.stop()...")
    service.stop()

    print(f"  -> is_transmitting apres stop() = {service.is_transmitting} (attendu : False)")
    print(f"  -> transmission_stopped recu = {bool(stopped)} (attendu : True)")

    _wait(0.3)
    cut_immediately = _ask("Le son s'est-il arrete NET et le voyant TX eteint immediatement apres stop() (pas apres la fin naturelle des ~6s) ?")

    return bool(stopped) and not service.is_transmitting and cut_immediately


def _scenario_3_invalid_audio_file(service: TransmissionService, tone_short: Path, tone_long: Path, errors_seen: list) -> bool:
    print("Fichier audio invalide (inexistant) : le PTT doit s'activer puis retomber aussitot, proprement.")

    missing_path = tone_short.parent / "ce_fichier_n_existe_pas.wav"

    errored = []
    service.transmission_error.connect(lambda msg: errored.append(msg))

    ok = service.transmit(str(missing_path), owner="validate_transmission_service")
    print(
        f"  -> transmit() = {ok} (attendu : False -- le PTT s'active puis playback_error"
        " survient de facon synchrone avant que transmit() ne rende la main, voir le"
        " correctif de l'etape 3 dans apps/cat_server/transmission_service.py)"
    )

    _wait(0.5)

    print(f"  -> transmission_error recu = {bool(errored)} (attendu : True)")
    if errored:
        print(f"  -> message : {errored[0]}")
    print(f"  -> is_transmitting = {service.is_transmitting} (attendu : False)")

    visual_off = _ask("Le voyant TX est-il reste eteint, ou s'est-il eteint immediatement (pas de blocage en emission) ?")

    return bool(errored) and not service.is_transmitting and visual_off


_SCENARIOS = (
    ("1/3 - Transmission complete", _scenario_1_full_transmission),
    ("2/3 - Arret manuel (STOP) en cours de lecture", _scenario_2_manual_stop),
    ("3/3 - Fichier audio invalide", _scenario_3_invalid_audio_file),
)


def _print_safety_warning() -> None:
    print("=" * 70)
    print("!!! AVERTISSEMENT - A LIRE AVANT DE CONTINUER !!!")
    print("=" * 70)
    print("- La radio DOIT etre reliee a une charge adaptee ou a une")
    print("  antenne utilisable avant de lancer ce script.")
    print("- Reglez la puissance d'emission au MINIMUM pour ces essais.")
    print("- Chaque scenario transmet reellement de l'audio sur l'air,")
    print("  pendant quelques secondes seulement.")
    print("- Ctrl+C interrompt ce script IMMEDIATEMENT, a tout moment, et")
    print("  arrete la transmission (PTT + audio) si une est en cours.")
    print("=" * 70)
    input("\nAppuyez sur Entree pour continuer, ou fermez cette fenetre pour annuler...")


def main() -> int:
    port = sys.argv[1] if len(sys.argv) > 1 else "COM3"
    baudrate = int(sys.argv[2]) if len(sys.argv) > 2 else 19200

    signal.signal(signal.SIGINT, _emergency_stop)

    print("=" * 70)
    print("ON3RT Radio Suite - Validation materielle de TransmissionService")
    print("=" * 70)

    _print_safety_warning()

    app = QApplication.instance() or QApplication(sys.argv)

    print("\nJournal detaille : logs/cat_server.log")
    print("Ctrl+C a tout moment : arret d'urgence (PTT + audio)")

    radio_service = RadioService(port=port, baudrate=baudrate, live_data_path=_LIVE_DATA_PATH)

    errors_seen: list[str] = []
    radio_service.error.connect(lambda msg: errors_seen.append(msg))

    print("\nConnexion a la radio...")
    if not radio_service.connect():
        print("ECHEC : impossible de se connecter a la radio. Verifiez le port/baudrate. Arret.")
        return 1

    radio_service.timer.stop()

    print("\n" + "=" * 70)
    print("ETAT DE LA CONNEXION")
    print("=" * 70)
    print(f"Port COM utilise   : {radio_service.port}")
    print(f"Vitesse CAT        : {radio_service.baudrate} bauds")
    print(
        f"Modele configure   : {radio_service.model}  "
        "(valeur configuree, pas interrogee via CAT)"
    )
    print(f"Frequence lue      : {radio_service.frequency} Hz")
    print(f"Mode lu            : {radio_service.mode}")
    print("=" * 70)

    if not _ask(
        "\nEtes-vous pret a transmettre reellement sur l'air pour la premiere fois "
        "(charge/antenne connectee, puissance reduite) ?"
    ):
        print("Arret demande avant toute transmission.")
        radio_service.disconnect()
        return 1

    ptt_guard = PTTGuard(radio_service=radio_service)
    audio_service = AudioOutputService()
    service = TransmissionService(audio_service=audio_service, ptt_guard=ptt_guard)

    global _active_service
    _active_service = service

    tmp_dir = Path(tempfile.mkdtemp(prefix="on3rt_validate_transmission_"))
    tone_short = tmp_dir / "tone_short.wav"
    tone_long = tmp_dir / "tone_long.wav"
    _generate_tone_wav(tone_short, duration_s=1.5)
    _generate_tone_wav(tone_long, duration_s=6.0)
    print(f"\nFichiers de test generes dans : {tmp_dir}")

    results: dict[str, bool] = {}

    try:
        for name, func in _SCENARIOS:
            if not _pause_or_quit(name):
                print("Arret demande par l'operateur.")
                break

            print("\n" + "=" * 70)
            print(name)
            print("=" * 70)

            try:
                passed = func(service, tone_short, tone_long, errors_seen)
            except Exception as exc:
                print(f"EXCEPTION NON GEREE pendant le scenario : {exc!r}")
                passed = False

            results[name] = passed
            print(f"\n-> RESULTAT : {'PASS' if passed else 'ECHEC'}")

    finally:
        if _active_service is not None and _active_service.is_transmitting:
            print("\nNettoyage final : transmission encore active, arret...")
            _active_service.stop()

        radio_service.disconnect()
        shutil.rmtree(tmp_dir, ignore_errors=True)

    print("\n" + "=" * 70)
    print("RESUME")
    print("=" * 70)

    for name, passed in results.items():
        print(f"  [{'PASS' if passed else 'ECHEC'}] {name}")

    all_passed = len(results) == len(_SCENARIOS) and all(results.values())
    print("\n=> Validation complete et reussie." if all_passed else "\n=> Validation incomplete ou scenario(s) en echec -- voir ci-dessus.")

    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
