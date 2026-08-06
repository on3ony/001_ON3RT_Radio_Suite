"""
ON3RT Radio Suite
apps/cat_server/status.py

État partagé du CAT Server.
"""

from __future__ import annotations

from dataclasses import dataclass

from libraries.radio.band_manager import BandManager

_BAND_MANAGER = BandManager()


@dataclass
class RadioStatus:
    connected: bool = False
    port: str = "COM3"
    baudrate: int = 19200
    model: str = "IC-7300"

    frequency: int = 0
    mode: str = "---"

    ptt: bool = False

    vfo: str = "A"

    # smeter_level (0-255, brut) est la donnée de RÉFÉRENCE, destinée
    # aux futurs widgets graphiques/animés ; smeter (texte, ex. "S9")
    # n'en est qu'une représentation dérivée pour l'interface actuelle
    # -- voir CATEngine.read_smeter().
    smeter_level: int | None = None
    smeter: str | None = None

    # Contrairement à frequency/mode/ptt/smeter ci-dessus, aucun cycle
    # de sondage ne relit cet état dans l'architecture actuelle de
    # cette Suite (voir libraries/cat/data_mode.py) : data_mode est
    # donc la seule donnée de ce dataclass mise à jour de manière
    # optimiste, uniquement après une commande d'écriture réussie
    # (voir RadioService.set_data_mode()), jamais rafraîchie par poll().
    data_mode: bool = False

    last_error: str = ""

    def reset(self) -> None:
        self.connected = False
        self.frequency = 0
        self.mode = "---"
        self.ptt = False
        self.vfo = "A"
        self.smeter_level = None
        self.smeter = None
        self.data_mode = False
        self.last_error = ""

    @property
    def frequency_mhz(self) -> str:
        if self.frequency <= 0:
            return "-----"

        return f"{self.frequency / 1_000_000:.6f}"

    @property
    def band(self) -> str:
        return _BAND_MANAGER.get_band(self.frequency) or "--"