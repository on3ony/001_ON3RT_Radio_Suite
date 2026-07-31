#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
validate_voice_service.py
-------------------------------------------------
ON3RT Radio Suite - Validation de VoiceService (etape 4d de l'architecture Voix)

Outil de validation autonome pour libraries/voice/voice_service.py
(VoiceService) et sa gestion automatique du cache (prune_cache(),
étape 4c), avec le VRAI moteur pyttsx3 et la VRAIE lecture audio
(AudioOutputService, déjà validée matériellement à l'étape 1) — ce que
la suite automatisée (tests/test_voice_service.py, 36 tests) ne peut
pas prouver, puisqu'elle remplace systématiquement le moteur par un
faux (_FakeEngine) pour rester rapide et déterministe.

Ce script EST un consommateur de VoiceService comme un autre, au même
titre que validate_ptt_guard.py/validate_transmission_service.py le
sont pour PTTGuard/TransmissionService — même esprit, mais sans aucun
matériel CAT/RF : VoiceService n'importe rien de apps.cat_server.*, ne
pilote ni PTT ni radio. Rien n'est émis sur l'air, aucune radio n'est
requise.

L'agent ne peut juger que des propriétés MESURABLES (fichier produit,
durée de synthèse, format WAV, chemin réutilisé ou non, comportement
du cache) — jamais la qualité audio elle-même (clarté, langue,
contenu réellement prononcé). Chaque scénario qui l'exige demande donc
une confirmation humaine explicite après une lecture réelle ; les
scénarios purement mesurables (cache HIT, tmp/, repli moteur,
prune_cache) ne demandent rien à l'opérateur.

data/voice_cache/ (le vrai cache de production) n'est jamais touché :
VoiceService est construit ici avec un répertoire de cache temporaire
et jetable (tempfile.mkdtemp()), supprimé à la fin — même logique que
la redirection de data/live.json vers un fichier de pont jetable dans
les scripts de validation CAT.

Journalisation : ce script réutilise le vrai VoiceLogger
(libraries/voice/logger.py, logs/voice.log), déjà utilisé par
VoiceService en production — même convention que la réutilisation du
logger CAT_SERVER réel dans les scripts de validation CAT.

Interruption immédiate : Ctrl+C à tout moment arrête toute lecture
audio en cours (AudioOutputService.stop()) avant de quitter. Entre
chaque scénario, une invite permet aussi de s'arrêter proprement
(taper "q").

Les messages affichés à l'écran (print/input) évitent volontairement
les caractères accentués — même convention que civ_diagnostic.py/
validate_ptt_guard.py/validate_transmission_service.py ; logs/voice.log,
lui, reste en UTF-8 avec les accents normaux.

Usage :
    python validate_voice_service.py

Aucun argument : contrairement aux scripts de validation CAT, aucune
radio n'est impliquée.
"""

from __future__ import annotations

import os
import shutil
import signal
import sys
import tempfile
import time
import wave
from pathlib import Path
from types import SimpleNamespace

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

from libraries.audio.audio_output_service import AudioOutputService
from libraries.voice.voice_params import VoiceParams
from libraries.voice.voice_service import VoiceService

# Référence à l'AudioOutputService actif, utilisée par _emergency_stop()
# (Ctrl+C) : contrairement aux scripts de validation CAT, il n'y a ici
# aucun PTT à relâcher -- seulement une éventuelle lecture audio en
# cours à interrompre proprement.
_active_audio_service: AudioOutputService | None = None


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

    if _active_audio_service is not None and _active_audio_service.is_playing():
        print("Lecture audio en cours detectee -> arret...")
        _active_audio_service.stop()
    else:
        print("Aucune lecture en cours.")

    sys.exit(1)


def _synthesize_and_wait(
    service: VoiceService,
    text: str,
    values: dict | None = None,
    params: VoiceParams | None = None,
    cacheable: bool = True,
    owner: str = "validate_voice_service",
    timeout_s: float = 10.0,
) -> SimpleNamespace:
    """
    Lance une synthese et attend son resultat (fini ou erreur), avec
    mesure de la duree ecoulee -- equivalent, pour ce script autonome,
    de _wait_for_signal() dans tests/test_voice_service.py.
    """

    request_id_holder: dict[str, str | None] = {"id": None}
    finished: list[str] = []
    errored: list[str] = []

    def _on_finished(rid: str, output_path: str) -> None:
        if rid == request_id_holder["id"]:
            finished.append(output_path)

    def _on_error(rid: str, message: str) -> None:
        if rid == request_id_holder["id"]:
            errored.append(message)

    service.synthesis_finished.connect(_on_finished)
    service.synthesis_error.connect(_on_error)

    start = time.monotonic()
    request_id = service.synthesize(text, values=values, params=params, cacheable=cacheable, owner=owner)
    request_id_holder["id"] = request_id

    elapsed_s = 0.0
    tick_s = 0.05
    while elapsed_s < timeout_s and not finished and not errored:
        _wait(tick_s)
        elapsed_s += tick_s

    service.synthesis_finished.disconnect(_on_finished)
    service.synthesis_error.disconnect(_on_error)

    duration_s = time.monotonic() - start

    return SimpleNamespace(
        request_id=request_id,
        output_path=Path(finished[0]) if finished else None,
        error=errored[0] if errored else None,
        duration_s=duration_s,
    )


def _read_wav_properties(path: Path) -> dict:
    with wave.open(str(path), "rb") as f:
        frames = f.getnframes()
        rate = f.getframerate()
        channels = f.getnchannels()
        sampwidth = f.getsampwidth()

    return {
        "frames": frames,
        "rate": rate,
        "channels": channels,
        "sampwidth": sampwidth,
        "duration_s": (frames / rate) if rate else 0.0,
    }


def _touch_wav(path: Path, size: int = 8, age_s: float = 0.0) -> None:
    """Cree un faux .wav de `size` octets, vieux de `age_s` secondes (mtime) -- pour prune_cache()."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x00" * size)
    if age_s:
        timestamp = time.time() - age_s
        os.utime(path, (timestamp, timestamp))


# ----------------------------------------------------------------------
# Scenarios
# ----------------------------------------------------------------------

def _scenario_1_basic_synthesis(service: VoiceService, audio_service: AudioOutputService) -> bool:
    print("Synthese de base (cache MISS) : proprietes mesurables du fichier produit, puis lecture reelle.")

    text = "Bonjour, ceci est un test du service vocal ON3RT."
    result = _synthesize_and_wait(service, text, cacheable=True)

    print(f"  -> synthese terminee en {result.duration_s:.3f}s (attendu : jamais instantanee en cache MISS)")

    if result.error:
        print(f"  -> ECHEC : erreur de synthese recue : {result.error}")
        return False

    if result.output_path is None or not result.output_path.exists():
        print("  -> ECHEC : aucun fichier produit.")
        return False

    props = _read_wav_properties(result.output_path)
    print(f"  -> fichier : {result.output_path.name}")
    print(
        f"  -> proprietes WAV : {props['channels']} canal(aux), {props['rate']} Hz, "
        f"{props['sampwidth'] * 8} bits, duree audio = {props['duration_s']:.2f}s"
    )

    properties_ok = props["frames"] > 0 and props["rate"] > 0 and props["duration_s"] > 0

    playback_events: list[bool] = []
    audio_service.playback_finished.connect(lambda: playback_events.append(True))

    print("  -> Lecture du fichier via AudioOutputService...")
    audio_service.play_file(str(result.output_path))

    wait_elapsed = 0.0
    while wait_elapsed < 10.0 and not playback_events:
        _wait(0.1)
        wait_elapsed += 0.1

    audio_service.playback_finished.disconnect()

    heard_clearly = _ask("Avez-vous entendu un son clair, en francais ?")

    return properties_ok and bool(playback_events) and heard_clearly


def _scenario_2_cache_hit(service: VoiceService, audio_service: AudioOutputService) -> bool:
    print("Cache HIT : meme texte, memes parametres -- le 2e appel doit reutiliser le fichier, sans resynthese.")

    text = "CQ CQ CQ de test, cache hit."
    first = _synthesize_and_wait(service, text, cacheable=True)
    if first.error:
        print(f"  -> ECHEC : erreur au premier appel : {first.error}")
        return False

    second = _synthesize_and_wait(service, text, cacheable=True)
    if second.error:
        print(f"  -> ECHEC : erreur au deuxieme appel : {second.error}")
        return False

    print(f"  -> duree 1er appel (cache MISS)      = {first.duration_s:.3f}s")
    print(f"  -> duree 2e appel (cache HIT attendu) = {second.duration_s:.3f}s (attendu : nettement plus court)")

    same_file = first.output_path == second.output_path
    clearly_faster = second.duration_s < first.duration_s

    print(f"  -> meme fichier reutilise = {same_file} (attendu : True)")

    return same_file and clearly_faster


def _scenario_3_variable_resolution(service: VoiceService, audio_service: AudioOutputService) -> bool:
    print("Resolution de variables %CLE% : le texte RESOLU doit etre synthetise, jamais le gabarit litteral.")

    values = {"CALL": "F4AAA", "RST": "599"}
    result = _synthesize_and_wait(service, "%CALL% %RST%", values=values, cacheable=False)

    if result.error:
        print(f"  -> ECHEC : erreur de synthese : {result.error}")
        return False

    if result.output_path is None:
        print("  -> ECHEC : aucun fichier produit.")
        return False

    print(f"  -> fichier produit : {result.output_path.name}")

    playback_events: list[bool] = []
    audio_service.playback_finished.connect(lambda: playback_events.append(True))

    audio_service.play_file(str(result.output_path))
    wait_elapsed = 0.0
    while wait_elapsed < 10.0 and not playback_events:
        _wait(0.1)
        wait_elapsed += 0.1

    audio_service.playback_finished.disconnect()

    heard_resolved = _ask(
        "Avez-vous entendu 'F4AAA 599' (valeurs resolues), et non le gabarit litteral '%CALL% %RST%' ?"
    )

    return bool(playback_events) and heard_resolved


def _scenario_4_cacheable_false_tmp(service: VoiceService, audio_service: AudioOutputService) -> bool:
    print("cacheable=False : chaque appel doit ecrire dans tmp/ un NOUVEAU fichier, jamais reutilise.")

    text = "Message dynamique de concours, jamais mis en cache."
    first = _synthesize_and_wait(service, text, cacheable=False)
    second = _synthesize_and_wait(service, text, cacheable=False)

    if first.error or second.error:
        print(f"  -> ECHEC : erreur de synthese ({first.error or second.error})")
        return False

    print(f"  -> 1er fichier : {first.output_path}")
    print(f"  -> 2e fichier  : {second.output_path}")

    both_in_tmp = (
        first.output_path is not None
        and second.output_path is not None
        and first.output_path.parent.name == "tmp"
        and second.output_path.parent.name == "tmp"
    )
    never_reused = first.output_path != second.output_path

    print(f"  -> les deux dans tmp/ = {both_in_tmp} (attendu : True)")
    print(f"  -> jamais reutilise = {never_reused} (attendu : True)")

    return both_in_tmp and never_reused


def _scenario_5_engine_fallback(service: VoiceService, audio_service: AudioOutputService) -> bool:
    print("Moteur demande inconnu ('does_not_exist') : repli automatique sur pyttsx3, sans erreur.")

    result = _synthesize_and_wait(
        service,
        "Repli automatique sur le moteur par defaut.",
        params=VoiceParams(engine="does_not_exist"),
        cacheable=False,
    )

    print(f"  -> erreur recue = {result.error} (attendu : None)")
    print(f"  -> fichier produit = {result.output_path} (attendu : un fichier existant)")

    return result.error is None and result.output_path is not None and result.output_path.exists()


def _scenario_6_prune_cache(service: VoiceService, audio_service: AudioOutputService) -> bool:
    print("prune_cache() sur le vrai systeme de fichiers Windows (repertoire jetable) : eviction reelle par age.")

    old_cache = service._cache_dir / "old_fake_cache_entry.wav"
    _touch_wav(old_cache, age_s=40 * 86400)
    recent_cache = service._cache_dir / "recent_fake_cache_entry.wav"
    _touch_wav(recent_cache, age_s=0)

    old_tmp = service._tmp_dir / "old_fake_tmp_entry.wav"
    _touch_wav(old_tmp, age_s=30 * 3600)
    recent_tmp = service._tmp_dir / "recent_fake_tmp_entry.wav"
    _touch_wav(recent_tmp, age_s=0)

    result = service.prune_cache(max_cache_age_days=30, max_tmp_age_hours=24, max_total_size_mb=None)

    print(f"  -> PruneResult : {result.removed_files} fichier(s) supprime(s), {result.freed_bytes} octet(s) liberes")

    old_cache_removed = not old_cache.exists()
    recent_cache_kept = recent_cache.exists()
    old_tmp_removed = not old_tmp.exists()
    recent_tmp_kept = recent_tmp.exists()

    print(f"  -> vieux fichier cache supprime  = {old_cache_removed} (attendu : True)")
    print(f"  -> fichier cache recent conserve = {recent_cache_kept} (attendu : True)")
    print(f"  -> vieux fichier tmp supprime    = {old_tmp_removed} (attendu : True)")
    print(f"  -> fichier tmp recent conserve   = {recent_tmp_kept} (attendu : True)")

    return old_cache_removed and recent_cache_kept and old_tmp_removed and recent_tmp_kept


def _scenario_7_continuous_use(service: VoiceService, audio_service: AudioOutputService) -> bool:
    print(
        "Usage continu : plusieurs syntheses lancees sans attente entre elles, puis lecture successive "
        "des fichiers produits -- verifie l'absence de blocage/verrou (reutilisation du meme QThreadPool, "
        "voir engines.py)."
    )

    texts = [
        "Premier message de la sequence.",
        "Deuxieme message de la sequence.",
        "Troisieme message de la sequence.",
        "Quatrieme message de la sequence.",
        "Cinquieme message de la sequence.",
    ]

    finished: dict[str, str] = {}
    errored: dict[str, str] = {}

    def _on_finished(rid: str, output_path: str) -> None:
        finished[rid] = output_path

    def _on_error(rid: str, message: str) -> None:
        errored[rid] = message

    service.synthesis_finished.connect(_on_finished)
    service.synthesis_error.connect(_on_error)

    request_ids = [service.synthesize(text, cacheable=False, owner="validate_voice_service") for text in texts]
    print(f"  -> {len(request_ids)} syntheses lancees sans attente entre elles (toutes cacheable=False)")

    timeout_s = 15.0
    tick_s = 0.1
    elapsed_s = 0.0
    while elapsed_s < timeout_s and (len(finished) + len(errored)) < len(request_ids):
        _wait(tick_s)
        elapsed_s += tick_s

    service.synthesis_finished.disconnect(_on_finished)
    service.synthesis_error.disconnect(_on_error)

    all_arrived = (len(finished) + len(errored)) == len(request_ids)
    print(
        f"  -> resultats recus = {len(finished) + len(errored)}/{len(request_ids)} en ~{elapsed_s:.1f}s "
        f"(attendu : {len(request_ids)}/{len(request_ids)}, aucun blocage)"
    )

    if errored:
        print(f"  -> {len(errored)} erreur(s) recue(s) (attendu : 0) :")
        for rid, message in errored.items():
            print(f"     - {rid} : {message}")

    if not all_arrived or errored:
        return False

    print("  -> Lecture successive des fichiers produits...")

    playback_events: list[bool] = []
    playback_errors: list[str] = []
    audio_service.playback_finished.connect(lambda: playback_events.append(True))
    audio_service.playback_error.connect(lambda message: playback_errors.append(message))

    for index, rid in enumerate(request_ids, start=1):
        path = finished.get(rid)
        if not path:
            continue

        print(f"     -> lecture {index}/{len(request_ids)} : {Path(path).name}")
        events_before = len(playback_events) + len(playback_errors)

        audio_service.play_file(path)

        wait_elapsed = 0.0
        while wait_elapsed < 10.0 and (len(playback_events) + len(playback_errors)) <= events_before:
            _wait(0.1)
            wait_elapsed += 0.1

    audio_service.playback_finished.disconnect()
    audio_service.playback_error.disconnect()

    if playback_errors:
        print(f"  -> {len(playback_errors)} erreur(s) de lecture (attendu : 0) : {playback_errors}")

    no_freeze_confirmed = _ask(
        "Avez-vous entendu les 5 messages joues les uns a la suite des autres, sans blocage ni son fige ?"
    )

    return not playback_errors and no_freeze_confirmed


_SCENARIOS = (
    ("1/7 - Synthese de base + lecture reelle", _scenario_1_basic_synthesis),
    ("2/7 - Cache HIT", _scenario_2_cache_hit),
    ("3/7 - Resolution de variables %CLE%", _scenario_3_variable_resolution),
    ("4/7 - cacheable=False / tmp", _scenario_4_cacheable_false_tmp),
    ("5/7 - Repli moteur inconnu -> pyttsx3", _scenario_5_engine_fallback),
    ("6/7 - prune_cache() reel sur disque", _scenario_6_prune_cache),
    ("7/7 - Usage continu (plusieurs syntheses/lectures successives)", _scenario_7_continuous_use),
)


def _print_info_banner() -> None:
    print("=" * 70)
    print("A LIRE AVANT DE CONTINUER")
    print("=" * 70)
    print("- Ce script utilise reellement pyttsx3 (synthese vocale) et")
    print("  AudioOutputService (lecture audio locale) -- casque ou")
    print("  haut-parleurs necessaires pour repondre aux questions.")
    print("- Aucun materiel CAT/RF n'est implique : rien n'est emis sur")
    print("  l'air, aucune radio n'est requise.")
    print("- Un repertoire de cache temporaire et jetable est utilise :")
    print("  data/voice_cache/ (le vrai cache de production) n'est")
    print("  jamais touche.")
    print("- Ctrl+C interrompt ce script IMMEDIATEMENT, a tout moment, et")
    print("  arrete la lecture audio en cours si une est active.")
    print("=" * 70)
    input("\nAppuyez sur Entree pour continuer, ou fermez cette fenetre pour annuler...")


def main() -> int:
    signal.signal(signal.SIGINT, _emergency_stop)

    print("=" * 70)
    print("ON3RT Radio Suite - Validation de VoiceService (etape 4d)")
    print("=" * 70)

    _print_info_banner()

    app = QApplication.instance() or QApplication(sys.argv)

    print("\nJournal detaille : logs/voice.log")
    print("Ctrl+C a tout moment : arret d'urgence de la lecture en cours")

    tmp_dir = Path(tempfile.mkdtemp(prefix="on3rt_validate_voice_service_"))
    print(f"Repertoire de cache temporaire (jetable) : {tmp_dir}")

    service = VoiceService(cache_dir=tmp_dir)
    audio_service = AudioOutputService()

    global _active_audio_service
    _active_audio_service = audio_service

    synthesis_errors_seen: list[str] = []
    playback_errors_seen: list[str] = []
    service.synthesis_error.connect(lambda request_id, message: synthesis_errors_seen.append(message))
    audio_service.playback_error.connect(lambda message: playback_errors_seen.append(message))

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
                passed = func(service, audio_service)
            except Exception as exc:
                print(f"EXCEPTION NON GEREE pendant le scenario : {exc!r}")
                passed = False

            results[name] = passed
            print(f"\n-> RESULTAT : {'PASS' if passed else 'ECHEC'}")

    finally:
        if audio_service.is_playing():
            print("\nNettoyage final : lecture encore active, arret...")
            audio_service.stop()

        shutil.rmtree(tmp_dir, ignore_errors=True)

    print("\n" + "=" * 70)
    print("RESUME")
    print("=" * 70)

    for name, passed in results.items():
        print(f"  [{'PASS' if passed else 'ECHEC'}] {name}")

    if synthesis_errors_seen or playback_errors_seen:
        print(
            f"\n{len(synthesis_errors_seen) + len(playback_errors_seen)} erreur(s) observee(s) "
            "pendant la validation :"
        )
        for msg in synthesis_errors_seen:
            print(f"  - synthese : {msg}")
        for msg in playback_errors_seen:
            print(f"  - lecture  : {msg}")

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
