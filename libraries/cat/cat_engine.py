"""
ON3RT HF Manager V2
modules/cat/cat_engine.py
"""

from __future__ import annotations

from libraries.cat.serial_transport import SerialTransport
from libraries.cat.civ_protocol import CIVProtocol
from libraries.cat.parser import CIVParser
from libraries.cat.frequency import FrequencyManager
from libraries.cat.mode import ModeManager
from libraries.cat.ptt import PTTManager
from libraries.cat.vfo import VFOManager
from libraries.cat.command_queue import CommandQueue


class CATEngine:

    def __init__(self, port: str = "", baudrate: int = 19200):
        self.transport = SerialTransport(port=port, baudrate=baudrate)

        self.civ = CIVProtocol()
        self.parser = CIVParser()

        self.frequency = FrequencyManager()
        self.mode = ModeManager()
        self.ptt = PTTManager()
        self.vfo = VFOManager()

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
        return parsed.get("decoded", {}).get("frequency_hz", 0)

    def set_frequency(self, hz: int) -> None:
        self.transact(self.frequency.build_set_command(hz))

    def read_mode(self) -> str:
        response = self.transact(self.mode.build_read_command())
        parsed = self.parser.parse(response)
        return parsed.get("decoded", {}).get("mode_name", "UNKNOWN")

    def set_mode(self, mode) -> None:
        self.transact(self.mode.build_set_command(mode))

    def read_ptt(self):
        response = self.transact(self.ptt.build_read_command())
        parsed = self.parser.parse(response)
        return parsed.get("decoded", {"ptt": False})

    def set_ptt(self, state: bool) -> None:
        self.transact(self.ptt.build_set_command(state))

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