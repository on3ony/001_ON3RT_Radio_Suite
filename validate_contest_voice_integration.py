#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
validate_contest_voice_integration.py
-------------------------------------------------
ON3RT Radio Suite - Validation materielle de l'integration Contest Assistant <-> Voix (etape 4e-4)

Outil de validation autonome pour le premier vrai consommateur de
l'architecture Voix : le bouton "Annoncer" de
apps/contest_assistant/window.py (ContestAssistantWindow), branche sur
la VRAIE chaine de services -- RadioService -> PTTGuard ->
TransmissionService <- AudioOutputService, et VoiceService -- sur
materiel CAT/CI-V reel (IC-7300), exactement comme core/application.py
les cable en production (meme constructeurs, memes parametres). Ce que
ni tests/test_contest_assistant_window.py (doubles de test, aucune
vraie synthese/transmission) ni validate_voice_service.py (aucun
materiel CAT/RF) ne peuvent prouver a eux seuls : que le VRAI cablage
de bout en bout, dans la fenetre reelle, fonctionne sur l'air.

Ce script pilote la VRAIE ContestAssistantWindow via ses widgets publics
(btn_announce.click(), btn_send.click(), champs de saisie) -- exactement
comme un utilisateur reel -- plutot que d'appeler les services
directement : c'est le cablage lui-meme (core/application.py ->
core/main_window.py -> ContestAssistantWindow) qui est sous test, pas
seulement les briques individuelles deja validees separement (etapes
1 a 4d).

Aucune donnee reelle de l'application n'est touchee : ContestMessageService
et StationService sont construits ici avec des fichiers de configuration
temporaires et jetables (jamais data/contest_assistant.json ni
data/station.json), VoiceService avec un repertoire de cache temporaire
et jetable (jamais data/voice_cache/) -- memes principes que
validate_voice_service.py. data/live.json (le vrai pont ON3RT Live)
n'est jamais touche : RadioService est redirige vers un fichier de pont
jetable, comme dans validate_ptt_guard.py/validate_transmission_service.py.

Automatise tout ce qui est objectivement verifiable (etat des boutons,
signaux recus, delais mesures, numero progressif/historique inchanges
par "Annoncer", battements de minuterie prouvant que l'interface ne
gele jamais, messages d'erreur affiches) ; ne demande une confirmation
humaine que pour ce que l'agent ne peut pas juger lui-meme : qualite de
la voix, PTT (voyant TX), emission reelle sur l'air, audio effectivement
entendu.

Journalisation : ce script reutilise les vrais loggers de la Suite
(logs/cat_server.log pour RadioService/PTTGuard/TransmissionService,
logs/voice.log pour VoiceService) -- memes fichiers qu'en production.

Interruption immediate : Ctrl+C a tout moment arrete toute transmission
en cours (PTT + audio) avant de quitter. Entre chaque scenario, une
invite permet aussi de s'arreter proprement (taper "q").

Les messages affiches a l'ecran (print/input) evitent volontairement
les caracteres accentues -- meme convention que les autres scripts
validate_*.py de ce depot ; les fichiers de log, eux, restent en UTF-8
avec les accents normaux.

Usage :
    python validate_contest_voice_integration.py [PORT] [BAUDRATE]

Par defaut : COM3, 19200 bauds.
"""

from __future__ import annotations

import shutil
import signal
import sys
import tempfile
import time
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

from apps.cat_server.ptt_guard import PTTGuard
from apps.cat_server.radio_service import RadioService
from apps.cat_server.transmission_service import TransmissionService
from apps.contest_assistant.message_service import ContestMessageService
from apps.contest_assistant.window import ContestAssistantWindow
from libraries.audio.audio_output_service import AudioOutputService
from libraries.station.station_service import StationService
from libraries.voice.voice_service import VoiceService

_LIVE_DATA_PATH = Path(__file__).resolve().parent / "logs" / "validate_contest_voice_integration_live.json"

# Reference au TransmissionService actif, utilisee par _emergency_stop()
# (Ctrl+C) : stop() relache le PTT ET coupe l'audio, quel que soit le
# scenario en cours -- meme logique que validate_transmission_service.py.
_active_transmission_service: TransmissionService | None = None


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

    if _active_transmission_service is not None and _active_transmission_service.is_transmitting:
        print("Transmission active detectee -> arret force (PTT + audio)...")
        _active_transmission_service.stop()
    else:
        print("Aucune transmission active.")

    sys.exit(1)


def _build_message_service(tmp_dir: Path) -> ContestMessageService:
    """
    ContestMessageService jetable, avec un unique modele de test
    couvrant les quatre variables resolues par la fenetre
    (%MYCALL%/%CALL%/%RST%/%SERIAL%) -- jamais data/contest_assistant.json.
    """

    seed_path = tmp_dir / "contest_assistant_seed.json"
    seed_path.write_text(
        '[{"label": "Test 4e-4", '
        '"text_fr": "Test %MYCALL% de %CALL%, %RST%, numero %SERIAL%.", '
        '"text_en": "Test %MYCALL% de %CALL%, %RST%, number %SERIAL%."}]',
        encoding="utf-8",
    )
    return ContestMessageService(
        config_path=tmp_dir / "contest_assistant.json",
        seed_path=seed_path,
    )


def _build_station_service(tmp_dir: Path) -> StationService:
    """StationService jetable, indicatif de test -- jamais data/station.json."""

    service = StationService(config_path=tmp_dir / "station.json")
    service.callsign = "ON3RT"
    return service


# ----------------------------------------------------------------------
# Scenarios
# ----------------------------------------------------------------------

def _scenario_1_initial_button_states(
    window, radio_service, transmission_service, voice_service, message_service, audio_service
) -> bool:
    print("Etat initial des boutons 'Annoncer'/'Envoyer' -- verification purement objective.")

    announce_enabled = window.btn_announce.isEnabled()
    send_enabled = window.btn_send.isEnabled()

    print(f"  -> btn_announce.isEnabled() = {announce_enabled} (attendu : True, services reels injectes)")
    print(f"  -> btn_send.isEnabled()     = {send_enabled} (attendu : True, inchange)")

    return announce_enabled and send_enabled


def _scenario_2_full_announce_pipeline(
    window, radio_service, transmission_service, voice_service, message_service, audio_service
) -> bool:
    print("Annonce complete : CAT + PTT + synthese + transmission + audio REELS, via le vrai bouton 'Annoncer'.")

    window.template_table.selectRow(0)
    window.edit_call.setText("F4XYZ")
    window.edit_rst.setText("599")

    serial_before = message_service.serial
    history_len_before = len(message_service.history)

    synth_events: list = []
    tx_events: list = []

    def _on_synth_finished(request_id, output_path):
        synth_events.append(output_path)

    def _on_synth_error(request_id, message):
        synth_events.append(("ERROR", message))

    def _on_tx_finished():
        tx_events.append("finished")

    def _on_tx_error(message):
        tx_events.append(("error", message))

    voice_service.synthesis_finished.connect(_on_synth_finished)
    voice_service.synthesis_error.connect(_on_synth_error)
    transmission_service.transmission_finished.connect(_on_tx_finished)
    transmission_service.transmission_error.connect(_on_tx_error)

    start = time.monotonic()
    window.btn_announce.click()

    button_disabled_immediately = not window.btn_announce.isEnabled()
    print(f"  -> bouton desactive immediatement apres le clic = {button_disabled_immediately} (attendu : True)")

    elapsed_s = 0.0
    while elapsed_s < 20.0 and not tx_events:
        _wait(0.1)
        elapsed_s += 0.1

    duration_s = time.monotonic() - start

    voice_service.synthesis_finished.disconnect(_on_synth_finished)
    voice_service.synthesis_error.disconnect(_on_synth_error)
    transmission_service.transmission_finished.disconnect(_on_tx_finished)
    transmission_service.transmission_error.disconnect(_on_tx_error)

    print(f"  -> duree totale synthese+transmission = {duration_s:.2f}s")
    print(f"  -> evenement(s) de synthese      = {synth_events}")
    print(f"  -> evenement(s) de transmission  = {tx_events}")

    pipeline_ok = bool(synth_events) and tx_events == ["finished"]
    button_reenabled = window.btn_announce.isEnabled()
    independence_ok = message_service.serial == serial_before and len(message_service.history) == history_len_before

    print(f"  -> bouton reactive a la fin                = {button_reenabled} (attendu : True)")
    print(f"  -> numero/historique inchanges (independance) = {independence_ok} (attendu : True)")

    if not (pipeline_ok and button_reenabled and independence_ok):
        return False

    ptt_ok = _ask("Le voyant TX de la radio s'est-il allume pendant la lecture, puis eteint a la fin ?")
    rf_ok = _ask("Une emission reelle a-t-elle bien eu lieu sur l'air (puissance reduite) ?")
    audio_ok = _ask("Avez-vous entendu le son distinctement ?")
    content_ok = _ask("Avez-vous entendu 'F4XYZ' et '599' (valeurs resolues), et non le gabarit litteral ?")
    voice_quality_ok = _ask("La voix etait-elle claire et comprehensible, en francais ?")

    return ptt_ok and rf_ok and audio_ok and content_ok and voice_quality_ok


def _scenario_3_ui_stays_responsive_during_announce(
    window, radio_service, transmission_service, voice_service, message_service, audio_service
) -> bool:
    print("Non-blocage de l'interface pendant l'annonce -- mesure objective par battements de minuterie.")

    window.template_table.selectRow(0)
    window.edit_call.setText("F4ABC")
    window.edit_rst.setText("579")

    heartbeat_count = {"n": 0}
    heartbeat_timer = QTimer()
    heartbeat_timer.setInterval(50)
    heartbeat_timer.timeout.connect(lambda: heartbeat_count.__setitem__("n", heartbeat_count["n"] + 1))
    heartbeat_timer.start()

    tx_events: list = []

    def _on_tx_finished():
        tx_events.append("finished")

    def _on_tx_error(message):
        tx_events.append(("error", message))

    transmission_service.transmission_finished.connect(_on_tx_finished)
    transmission_service.transmission_error.connect(_on_tx_error)

    start = time.monotonic()
    window.btn_announce.click()

    elapsed_s = 0.0
    while elapsed_s < 20.0 and not tx_events:
        _wait(0.1)
        elapsed_s += 0.1

    duration_s = time.monotonic() - start

    heartbeat_timer.stop()
    transmission_service.transmission_finished.disconnect(_on_tx_finished)
    transmission_service.transmission_error.disconnect(_on_tx_error)

    # Tolerance large (50%) : ce n'est pas un test de precision de
    # minuterie, seulement la preuve que la boucle d'evenements Qt n'a
    # jamais ete gelee pendant toute la duree de l'annonce -- si elle
    # l'avait ete, heartbeat_count serait proche de 0 quelle que soit
    # la duree ecoulee.
    expected_min_heartbeats = int((duration_s * 1000 / 50) * 0.5)

    print(f"  -> duree ecoulee = {duration_s:.2f}s")
    print(
        f"  -> battements de minuterie recus = {heartbeat_count['n']} "
        f"(attendu : au moins ~{expected_min_heartbeats}, preuve que l'interface n'a jamais gele)"
    )

    return bool(tx_events) and heartbeat_count["n"] >= expected_min_heartbeats


def _scenario_4_send_independent_after_announce(
    window, radio_service, transmission_service, voice_service, message_service, audio_service
) -> bool:
    print("'Envoyer' apres plusieurs annonces -- verification objective que son comportement reste inchange.")

    window.template_table.selectRow(0)
    window.edit_call.setText("F4XYZ")
    window.edit_rst.setText("599")

    serial_before = message_service.serial

    window.btn_send.click()

    serial_advanced = message_service.serial == serial_before + 1
    history_recorded = len(message_service.history) > 0
    last_entry = message_service.history[-1] if message_service.history else None

    print(f"  -> numero avant -> apres = {serial_before} -> {message_service.serial} (attendu : +1)")
    print(f"  -> dernier texte enregistre = {last_entry.resolved_text if last_entry else None}")

    content_ok = last_entry is not None and "F4XYZ" in last_entry.resolved_text

    return serial_advanced and history_recorded and content_ok


def _scenario_5_cat_unavailable_error_handling(
    window, radio_service, transmission_service, voice_service, message_service, audio_service
) -> bool:
    print("CAT indisponible pendant une annonce : la synthese doit reussir, la transmission doit echouer proprement.")

    window.template_table.selectRow(0)

    print("  -> deconnexion volontaire de la liaison CAT...")
    radio_service.disconnect()

    tx_errors: list = []

    def _on_tx_error(message):
        tx_errors.append(message)

    transmission_service.transmission_error.connect(_on_tx_error)

    window.btn_announce.click()

    elapsed_s = 0.0
    while elapsed_s < 20.0 and not tx_errors and not window.btn_announce.isEnabled():
        _wait(0.1)
        elapsed_s += 0.1

    transmission_service.transmission_error.disconnect(_on_tx_error)

    print(f"  -> erreur de transmission recue = {bool(tx_errors)} (attendu : True)")
    if tx_errors:
        print(f"     detail : {tx_errors[0]}")
    print(f"  -> message affiche dans la barre d'etat = {window.statusBar().currentMessage()!r}")
    print(f"  -> bouton reactive = {window.btn_announce.isEnabled()} (attendu : True)")

    error_handled = bool(tx_errors) and window.btn_announce.isEnabled() and not transmission_service.is_transmitting

    print("\n  -> reconnexion de la liaison CAT pour la suite...")
    reconnected = radio_service.connect()
    if reconnected:
        radio_service.timer.stop()
    print(f"  -> connect() = {reconnected} (attendu : True)")

    if not error_handled:
        return False

    ptt_stayed_off = _ask("Le voyant TX est-il reste eteint pendant tout ce scenario (aucune emission) ?")

    return error_handled and ptt_stayed_off and reconnected


def _scenario_6_window_closed_during_announce(
    window, radio_service, transmission_service, voice_service, message_service, audio_service
) -> bool:
    print(
        "Fermeture de Contest Assistant PENDANT une annonce en cours : ni plantage, ni gel, "
        "ni PTT bloque, ni audio orphelin."
    )

    window.template_table.selectRow(0)
    window.edit_call.setText("F4CLS")
    window.edit_rst.setText("559")

    tx_events: list = []

    def _on_tx_finished():
        tx_events.append("finished")

    def _on_tx_error(message):
        tx_events.append(("error", message))

    transmission_service.transmission_finished.connect(_on_tx_finished)
    transmission_service.transmission_error.connect(_on_tx_error)

    window.btn_announce.click()

    print("  -> attente du debut reel de la transmission (PTT actif) avant de fermer la fenetre...")
    elapsed_s = 0.0
    while elapsed_s < 20.0 and not transmission_service.is_transmitting and not tx_events:
        _wait(0.1)
        elapsed_s += 0.1

    transmitting_when_closed = transmission_service.is_transmitting
    print(f"  -> transmission en cours au moment de la fermeture = {transmitting_when_closed} (attendu : True)")

    print("  -> fermeture de la fenetre Contest Assistant (window.close())...")
    try:
        window.close()
        closed_without_crash = True
    except Exception as exc:
        print(f"  -> EXCEPTION pendant la fermeture de la fenetre : {exc!r}")
        closed_without_crash = False

    print(
        "  -> fenetre fermee ; attente de la fin naturelle de la transmission "
        "(service partage, independant de la fenetre -- voir docstring de window.py)..."
    )
    elapsed_s = 0.0
    while elapsed_s < 20.0 and not tx_events:
        _wait(0.1)
        elapsed_s += 0.1

    no_freeze = bool(tx_events)  # la boucle d'attente a recu un evenement : la Suite n'est pas gelee
    print(f"  -> evenement de transmission recu apres fermeture = {tx_events} (attendu : au moins un evenement)")

    transmission_service.transmission_finished.disconnect(_on_tx_finished)
    transmission_service.transmission_error.disconnect(_on_tx_error)

    ptt_not_stuck = not transmission_service.is_transmitting
    audio_not_orphaned = not audio_service.is_playing()

    print(f"  -> PTT non bloque (is_transmitting redevenu False) = {ptt_not_stuck} (attendu : True)")
    print(f"  -> aucune lecture audio orpheline (is_playing)     = {audio_not_orphaned} (attendu : True)")

    print("\n  -> reouverture de Contest Assistant pour clore proprement la validation...")
    window.show()

    window_state_consistent = window.btn_announce.isEnabled()
    print(f"  -> bouton 'Annoncer' correctement reactive apres reouverture = {window_state_consistent} (attendu : True)")

    objective_ok = (
        transmitting_when_closed
        and closed_without_crash
        and no_freeze
        and ptt_not_stuck
        and audio_not_orphaned
        and window_state_consistent
    )

    if not objective_ok:
        return False

    ptt_confirmed_off = _ask(
        "Le voyant TX s'est-il eteint normalement malgre la fermeture de la fenetre pendant "
        "l'annonce (pas de PTT bloque en emission) ?"
    )
    no_orphan_audio_heard = _ask(
        "N'avez-vous entendu AUCUN son residuel/en boucle apres la fermeture de la fenetre "
        "(pas de lecture audio orpheline) ?"
    )

    return ptt_confirmed_off and no_orphan_audio_heard


_SCENARIOS = (
    ("1/6 - Etat initial des boutons", _scenario_1_initial_button_states),
    ("2/6 - Annonce complete (CAT + PTT + voix + audio + RF reels)", _scenario_2_full_announce_pipeline),
    ("3/6 - Interface non bloquante pendant l'annonce", _scenario_3_ui_stays_responsive_during_announce),
    ("4/6 - 'Envoyer' independant apres plusieurs annonces", _scenario_4_send_independent_after_announce),
    ("5/6 - Gestion d'erreur : CAT indisponible", _scenario_5_cat_unavailable_error_handling),
    ("6/6 - Fermeture de la fenetre pendant une annonce en cours", _scenario_6_window_closed_during_announce),
)


def _print_safety_warning() -> None:
    print("=" * 70)
    print("!!! AVERTISSEMENT - A LIRE AVANT DE CONTINUER !!!")
    print("=" * 70)
    print("- La radio DOIT etre reliee a une charge adaptee ou a une")
    print("  antenne utilisable avant de lancer ce script.")
    print("- Reglez la puissance d'emission au MINIMUM pour ces essais.")
    print("- Ce script transmet reellement de l'audio sur l'air, via le")
    print("  vrai bouton 'Annoncer' de Contest Assistant, a plusieurs")
    print("  reprises, pendant quelques secondes a chaque fois.")
    print("- Ctrl+C interrompt ce script IMMEDIATEMENT, a tout moment, et")
    print("  arrete la transmission (PTT + audio) si une est en cours.")
    print("=" * 70)
    input("\nAppuyez sur Entree pour continuer, ou fermez cette fenetre pour annuler...")


def main() -> int:
    port = sys.argv[1] if len(sys.argv) > 1 else "COM3"
    baudrate = int(sys.argv[2]) if len(sys.argv) > 2 else 19200

    signal.signal(signal.SIGINT, _emergency_stop)

    print("=" * 70)
    print("ON3RT Radio Suite - Validation de l'integration Contest Assistant <-> Voix (etape 4e-4)")
    print("=" * 70)

    _print_safety_warning()

    app = QApplication.instance() or QApplication(sys.argv)

    print("\nJournaux detailles : logs/cat_server.log et logs/voice.log")
    print("Ctrl+C a tout moment : arret d'urgence (PTT + audio)")

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
        "\nEtes-vous pret a transmettre reellement sur l'air pour cette validation "
        "(charge/antenne connectee, puissance reduite) ?"
    ):
        print("Arret demande avant toute transmission.")
        radio_service.disconnect()
        return 1

    tmp_dir = Path(tempfile.mkdtemp(prefix="on3rt_validate_contest_voice_"))
    print(f"\nConfiguration temporaire (jetable, jamais les vraies donnees) : {tmp_dir}")

    audio_service = AudioOutputService()
    ptt_guard = PTTGuard(radio_service=radio_service)
    transmission_service = TransmissionService(audio_service=audio_service, ptt_guard=ptt_guard)
    voice_service = VoiceService(cache_dir=tmp_dir / "voice_cache")
    message_service = _build_message_service(tmp_dir)
    station_service = _build_station_service(tmp_dir)

    global _active_transmission_service
    _active_transmission_service = transmission_service

    window = ContestAssistantWindow(
        message_service=message_service,
        station_service=station_service,
        transmission_service=transmission_service,
        voice_service=voice_service,
    )
    window.show()

    synthesis_errors_seen: list[str] = []
    transmission_errors_seen: list[str] = []
    voice_service.synthesis_error.connect(lambda rid, msg: synthesis_errors_seen.append(msg))
    transmission_service.transmission_error.connect(lambda msg: transmission_errors_seen.append(msg))

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
                passed = func(window, radio_service, transmission_service, voice_service, message_service, audio_service)
            except Exception as exc:
                print(f"EXCEPTION NON GEREE pendant le scenario : {exc!r}")
                passed = False

            results[name] = passed
            print(f"\n-> RESULTAT : {'PASS' if passed else 'ECHEC'}")

    finally:
        if transmission_service.is_transmitting:
            print("\nNettoyage final : transmission encore active, arret...")
            transmission_service.stop()

        window.close()

        if not radio_service.connected:
            print("\nRadio non connectee : reconnexion pour la fermeture propre...")
            radio_service.connect()

        radio_service.disconnect()
        shutil.rmtree(tmp_dir, ignore_errors=True)

    print("\n" + "=" * 70)
    print("RESUME")
    print("=" * 70)

    for name, passed in results.items():
        print(f"  [{'PASS' if passed else 'ECHEC'}] {name}")

    if synthesis_errors_seen or transmission_errors_seen:
        print(
            f"\n{len(synthesis_errors_seen) + len(transmission_errors_seen)} erreur(s) observee(s) "
            "pendant la validation :"
        )
        for msg in synthesis_errors_seen:
            print(f"  - synthese     : {msg}")
        for msg in transmission_errors_seen:
            print(f"  - transmission : {msg}")

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
