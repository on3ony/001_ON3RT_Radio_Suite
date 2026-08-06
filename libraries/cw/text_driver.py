"""
ON3RT Radio Suite
libraries/cw/text_driver.py

TextDriver : seconde implémentation concrète du contrat CWDriver
(libraries/cw/cw_driver.py), pour la famille "text" (voir
libraries/cw/ARCHITECTURE.md) -- un backend qui reçoit du texte brut et
génère lui-même le timing Morse (ex. CI-V 0x17 de l'IC-7300, un
Winkeyer en mode host, Hamlib).

Indépendance totale vis-à-vis du protocole utilisé (contrainte
explicite validée avec l'utilisateur) : TextDriver ne connaît RIEN du
CI-V, de l'IC-7300, de Hamlib, d'un Winkeyer, ni d'aucune limite de
caractères codée en dur -- la SEULE propriété du backend qu'il lit est
max_chunk_chars (contrat TextBackend, libraries/cw/keyer_backend.py).
Si un futur backend accepte 60 caractères, une longueur illimitée, ou
un tout autre protocole, seul ce backend change -- jamais TextDriver.

Découpage : en morceaux d'au plus max_chunk_chars caractères (découpage
naïf par position, aucune notion de limite de mot -- volontairement
simple ; à affiner plus tard si un besoin réel est constaté sur
matériel). max_chunk_chars absent, None ou <= 0 : traité comme
"illimité", un seul morceau contient tout le texte.

Estimation, jamais un vrai pilotage : TextDriver réutilise MorseEncoder
+ TimingEngine, mais UNIQUEMENT pour estimer la durée totale et générer
des points de progression SIMULÉS -- c'est le matériel qui génère le
timing réel, jamais ce driver. on_progress()/on_finished() ne sont
donc jamais une confirmation matérielle, toujours une estimation
logicielle -- documenté ici explicitement pour ne jamais laisser croire
le contraire à un futur lecteur (UI comprise).

Chaque morceau est envoyé via backend.send_text() dès l'instant estimé
de son début (le premier morceau immédiatement après le démarrage
différé, les suivants après la durée estimée du morceau précédent) --
règle générale utile à tout backend texte pour ne jamais superposer
deux envois sur la même ressource matérielle, jamais une particularité
d'un protocole précis. send_text() est appelé même pour un morceau dont
AUCUN caractère n'est reconnu par MorseEncoder : la table de caractères
du matériel peut être plus large que la nôtre -- seule l'ESTIMATION de
durée dépend de MorseEncoder, jamais l'envoi réel. C'est une différence
assumée avec ElementDriver, où un texte entièrement non supporté ne
touche jamais le backend (là-bas, c'est notre propre encodage qui
pilote le matériel élément par élément ; ici, le matériel reçoit le
texte brut quoi qu'il arrive).

Aucune journalisation ici (même contrainte que ElementDriver, contrat
CWDriver) : stop() absorbe silencieusement un échec de
backend.stop_sending(), jamais journalisé.

backend.stop_sending() est appelé aussi bien sur un arrêt explicite
(stop()) que sur une fin NORMALE d'émission (bug réel trouvé lors de la
validation matérielle du chantier CW Decode, 2026-08-02, avec
CIVTextKeyerBackend) : la ressource acquise par le backend au moment de
send_text() (le PTT, pour CIVTextKeyerBackend) n'a auparavant jamais été
relâchée après une fin normale -- seul un stop() explicite le faisait.
Un second envoi consécutif, même normal (ex. deux macros envoyées à
quelques secondes d'intervalle), échouait alors avec "PTT déjà activé",
le seul filet de sécurité restant étant la minuterie de secours de
PTTGuard (30 secondes). Même symétrie que ElementDriver._finish_successfully()
(_safe_key_up() avant on_finished()) : le relâchement précède toujours
la notification de fin, jamais l'inverse.
"""

from __future__ import annotations

from PySide6.QtCore import QTimer

from libraries.cw.morse_encoder import MorseEncoder
from libraries.cw.timing import TimingEngine


def _chunk_text(text: str, max_chunk_chars: int | None) -> list[str]:
    if not text:
        return []
    if not max_chunk_chars or max_chunk_chars <= 0:
        return [text]
    return [text[i:i + max_chunk_chars] for i in range(0, len(text), max_chunk_chars)]


class TextDriver:
    """Voir docstring du module pour l'ensemble des garanties fournies."""

    def __init__(self, backend) -> None:
        self._backend = backend
        self._encoder = MorseEncoder()

        self._start_timer = QTimer()
        self._start_timer.setSingleShot(True)
        self._start_timer.timeout.connect(self._on_start_timer)

        self._event_timer = QTimer()
        self._event_timer.setSingleShot(True)
        self._event_timer.timeout.connect(self._on_event_timer)

        self._events: list[tuple[float, str, object]] = []
        self._event_index = 0
        self._owner: str | None = None
        self._wpm = None
        self._farnsworth_wpm = None

        self._on_started = None
        self._on_progress = None
        self._on_finished = None
        self._on_error = None

    # ------------------------------------------------------------------
    # Contrat CWDriver
    # ------------------------------------------------------------------

    def start(self, text, wpm, farnsworth_wpm, owner, on_started, on_progress, on_finished, on_error) -> None:
        """Voir docstring du module -- peut lever de façon synchrone (WPM invalide, par ex.)."""

        # Valide wpm/farnsworth_wpm de façon synchrone, avant tout
        # découpage ni callback -- même comportement que ElementDriver,
        # y compris pour un texte vide (voir ARCHITECTURE.md).
        timing_engine = TimingEngine(wpm=wpm, farnsworth_wpm=farnsworth_wpm)

        max_chunk_chars = getattr(self._backend, "max_chunk_chars", None)
        chunks = _chunk_text(text, max_chunk_chars)

        self._events = self._build_events(chunks, timing_engine)
        self._event_index = 0
        self._owner = owner
        self._wpm = wpm
        self._farnsworth_wpm = farnsworth_wpm

        self._on_started = on_started
        self._on_progress = on_progress
        self._on_finished = on_finished
        self._on_error = on_error

        self._start_timer.start(0)

    def stop(self) -> None:
        """Voir docstring du module -- annule aussi un start() encore en attente."""

        self._start_timer.stop()
        self._event_timer.stop()
        self._safe_stop_sending()

    # ------------------------------------------------------------------
    # Construction de la ligne de temps -- estimation, jamais un
    # pilotage réel (voir docstring du module).
    # ------------------------------------------------------------------

    def _build_events(self, chunks: list[str], timing_engine: TimingEngine) -> list[tuple[float, str, object]]:
        events: list[tuple[float, str, object]] = []
        elapsed = 0.0
        offset_chars = 0
        last_char_index: int | None = None

        for chunk in chunks:
            events.append((elapsed, "send", chunk))

            elements = self._encoder.encode(chunk)
            timed_elements = timing_engine.apply(elements)

            for timed_element in timed_elements:
                global_char_index = offset_chars + timed_element.char_index
                if global_char_index != last_char_index:
                    events.append((elapsed, "progress", global_char_index))
                    last_char_index = global_char_index
                elapsed += timed_element.duration_s

            offset_chars += len(chunk)

        events.append((elapsed, "finish", None))
        return events

    # ------------------------------------------------------------------
    # Minuteries internes (jamais exposées à CWService)
    # ------------------------------------------------------------------

    def _on_start_timer(self) -> None:
        self._on_started()
        self._process_events_from(0)

    def _on_event_timer(self) -> None:
        self._process_events_from(self._event_index)

    def _process_events_from(self, index: int) -> None:
        self._event_index = index

        while self._event_index < len(self._events):
            elapsed, kind, payload = self._events[self._event_index]

            if kind == "send":
                try:
                    self._backend.send_text(payload, self._wpm, self._farnsworth_wpm, owner=self._owner)
                except Exception as exc:
                    self._event_index = len(self._events)
                    self._on_error(str(exc))
                    return
            elif kind == "progress":
                self._on_progress(payload)
            else:  # "finish"
                self._event_index = len(self._events)
                self._safe_stop_sending()
                self._on_finished()
                return

            self._event_index += 1

            if self._event_index < len(self._events):
                next_elapsed = self._events[self._event_index][0]
                delay_s = next_elapsed - elapsed
                if delay_s > 0:
                    self._event_timer.start(max(0, int(delay_s * 1000)))
                    return
                # sinon : plusieurs événements au même instant estimé --
                # on continue la boucle sans reprogrammer de minuterie.

    def _safe_stop_sending(self) -> None:
        try:
            self._backend.stop_sending()
        except Exception:
            pass
