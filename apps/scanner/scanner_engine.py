"""
ON3RT Radio Suite
Module Scanner
Moteur de balayage.

Pilote un ScannerModel au rythme d'un QTimer et envoie chaque
fréquence calculée à RadioService (exclusivement injecté, jamais créé
ici, jamais d'accès direct à CATController) — c'est ce qui distingue
ce moteur de celui de HF Manager, qui ne faisait qu'incrémenter un
compteur en mémoire sans jamais piloter la radio.

Volontairement réaliste : si aucun RadioService n'est disponible ou
que la radio n'est pas connectée, le balayage refuse de démarrer (ou
s'arrête de lui-même si la connexion tombe en cours de route) plutôt
que de continuer à "balayer" une fréquence qui ne serait envoyée nulle
part — jamais de simulation silencieuse. Aucune logique d'interface
ici (pas de boîte de dialogue, pas de message) : ScannerWindow
(étape suivante) interprète les valeurs de retour et les signaux pour
informer l'utilisateur.
"""

from PySide6.QtCore import QObject, QTimer, Signal

from apps.scanner.scanner_model import ScannerModel


class ScannerEngine(QObject):

    frequency_changed = Signal(int)
    started = Signal()
    stopped = Signal()

    def __init__(self, model: ScannerModel, radio_service=None, parent=None):
        super().__init__(parent)

        self.model = model
        self.radio_service = radio_service

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._scan_step)

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def set_speed(self, milliseconds: int) -> None:
        self.model.speed_ms = milliseconds
        self.timer.setInterval(milliseconds)

    # ------------------------------------------------------------------
    # Commandes
    # ------------------------------------------------------------------

    def start(self) -> bool:
        """
        Démarre le balayage. Refuse honnêtement si aucun RadioService
        n'est disponible ou si la radio n'est pas connectée : jamais
        de balayage simulé sans radio réelle derrière.
        """

        if self.timer.isActive():
            return True

        if self.radio_service is None or not self.radio_service.connected:
            return False

        self.model.start()
        self.timer.start(self.model.speed_ms)
        self.started.emit()
        return True

    def stop(self) -> None:
        if self.timer.isActive():
            self.timer.stop()

        self.model.stop()
        self.stopped.emit()

    def toggle(self) -> bool:
        if self.timer.isActive():
            self.stop()
            return True

        return self.start()

    # ------------------------------------------------------------------
    # État
    # ------------------------------------------------------------------

    def is_running(self) -> bool:
        return self.timer.isActive()

    # ------------------------------------------------------------------
    # Balayage
    # ------------------------------------------------------------------

    def _scan_step(self) -> None:
        if self.radio_service is None or not self.radio_service.connected:
            # La radio a disparu en cours de balayage (déconnexion,
            # câble débranché...) : on s'arrête plutôt que de
            # continuer à avancer un compteur qui ne pilote plus rien.
            self.stop()
            return

        freq = self.model.next_frequency()
        self.radio_service.set_frequency(freq)
        self.frequency_changed.emit(freq)
