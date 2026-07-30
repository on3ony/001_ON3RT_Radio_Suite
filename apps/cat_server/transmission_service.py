"""
ON3RT Radio Suite
apps/cat_server/transmission_service.py

TransmissionService : orchestration complète d'une émission vocale —
PTT ON -> lecture audio -> PTT OFF. Troisième et dernière brique de
l'architecture Voix (AudioOutputService / PTTGuard / TransmissionService).
Ne connaît ni la synthèse vocale, ni le contenu transmis, ni le format
au-delà de ce qu'AudioOutputService sait déjà jouer : il compose les
deux briques déjà validées (étapes 1 et 2), rien de plus.

Emplacement — choix actuel, pas une règle définitive : ce fichier vit
dans apps/cat_server/ parce qu'il dépend directement de PTTGuard
(même package) — le sens normal des dépendances dans cette Suite est
apps/ -> libraries/, jamais l'inverse. Si, plus tard, plusieurs
modules utilisent TransmissionService indépendamment du CAT, il pourra
être déplacé vers une bibliothèque partagée sans casser son API
publique (transmit()/stop()/is_transmitting) — voir aussi le
raisonnement identique déjà appliqué à PTTGuard à l'étape 2.

Contrat public volontairement minimal : transmit(source, owner=None),
stop(), la propriété is_transmitting. Un futur module n'a besoin de
rien connaître du fonctionnement interne de PTTGuard ni des signaux
d'AudioOutputService pour utiliser ce service en toute sécurité —
transmit() puis, si besoin, stop() suffisent. Les signaux de sortie
(transmission_started/finished/stopped/error) sont une observabilité
OPTIONNELLE pour un consommateur qui veut réagir en direct (ex. un
indicateur "TX actif"), jamais requise pour utiliser le service.

Paramètre "source", pas "path" : nom délibérément choisi pour ne pas
présupposer que la source audio sera toujours un fichier sur disque.
Aujourd'hui, source doit être ce qu'AudioOutputService.play_file()
sait jouer (un chemin de fichier WAV, str ou Path) — TransmissionService
ne l'inspecte ni ne l'interprète jamais lui-même, il le transmet tel
quel à AudioOutputService, dont c'est le rôle de savoir quoi en faire.
Le jour où AudioOutputService gagnera la capacité de jouer un buffer
en mémoire, un flux, ou un autre format, transmit(source, ...) pourra
accepter ces nouvelles formes sans que sa signature ni son nom n'aient
à changer.

Compatible file d'attente future, sans en implémenter une aujourd'hui :
transmit() refuse proprement (retourne False, transmission_error émis)
si une transmission est déjà en cours, plutôt que de bloquer ou de
mettre en attente silencieusement — et les trois signaux de fin
(transmission_finished/stopped/error) se déclenchent de façon fiable,
une fois par transmission réellement démarrée. Une future file
d'attente est un CONSOMMATEUR naturel de ce contrat existant (elle
n'appelle transmit() pour l'élément suivant qu'une fois le précédent
terminé, sur réception d'un de ces trois signaux) — pas une raison de
le modifier.

Orchestration (transmit() est non bloquant, exactement comme
AudioOutputService.play_file() qu'il pilote) :
    1. rejet si une transmission est déjà en cours (is_transmitting)
    2. ptt_guard.key(owner) -- lève PTTError si échec, jamais d'audio
       démarré dans ce cas
    3. audio_service.play_file(source)
    4. la suite se joue via playback_finished/playback_error, connectés
       UNE SEULE FOIS au constructeur (AudioOutputService est une
       ressource partagée unique, comme PTTGuard -- pas de connexion/
       déconnexion par transmission)

Piège réel trouvé en testant cette séquence (pas deviné) : pour un
échec IMMÉDIAT (ex. fichier introuvable), AudioOutputService.play_file()
émet playback_error de façon SYNCHRONE, avant même de rendre la main —
même thread, connexion directe Qt. _on_playback_error()/_finish() ont
donc déjà tout nettoyé (PTT relâché, transmission_error émis,
is_transmitting redevenu False) au moment où transmit() reprend la
main après l'appel à play_file(). transmit() vérifie explicitement
is_transmitting après cet appel avant de logguer "lecture démarrée" et
de retourner True — sans cette vérification, un échec immédiat aurait
paru réussi (retour True, log trompeur) alors que la transmission
était déjà terminée en échec.

stop() : point d'entrée unique pour tout déclencheur d'arrêt (bouton
STOP, une future sécurité automatique) -- aucune logique propre côté
appelant, même principe que PTTGuard.release() à l'étape 2. Relâche le
PTT AVANT d'arrêter l'audio : couper l'émission RF est la priorité
absolue, arrêter le son qui continuerait sinon à jouer localement sur
la carte son n'a aucune conséquence sur l'air. Les deux appels sous-
jacents sont toujours effectués (déjà sûrs à répéter), mais l'état
interne n'est modifié et transmission_stopped n'est émis que si une
transmission était réellement en cours.

Prévention des transmissions simultanées, deux niveaux volontairement
redondants : is_transmitting rejette avant même de solliciter
PTTGuard ; l'anti-superposition propre de PTTGuard reste un filet de
secours si jamais un appelant contournait TransmissionService.

Aucun verrou explicite : tout tourne sur le thread principal Qt, même
modèle que RadioService/PTTGuard/AudioOutputService.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from apps.cat_server.logger import logger
from apps.cat_server.ptt_guard import PTTError


class TransmissionService(QObject):
    """Voir docstring du module pour l'ensemble des garanties fournies."""

    transmission_started = Signal()
    transmission_finished = Signal()
    transmission_stopped = Signal()
    transmission_error = Signal(str)

    def __init__(self, audio_service, ptt_guard, parent=None):
        super().__init__(parent)

        self._audio_service = audio_service
        self._ptt_guard = ptt_guard

        self._is_transmitting = False
        self._owner: str | None = None

        self._audio_service.playback_finished.connect(self._on_playback_finished)
        self._audio_service.playback_error.connect(self._on_playback_error)

    @property
    def is_transmitting(self) -> bool:
        return self._is_transmitting

    # ------------------------------------------------------------------
    # API publique
    # ------------------------------------------------------------------

    def transmit(self, source, owner: str | None = None) -> bool:
        """
        Démarre une transmission (PTT ON -> lecture -> PTT OFF), sans
        bloquer. Retourne True si elle a bien démarré (PTT activé,
        lecture lancée) ; False sinon (déjà en cours, ou échec
        d'activation du PTT) — dans ce cas, transmission_error a déjà
        été émis avec le détail.
        """

        logger.transmission_requested(owner)

        if self._is_transmitting:
            reason = f"une transmission est déjà en cours (demandeur='{self._owner or 'inconnu'}')"
            logger.transmission_rejected(owner, reason)
            self.transmission_error.emit(reason)
            return False

        try:
            self._ptt_guard.key(owner=owner)
        except PTTError as exc:
            logger.transmission_rejected(owner, str(exc))
            self.transmission_error.emit(str(exc))
            return False

        self._is_transmitting = True
        self._owner = owner
        logger.transmission_accepted(owner)
        self.transmission_started.emit()

        try:
            self._audio_service.play_file(source)
        except Exception as exc:
            # Défense en profondeur : play_file() ne lève normalement
            # jamais (erreurs rapportées via playback_error), mais le
            # PTT ne doit jamais rester actif si ce contrat était un
            # jour rompu par un bug ailleurs.
            self._finish(success=False, message=str(exc))
            return False

        if not self._is_transmitting:
            # playback_error a déjà été reçu de façon SYNCHRONE pendant
            # l'appel ci-dessus (ex. fichier introuvable : émis avant
            # même que play_file() ne rende la main — même thread,
            # connexion directe). _on_playback_error()/_finish() ont
            # déjà tout nettoyé (PTT relâché, transmission_error émis) :
            # rien de plus à faire, et surtout ne pas logguer un
            # "lecture démarrée" pour une lecture qui n'a jamais eu lieu.
            return False

        logger.transmission_playback_started(owner)

        return True

    def stop(self) -> None:
        """
        Arrêt immédiat, quel que soit le déclencheur (bouton STOP,
        sécurité future) : relâche le PTT puis arrête l'audio, dans cet
        ordre — voir docstring du module. Sûr à appeler à tout moment,
        y compris au repos (idempotent, ne lève jamais).
        """

        was_transmitting = self._is_transmitting
        owner = self._owner

        self._ptt_guard.release()
        self._audio_service.stop()

        if was_transmitting:
            self._is_transmitting = False
            self._owner = None
            logger.transmission_stopped(owner)
            self.transmission_stopped.emit()

    # ------------------------------------------------------------------
    # Signaux d'AudioOutputService
    # ------------------------------------------------------------------

    def _on_playback_finished(self) -> None:
        if not self._is_transmitting:
            return

        logger.transmission_playback_finished(self._owner)
        self._finish(success=True)

    def _on_playback_error(self, message: str) -> None:
        if not self._is_transmitting:
            return

        self._finish(success=False, message=message)

    # ------------------------------------------------------------------
    # Fin de transmission (succès ou échec) — toujours relâcher le PTT
    # avant d'émettre le signal de sortie correspondant.
    # ------------------------------------------------------------------

    def _finish(self, success: bool, message: str = "") -> None:
        owner = self._owner

        self._is_transmitting = False
        self._owner = None

        self._ptt_guard.release()

        if success:
            self.transmission_finished.emit()
        else:
            logger.transmission_error_occurred(owner, message)
            self.transmission_error.emit(message)
