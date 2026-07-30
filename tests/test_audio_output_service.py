"""
Tests de libraries/audio/audio_output_service.py.

sounddevice est systématiquement monkeypatché : ces tests ne doivent
jamais toucher un vrai périphérique audio (non déterministe, lent,
indisponible en environnement de test). La lecture réelle sur
matériel réel (IC-7300 en USB Audio CODEC notamment) est validée
manuellement par l'utilisateur, comme le reste des services matériels
de la Suite (CAT, propagation).
"""

import struct
import wave

import numpy as np
import pytest

from libraries.audio import audio_output_service as aos_module
from libraries.audio.audio_output_service import AudioOutputService


def _write_wav(path, n_channels=1, samplerate=44100, sampwidth=2, n_frames=100):
    with wave.open(str(path), "wb") as f:
        f.setnchannels(n_channels)
        f.setsampwidth(sampwidth)
        f.setframerate(samplerate)
        frames = bytearray()
        for i in range(n_frames * n_channels):
            frames += struct.pack("<h", (i % 200) - 100)
        f.writeframes(bytes(frames))


class _FakeStream:
    def __init__(self, active=True):
        self.active = active


# Reproduit la duplication réelle observée sur le matériel de
# l'utilisateur (IC-7300 visible 3 fois, une entrée par API audio) —
# voir docstring du module testé.
_FAKE_DEVICES = [
    {"name": "Casque (Realtek(R) Audio)", "hostapi": 0, "max_output_channels": 2,
     "max_input_channels": 0, "default_samplerate": 44100.0},
    {"name": "Microphone (Realtek(R) Audio)", "hostapi": 0, "max_output_channels": 0,
     "max_input_channels": 2, "default_samplerate": 44100.0},
    {"name": "Icom IC-7300 (3- USB Audio CODEC )", "hostapi": 0, "max_output_channels": 2,
     "max_input_channels": 0, "default_samplerate": 44100.0},
    {"name": "Icom IC-7300 (3- USB Audio CODEC )", "hostapi": 1, "max_output_channels": 2,
     "max_input_channels": 0, "default_samplerate": 44100.0},
    {"name": "Icom IC-7300 (3- USB Audio CODEC )", "hostapi": 2, "max_output_channels": 2,
     "max_input_channels": 0, "default_samplerate": 48000.0},
]

_FAKE_HOSTAPIS = [
    {"name": "MME"},
    {"name": "Windows DirectSound"},
    {"name": "Windows WASAPI"},
]


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture(autouse=True)
def fake_device_list(monkeypatch):
    """Isole toutes les requêtes de périphériques : jamais le vrai matériel pendant les tests."""

    monkeypatch.setattr(aos_module.sd, "query_devices", lambda: _FAKE_DEVICES)
    monkeypatch.setattr(aos_module.sd, "query_hostapis", lambda: _FAKE_HOSTAPIS)


@pytest.fixture
def service(tmp_path, qapp):
    return AudioOutputService(config_path=tmp_path / "audio_output.json")


# ------------------------------------------------------------------
# Persistance
# ------------------------------------------------------------------

def test_default_device_name_is_none(service):
    assert service.device_name is None


def test_set_output_device_persists_and_reloads(tmp_path, qapp):
    config_path = tmp_path / "audio_output.json"
    service = AudioOutputService(config_path=config_path)

    service.set_output_device("Icom IC-7300 (3- USB Audio CODEC )")

    reloaded = AudioOutputService(config_path=config_path)
    assert reloaded.device_name == "Icom IC-7300 (3- USB Audio CODEC )"


def test_set_output_device_none_clears_and_persists(tmp_path, qapp):
    config_path = tmp_path / "audio_output.json"
    service = AudioOutputService(config_path=config_path)
    service.set_output_device("Casque (Realtek(R) Audio)")

    service.set_output_device(None)

    reloaded = AudioOutputService(config_path=config_path)
    assert reloaded.device_name is None


def test_load_keeps_default_when_file_absent(tmp_path, qapp):
    service = AudioOutputService(config_path=tmp_path / "missing.json")
    assert service.device_name is None


def test_load_keeps_default_when_file_is_malformed(tmp_path, qapp):
    config_path = tmp_path / "audio_output.json"
    config_path.write_text("not json", encoding="utf-8")

    service = AudioOutputService(config_path=config_path)
    assert service.device_name is None


# ------------------------------------------------------------------
# Énumération des périphériques
# ------------------------------------------------------------------

def test_list_output_devices_excludes_input_only_devices(service):
    names = [d["name"] for d in service.list_output_devices()]
    assert "Microphone (Realtek(R) Audio)" not in names
    assert names.count("Casque (Realtek(R) Audio)") == 1


def test_list_output_devices_includes_every_hostapi_entry_for_a_duplicated_device(service):
    entries = [d for d in service.list_output_devices() if d["name"] == "Icom IC-7300 (3- USB Audio CODEC )"]
    assert len(entries) == 3
    assert {e["hostapi"] for e in entries} == {"MME", "Windows DirectSound", "Windows WASAPI"}


def test_resolve_device_prefers_wasapi_when_name_is_ambiguous(service):
    service.set_output_device("Icom IC-7300 (3- USB Audio CODEC )")

    index, samplerate = service._resolve_device()

    assert index == 4  # entrée WASAPI dans _FAKE_DEVICES
    assert samplerate == 48000.0


def test_resolve_device_falls_back_to_first_match_without_wasapi(service):
    service.set_output_device("Casque (Realtek(R) Audio)")

    index, samplerate = service._resolve_device()

    assert index == 0
    assert samplerate == 44100.0


def test_resolve_device_returns_none_for_unset_device_name(service):
    assert service._resolve_device() == (None, None)


def test_resolve_device_returns_none_for_unknown_device_name(service):
    service.device_name = "Périphérique inexistant"
    assert service._resolve_device() == (None, None)


# ------------------------------------------------------------------
# Lecture WAV (_read_wav)
# ------------------------------------------------------------------

def test_read_wav_returns_correct_shape_dtype_and_samplerate(tmp_path):
    wav_path = tmp_path / "tone.wav"
    _write_wav(wav_path, n_channels=1, samplerate=44100, n_frames=100)

    data, samplerate = aos_module._read_wav(wav_path)

    assert samplerate == 44100
    assert data.shape == (100, 1)
    assert data.dtype == np.int16


def test_read_wav_handles_stereo(tmp_path):
    wav_path = tmp_path / "stereo.wav"
    _write_wav(wav_path, n_channels=2, samplerate=44100, n_frames=50)

    data, samplerate = aos_module._read_wav(wav_path)

    assert data.shape == (50, 2)


# ------------------------------------------------------------------
# Ré-échantillonnage (_resample_linear)
# ------------------------------------------------------------------

def test_resample_linear_is_a_no_op_when_rates_match():
    data = np.array([[1], [2], [3]], dtype=np.int16)

    result = aos_module._resample_linear(data, 44100, 44100)

    assert result is data


def test_resample_linear_changes_length_proportionally():
    data = np.zeros((44100, 1), dtype=np.int16)

    result = aos_module._resample_linear(data, 44100, 48000)

    assert result.shape == (48000, 1)
    assert result.dtype == np.int16


# ------------------------------------------------------------------
# Lecture (play_file / stop / is_playing)
# ------------------------------------------------------------------

def test_play_file_reads_resamples_and_starts_playback_on_resolved_device(tmp_path, service, monkeypatch):
    wav_path = tmp_path / "tone.wav"
    _write_wav(wav_path, samplerate=44100, n_frames=100)
    service.set_output_device("Icom IC-7300 (3- USB Audio CODEC )")  # résout vers l'entrée WASAPI, 48000 Hz

    play_calls = []
    monkeypatch.setattr(aos_module.sd, "play", lambda data, sr, device=None: play_calls.append((data, sr, device)))
    monkeypatch.setattr(aos_module.sd, "get_stream", lambda: _FakeStream(active=True))

    service.play_file(wav_path)

    assert len(play_calls) == 1
    data, samplerate, device = play_calls[0]
    assert samplerate == 48000.0  # ré-échantillonné vers le débit du périphérique WASAPI
    assert data.shape[0] == round(100 * 48000 / 44100)
    assert device == 4


def test_play_file_stops_previous_playback_first(tmp_path, service, monkeypatch):
    wav_path = tmp_path / "tone.wav"
    _write_wav(wav_path)

    stop_calls = []
    monkeypatch.setattr(service, "stop", lambda: stop_calls.append(True))
    monkeypatch.setattr(aos_module.sd, "play", lambda *a, **k: None)

    service.play_file(wav_path)

    assert stop_calls == [True]


def test_play_file_emits_error_and_never_calls_play_when_file_is_missing(service, monkeypatch):
    play_calls = []
    monkeypatch.setattr(aos_module.sd, "play", lambda *a, **k: play_calls.append(True))

    received = []
    service.playback_error.connect(lambda msg: received.append(msg))

    service.play_file("does_not_exist.wav")

    assert len(received) == 1
    assert play_calls == []


def test_play_file_emits_error_when_stream_fails_to_open(tmp_path, service, monkeypatch):
    wav_path = tmp_path / "tone.wav"
    _write_wav(wav_path)

    def _raise(*args, **kwargs):
        raise aos_module.sd.PortAudioError("device unavailable")

    monkeypatch.setattr(aos_module.sd, "play", _raise)

    received = []
    service.playback_error.connect(lambda msg: received.append(msg))

    service.play_file(wav_path)

    assert len(received) == 1


def test_playback_finished_is_emitted_once_the_stream_becomes_inactive(tmp_path, service, monkeypatch):
    wav_path = tmp_path / "tone.wav"
    _write_wav(wav_path)

    monkeypatch.setattr(aos_module.sd, "play", lambda *a, **k: None)
    stream = _FakeStream(active=True)
    monkeypatch.setattr(aos_module.sd, "get_stream", lambda: stream)

    received = []
    service.playback_finished.connect(lambda: received.append(True))

    service.play_file(wav_path)
    assert received == []  # toujours en cours

    stream.active = False
    service._poll_playback()  # simule le prochain sondage du QTimer

    assert received == [True]


def test_stop_stops_polling_and_calls_sd_stop(service, monkeypatch):
    stop_calls = []
    monkeypatch.setattr(aos_module.sd, "stop", lambda: stop_calls.append(True))

    service._poll_timer.start()
    service.stop()

    assert stop_calls == [True]
    assert not service._poll_timer.isActive()


def test_is_playing_reflects_stream_state(service, monkeypatch):
    monkeypatch.setattr(aos_module.sd, "get_stream", lambda: _FakeStream(active=True))
    assert service.is_playing() is True

    monkeypatch.setattr(aos_module.sd, "get_stream", lambda: _FakeStream(active=False))
    assert service.is_playing() is False

    monkeypatch.setattr(aos_module.sd, "get_stream", lambda: None)
    assert service.is_playing() is False
