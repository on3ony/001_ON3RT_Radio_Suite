"""
ON3RT Radio Suite
libraries/cw/cw_service.py

CWService : unique orchestrateur public de l'émission CW. Voir
libraries/cw/ARCHITECTURE.md pour le schéma complet des responsabilités
(CWService -> CWDriver -> ElementDriver/TextDriver -> KeyerBackend/
TextBackend) -- ce document fait foi, architecture figée et validée
avant cette refonte.

Ignorance totale du matériel, du backend, du protocole et de la
stratégie d'émission (contrainte explicite, validée avec l'utilisateur) :
CWService ne connaît, ne construit et ne possède ni MorseEncoder, ni
TimingEngine, ni un backend direct -- uniquement un CWDriver
(libraries/cw/cw_driver.py), reçu en injection et JAMAIS construit ici.
Le choix du driver (ElementDriver ou TextDriver, aujourd'hui ; une
future famille, demain) se fait UNE SEULE FOIS, dans
core/application.py -- jamais ici. CWService ne fait et ne fera JAMAIS
de test sur le type du driver injecté, ni n'adapte son comportement
selon la stratégie utilisée : un driver n'est, de son point de vue,
qu'un objet respectant le contrat start()/stop() de CWDriver, rien de
plus.

Callbacks plutôt que signaux Qt vers le driver (voir cw_driver.py) :
send() construit, à chaque appel, quatre fermetures liées au
request_id et à l'owner de CETTE demande précise (on_started/
on_progress/on_finished/on_error), et les transmet à driver.start().
C'est le driver qui les invoque lui-même, aux moments qui lui
appartiennent -- CWService n'a donc plus besoin d'un QTimer interne
pour enchaîner quoi que ce soit lui-même ; seules les émissions de
signaux qui se produisent SYNCHRONMENT dans la pile d'appel de send()/
stop() (refus de concurrence, échec immédiat, arrêt) restent
explicitement différées via QTimer.singleShot(0, ...) -- même
convention Suite qu'avant (VoiceService), pour que l'idiome "connecter
le signal juste après l'appel" fonctionne toujours, quelle que soit la
rapidité du traitement.

Producteurs de texte multiples, dès le départ : send(text, owner=None)
ne fait aucune hypothèse sur l'origine du texte (macro résolue, saisie
libre, futur module Contest/Scheduler/API/Voice...) — c'est à
l'appelant de préparer le texte final (résolution de variables
incluse) avant d'appeler send(). CWService ne connaît ni les macros ni
resolve_variables().

Une seule émission active à la fois, refus explicite (jamais de file
d'attente) : send() retourne None et journalise un refus si une
émission est déjà en cours (self.state is CWState.SENDING) — même
philosophie que TransmissionService.transmit(), qui refuse aussi
proprement plutôt que d'empiler silencieusement. cw_error est émis
avec le détail dans ce cas.

stop() délègue le relâchement réel à driver.stop() -- garanti
synchrone et immédiat par contrat (voir cw_driver.py), quelle que soit
la famille de driver. Seule l'émission de cw_stopped reste différée.

Gestion des erreurs : start() peut lever une exception de façon
SYNCHRONE pour un échec immédiat détectable avant tout démarrage (ex.
WPM invalide) -- CWService l'attrape et la transforme en cw_error,
sans jamais savoir ce qui a précisément échoué côté driver/matériel
(seul le message de l'exception est journalisé/émis). Un échec survenant
après un démarrage réussi passe exclusivement par le callback on_error,
que CWService transforme de la même façon en cw_error -- c'est
strictement TOUT ce que CWService fait de la gestion d'erreur : il ne
sait jamais POURQUOI un driver a échoué, seulement QU'il a échoué.

État (CWState) : IDLE et SENDING reflètent l'activité réelle (SENDING
est le SEUL état qui bloque un nouveau send()) ; STOPPED et ERROR ne
sont que le résultat informatif du DERNIER envoi terminé — un nouvel
appel à send() est accepté immédiatement après un arrêt ou une erreur,
sans jamais avoir besoin de revenir explicitement à IDLE.

Progression (cw_progress) : émise selon ce que le driver rapporte via
on_progress(char_index) -- une fois par caractère pour ElementDriver
(confirmée par le pilotage réel), une fois par caractère estimé pour
TextDriver (voir sa docstring) -- CWService relaie tel quel, sans
distinguer les deux cas, exactement la contrainte d'ignorance totale
énoncée ci-dessus.
"""

from __future__ import annotations

import uuid
from enum import Enum

from PySide6.QtCore import QObject, QTimer, Signal

from libraries.cw.logger import logger


class CWState(Enum):
    """État de CWService — voir docstring du module pour la sémantique de chaque valeur."""

    IDLE = "idle"
    SENDING = "sending"
    STOPPED = "stopped"
    ERROR = "error"


class CWService(QObject):
    """Voir docstring du module pour l'ensemble des garanties fournies."""

    cw_started = Signal(str)               # request_id
    cw_progress = Signal(str, int, int)    # request_id, char_index, total_chars
    cw_finished = Signal(str)               # request_id
    cw_stopped = Signal(str)                 # request_id
    cw_error = Signal(str, str)               # request_id, message

    def __init__(self, driver, wpm: float = 20, farnsworth_wpm: float | None = None, parent=None):
        super().__init__(parent)

        self._driver = driver
        self.wpm = wpm
        self.farnsworth_wpm = farnsworth_wpm

        self._state = CWState.IDLE
        self._active_request_id: str | None = None
        self._owner: str | None = None

    @property
    def state(self) -> CWState:
        return self._state

    # ------------------------------------------------------------------
    # API publique
    # ------------------------------------------------------------------

    def send(self, text: str, owner: str | None = None) -> str | None:
        """
        Démarre une émission CW, sans bloquer. Retourne un identifiant
        de requête si l'émission démarre ; None si une émission est
        déjà en cours (refus explicite, cw_error émis avec le détail —
        voir docstring du module).
        """

        logger.cw_requested(owner)

        if self._state == CWState.SENDING:
            reason = f"une émission est déjà en cours (demandeur='{self._owner or 'inconnu'}')"
            logger.cw_rejected(owner, reason)
            QTimer.singleShot(0, lambda: self.cw_error.emit("", reason))
            return None

        request_id = uuid.uuid4().hex
        total_chars = len(text)

        try:
            self._driver.start(
                text, self.wpm, self.farnsworth_wpm, owner,
                on_started=lambda: self._on_driver_started(request_id),
                on_progress=lambda char_index: self._on_driver_progress(request_id, char_index, total_chars),
                on_finished=lambda: self._on_driver_finished(request_id, owner),
                on_error=lambda message: self._on_driver_error(request_id, owner, message),
            )
        except Exception as exc:
            # message calcule ICI, jamais "exc" reference dans le lambda
            # differe ci-dessous : Python efface la variable d'exception
            # a la sortie du bloc except, un lambda qui la referencerait
            # encore au moment de son execution reelle (plus tard, via
            # QTimer.singleShot) leverait NameError.
            message = str(exc)
            logger.cw_error(owner, message)
            QTimer.singleShot(0, lambda: self.cw_error.emit(request_id, message))
            return request_id

        self._active_request_id = request_id
        self._owner = owner
        self._state = CWState.SENDING
        logger.cw_started(owner)

        return request_id

    def stop(self) -> None:
        """
        Arrêt immédiat, quel que soit le déclencheur (bouton Stop,
        sécurité future) : sûr à appeler à tout moment, y compris hors
        émission (ne fait rien). La libération réelle est TOUJOURS
        synchrone et immédiate, garantie par contrat quel que soit le
        driver (voir docstring du module) ; seule l'émission de
        cw_stopped est différée, même principe que send() ci-dessus.
        """

        if self._state != CWState.SENDING:
            return

        self._driver.stop()

        owner = self._owner
        request_id = self._active_request_id

        self._state = CWState.STOPPED
        self._active_request_id = None

        logger.cw_stopped(owner)
        QTimer.singleShot(0, lambda: self.cw_stopped.emit(request_id))

    # ------------------------------------------------------------------
    # Callbacks du contrat CWDriver -- invoqués par le driver lui-même,
    # jamais par CWService. Chaque fermeture construite dans send() ci-
    # dessus capture déjà request_id/owner/total_chars de LA demande
    # concernée -- ces méthodes n'ont donc besoin de rien d'autre.
    # ------------------------------------------------------------------

    def _on_driver_started(self, request_id: str) -> None:
        self.cw_started.emit(request_id)

    def _on_driver_progress(self, request_id: str, char_index: int, total_chars: int) -> None:
        self.cw_progress.emit(request_id, char_index, total_chars)

    def _on_driver_finished(self, request_id: str, owner: str | None) -> None:
        self._state = CWState.IDLE
        self._active_request_id = None

        logger.cw_finished(owner)
        self.cw_finished.emit(request_id)

    def _on_driver_error(self, request_id: str, owner: str | None, message: str) -> None:
        self._state = CWState.ERROR
        self._active_request_id = None

        logger.cw_error(owner, message)
        self.cw_error.emit(request_id, message)
