"""
ON3RT Radio Suite
apps/cat_server/radio_service.py

Service central de communication avec l'IC-7300.
Version de transition compatible RadioManager.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QTimer, Signal

from libraries.cat.cat_controller import CATController
from libraries.radio.band_manager import BandManager
from libraries.radio.mode_manager import ModeManager
from libraries.radio.utc_manager import UTCManager

from apps.cat_server.status import RadioStatus
from apps.cat_server.logger import logger


class RadioService(QObject):

    updated = Signal()
    connected = Signal()
    disconnected = Signal()
    error = Signal(str)

    def __init__(self, port="COM3", baudrate=19200):
        super().__init__()

        self.status = RadioStatus(port=port)
        self.controller = CATController(port=port, baudrate=baudrate)

        self.band_manager = BandManager()
        self.mode_manager = ModeManager()
        self.utc_manager = UTCManager()

        self.timer = QTimer(self)
        self.timer.setInterval(250)
        self.timer.timeout.connect(self.poll)

    def connect(self):
        try:
            ok = self.controller.connect()
            self.status.connected = bool(ok)
            if ok:
                logger.connected(self.status.port)
                self.connected.emit()
                self.timer.start()
                self.poll()
            return ok
        except Exception as exc:
            self.status.last_error = str(exc)
            logger.exception(exc)
            self.error.emit(str(exc))
            return False

    def disconnect(self):
        self.timer.stop()
        try:
            self.controller.disconnect()
        except Exception:
            pass
        self.status.connected = False
        logger.disconnected()
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
            return
        try:
            f = self.controller.read_frequency()
            m = self.controller.read_mode()
            p = self.controller.read_ptt()

            changed = False

            if f is not None and f != self.status.frequency:
                self.status.frequency = f
                logger.frequency(f)
                changed = True

            m = self.mode_manager.normalize(m)
            if m is not None and m != self.status.mode:
                self.status.mode = m
                logger.mode(m)
                changed = True

            state = p.get("ptt", False) if isinstance(p, dict) else bool(p)
            if state != self.status.ptt:
                self.status.ptt = state
                logger.ptt(state)
                changed = True

            self.status.connected = True

            if changed:
                self.updated.emit()

        except Exception as exc:
            self.status.last_error = str(exc)
            logger.exception(exc)
            self.error.emit(str(exc))

    def info(self):
        return {
            "connected": self.connected,
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
