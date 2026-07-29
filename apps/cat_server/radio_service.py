"""
ON3RT Radio Suite
apps/cat_server/radio_service.py

Service central de communication avec l'IC-7300.
Version de transition compatible RadioManager.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Signal

from libraries.cat.cat_controller import CATController
from libraries.radio.band_manager import BandManager
from libraries.radio.mode_manager import ModeManager
from libraries.radio.utc_manager import UTCManager

from apps.cat_server.status import RadioStatus
from apps.cat_server.logger import logger

# ----------------------------------------------------------------------
# Emplacement par défaut du pont data/live.json (ON3RT Live)
# ----------------------------------------------------------------------

DEFAULT_LIVE_DATA_FILE = (
    Path(__file__).resolve().parents[2]
    / "001_ON3RT_live"
    / "data"
    / "live.json"
)


class RadioService(QObject):

    updated = Signal()
    connectionChanged = Signal(bool)
    disconnected = Signal()
    error = Signal(str)

    def __init__(self, port="COM3", baudrate=19200, live_data_path=None):
        super().__init__()

        self.status = RadioStatus(port=port, baudrate=baudrate)
        self.controller = CATController(port=port, baudrate=baudrate)

        self.band_manager = BandManager()
        self.mode_manager = ModeManager()
        self.utc_manager = UTCManager()

        self._live_data_path = (
            Path(live_data_path) if live_data_path else DEFAULT_LIVE_DATA_FILE
        )

        self.timer = QTimer(self)
        self.timer.setInterval(250)
        self.timer.timeout.connect(self.poll)

        # ------------------------------------------------
        # RadioService = source de vérité unique : toute
        # notification de changement (poll) ou de connexion
        # déclenche l'écriture de data/live.json.
        # ------------------------------------------------

        self.updated.connect(self._write_live_state)
        self.connectionChanged.connect(lambda _connected: self._write_live_state())

    def reconfigure(self, port, baudrate):
        """
        Change le port/baudrate cible avant une (re)connexion. Le port est
        figé à la création de CATController : on le recrée donc, après
        avoir coupé une éventuelle connexion en cours.
        """

        logger.event(f"reconfigure() : port={port}, baudrate={baudrate} (était port={self.status.port}, baudrate={self.status.baudrate})")

        if self.controller.connected:
            self.disconnect()

        self.status.port = port
        self.status.baudrate = baudrate
        self.controller = CATController(port=port, baudrate=baudrate)

    def connect(self):
        logger.event(f"connect() appelé : port={self.status.port}, baudrate={self.status.baudrate}")

        try:
            ok = self.controller.connect()
            self.status.connected = bool(ok)

            if ok:
                logger.connected(self.status.port)
                self.connectionChanged.emit(True)
                self.timer.start()
                logger.polling_started(self.timer.interval())
                self.poll()
            else:
                logger.event("connect() : échec (controller.connect() a retourné False)")

            return ok

        except Exception as exc:
            self.status.last_error = str(exc)
            logger.exception(exc)
            self.error.emit(str(exc))
            return False

    def disconnect(self):
        logger.event(f"disconnect() appelé : port={self.status.port}")

        self.timer.stop()
        logger.polling_stopped()

        try:
            self.controller.disconnect()
        except Exception as exc:
            logger.exception(exc)

        self.status.connected = False

        logger.disconnected()

        self.connectionChanged.emit(False)
        self.disconnected.emit()

    @property
    def connected(self):
        return self.status.connected

    @property
    def frequency(self):
        return self.status.frequency

    @property
    def mode(self):
        return self.mode_manager.normalize(self.status.mode)

    @property
    def band(self):
        return self.band_manager.get_band(self.status.frequency)

    @property
    def port(self):
        return self.status.port

    @property
    def baudrate(self):
        return self.status.baudrate

    @property
    def model(self):
        return self.status.model

    @property
    def utc_date(self):
        return self.utc_manager.date()

    @property
    def utc_time(self):
        return self.utc_manager.time()

    @property
    def adif_date(self):
        return self.utc_manager.adif_date()

    @property
    def adif_time(self):
        return self.utc_manager.adif_time()

    def poll(self):
        if not self.controller.connected:
            logger.event("poll() ignoré : controller.connected == False")
            return

        logger.event("---- poll() : cycle fréquence/mode/PTT ----")

        # ------------------------------------------------
        # Le VFO n'est volontairement PAS interrogé ici.
        #
        # Sur le protocole CI-V Icom, la fréquence (0x03 lecture /
        # 0x05 écriture) et le mode (0x04 lecture / 0x06 écriture)
        # ont chacun un opcode de LECTURE dédié, distinct de leur
        # opcode d'écriture. La commande 0x07 ("select VFO"), elle,
        # n'a aucune forme de lecture : elle sert exclusivement à
        # sélectionner/échanger/égaliser le VFO A/B ou MAIN/SUB, et
        # attend toujours un octet de donnée pour préciser l'action.
        #
        # L'envoyer sans donnée (comme le faisait l'ancienne version
        # de ce polling, 4x/seconde) est une trame mal formée pour ce
        # même sous-système que celui utilisé par la sélection de
        # bande au panneau avant de l'IC-7300 — c'est très probablement
        # ce qui bloquait le changement de bande pendant que le CAT
        # Server était connecté. Tant qu'aucune vraie commande de
        # lecture VFO n'est disponible/nécessaire, ce poll reste
        # strictement composé de lectures sans ambiguïté (fréquence,
        # mode, PTT).
        # ------------------------------------------------

        try:
            f = self.controller.read_frequency()
            m = self.controller.read_mode()
            p = self.controller.read_ptt()

            if f is not None and f != self.status.frequency:
                self.status.frequency = f
                logger.frequency(f)

            m = self.mode_manager.normalize(m)

            if m is not None and m != self.status.mode:
                self.status.mode = m
                logger.mode(m)

            state = p.get("ptt", False) if isinstance(p, dict) else bool(p)

            if state != self.status.ptt:
                self.status.ptt = state
                logger.ptt(state)

            self.status.connected = True

            # Émis à chaque poll réussi (pas seulement au changement) afin
            # que le timestamp de data/live.json reste frais : c'est ce qui
            # permet à ON3RT Live de distinguer "radio connectée et parquée
            # sur la même fréquence" de "pont CAT arrêté / figé".
            self.updated.emit()

        except Exception as exc:
            self.status.last_error = str(exc)
            logger.exception(exc)
            self.error.emit(str(exc))

    def set_frequency(self, frequency_hz: int) -> bool:
        """
        Envoie une fréquence à la radio (Hz). Ne fait rien si la radio
        n'est pas connectée. L'état affiché (status.frequency) n'est
        pas mis à jour de manière optimiste ici : il sera rafraîchi au
        prochain cycle de poll(), qui reste l'unique source de vérité.
        """

        if not self.controller.connected:
            logger.event("set_frequency() ignoré : controller.connected == False")
            return False

        logger.event(f"set_frequency() appelé : {frequency_hz} Hz")

        try:
            self.controller.set_frequency(frequency_hz)
            return True
        except Exception as exc:
            self.status.last_error = str(exc)
            logger.exception(exc)
            self.error.emit(str(exc))
            return False

    def set_mode(self, mode: str) -> bool:
        """
        Envoie un mode à la radio (CI-V : USB/LSB/AM/FM/CW/RTTY/CW-R/
        RTTY-R/DV uniquement — voir libraries/cat/mode.py). Ne fait
        rien si la radio n'est pas connectée.
        """

        if not self.controller.connected:
            logger.event("set_mode() ignoré : controller.connected == False")
            return False

        logger.event(f"set_mode() appelé : {mode}")

        try:
            self.controller.set_mode(mode)
            return True
        except Exception as exc:
            self.status.last_error = str(exc)
            logger.exception(exc)
            self.error.emit(str(exc))
            return False

    def info(self):
        return {
            "timestamp": time.time(),
            "connected": self.connected,
            "model": self.model,
            "port": self.port,
            "baudrate": self.baudrate,
            "frequency": self.frequency,
            "frequency_hz": self.frequency,
            "band": self.band,
            "mode": self.mode,
            "utc_date": self.utc_date,
            "utc_time": self.utc_time,
            "adif_date": self.adif_date,
            "adif_time": self.adif_time,
            "ptt": self.status.ptt,
        }

    def _write_live_state(self):
        """
        Écrit l'état courant (données brutes, aucun formatage
        destiné à l'interface) dans data/live.json, en écriture
        atomique (fichier temporaire puis remplacement), pour
        alimenter ON3RT Live (services/live_service.py).
        """

        try:
            self._live_data_path.parent.mkdir(parents=True, exist_ok=True)

            tmp_path = self._live_data_path.with_suffix(".tmp")

            tmp_path.write_text(
                json.dumps(self.info(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            tmp_path.replace(self._live_data_path)

        except Exception as exc:
            logger.exception(exc)