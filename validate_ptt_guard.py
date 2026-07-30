#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
validate_ptt_guard.py
-------------------------------------------------
ON3RT Radio Suite - Validation matérielle de PTTGuard

Outil de validation autonome pour apps/cat_server/ptt_guard.py
(PTTGuard) et RadioService.set_ptt()/aboutToDisconnect
(apps/cat_server/radio_service.py), sur matériel CAT/CI-V réel
(IC-7300). Déroule les 6 scénarios définis lors de l'étude de
conception de l'étape 2 ("PTT sécurisé") de l'architecture Voix :
primitive brute, cycle normal, exception dans le bloc with, minuterie
de sécurité, fermeture de la liaison CAT, fermeture de l'application
pendant une émission.

Scénario 5 corrigé après un premier essai matériel réel : la première
version fermait la liaison CAT (radio_service.disconnect()) AVANT tout
release(), ce qui laissait le PTT actif sans aucune commande envoyée
(set_ptt() refusait d'agir, port déjà fermé). Le scénario teste
maintenant directement le correctif (RadioService.aboutToDisconnect,
voir sa docstring et celle de PTTGuard) : disconnect() est appelé SANS
release() explicite avant, et doit désormais relâcher le PTT tout
seul, avant la fermeture réelle du port.

Volontairement SANS :
    - AudioOutputService
    - VoiceService / TransmissionService (n'existent pas encore)
    - tout code spécifique au futur module Voix

N'utilise que RadioService et PTTGuard, exactement tels qu'ils
existeront pour tout futur consommateur : ce script EST un
consommateur de PTTGuard comme un autre, pas un simulateur séparé.

data/live.json (le vrai pont ON3RT Live) n'est jamais touché : ce
script redirige RadioService vers un fichier de pont jetable
(logs/validate_ptt_guard_live.json), pour ne jamais interférer avec
une éventuelle instance de la Suite déjà ouverte en parallèle.

Le polling automatique de RadioService (250 ms) est désactivé juste
après la connexion : ce diagnostic ne lit le PTT que lorsqu'il le
demande explicitement, pour un trafic CAT prévisible pendant le test
et un journal plus facile à lire.

Journalisation : ce script réutilise le logger CAT_SERVER réel
(apps/cat_server/logger.py), déjà utilisé par RadioService/PTTGuard —
chaque action apparaît donc à la fois à l'écran (résumé de ce script)
et dans logs/cat_server.log (détail CAT complet : trames TX/RX,
timeouts, etc.), sans configuration supplémentaire.

Interruption immédiate : Ctrl+C à tout moment force le relâchement du
PTT actif (s'il y en a un) avant de quitter. Entre chaque scénario,
une invite permet aussi de s'arrêter proprement (taper "q").

Garde-fous avant tout PTT réel : un avertissement (charge/antenne,
puissance minimale, durée de PTT volontairement courte, Ctrl+C
disponible) s'affiche avant toute connexion, puis, une fois connecté,
le port/la vitesse/le modèle configuré sont affichés et une
confirmation explicite est demandée avant la toute première activation
du PTT (scénario 1). "Modèle configuré" est la valeur par défaut de
RadioStatus.model ("IC-7300") — jamais interrogée via CAT, cette chaîne
n'a aucune commande de lecture de modèle.

Les messages affichés à l'écran (print/input) évitent volontairement
les caractères accentués — même convention que civ_diagnostic.py à la
racine du dépôt — certaines consoles Windows les affichent mal selon
leur page de code active. logs/cat_server.log, lui, est toujours en
UTF-8 et garde les accents normalement.

Usage :
    python validate_ptt_guard.py [PORT] [BAUDRATE]

Par défaut : COM3, 19200 bauds.
"""

from __future__ import annotations

import signal
import sys
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

from apps.cat_server.ptt_guard import PTTGuard
from apps.cat_server.radio_service import RadioService

_LIVE_DATA_PATH = Path(__file__).resolve().parent / "logs" / "validate_ptt_guard_live.json"

# Reference au PTTGuard actif pendant le scenario en cours, utilisee
# par _emergency_stop() : Ctrl+C doit pouvoir relacher le PTT meme en
# plein milieu d'un scenario, sans dependre du deroulement normal du
# script (meme logique que la minuterie de securite de PTTGuard
# lui-meme).
_active_guard: PTTGuard | None = None


def _wait(seconds: float) -> None:
    """Attend `seconds` secondes en laissant tourner la boucle d'evenements Qt (minuteries PTTGuard actives pendant l'attente)."""

    loop = QEventLoop()
    QTimer.singleShot(int(seconds * 1000), loop.quit)
    loop.exec()


def _ask(question: str) -> bool:
    answer = input(f"{question} [o/n] : ").strip().lower()
    return answer in ("o", "oui", "y", "yes")


def _pause_or_quit(step_name: str) -> bool:
    """Retourne False si l'operateur souhaite arreter la validation ici."""

    answer = input(f"\n-- Entree pour continuer vers [{step_name}], ou 'q' pour arreter -- ").strip().lower()
    return answer != "q"


def _read_ptt_state(radio_service: RadioService) -> bool:
    raw = radio_service.controller.read_ptt()
    return raw.get("ptt", False) if isinstance(raw, dict) else bool(raw)


def _emergency_stop(signum, frame) -> None:
    print("\n\n*** INTERRUPTION (Ctrl+C) : arret d'urgence ***")

    if _active_guard is not None and _active_guard.is_keyed:
        print("PTT actif detecte -> relachement force...")
        _active_guard.release()
        print(f"PTT relache : is_keyed = {_active_guard.is_keyed}")
    else:
        print("Aucun PTT actif.")

    sys.exit(1)


# ----------------------------------------------------------------------
# Scenarios
# ----------------------------------------------------------------------

def _scenario_1_raw_set_ptt(radio_service: RadioService, errors_seen: list) -> bool:
    print("Test de la primitive brute RadioService.set_ptt(), sans PTTGuard.")

    print("\nActivation : set_ptt(True)")
    ok_on = radio_service.set_ptt(True)
    print(f"  -> retour = {ok_on}")
    if not ok_on:
        print("  ECHEC : set_ptt(True) a retourne False.")
        return False

    _wait(0.5)
    print(f"  -> lecture radio (read_ptt) = {_read_ptt_state(radio_service)}")
    visual_on = _ask("Le voyant TX de l'IC-7300 est-il allume ?")

    print("\nDesactivation : set_ptt(False)")
    ok_off = radio_service.set_ptt(False)
    print(f"  -> retour = {ok_off}")

    _wait(0.5)
    print(f"  -> lecture radio (read_ptt) = {_read_ptt_state(radio_service)}")
    visual_off = _ask("Le voyant TX est-il eteint ?")

    return ok_on and ok_off and visual_on and visual_off


def _scenario_2_normal_cycle(radio_service: RadioService, errors_seen: list) -> bool:
    global _active_guard
    print("Cycle normal : PTTGuard.keyed() en gestionnaire de contexte.")

    guard = PTTGuard(radio_service=radio_service, safety_timeout_s=30.0)
    _active_guard = guard

    with guard.keyed(owner="validate_ptt_guard"):
        print(f"  -> is_keyed = {guard.is_keyed} (attendu : True)")
        _wait(1.0)
        visual_on = _ask("Le voyant TX est-il allume ?")

    print(f"  -> apres le bloc with, is_keyed = {guard.is_keyed} (attendu : False)")
    _wait(0.5)
    visual_off = _ask("Le voyant TX est-il eteint ?")

    _active_guard = None

    return visual_on and visual_off and not guard.is_keyed


def _scenario_3_exception_releases(radio_service: RadioService, errors_seen: list) -> bool:
    global _active_guard
    print("Exception provoquee dans le bloc with : le PTT doit quand meme retomber, et l'exception doit rester visible.")

    guard = PTTGuard(radio_service=radio_service, safety_timeout_s=30.0)
    _active_guard = guard

    exception_seen = False
    try:
        with guard.keyed(owner="validate_ptt_guard"):
            print(f"  -> is_keyed = {guard.is_keyed} (attendu : True)")
            _wait(0.5)
            print("  -> levee volontaire d'une RuntimeError...")
            raise RuntimeError("Exception de test volontaire (scenario 3)")
    except RuntimeError as exc:
        exception_seen = True
        print(f"  -> exception bien recue par ce script : {exc!r}")

    print(f"  -> apres l'exception, is_keyed = {guard.is_keyed} (attendu : False)")
    _wait(0.5)
    visual_off = _ask("Le voyant TX est-il eteint (malgre l'exception) ?")

    _active_guard = None

    return exception_seen and visual_off and not guard.is_keyed


def _scenario_4_safety_timeout(radio_service: RadioService, errors_seen: list) -> bool:
    """
    Aucune saisie clavier (input()) pendant la fenetre d'attente : la
    version precedente demandait une confirmation visuelle juste apres
    key(), ce qui bloquait la boucle d'evenements Qt pendant que
    l'operateur repondait -- la minuterie continue de compter en
    interne, mais son declenchement ne peut etre livre qu'une fois la
    boucle relancee, faussant le moment observe. Ici, key() est suivi
    IMMEDIATEMENT d'une boucle d'attente qui pompe en continu la boucle
    d'evenements (aucun appel bloquant entre les deux) : la minuterie
    de PTTGuard se declenche donc dans les memes conditions que dans
    l'application reelle. La seule question posee a l'operateur arrive
    APRES la fin de cette fenetre, pour ne jamais interferer avec elle.
    """

    global _active_guard
    short_timeout = 5.0
    margin_s = 3.0
    tick_s = 0.5

    print(f"Minuterie de securite reduite a {short_timeout:.0f}s pour ce test (PTT jamais relache explicitement).")
    print("Aucune saisie clavier pendant l'attente : la boucle d'evenements Qt tourne en continu.")

    guard = PTTGuard(radio_service=radio_service, safety_timeout_s=short_timeout)
    _active_guard = guard

    guard.key(owner="validate_ptt_guard")
    print(f"\n  -> PTT active (is_keyed = {guard.is_keyed}). Observez le voyant TX sans intervenir.")

    total_wait_s = short_timeout + margin_s
    elapsed_s = 0.0
    released_after_s = None

    while elapsed_s < total_wait_s:
        _wait(tick_s)
        elapsed_s += tick_s

        if not guard.is_keyed:
            released_after_s = elapsed_s
            break

        print(f"  -> t+{elapsed_s:.1f}s : is_keyed = {guard.is_keyed}")

    if released_after_s is not None:
        print(f"\n  -> PTT relache automatiquement apres ~{released_after_s:.1f}s (minuterie reglee a {short_timeout:.0f}s)")
    else:
        print(f"\n  -> is_keyed = {guard.is_keyed} apres {total_wait_s:.1f}s d'attente (attendu : False -- ECHEC)")

    timer_fired_in_time = released_after_s is not None

    visual_off = _ask(
        "Le voyant TX s'est-il allume au debut puis eteint tout seul pendant cette attente,"
        " sans aucune action de votre part ?"
    )

    _active_guard = None

    return timer_fired_in_time and visual_off and not guard.is_keyed


def _scenario_5_cat_disconnect(radio_service: RadioService, errors_seen: list) -> bool:
    global _active_guard
    print("Fermeture de la liaison CAT pendant que le PTT est actif (radio_service.disconnect() direct,")
    print("AUCUN release() explicite avant). Verifie le correctif aboutToDisconnect : PTTGuard doit")
    print("relacher le PTT tout seul, PENDANT que disconnect() tourne, avant que le port ne se ferme.")

    guard = PTTGuard(radio_service=radio_service, safety_timeout_s=30.0)
    _active_guard = guard

    guard.key(owner="validate_ptt_guard")
    print(f"  -> is_keyed = {guard.is_keyed} (attendu : True)")

    if not _ask("Le voyant TX est-il allume ?"):
        guard.release()
        _active_guard = None
        return False

    print("\n  -> radio_service.disconnect() (sans appel a guard.release() avant)...")
    radio_service.disconnect()
    print(f"  -> radio_service.connected = {radio_service.connected}")
    print(
        f"  -> is_keyed = {guard.is_keyed} (attendu : False -- relache automatiquement"
        " via aboutToDisconnect, avant la fermeture reelle du port)"
    )

    _wait(0.5)
    visual_off = _ask("Le voyant TX est-il eteint (relache automatiquement par la deconnexion) ?")

    print("\n  Reconnexion pour la suite de la validation...")
    reconnected = radio_service.connect()
    if reconnected:
        radio_service.timer.stop()
    print(f"  -> connect() = {reconnected}")

    _active_guard = None

    return visual_off and not guard.is_keyed and reconnected


def _scenario_6_about_to_quit(radio_service: RadioService, errors_seen: list) -> bool:
    global _active_guard
    print("Fermeture de l'application pendant une emission (aboutToQuit simule, sans quitter reellement ce script).")

    if not radio_service.connected:
        print("  -> radio non connectee, reconnexion...")
        radio_service.connect()
        radio_service.timer.stop()

    guard = PTTGuard(radio_service=radio_service, safety_timeout_s=30.0)
    _active_guard = guard

    guard.key(owner="validate_ptt_guard")
    print(f"  -> is_keyed = {guard.is_keyed} (attendu : True)")

    if not _ask("Le voyant TX est-il allume ?"):
        guard.release()
        _active_guard = None
        return False

    app = QApplication.instance()

    print("\n  -> emission manuelle de QApplication.aboutToQuit (simulation de fermeture)...")
    app.aboutToQuit.emit()

    print(f"  -> apres aboutToQuit, is_keyed = {guard.is_keyed} (attendu : False)")
    _wait(0.5)
    visual_off = _ask("Le voyant TX est-il eteint ?")

    remaining_receivers = app.receivers("2aboutToQuit()")
    print(f"  -> receivers restants sur aboutToQuit (detail technique, attendu 0) : {remaining_receivers}")

    _active_guard = None

    return visual_off and not guard.is_keyed and remaining_receivers == 0


_SCENARIOS = (
    ("1/6 - set_ptt() brut (RadioService)", _scenario_1_raw_set_ptt),
    ("2/6 - PTTGuard.keyed() cycle normal", _scenario_2_normal_cycle),
    ("3/6 - Exception dans le bloc with", _scenario_3_exception_releases),
    ("4/6 - Minuterie de securite", _scenario_4_safety_timeout),
    ("5/6 - Perte de communication CAT", _scenario_5_cat_disconnect),
    ("6/6 - Fermeture de l'application", _scenario_6_about_to_quit),
)


def _print_safety_warning() -> None:
    print("=" * 70)
    print("!!! AVERTISSEMENT - A LIRE AVANT DE CONTINUER !!!")
    print("=" * 70)
    print("- La radio DOIT etre reliee a une charge adaptee ou a une")
    print("  antenne utilisable avant de lancer ce script.")
    print("- Reglez la puissance d'emission au MINIMUM pour ces essais.")
    print("- Aucun scenario ne doit laisser le PTT actif plus longtemps")
    print("  que necessaire : chaque etape est volontairement courte.")
    print("- Ctrl+C interrompt ce script IMMEDIATEMENT, a tout moment, et")
    print("  relache le PTT si un scenario est en cours.")
    print("=" * 70)
    input("\nAppuyez sur Entree pour continuer, ou fermez cette fenetre pour annuler...")


def main() -> int:
    port = sys.argv[1] if len(sys.argv) > 1 else "COM3"
    baudrate = int(sys.argv[2]) if len(sys.argv) > 2 else 19200

    signal.signal(signal.SIGINT, _emergency_stop)

    print("=" * 70)
    print("ON3RT Radio Suite - Validation materielle de PTTGuard")
    print("=" * 70)

    _print_safety_warning()

    app = QApplication.instance() or QApplication(sys.argv)

    print("\nJournal detaille : logs/cat_server.log")
    print("Ctrl+C a tout moment : arret d'urgence, relache le PTT si actif")

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
        "(valeur configuree, pas interrogee via CAT -- aucune commande"
        " de lecture de modele n'existe dans cette chaine CAT)"
    )
    print(f"Frequence lue      : {radio_service.frequency} Hz")
    print(f"Mode lu            : {radio_service.mode}")
    print("=" * 70)

    if not _ask(
        "\nEtes-vous pret a activer le PTT pour la premiere fois "
        "(charge/antenne connectee, puissance reduite) ?"
    ):
        print("Arret demande avant toute activation du PTT.")
        radio_service.disconnect()
        return 1

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
                passed = func(radio_service, errors_seen)
            except Exception as exc:
                print(f"EXCEPTION NON GEREE pendant le scenario : {exc!r}")
                passed = False

            results[name] = passed
            print(f"\n-> RESULTAT : {'PASS' if passed else 'ECHEC'}")

    finally:
        if _active_guard is not None and _active_guard.is_keyed:
            print("\nNettoyage final : PTT encore actif, relachement...")
            _active_guard.release()

        if not radio_service.connected:
            print("\nRadio non connectee : reconnexion pour la fermeture propre...")
            radio_service.connect()

        radio_service.disconnect()

    print("\n" + "=" * 70)
    print("RESUME")
    print("=" * 70)

    for name, passed in results.items():
        print(f"  [{'PASS' if passed else 'ECHEC'}] {name}")

    if errors_seen:
        print(f"\n{len(errors_seen)} erreur(s) CAT observee(s) pendant la validation (non attendu) :")
        for msg in errors_seen:
            print(f"  - {msg}")

    all_passed = len(results) == len(_SCENARIOS) and all(results.values())
    print("\n=> Validation complete et reussie." if all_passed else "\n=> Validation incomplete ou scenario(s) en echec -- voir ci-dessus.")

    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
