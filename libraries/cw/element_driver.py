"""
ON3RT Radio Suite
libraries/cw/element_driver.py

ElementDriver : première implémentation concrète du contrat CWDriver
(libraries/cw/cw_driver.py) -- extraction pure de la logique de
pilotage élément par élément qui vivait auparavant directement dans
CWService. Comportement, timing et garanties strictement identiques ;
seul l'emplacement change (voir libraries/cw/ARCHITECTURE.md).

Pipeline : texte -> MorseEncoder -> TimingEngine -> QTimer -> backend
(KeyerBackend, key_down()/key_up() par élément). ElementDriver possède
et construit lui-même MorseEncoder/TimingEngine -- CWService ne les
connaît plus du tout, exactement la conséquence validée avec
l'utilisateur avant cette étape.

Deux minuteries internes, jamais partagées avec CWService :
  - _start_timer (0 ms, à chaque start()) : différé le temps d'un tour
    de boucle d'événements avant d'appeler on_started() et de démarrer
    le premier élément -- même principe que le CWService.singleShot(0,
    ...) d'origine (l'appelant ne doit jamais dépendre de la rapidité
    du traitement).
  - _element_timer : enchaîne chaque élément Morse (durée en
    millisecondes, tronquée -- limite déjà documentée dans l'ancien
    CWService, inchangée ici).
Utiliser de vraies instances QTimer (plutôt que la fonction statique
QTimer.singleShot()) pour les deux est un choix délibéré : cela permet
à stop() d'annuler un start() encore en attente. C'est une correction
d'une race pré-existante et jamais testée dans l'ancien CWService
(stop() appelé si vite après send() que le _start_sending() différé
n'avait pas encore eu lieu aurait laissé ce _start_sending() s'exécuter
malgré tout, après le stop() -- voir tests/test_element_driver.py::
test_stop_called_before_the_deferred_start_fires_cancels_it_entirely).

Aucune journalisation ici (contrainte explicite du contrat CWDriver) :
un échec de key_up() de sécurité (_safe_key_up) est absorbé
silencieusement, jamais journalisé -- c'est désormais entièrement à la
charge de CWService de journaliser à partir de ce que les callbacks
lui rapportent, jamais du driver lui-même.

start() peut lever une exception de façon SYNCHRONE (échec de
MorseEncoder.encode()/TimingEngine.apply(), par exemple un WPM
invalide) -- avant tout appel à on_started(), avant toute modification
de l'état interne du driver. CWService attrape cette exception et la
transforme en cw_error (voir docstring de cw_driver.py). Un échec
survenant APRÈS un démarrage réussi (ex. key_down() qui lève parce que
la radio s'est déconnectée en cours de route) ne lève jamais -- il
passe exclusivement par on_error(message).
"""

from __future__ import annotations

from PySide6.QtCore import QTimer

from libraries.cw.morse_encoder import MorseElementKind, MorseEncoder
from libraries.cw.timing import TimingEngine

_KEYING_KINDS = frozenset({MorseElementKind.DIT, MorseElementKind.DAH})


class ElementDriver:
    """Voir docstring du module pour l'ensemble des garanties fournies."""

    def __init__(self, backend) -> None:
        self._backend = backend
        self._encoder = MorseEncoder()

        self._start_timer = QTimer()
        self._start_timer.setSingleShot(True)
        self._start_timer.timeout.connect(self._on_start_timer)

        self._element_timer = QTimer()
        self._element_timer.setSingleShot(True)
        self._element_timer.timeout.connect(self._on_element_timer)

        self._owner: str | None = None
        self._timed_elements: list = []
        self._element_index = 0
        self._total_chars = 0
        self._last_reported_char_index: int | None = None

        self._on_started = None
        self._on_progress = None
        self._on_finished = None
        self._on_error = None

    # ------------------------------------------------------------------
    # Contrat CWDriver
    # ------------------------------------------------------------------

    def start(self, text, wpm, farnsworth_wpm, owner, on_started, on_progress, on_finished, on_error) -> None:
        """Voir docstring du module -- peut lever de façon synchrone (voir ci-dessus)."""

        elements = self._encoder.encode(text)
        timing_engine = TimingEngine(wpm=wpm, farnsworth_wpm=farnsworth_wpm)
        timed_elements = timing_engine.apply(elements)

        self._owner = owner
        self._timed_elements = timed_elements
        self._element_index = 0
        self._total_chars = len(text)
        self._last_reported_char_index = None

        self._on_started = on_started
        self._on_progress = on_progress
        self._on_finished = on_finished
        self._on_error = on_error

        self._start_timer.start(0)

    def stop(self) -> None:
        """Voir docstring du module -- annule aussi un start() encore en attente."""

        self._start_timer.stop()
        self._element_timer.stop()
        self._safe_key_up()

    # ------------------------------------------------------------------
    # Minuteries internes (jamais exposées à CWService)
    # ------------------------------------------------------------------

    def _on_start_timer(self) -> None:
        self._on_started()
        self._schedule_next_element()

    def _on_element_timer(self) -> None:
        self._schedule_next_element()

    def _schedule_next_element(self) -> None:
        if self._element_index >= len(self._timed_elements):
            self._finish_successfully()
            return

        element = self._timed_elements[self._element_index]

        try:
            if element.kind in _KEYING_KINDS:
                self._backend.key_down(owner=self._owner)
            else:
                self._backend.key_up()
        except Exception as exc:
            self._finish_with_error(str(exc))
            return

        if element.char_index != self._last_reported_char_index:
            self._last_reported_char_index = element.char_index
            self._on_progress(element.char_index)

        self._element_index += 1
        self._element_timer.start(max(0, int(element.duration_s * 1000)))

    # ------------------------------------------------------------------
    # Fin d'émission (succès ou échec) -- toujours relâcher la clé avant
    # d'appeler le callback de sortie correspondant.
    # ------------------------------------------------------------------

    def _finish_successfully(self) -> None:
        self._safe_key_up()
        self._on_finished()

    def _finish_with_error(self, message: str) -> None:
        self._safe_key_up()
        self._on_error(message)

    def _safe_key_up(self) -> None:
        try:
            self._backend.key_up()
        except Exception:
            pass
