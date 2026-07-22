"""
ON3RT Radio Suite
apps/cat_server/radio_service.py

Service central de communication avec l'IC-7300.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QTimer, Signal

from libraries.cat.cat_controller import CATController
from apps.cat_server.status import RadioStatus
from apps.cat_server.logger import logger


class RadioService(QObject):

    updated = Signal()
    connected = Signal()
    disconnected = Signal()
    error = Signal(str)

    def __init__(self, port: str = "COM3", baudrate: int = 19200):

        super().__init__()

        self.status = RadioStatus(port=port)

        self.controller = CATController(
            port=port,
            baudrate=baudrate,
        )

        self.timer = QTimer(self)
        self.timer.setInterval(250)
        self.timer.timeout.connect(self.poll)

    def connect(self) -> bool:

        try:

            ok = self.controller.connect()

            if not ok:
                self.status.connected = False
                self.status.last_error = "Impossible de se connecter"
                self.error.emit(self.status.last_error)
                return False

            self.status.connected = True
            self.status.last_error = ""

            logger.separator()
            logger.connected(self.status.port)

            self.connected.emit()

            self.timer.start()
            self.poll()

            return True

        except Exception as exc:

            self.status.connected = False
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

    def poll(self):

        if not getattr(self.controller, "connected", False):
            return

        try:

            freq = self.controller.read_frequency()
            mode = self.controller.read_mode()
            ptt = self.controller.read_ptt()

            changed = False

            if freq is not None and freq != self.status.frequency:
                self.status.frequency = freq
                logger.frequency(freq)
                changed = True

            if mode is not None and mode != self.status.mode:
                self.status.mode = mode
                logger.mode(mode)
                changed = True

            if isinstance(ptt, dict):
                state = ptt.get("ptt", False)
            else:
                state = bool(ptt)

            if state != self.status.ptt:
                self.status.ptt = state
                logger.ptt(state)
                changed = True

            self.status.connected = True
            self.status.last_error = ""

            if changed:
                self.updated.emit()

        except Exception as exc:

            self.status.last_error = str(exc)

            logger.exception(exc)

            self.error.emit(str(exc))