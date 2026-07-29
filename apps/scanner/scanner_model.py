"""
ON3RT Radio Suite
Module Scanner
État pur du scanner.

Aucune dépendance Qt ni radio ici : ScannerModel ne fait que
représenter l'état d'un balayage (bornes, pas, vitesse, direction,
fréquence courante) et calculer la fréquence suivante. Le pilotage
réel de la radio (RadioService) et le rythme du balayage (QTimer)
relèvent de ScannerEngine (étape suivante) — jamais de ce fichier.

Fréquences exprimées en Hz (entiers), jamais en MHz flottant : le
scanner original de HF Manager accumulait un `float` MHz par `+=`
répétés à chaque pas, ce qui dérive sur un balayage long. Les entiers
Hz éliminent ce risque par construction.
"""

from dataclasses import dataclass


@dataclass(slots=True)
class ScannerModel:

    start_freq_hz: int = 1_800_000
    stop_freq_hz: int = 30_000_000
    current_freq_hz: int = 14_074_000

    step_hz: int = 100
    speed_ms: int = 100

    direction: str = "UP"
    scanning: bool = False

    # ------------------------------------------------------------------
    # Commandes
    # ------------------------------------------------------------------

    def start(self) -> None:
        self.scanning = True

    def stop(self) -> None:
        self.scanning = False

    # ------------------------------------------------------------------
    # Paramètres
    # ------------------------------------------------------------------

    def set_limits(self, start_freq_hz: int, stop_freq_hz: int) -> None:
        if start_freq_hz >= stop_freq_hz:
            raise ValueError("La fréquence de début doit être inférieure à la fréquence de fin.")

        self.start_freq_hz = start_freq_hz
        self.stop_freq_hz = stop_freq_hz

    def set_frequency(self, freq_hz: int) -> None:
        if not (self.start_freq_hz <= freq_hz <= self.stop_freq_hz):
            raise ValueError("Fréquence hors limites.")

        self.current_freq_hz = freq_hz

    # ------------------------------------------------------------------
    # Déplacement fréquence
    # ------------------------------------------------------------------

    def next_frequency(self) -> int:
        if self.direction == "UP":
            self.current_freq_hz += self.step_hz
            if self.current_freq_hz > self.stop_freq_hz:
                self.current_freq_hz = self.start_freq_hz
        else:
            self.current_freq_hz -= self.step_hz
            if self.current_freq_hz < self.start_freq_hz:
                self.current_freq_hz = self.stop_freq_hz

        return self.current_freq_hz

    def step_up(self) -> int:
        self.direction = "UP"
        return self.next_frequency()

    def step_down(self) -> int:
        self.direction = "DOWN"
        return self.next_frequency()
