#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
validate_cw_keying.py
-------------------------------------------------
ON3RT Radio Suite - Validation materielle du keying CW (etape 6)

Outil de validation autonome pour le pipeline CW complet -- Texte ->
MorseEncoder -> TimingEngine -> CWService -> PTTKeyerBackend -- sur
materiel CAT/CI-V reel (IC-7300), premiere emission CW reelle de la
Suite sur l'air. Construit la chaine exactement comme core/application.py
le fera en production : RadioService -> PTTGuard -> PTTKeyerBackend ->
CWService, aucune simulation, aucun double de test (contrairement a
tests/test_cw_service.py, qui utilise volontairement NullKeyerBackend
pour rester rapide et deterministe -- ce script fait l'inverse,
volontairement).

Ce que ni les tests unitaires (aucun materiel) ni l'architecture seule
ne peuvent prouver : la precision REELLE du timing obtenue en pilotant
le PTT via des commandes CAT serie repetees -- risque explicitement
identifie des la conception du chantier CW (latence/gigue du
round-trip serie, GIL, ordonnanceur Windows). Chaque scenario affiche
donc, de facon lisible : le backend utilise, la vitesse WPM (et
Farnsworth le cas echeant), la duree ESTIMEE (calculee independamment
via TimingEngine) et la duree REELLEMENT MESUREE (chronometrage
reel entre send() et cw_finished/cw_stopped), pour faciliter les essais
avec differents reglages et differents materiels.

Volontairement SANS AudioOutputService/VoiceService : ce script ne
teste que le keying CW lui-meme, pas la synthese vocale.

data/live.json (le vrai pont ON3RT Live) n'est jamais touche :
RadioService est redirige vers un fichier de pont jetable, comme dans
les autres scripts validate_*.py de ce depot.

Interruption immediate : Ctrl+C a tout moment appelle CWService.stop()
(relache le PTT) avant de quitter. Entre chaque scenario, une invite
permet aussi de s'arreter proprement (taper "q").

Garde-fous avant tout essai reel : memes avertissements (charge/antenne,
puissance minimale) que validate_ptt_guard.py/validate_transmission_service.py.

Les messages affiches a l'ecran evitent volontairement les caracteres
accentues -- meme convention que les autres scripts validate_*.py de
ce depot ; logs/cw.log, lui, reste en UTF-8 avec les accents normaux.

Usage :
    python validate_cw_keying.py [PORT] [BAUDRATE]

Par defaut : COM3, 19200 bauds.
"""

from __future__ import annotations

import signal
import sys
import time
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

from apps.cat_server.cw_ptt_backend import PTTKeyerBackend
from apps.cat_server.ptt_guard import PTTGuard
from apps.cat_server.radio_service import RadioService
from libraries.cw.cw_service import CWService, CWState
from libraries.cw.element_driver import ElementDriver
from libraries.cw.morse_encoder import MorseEncoder
from libraries.cw.timing import TimingEngine

_LIVE_DATA_PATH = Path(__file__).resolve().parent / "logs" / "validate_cw_keying_live.json"

# Reference au CWService actif, utilisee par _emergency_stop() (Ctrl+C) :
# stop() relache le PTT immediatement, quel que soit le scenario en cours.
_active_service: CWService | None = None


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


def _emergency_stop(signum, frame) -> None:
    print("\n\n*** INTERRUPTION (Ctrl+C) : arret d'urgence ***")

    if _active_service is not None and _active_service.state is CWState.SENDING:
        print("Emission active detectee -> arret force (PTT)...")
        _active_service.stop()
    else:
        print("Aucune emission active.")

    sys.exit(1)


def _estimated_duration_s(text: str, wpm: float, farnsworth_wpm: float | None = None) -> float:
    """Duree theorique, calculee INDEPENDAMMENT de CWService (MorseEncoder + TimingEngine directs)."""

    elements = MorseEncoder().encode(text)
    timed = TimingEngine(wpm=wpm, farnsworth_wpm=farnsworth_wpm).apply(elements)
    return sum(e.duration_s for e in timed)


def _print_settings(backend, service: CWService, text: str, estimated_s: float) -> None:
    farnsworth_note = f" (Farnsworth : {service.farnsworth_wpm} WPM)" if service.farnsworth_wpm else ""
    print("-" * 70)
    print(f"Backend utilise    : {backend.name}")
    print(f"Vitesse WPM        : {service.wpm}{farnsworth_note}")
    print(f"Message            : {text!r}")
    print(f"Duree estimee      : {estimated_s:.3f}s")
    print("-" * 70)


def _print_measured_result(estimated_s: float, measured_s: float, tolerance_ratio: float = 0.15) -> bool:
    deviation = abs(measured_s - estimated_s) / estimated_s if estimated_s > 0 else 0.0
    within_tolerance = deviation <= tolerance_ratio

    print(f"Duree mesuree      : {measured_s:.3f}s")
    print(f"Ecart estime/mesure: {deviation * 100:.1f}% (tolerance : {tolerance_ratio * 100:.0f}%)")
    print(f"Resultat (timing)  : {'PASS' if within_tolerance else 'ECHEC'}")

    return within_tolerance


def _send_and_measure(service: CWService, text: str, owner: str, timeout_s: float = 30.0):
    """Envoie `text`, chronometre send() -> cw_finished/cw_error. Retourne (succes, duree_mesuree_s, erreur)."""

    finished = []
    errored = []

    def _on_finished(rid):
        finished.append(rid)

    def _on_error(rid, message):
        errored.append(message)

    service.cw_finished.connect(_on_finished)
    service.cw_error.connect(_on_error)

    start = time.monotonic()
    service.send(text, owner=owner)

    elapsed_s = 0.0
    tick_s = 0.02
    while elapsed_s < timeout_s and not finished and not errored:
        _wait(tick_s)
        elapsed_s += tick_s

    measured_s = time.monotonic() - start

    service.cw_finished.disconnect(_on_finished)
    service.cw_error.disconnect(_on_error)

    if errored:
        return False, measured_s, errored[0]

    return bool(finished), measured_s, None


# ----------------------------------------------------------------------
# Scenarios
# ----------------------------------------------------------------------

def _scenario_1_basic_keying(service, backend, radio_service) -> bool:
    print("Emission de base a vitesse normale : mesure du timing + confirmation PTT/RF/audio.")

    text = "VVV TEST"
    estimated_s = _estimated_duration_s(text, service.wpm, service.farnsworth_wpm)
    _print_settings(backend, service, text, estimated_s)

    success, measured_s, error = _send_and_measure(service, text, owner="validate_cw_keying")

    if not success:
        print(f"  -> ECHEC : {error or 'timeout, aucun signal recu'}")
        return False

    timing_ok = _print_measured_result(estimated_s, measured_s)

    ptt_ok = _ask("Le voyant TX de la radio s'est-il allume pendant toute l'emission, puis eteint a la fin ?")
    rf_ok = _ask("Une emission reelle a-t-elle eu lieu sur l'air (puissance reduite) ?")
    audio_ok = _ask("Avez-vous entendu/vu un CW propre, sans coupure ni a-coup anormal ?")

    return timing_ok and ptt_ok and rf_ok and audio_ok


def _scenario_2_immediate_stop(service, backend, radio_service) -> bool:
    print("Arret immediat (stop()) en plein milieu d'un message plus long.")

    text = "PARIS PARIS PARIS PARIS"
    estimated_s = _estimated_duration_s(text, service.wpm, service.farnsworth_wpm)
    _print_settings(backend, service, text, estimated_s)

    stopped = []
    service.cw_stopped.connect(lambda rid: stopped.append(rid))

    start = time.monotonic()
    service.send(text, owner="validate_cw_keying")

    print("  -> emission en cours, arret dans ~1.5s...")
    _wait(1.5)

    print(f"  -> etat avant stop() = {service.state} (attendu : SENDING)")
    service.stop()
    stop_elapsed_s = time.monotonic() - start

    print(f"  -> etat apres stop() = {service.state} (attendu : STOPPED)")
    print(f"  -> duree ecoulee avant l'arret = {stop_elapsed_s:.3f}s (sur {estimated_s:.3f}s estimees au total)")

    _wait(0.3)  # laisse le signal cw_stopped (differe) arriver

    state_ok = service.state is CWState.STOPPED
    signal_ok = bool(stopped)

    print(f"  -> signal cw_stopped recu = {signal_ok} (attendu : True)")

    ptt_off_ok = _ask("Le voyant TX s'est-il eteint IMMEDIATEMENT au moment du stop() (pas a la fin naturelle du message) ?")

    return state_ok and signal_ok and ptt_off_ok


def _scenario_3_farnsworth(service, backend, radio_service) -> bool:
    print("Farnsworth : lettres a vitesse normale, espaces etires -- confirmation a l'oreille de la difference.")

    original_wpm = service.wpm
    original_farnsworth = service.farnsworth_wpm

    service.wpm = 20
    service.farnsworth_wpm = 8

    text = "CQ CQ DE TEST"
    estimated_s = _estimated_duration_s(text, service.wpm, service.farnsworth_wpm)
    _print_settings(backend, service, text, estimated_s)

    success, measured_s, error = _send_and_measure(service, text, owner="validate_cw_keying")

    service.wpm = original_wpm
    service.farnsworth_wpm = original_farnsworth

    if not success:
        print(f"  -> ECHEC : {error or 'timeout, aucun signal recu'}")
        return False

    timing_ok = _print_measured_result(estimated_s, measured_s)

    farnsworth_ok = _ask(
        "Les lettres vous ont-elles semble rapides, mais avec des pauses nettement plus longues "
        "entre elles qu'a vitesse normale (effet Farnsworth) ?"
    )

    return timing_ok and farnsworth_ok


def _scenario_4_concurrent_send_is_rejected(service, backend, radio_service) -> bool:
    print("Refus d'une seconde emission pendant qu'une premiere est en cours -- verification purement objective.")

    text = "PARIS PARIS"
    service.send(text, owner="premier")

    print(f"  -> etat apres le premier send() = {service.state} (attendu : SENDING)")

    second_request_id = service.send("DEUXIEME", owner="second")
    print(f"  -> second send() pendant l'emission = {second_request_id} (attendu : None)")

    rejected = second_request_id is None

    service.stop()
    _wait(0.3)

    return rejected


def _scenario_5_cat_unavailable_error_handling(service, backend, radio_service) -> bool:
    print("CAT indisponible pendant une emission : doit echouer proprement (etat ERROR), jamais de plantage.")

    print("  -> deconnexion volontaire de la liaison CAT...")
    radio_service.disconnect()

    errors = []
    service.cw_error.connect(lambda rid, message: errors.append(message))

    service.send("TEST", owner="validate_cw_keying")

    elapsed_s = 0.0
    while elapsed_s < 10.0 and not errors:
        _wait(0.1)
        elapsed_s += 0.1

    service.cw_error.disconnect()

    print(f"  -> erreur recue = {bool(errors)} (attendu : True)")
    if errors:
        print(f"     detail : {errors[0]}")
    print(f"  -> etat = {service.state} (attendu : ERROR)")

    error_handled = bool(errors) and service.state is CWState.ERROR

    print("\n  -> reconnexion de la liaison CAT pour la suite...")
    reconnected = radio_service.connect()
    if reconnected:
        radio_service.timer.stop()
    print(f"  -> connect() = {reconnected} (attendu : True)")

    if not error_handled:
        return False

    ptt_stayed_off = _ask("Le voyant TX est-il reste eteint pendant tout ce scenario (aucune emission) ?")

    return error_handled and ptt_stayed_off and reconnected


_SCENARIOS = (
    ("1/5 - Emission de base (timing + PTT + RF reels)", _scenario_1_basic_keying),
    ("2/5 - Arret immediat en plein milieu", _scenario_2_immediate_stop),
    ("3/5 - Farnsworth", _scenario_3_farnsworth),
    ("4/5 - Refus d'une emission concurrente", _scenario_4_concurrent_send_is_rejected),
    ("5/5 - Gestion d'erreur : CAT indisponible", _scenario_5_cat_unavailable_error_handling),
)


def _print_safety_warning() -> None:
    print("=" * 70)
    print("!!! AVERTISSEMENT - A LIRE AVANT DE CONTINUER !!!")
    print("=" * 70)
    print("- La radio DOIT etre reliee a une charge adaptee ou a une")
    print("  antenne utilisable avant de lancer ce script.")
    print("- Reglez la puissance d'emission au MINIMUM pour ces essais.")
    print("- Ceci est la PREMIERE emission CW reelle de la Suite -- chaque")
    print("  scenario transmet reellement sur l'air, pendant quelques")
    print("  secondes a chaque fois.")
    print("- Ctrl+C interrompt ce script IMMEDIATEMENT, a tout moment, et")
    print("  relache le PTT si une emission est en cours.")
    print("=" * 70)
    input("\nAppuyez sur Entree pour continuer, ou fermez cette fenetre pour annuler...")


def main() -> int:
    port = sys.argv[1] if len(sys.argv) > 1 else "COM3"
    baudrate = int(sys.argv[2]) if len(sys.argv) > 2 else 19200

    signal.signal(signal.SIGINT, _emergency_stop)

    print("=" * 70)
    print("ON3RT Radio Suite - Validation materielle du keying CW (etape 6)")
    print("=" * 70)

    _print_safety_warning()

    app = QApplication.instance() or QApplication(sys.argv)

    print("\nJournal detaille : logs/cat_server.log et logs/cw.log")
    print("Ctrl+C a tout moment : arret d'urgence (relache le PTT)")

    radio_service = RadioService(port=port, baudrate=baudrate, live_data_path=_LIVE_DATA_PATH)

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
    print(f"Modele configure   : {radio_service.model}  (valeur configuree, pas interrogee via CAT)")
    print("=" * 70)

    if not _ask(
        "\nEtes-vous pret a transmettre reellement en CW sur l'air pour cette validation "
        "(charge/antenne connectee, puissance reduite) ?"
    ):
        print("Arret demande avant toute transmission.")
        radio_service.disconnect()
        return 1

    ptt_guard = PTTGuard(radio_service=radio_service)
    backend = PTTKeyerBackend(ptt_guard=ptt_guard)
    service = CWService(driver=ElementDriver(backend), wpm=20)

    global _active_service
    _active_service = service

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
                passed = func(service, backend, radio_service)
            except Exception as exc:
                print(f"EXCEPTION NON GEREE pendant le scenario : {exc!r}")
                passed = False

            results[name] = passed
            print(f"\n-> RESULTAT : {'PASS' if passed else 'ECHEC'}")

    finally:
        if service.state is CWState.SENDING:
            print("\nNettoyage final : emission encore active, arret...")
            service.stop()

        if not radio_service.connected:
            print("\nRadio non connectee : reconnexion pour la fermeture propre...")
            radio_service.connect()

        radio_service.disconnect()

    print("\n" + "=" * 70)
    print("RESUME")
    print("=" * 70)

    for name, passed in results.items():
        print(f"  [{'PASS' if passed else 'ECHEC'}] {name}")

    total_scenarios = len(_SCENARIOS)
    ran_scenarios = len(results)
    passed_scenarios = sum(1 for passed in results.values() if passed)
    all_passed = ran_scenarios == total_scenarios and passed_scenarios == total_scenarios

    print()
    if all_passed:
        print(f"PASS : {passed_scenarios}/{total_scenarios}")
    else:
        failed_names = [name for name, passed in results.items() if not passed]
        not_run = [name for name, _ in _SCENARIOS if name not in results]
        failed_names.extend(f"{name} (non execute)" for name in not_run)
        print(f"FAILED : {', '.join(failed_names)}")

    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
