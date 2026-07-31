"""
ON3RT Radio Suite
libraries/voice/voice_service.py

VoiceService : transforme un texte en fichier audio (WAV), avec cache
et résolution des variables %CLE% — rien de plus. Quatrième brique de
l'architecture Voix (AudioOutputService / PTTGuard / TransmissionService
/ VoiceService), totalement indépendante des trois autres : aucun
import vers apps.cat_server.*, ne pilote jamais le PTT ni la lecture
audio. Le futur TransmissionService reste l'unique consommateur qui
sait jouer le fichier produit ici — VoiceService ne le sait pas et n'a
pas besoin de le savoir.

Emplacement : libraries/voice/, comme AudioOutputService — aucune
dépendance CAT, contrairement à PTTGuard/TransmissionService qui
vivent dans apps/cat_server/ pour la raison inverse (voir leurs
docstrings respectives).

Paramètres regroupés (VoiceParams, voice_params.py) : un nouveau
paramètre de synthèse s'ajoute à VoiceParams, jamais à la signature de
synthesize().

Variables dynamiques : résolues (libraries/text/variable_resolver.py)
AVANT tout calcul de clé de cache — deux appels avec le même gabarit
mais des valeurs différentes ne partagent jamais un fichier ; deux
appels avec les mêmes valeurs résolues partagent le même fichier.

Déterminisme de la clé de cache : SHA-256 d'une chaîne canonique
combinant le texte déjà résolu + langue + MOTEUR RÉELLEMENT UTILISÉ
(jamais "auto" — résolu avant le calcul de la clé, sinon deux
synthèses "auto" à des moments différents, résolues vers des moteurs
différents si la disponibilité change, partageraient à tort la même
clé) + profil de voix + débit + volume, dans un ordre fixe (celui des
champs de VoiceParams). Ceci garantit que même entrée -> même clé ->
même fichier réutilisé, indépendamment du fait que le moteur
sous-jacent produise ou non des octets identiques à chaque synthèse
(ce que rien ici n'exige : une fois en cache, un fichier n'est plus
jamais re-synthétisé pour la même clé).

Éligibilité au cache : cacheable=True par défaut, mais décidée par
L'APPELANT (synthesize(..., cacheable=False)) — VoiceService ne peut
pas deviner si un texte déjà résolu correspond à un message fixe (CQ,
très rentable à mettre en cache) ou dynamique (l'échange contest avec
%RST%/%SERIAL%, quasi jamais réutilisé, cache inutile qui ferait
seulement grossir data/voice_cache/ indéfiniment). Un résultat non
cacheable est écrit dans data/voice_cache/tmp/ (sous-dossier distinct
de la clé de cache permanente), nettoyé par prune_cache() (étape 4c,
voir plus bas).

Nettoyage du cache (prune_cache(), étape 4c) : trois passes
indépendantes, chacune désactivable (paramètre à None) :
  1. tmp/ : supprime les *.wav plus vieux que max_tmp_age_hours —
     ces fichiers ne sont jamais relus par une clé de cache, un simple
     critère d'âge suffit.
  2. data/voice_cache/ (racine, jamais tmp/) : supprime les *.wav plus
     vieux que max_cache_age_days.
  3. Si la taille totale des *.wav restants à la racine dépasse
     max_total_size_mb, supprime les plus anciens un par un jusqu'à
     repasser sous le seuil.
Ne traite jamais que les fichiers *.wav (jamais un dossier ou un
fichier d'une autre nature qui se serait glissé là).

Sécurité vis-à-vis d'une synthèse en cours : self._pending_tasks
référence les chemins de sortie des tâches actuellement exécutées par
le QThreadPool (voir plus haut) — ces chemins sont systématiquement
exclus de toute suppression, quel que soit leur âge ou leur taille.
Protection redondante avec le tri "plus ancien d'abord" (un fichier en
cours d'écriture a toujours le mtime le plus récent, donc n'est
structurellement jamais choisi en premier) mais gardée en plus car peu
coûteuse.

Résilience : chaque suppression individuelle est protégée
(OSError) — un fichier verrouillé (ex. lu au même moment par
AudioOutputService sous Windows) est journalisé et ignoré, jamais une
exception qui remonterait à l'appelant. Toujours synchrone (pas de
QThreadPool) : uniquement des opérations fichier, jamais de synthèse.

Pas encore de déclenchement automatique : comme les trois autres
briques de l'architecture Voix, prune_cache() attend son premier vrai
consommateur (scheduler applicatif ou appel manuel) avant d'être
câblée quelque part — cohérent avec la validation étape par étape déjà
suivie pour AudioOutputService/PTTGuard/TransmissionService.

Sélection automatique de moteur : "auto" (params.engine=None) essaie
TOUJOURS Pyttsx3Engine, même depuis l'ajout de PiperEngine comme second
moteur (étape 4f) — un choix délibéré, pas un oubli : Piper reste
strictement optionnel (paquet piper-tts non installé par défaut,
modèles de voix jamais téléchargés automatiquement, à installer
manuellement dans data/piper_voices/), donc "auto" ne doit jamais
dépendre de sa présence. Piper n'est utilisé que sur demande explicite
(VoiceParams(engine="piper")). Un moteur explicitement demandé mais
indisponible (Piper y compris) retombe sur pyttsx3, avec un
avertissement journalisé — jamais une erreur qui bloquerait l'appelant
(cohérent avec "la Suite reste pleinement fonctionnelle sans Piper").

Exécution en arrière-plan (QThreadPool + QRunnable) : première
fonctionnalité de la Suite nécessitant réellement un travail hors du
thread principal Qt (tout le reste tourne via QTimer sur le thread
principal) — la synthèse, même rapide avec pyttsx3 (~0.2s mesuré sur
la machine de développement pour une courte phrase), reste une
opération bloquante qui ne doit jamais geler l'interface. synthesize()
retourne immédiatement un identifiant de requête (uuid4) ; le résultat
arrive via synthesis_finished(request_id, output_path) ou
synthesis_error(request_id, message) — y compris pour un succès de
cache (mêmes signaux, juste plus vite : émis via un
QTimer.singleShot(0, ...) pour ne jamais faire dépendre le
comportement observable par l'appelant du fait que le cache ait servi
ou non).

Compatible avec un futur mode "en mémoire" (sans fichier temporaire) :
rien ici n'empêche l'ajout ultérieur d'une méthode
synthesize_to_buffer(...) avec ses propres signaux, en plus de
synthesize() — une addition, jamais une modification de ce qui existe.

Plusieurs profils de voix futurs (voix système, voix clonée
principale/secondaire...) : déjà pris en charge par
VoiceParams.voice_profile (identifiant libre, résolu en interne) —
ajouter un profil est une question de configuration, jamais un
changement d'API.

Journalisation : libraries/voice/logger.py (VoiceLogger, fichier et
logger dédiés — voir sa docstring pour pourquoi pas CATLogger), avec
le demandeur (owner) tracé à chaque étape, même convention que
PTTGuard/TransmissionService.
"""

from __future__ import annotations

import hashlib
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Signal

from libraries.text.variable_resolver import resolve_variables
from libraries.voice.engines import PiperEngine, Pyttsx3Engine
from libraries.voice.logger import logger
from libraries.voice.voice_params import VoiceParams

DEFAULT_CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "voice_cache"


@dataclass(frozen=True, slots=True)
class PruneResult:
    """Bilan d'un passage de VoiceService.prune_cache() — voir sa docstring."""

    removed_files: int
    freed_bytes: int


class _SynthesisSignals(QObject):
    finished = Signal(str, float)  # output_path, duration_s
    error = Signal(str)


class _SynthesisTask(QRunnable):
    """Exécutée sur un thread du QThreadPool global — voir docstring du module."""

    def __init__(self, engine, text: str, params: VoiceParams, output_path: Path):
        super().__init__()
        self._engine = engine
        self._text = text
        self._params = params
        self._output_path = output_path
        self.signals = _SynthesisSignals()

    def run(self) -> None:
        start = time.monotonic()
        try:
            self._engine.synthesize(self._text, self._params, self._output_path)
            duration_s = time.monotonic() - start
            self.signals.finished.emit(str(self._output_path), duration_s)
        except Exception as exc:
            self.signals.error.emit(str(exc))


class VoiceService(QObject):
    """Voir docstring du module pour l'ensemble des garanties fournies."""

    synthesis_finished = Signal(str, str)  # request_id, output_path
    synthesis_error = Signal(str, str)     # request_id, message

    def __init__(self, cache_dir=None, parent=None):
        super().__init__(parent)

        self._cache_dir = Path(cache_dir) if cache_dir else DEFAULT_CACHE_DIR
        self._tmp_dir = self._cache_dir / "tmp"
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._tmp_dir.mkdir(parents=True, exist_ok=True)

        self._engines = {
            "pyttsx3": Pyttsx3Engine(),
            "piper": PiperEngine(),
        }

        # Références gardées le temps de la synthèse : QRunnable n'est
        # pas un QObject, rien d'autre ne garde ces tâches en vie tant
        # que QThreadPool les exécute.
        self._pending_tasks: dict[str, _SynthesisTask] = {}

    def synthesize(
        self,
        text: str,
        values: dict | None = None,
        params: VoiceParams | None = None,
        cacheable: bool = True,
        owner: str | None = None,
    ) -> str:
        """
        Démarre une synthèse, sans bloquer. Retourne un identifiant de
        requête ; le résultat arrive via synthesis_finished/synthesis_error,
        y compris pour un succès de cache — voir docstring du module.
        """

        request_id = uuid.uuid4().hex

        params = params or VoiceParams()
        resolved_text = resolve_variables(text, values) if values else text

        engine_name, engine = self._resolve_engine(params.engine, owner)

        logger.synthesis_requested(owner, engine_name)

        cache_key = self._compute_cache_key(resolved_text, engine_name, params)
        cache_path = self._cache_dir / f"{cache_key}.wav"

        if cacheable and cache_path.exists():
            logger.synthesis_cache_hit(owner, cache_key)
            self._emit_finished_async(request_id, str(cache_path))
            return request_id

        logger.synthesis_cache_miss(owner, cache_key)

        output_path = cache_path if cacheable else self._tmp_dir / f"{request_id}.wav"

        task = _SynthesisTask(engine, resolved_text, params, output_path)
        task.signals.finished.connect(
            lambda path, duration_s: self._on_task_finished(request_id, path, engine_name, duration_s, owner)
        )
        task.signals.error.connect(lambda message: self._on_task_error(request_id, message, owner))

        self._pending_tasks[request_id] = task
        QThreadPool.globalInstance().start(task)

        return request_id

    # ------------------------------------------------------------------
    # Sélection de moteur
    # ------------------------------------------------------------------

    def _resolve_engine(self, requested_name: str | None, owner: str | None):
        if requested_name is not None:
            engine = self._engines.get(requested_name)
            if engine is not None and engine.is_available():
                return requested_name, engine
            reason = "moteur inconnu" if engine is None else "non installé"
            logger.synthesis_engine_fallback(owner, requested_name, reason)

        return "pyttsx3", self._engines["pyttsx3"]

    # ------------------------------------------------------------------
    # Cache
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_cache_key(resolved_text: str, engine_name: str, params: VoiceParams) -> str:
        canonical = "|".join(
            str(part)
            for part in (
                resolved_text,
                params.language,
                engine_name,
                params.voice_profile,
                params.rate,
                params.volume,
            )
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def _emit_finished_async(self, request_id: str, output_path: str) -> None:
        QTimer.singleShot(0, lambda: self.synthesis_finished.emit(request_id, output_path))

    # ------------------------------------------------------------------
    # Callbacks de fin de tâche
    # ------------------------------------------------------------------

    def _on_task_finished(self, request_id: str, output_path: str, engine_name: str, duration_s: float, owner) -> None:
        self._pending_tasks.pop(request_id, None)
        logger.synthesis_completed(owner, engine_name, duration_s)
        self.synthesis_finished.emit(request_id, output_path)

    def _on_task_error(self, request_id: str, message: str, owner) -> None:
        self._pending_tasks.pop(request_id, None)
        logger.synthesis_error(owner, message)
        self.synthesis_error.emit(request_id, message)

    # ------------------------------------------------------------------
    # Nettoyage du cache (prune_cache) — voir docstring du module
    # ------------------------------------------------------------------

    def prune_cache(
        self,
        max_cache_age_days: float | None = 30,
        max_tmp_age_hours: float | None = 24,
        max_total_size_mb: float | None = 200,
    ) -> PruneResult:
        """
        Nettoie data/voice_cache/ en trois passes indépendantes (chacune
        désactivable via None) — voir docstring du module pour le détail
        et les garanties de sécurité. Ne touche jamais qu'à des *.wav.
        """

        now = time.time()
        protected_paths = {task._output_path for task in self._pending_tasks.values()}

        removed_files = 0
        freed_bytes = 0

        if max_tmp_age_hours is not None:
            n, b = self._remove_files_older_than(
                self._tmp_dir, max_tmp_age_hours * 3600.0, now, protected_paths
            )
            removed_files += n
            freed_bytes += b

        if max_cache_age_days is not None:
            n, b = self._remove_files_older_than(
                self._cache_dir, max_cache_age_days * 86400.0, now, protected_paths
            )
            removed_files += n
            freed_bytes += b

        if max_total_size_mb is not None:
            n, b = self._enforce_total_size(
                self._cache_dir, max_total_size_mb * 1024 * 1024, protected_paths
            )
            removed_files += n
            freed_bytes += b

        logger.cache_pruned(removed_files, freed_bytes)
        return PruneResult(removed_files=removed_files, freed_bytes=freed_bytes)

    def _remove_files_older_than(
        self,
        directory: Path,
        max_age_s: float,
        now: float,
        protected_paths: set[Path],
    ) -> tuple[int, int]:
        removed_files = 0
        freed_bytes = 0

        for path in directory.glob("*.wav"):
            if path in protected_paths:
                continue
            try:
                age_s = now - path.stat().st_mtime
            except OSError as exc:
                logger.cache_prune_file_error(str(path), str(exc))
                continue
            if age_s < max_age_s:
                continue
            removed_files_delta, freed_bytes_delta = self._try_remove(path)
            removed_files += removed_files_delta
            freed_bytes += freed_bytes_delta

        return removed_files, freed_bytes

    def _enforce_total_size(
        self, directory: Path, max_total_bytes: float, protected_paths: set[Path]
    ) -> tuple[int, int]:
        entries: list[tuple[float, int, Path]] = []
        total_bytes = 0

        for path in directory.glob("*.wav"):
            try:
                stat = path.stat()
            except OSError as exc:
                logger.cache_prune_file_error(str(path), str(exc))
                continue
            entries.append((stat.st_mtime, stat.st_size, path))
            total_bytes += stat.st_size

        if total_bytes <= max_total_bytes:
            return 0, 0

        entries.sort(key=lambda entry: entry[0])  # plus ancien d'abord

        removed_files = 0
        freed_bytes = 0

        for _mtime, size, path in entries:
            if total_bytes <= max_total_bytes:
                break
            if path in protected_paths:
                continue
            removed_files_delta, freed_bytes_delta = self._try_remove(path)
            if removed_files_delta:
                total_bytes -= size
            removed_files += removed_files_delta
            freed_bytes += freed_bytes_delta

        return removed_files, freed_bytes

    @staticmethod
    def _try_remove(path: Path) -> tuple[int, int]:
        try:
            size = path.stat().st_size
            path.unlink()
        except OSError as exc:
            logger.cache_prune_file_error(str(path), str(exc))
            return 0, 0
        return 1, size
