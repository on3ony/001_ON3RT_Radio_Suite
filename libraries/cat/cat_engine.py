"""
ON3RT HF Manager V2
modules/cat/cat_engine.py
"""

from __future__ import annotations

import logging

from libraries.cat.serial_transport import SerialTransport
from libraries.cat.civ_protocol import CIVProtocol
from libraries.cat.parser import CIVParser
from libraries.cat.cw_message import CWMessageManager
from libraries.cat.data_mode import DataModeManager
from libraries.cat.frequency import FrequencyManager
from libraries.cat.keying_speed import KeyingSpeedManager
from libraries.cat.mode import ModeManager
from libraries.cat.ptt import PTTManager
from libraries.cat.smeter import SMeterManager
from libraries.cat.vfo import VFOManager
from libraries.cat.command_queue import CommandQueue

_log = logging.getLogger("CAT_SERVER")


class CATEngine:

    def __init__(self, port: str = "", baudrate: int = 19200):
        self.transport = SerialTransport(port=port, baudrate=baudrate)

        self.civ = CIVProtocol()
        self.parser = CIVParser()

        self.frequency = FrequencyManager()
        self.mode = ModeManager()
        self.ptt = PTTManager()
        self.smeter = SMeterManager()
        self.data_mode = DataModeManager()
        self.vfo = VFOManager()
        self.cw_message = CWMessageManager()
        self.keying_speed = KeyingSpeedManager()

        self.queue = CommandQueue()

    @property
    def connected(self) -> bool:
        return self.transport.is_connected

    def connect(self) -> bool:
        return self.transport.connect()

    def disconnect(self) -> None:
        self.transport.disconnect()

    def transact(self, frame: bytes) -> bytes:
        return self.transport.transact(frame)

    def read_frequency(self) -> int:
        response = self.transact(self.frequency.build_read_command())
        parsed = self.parser.parse(response)
        value = parsed.get("decoded", {}).get("frequency_hz", 0)
        _log.info(f"read_frequency() : RX brut={response.hex(' ').upper() if response else '(vide)'} -> {value}")
        return value

    def set_frequency(self, hz: int) -> None:
        self.transact(self.frequency.build_set_command(hz))

    def read_mode(self) -> str:
        response = self.transact(self.mode.build_read_command())
        parsed = self.parser.parse(response)
        value = parsed.get("decoded", {}).get("mode_name", "UNKNOWN")
        _log.info(f"read_mode() : RX brut={response.hex(' ').upper() if response else '(vide)'} -> {value}")
        return value

    def set_mode(self, mode) -> None:
        self.transact(self.mode.build_set_command(mode))

    def read_ptt(self):
        response = self.transact(self.ptt.build_read_command())
        parsed = self.parser.parse(response)
        value = parsed.get("decoded", {"ptt": False})
        _log.info(f"read_ptt() : RX brut={response.hex(' ').upper() if response else '(vide)'} -> {value}")
        return value

    def set_ptt(self, state: bool) -> None:
        self.transact(self.ptt.build_set_command(state))

    def read_smeter(self):
        """
        Retourne (level, display) : level est la donnée de RÉFÉRENCE, un
        entier brut 0-255 (SMeterManager.decode_level()) destiné aux
        futurs widgets graphiques/animés ; display en est une simple
        représentation textuelle dérivée du même level
        (SMeterManager.level_to_s_display()), utilisée par l'interface
        actuelle. (None, None) si la réponse est absente/malformée --
        jamais une valeur inventée (même discipline que read_frequency()/
        read_mode()).
        """

        response = self.transact(self.smeter.build_read_command())
        parsed = self.parser.parse(response)
        decoded = parsed.get("decoded", {})

        if decoded.get("meter_subcommand") != 0x02:
            _log.info(f"read_smeter() : RX brut={response.hex(' ').upper() if response else '(vide)'} -> (aucune donnée)")
            return None, None

        level = self.smeter.decode_level(decoded.get("meter_data", b""))
        display = self.smeter.level_to_s_display(level)
        _log.info(f"read_smeter() : RX brut={response.hex(' ').upper() if response else '(vide)'} -> level={level} ({display})")
        return level, display

    def set_data_mode(self, enabled: bool) -> bool:
        """
        Active/désactive l'indicateur CI-V "DATA mode" (commande 1A 06,
        voir libraries/cat/data_mode.py). Contrairement à
        set_frequency()/set_mode()/set_ptt() ci-dessus (qui n'inspectent
        jamais la réponse), retourne True/False selon que la radio a
        répondu ACK (FB) ou NG (FA) -- cette commande est celle où un
        NG a été observé en conditions réelles (chantier "Correction
        DATA Mode IC-7300", 2026-08-05 : un octet de filtre invalide
        était silencieusement traité comme un succès jusqu'à l'appelant,
        WSJT-X compris). Aucune mise à jour d'état ici, cette
        responsabilité reste à l'appelant (voir docstring de
        DataModeManager).
        """

        response = self.transact(self.data_mode.build_set_command(enabled))
        return self.civ.is_ack(response)

    def send_cw_message(self, text: str) -> None:
        self.transact(self.cw_message.build_send_command(text))

    def stop_cw_message(self) -> None:
        self.transact(self.cw_message.build_stop_command())

    def set_keying_speed(self, wpm: int) -> None:
        self.transact(self.keying_speed.build_set_command(wpm))

    def read_vfo(self):
        response = self.transact(self.vfo.build_read_command())
        parsed = self.parser.parse(response)
        return parsed.get("decoded", {"vfo": None})

    def set_vfo(self, vfo) -> None:
        self.transact(self.vfo.build_set_command(vfo))

    def queue_command(self, command, *args, **kwargs):
        self.queue.put(command, *args, **kwargs)

    def execute_queue(self):
        self.queue.execute_all()

    @staticmethod
    def available_ports():
        return SerialTransport.available_ports()