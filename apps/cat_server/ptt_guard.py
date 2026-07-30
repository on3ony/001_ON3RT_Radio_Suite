"""
ON3RT Radio Suite
apps/cat_server/ptt_guard.py

PTTGuard : couche de sécurité au-dessus de RadioService.set_ptt() —
minuterie de secours, garantie de relâchement, protection contre les
émissions superposées. Ne parle jamais directement au CAT (c'est le
rôle de RadioService) et ne connaît rien de la synthèse vocale ni de
AudioOutputService : deuxième brique indépendante de l'architecture
Voix (AudioOutputService / VoiceService / TransmissionService), le
futur TransmissionService sera uniquement consommateur des deux.

Ressource partagée unique : le PTT est une ressource matérielle
unique. PTTGuard doit donc être instancié UNE SEULE FOIS pour toute la
Suite (comme RadioService lui-même) et injecté à qui en a besoin —
jamais recréé par un module. Rien ne l'impose techniquement ici (pas
plus qu'un autre service partagé de la Suite ne l'impose), c'est une
règle d'architecture à respecter au moment du câblage dans
core/application.py, pas encore fait à ce stade puisqu'aucun
consommateur n'existe encore (même choix que AudioOutputService).

Extensibilité sans modifier PTTGuard : key()/keyed() acceptent un
`owner` libre (ex. "voice", "contest_assistant") — un futur module qui
souhaite utiliser le PTT n'a qu'à passer son propre nom, sans que
PTTGuard ait besoin de le connaître à l'avance. `owner` sert aussi de
contexte dans le journal (CATLogger.ptt_guard_*) pour distinguer, lors
d'un diagnostic sur matériel réel, quel module a demandé le PTT.

Deux niveaux d'API, pour une raison technique précise :
- key() / release() (impératif) : l'API que le futur TransmissionService
  utilisera réellement, parce que AudioOutputService.play_file() est
  non bloquant (la fin de lecture arrive via le signal
  playback_finished, pas par un retour de fonction) — un simple bloc
  try/finally ne peut donc pas envelopper toute la séquence
  "activer -> jouer -> attendre la fin". release() sera appelé depuis
  le gestionnaire de playback_finished/playback_error.
- keyed() (gestionnaire de contexte, try/finally réel construit sur
  key()/release()) : pour tout appelant synchrone — nos propres tests,
  ou un futur cas d'usage qui n'attend pas un signal Qt.
Dans les deux cas, la garantie de sécurité ne repose PAS sur ce
try/finally Python (qui ne peut pas s'étendre à travers une opération
pilotée par signal) mais sur la minuterie de secours et le crochet de
fermeture d'application ci-dessous, tous deux indépendants de la
façon dont release() finit par être appelé.

Minuterie de sécurité (DEFAULT_PTT_SAFETY_TIMEOUT_S, constante
centralisée — jamais de valeur codée en dur) : démarrée à key(),
arrêtée par release() si tout se passe normalement. Si elle se
déclenche, elle force release() elle-même. Limite honnête : ce filet
repose sur la boucle d'événements Qt, qui doit continuer à tourner
pour que le QTimer se déclenche — il protège contre un bug logique
(exception avalée, signal jamais reçu), pas contre un blocage total du
thread principal.

Fermeture de l'application pendant une émission : key() connecte
QApplication.instance().aboutToQuit vers release() ; release() le
déconnecte. Ce crochet n'existe donc que pendant une émission réelle,
jamais au repos, et ne fuit pas d'une émission à l'autre.

Fermeture de la liaison CAT pendant une émission (corrigé après essai
matériel réel — voir aboutToDisconnect ci-dessous) : le constructeur
connecte radio_service.aboutToDisconnect vers release() de façon
PERMANENTE, dès la création de PTTGuard — pas seulement pendant une
émission, contrairement au crochet aboutToQuit ci-dessus, puisqu'une
déconnexion peut survenir à tout moment. release() étant idempotent,
cette connexion permanente ne coûte rien quand le PTT n'est pas actif.

Cause réelle identifiée sur matériel réel : RadioService.disconnect()
fermait le port AVANT que quoi que ce soit ait pu relâcher un PTT actif.
set_ptt() refuse alors d'agir (controller.connected == False) — non pas
parce que la commande échoue, mais parce qu'elle n'est même plus
tentée : le port est déjà fermé. release(), appelé après coup, ne
pouvait donc plus rien faire. RadioService.aboutToDisconnect (émis
avant la fermeture réelle du port, voir apps/cat_server/radio_service.py)
donne maintenant à PTTGuard une fenêtre pendant laquelle la liaison
existe encore pour tenter set_ptt(False) — quel que soit l'appelant de
disconnect() (reconfigure(), une action manuelle, ce script de
validation, etc.), sans que RadioService ait besoin de connaître
PTTGuard : il annonce seulement son intention de se déconnecter.

Limite honnête qui subsiste, non contournable par du logiciel : une
coupure PHYSIQUE et imprévue (câble arraché, panne USB) ne passe par
aucun appel à disconnect() — aucun signal n'est alors émis avant coup,
et la tentative de set_ptt(False) échouera avec une vraie exception de
transport (capturée, journalisée, signal error émis) sans que la
radio n'ait pu être jointe. C'est une limite matérielle, pas un trou
de conception : en défense complémentaire indépendante de cette
chaîne, vérifier que le TOT (Time-Out Timer) de la radio elle-même est
activé.

Bouton STOP (futur module Voix) : appelle simplement release(), sans
logique propre — c'est exactement le même chemin que la fin normale
d'une émission ou le déclenchement de la minuterie de sécurité.
"""

from __future__ import annotations

from contextlib import contextmanager

from PySide6.QtCore import QObject, QTimer
from PySide6.QtWidgets import QApplication

from apps.cat_server.logger import logger

# Valeur centralisée, jamais codée en dur dans key()/le constructeur —
# voir docstring du module. Assez long pour tout message vocal réel,
# assez court pour qu'un PTT resté bloqué ne dure pas indéfiniment.
DEFAULT_PTT_SAFETY_TIMEOUT_S = 30.0


class PTTError(RuntimeError):
    """Levée quand PTTGuard.key() ne peut pas garantir l'activation du PTT."""


class PTTGuard(QObject):
    """Voir docstring du module pour l'ensemble des garanties fournies."""

    def __init__(self, radio_service, safety_timeout_s: float = DEFAULT_PTT_SAFETY_TIMEOUT_S, parent=None):
        super().__init__(parent)

        self._radio_service = radio_service
        self._safety_timeout_s = safety_timeout_s

        self._keyed = False
        self._owner: str | None = None

        self._safety_timer = QTimer(self)
        self._safety_timer.setSingleShot(True)
        self._safety_timer.timeout.connect(self._on_safety_timeout)

        # Connexion permanente (contrairement à aboutToQuit, connecté/
        # déconnecté uniquement pendant une émission) : une déconnexion
        # peut survenir à tout moment, pas seulement pendant que ce
        # PTTGuard a la main. release() est idempotent — sans coût
        # quand le PTT n'est pas actif. Voir docstring du module pour
        # la cause réelle que ceci corrige.
        self._radio_service.aboutToDisconnect.connect(self.release)

    @property
    def is_keyed(self) -> bool:
        return self._keyed

    # ------------------------------------------------------------------
    # API impérative
    # ------------------------------------------------------------------

    def key(self, owner: str | None = None) -> None:
        """
        Active le PTT. Lève PTTError sans rien modifier si un PTT est
        déjà actif (anti-superposition) ou si la commande CAT échoue
        (radio non connectée ou erreur) — jamais d'émission commencée
        sans confirmation.
        """

        if self._keyed:
            reason = f"PTT déjà activé par '{self._owner or 'inconnu'}'"
            logger.ptt_guard_rejected(owner, reason)
            raise PTTError(reason)

        if not self._radio_service.set_ptt(True):
            reason = "échec de la commande CAT (radio non connectée ou erreur)"
            logger.ptt_guard_rejected(owner, reason)
            raise PTTError(f"Impossible d'activer le PTT : {reason}.")

        self._keyed = True
        self._owner = owner
        logger.ptt_guard_activated(owner)

        self._safety_timer.start(int(self._safety_timeout_s * 1000))

        app = QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self.release)

    def release(self) -> None:
        """
        Relâche le PTT. Ne fait rien si aucun PTT n'est actif
        (idempotent — sûr à appeler depuis n'importe quel contexte :
        fin normale, minuterie de sécurité, fermeture de l'application,
        bouton STOP). Ne lève jamais.
        """

        if not self._keyed:
            return

        owner = self._owner

        self._keyed = False
        self._owner = None
        self._safety_timer.stop()

        app = QApplication.instance()
        if app is not None:
            try:
                app.aboutToQuit.disconnect(self.release)
            except (TypeError, RuntimeError):
                pass

        self._radio_service.set_ptt(False)
        logger.ptt_guard_released(owner)

    # ------------------------------------------------------------------
    # Gestionnaire de contexte (appelants synchrones uniquement)
    # ------------------------------------------------------------------

    @contextmanager
    def keyed(self, owner: str | None = None):
        self.key(owner)
        try:
            yield
        finally:
            self.release()

    # ------------------------------------------------------------------
    # Minuterie de sécurité
    # ------------------------------------------------------------------

    def _on_safety_timeout(self) -> None:
        logger.ptt_guard_timeout(self._owner, self._safety_timeout_s)
        self.release()
