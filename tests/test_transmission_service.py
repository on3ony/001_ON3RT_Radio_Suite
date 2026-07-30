"""
Tests de apps/cat_server/transmission_service.py.

AudioOutputService et PTTGuard sont des doubles de test minimaux :
TransmissionService ne doit dépendre que de leur interface publique
(play_file(source)/stop()/playback_finished/playback_error pour l'un,
key(owner)/release() pour l'autre), jamais de leur implémentation
réelle. La validation sur matériel réel (IC-7300) est faite
manuellement par l'utilisateur, comme le reste des garanties
matérielles de la Suite.
"""

import pytest
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

from apps.cat_server.ptt_guard import PTTError
from apps.cat_server.transmission_service import TransmissionService


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


class _FakeAudioService(QObject):
    playback_finished = Signal()
    playback_error = Signal(str)

    def __init__(self, raise_on_play=None, emit_error_synchronously=None):
        super().__init__()
        self.play_calls = []
        self.stop_calls = 0
        self._raise_on_play = raise_on_play
        self._emit_error_synchronously = emit_error_synchronously

    def play_file(self, source):
        self.play_calls.append(source)
        if self._raise_on_play is not None:
            raise self._raise_on_play
        if self._emit_error_synchronously is not None:
            # Reproduit le comportement réel d'AudioOutputService.play_file()
            # pour un échec immédiat (ex. fichier introuvable) : le
            # signal est émis AVANT que play_file() ne rende la main,
            # pas après.
            self.playback_error.emit(self._emit_error_synchronously)

    def stop(self):
        self.stop_calls += 1


class _FakePTTGuard:
    def __init__(self, key_should_raise=None):
        self.key_calls = []
        self.release_calls = 0
        self._key_should_raise = key_should_raise

    def key(self, owner=None):
        self.key_calls.append(owner)
        if self._key_should_raise is not None:
            raise self._key_should_raise

    def release(self):
        self.release_calls += 1


@pytest.fixture
def audio(qapp):
    return _FakeAudioService()


@pytest.fixture
def ptt(qapp):
    return _FakePTTGuard()


@pytest.fixture
def service(audio, ptt):
    return TransmissionService(audio_service=audio, ptt_guard=ptt)


# ------------------------------------------------------------------
# transmit() -- cas nominal
# ------------------------------------------------------------------

def test_transmit_keys_ptt_and_starts_playback(service, audio, ptt):
    result = service.transmit("message.wav", owner="voice")

    assert result is True
    assert ptt.key_calls == ["voice"]
    assert audio.play_calls == ["message.wav"]
    assert service.is_transmitting is True


def test_transmit_emits_transmission_started(service):
    received = []
    service.transmission_started.connect(lambda: received.append(True))

    service.transmit("message.wav", owner="voice")

    assert received == [True]


# ------------------------------------------------------------------
# Prévention des transmissions simultanées
# ------------------------------------------------------------------

def test_transmit_rejected_when_already_transmitting(service, audio, ptt):
    service.transmit("first.wav", owner="voice")

    received = []
    service.transmission_error.connect(lambda msg: received.append(msg))

    result = service.transmit("second.wav", owner="contest_assistant")

    assert result is False
    assert len(received) == 1
    assert ptt.key_calls == ["voice"]  # jamais un second appel
    assert audio.play_calls == ["first.wav"]
    assert service.is_transmitting is True  # la première transmission continue


def test_stop_allows_a_new_transmission_afterward(service, audio, ptt):
    service.transmit("first.wav", owner="voice")
    service.stop()

    result = service.transmit("second.wav", owner="voice")

    assert result is True
    assert service.is_transmitting is True
    assert audio.play_calls == ["first.wav", "second.wav"]


# ------------------------------------------------------------------
# Échecs avant/pendant le démarrage
# ------------------------------------------------------------------

def test_transmit_fails_cleanly_when_ptt_key_raises(audio):
    ptt = _FakePTTGuard(key_should_raise=PTTError("deja actif"))
    service = TransmissionService(audio_service=audio, ptt_guard=ptt)

    received = []
    service.transmission_error.connect(lambda msg: received.append(msg))

    result = service.transmit("message.wav", owner="voice")

    assert result is False
    assert service.is_transmitting is False
    assert audio.play_calls == []
    assert received == ["deja actif"]


def test_transmit_releases_ptt_when_play_file_raises_unexpectedly(qapp):
    """Défense en profondeur : play_file() ne lève normalement jamais, mais le PTT ne doit jamais rester actif si ce contrat était rompu."""

    audio = _FakeAudioService(raise_on_play=RuntimeError("bug audio"))
    ptt = _FakePTTGuard()
    service = TransmissionService(audio_service=audio, ptt_guard=ptt)

    received = []
    service.transmission_error.connect(lambda msg: received.append(msg))

    result = service.transmit("message.wav", owner="voice")

    assert result is False
    assert service.is_transmitting is False
    assert ptt.release_calls == 1
    assert received == ["bug audio"]


def test_transmit_returns_false_when_playback_error_fires_synchronously(qapp):
    """
    Bug réel trouvé en testant sur le vrai AudioOutputService : pour un
    échec immédiat (fichier introuvable), playback_error est émis de
    façon SYNCHRONE, avant que play_file() ne rende la main. Sans
    vérification explicite, transmit() retournait True et logguait
    "lecture démarrée" pour une transmission déjà terminée en échec.
    """

    audio = _FakeAudioService(emit_error_synchronously="fichier introuvable")
    ptt = _FakePTTGuard()
    service = TransmissionService(audio_service=audio, ptt_guard=ptt)

    received = []
    service.transmission_error.connect(lambda msg: received.append(msg))

    result = service.transmit("does_not_exist.wav", owner="voice")

    assert result is False
    assert service.is_transmitting is False
    assert ptt.release_calls == 1
    assert received == ["fichier introuvable"]


# ------------------------------------------------------------------
# playback_finished / playback_error
# ------------------------------------------------------------------

def test_playback_finished_releases_ptt_and_emits_transmission_finished(service, audio, ptt):
    service.transmit("message.wav", owner="voice")

    received = []
    service.transmission_finished.connect(lambda: received.append(True))

    audio.playback_finished.emit()

    assert received == [True]
    assert ptt.release_calls == 1
    assert service.is_transmitting is False


def test_playback_error_releases_ptt_and_emits_transmission_error(service, audio, ptt):
    service.transmit("message.wav", owner="voice")

    received = []
    service.transmission_error.connect(lambda msg: received.append(msg))

    audio.playback_error.emit("fichier illisible")

    assert received == ["fichier illisible"]
    assert ptt.release_calls == 1
    assert service.is_transmitting is False


def test_playback_finished_is_ignored_when_not_transmitting(service, audio, ptt):
    """Défense en profondeur : un signal reçu hors d'une transmission pilotée par ce service ne doit rien déclencher."""

    received = []
    service.transmission_finished.connect(lambda: received.append(True))

    audio.playback_finished.emit()

    assert received == []
    assert ptt.release_calls == 0


# ------------------------------------------------------------------
# stop()
# ------------------------------------------------------------------

def test_stop_releases_ptt_before_stopping_audio(service, audio, ptt):
    service.transmit("message.wav", owner="voice")

    call_order = []
    ptt.release = lambda: call_order.append("release")
    audio.stop = lambda: call_order.append("stop")

    service.stop()

    assert call_order == ["release", "stop"]


def test_stop_emits_transmission_stopped_when_transmitting(service, audio, ptt):
    service.transmit("message.wav", owner="voice")

    received = []
    service.transmission_stopped.connect(lambda: received.append(True))

    service.stop()

    assert received == [True]
    assert service.is_transmitting is False
    assert ptt.release_calls == 1
    assert audio.stop_calls == 1


def test_stop_is_safe_and_silent_when_idle(service, audio, ptt):
    received = []
    service.transmission_stopped.connect(lambda: received.append(True))

    service.stop()

    assert received == []
    assert ptt.release_calls == 1  # toujours tenté, sans danger
    assert audio.stop_calls == 1
