"""
Tests de libraries/voice/voice_service.py.

Le moteur pyttsx3 réel n'est jamais utilisé ici : chaque test remplace
l'entrée "pyttsx3" du registre interne de VoiceService par un moteur
simulé (_FakeEngine) — jamais de vraie synthèse dans la suite
automatisée (lente, dépendante des voix installées sur la machine). La
validation avec le vrai pyttsx3 (écoute réelle du résultat) est faite
manuellement, comme le reste des garanties matérielles/OS de la Suite.

synthesize() est asynchrone (QThreadPool) : _wait_for_signal() pompe
la boucle d'événements Qt jusqu'à réception du signal attendu, avec un
délai de sécurité borné pour ne jamais bloquer indéfiniment un test en
cas de régression.

prune_cache() est synchrone (aucun QThreadPool) : les tests qui le
concernent n'ont pas besoin de _wait_for_signal(). L'âge des fichiers
est contrôlé directement via os.utime() (_write_wav(..., age_s=...))
plutôt qu'en attendant réellement — déterministe et instantané.
"""

import os
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

from libraries.voice.voice_params import VoiceParams
from libraries.voice.voice_service import VoiceService
import libraries.voice.voice_service as voice_service_module


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


class _FakeEngine:
    def __init__(self, available=True, raise_error=None, content=b"FAKE_WAV"):
        self.calls = []
        self._available = available
        self._raise_error = raise_error
        self._content = content

    def is_available(self):
        return self._available

    def synthesize(self, text, params, output_path):
        self.calls.append((text, params, output_path))
        if self._raise_error is not None:
            raise self._raise_error
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(self._content)


def _wait_for_signal(signal, timeout_ms=3000):
    loop = QEventLoop()
    captured = {}

    def _capture(*args):
        captured["args"] = args
        loop.quit()

    signal.connect(_capture)
    QTimer.singleShot(timeout_ms, loop.quit)
    loop.exec()
    signal.disconnect(_capture)

    return captured.get("args")


def _write_wav(path: Path, size: int = 8, age_s: float = 0) -> None:
    """Crée un faux .wav de `size` octets, vieux de `age_s` secondes (mtime)."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x00" * size)
    if age_s:
        timestamp = time.time() - age_s
        os.utime(path, (timestamp, timestamp))


@pytest.fixture
def fake_engine():
    return _FakeEngine()


@pytest.fixture
def service(qapp, tmp_path, fake_engine):
    svc = VoiceService(cache_dir=tmp_path / "voice_cache")
    svc._engines["pyttsx3"] = fake_engine
    return svc


# ------------------------------------------------------------------
# Cycle nominal
# ------------------------------------------------------------------

def test_synthesize_calls_engine_and_emits_finished(service, fake_engine):
    request_id = service.synthesize("CQ Concours", owner="test")

    args = _wait_for_signal(service.synthesis_finished)

    assert args is not None
    received_id, output_path = args
    assert received_id == request_id
    assert Path(output_path).exists()
    assert len(fake_engine.calls) == 1


def test_synthesize_returns_a_request_id(service):
    request_id = service.synthesize("CQ", owner="test")

    assert isinstance(request_id, str)
    assert len(request_id) > 0


# ------------------------------------------------------------------
# Variables dynamiques (avant calcul de la clé de cache)
# ------------------------------------------------------------------

def test_synthesize_resolves_variables_before_synthesis(service, fake_engine):
    service.synthesize("%RST% %SERIAL%", values={"RST": "599", "SERIAL": "007"}, owner="test")
    _wait_for_signal(service.synthesis_finished)

    assert fake_engine.calls[0][0] == "599 007"


def test_different_variable_values_produce_different_cache_files(service, fake_engine):
    service.synthesize("%CALL%", values={"CALL": "F4AAA"}, owner="test")
    _wait_for_signal(service.synthesis_finished)

    service.synthesize("%CALL%", values={"CALL": "F4BBB"}, owner="test")
    _wait_for_signal(service.synthesis_finished)

    assert len(fake_engine.calls) == 2
    assert fake_engine.calls[0][2] != fake_engine.calls[1][2]


def test_resolved_text_matches_regardless_of_how_it_was_produced(service, fake_engine):
    """Déterminisme : un gabarit résolu et le même texte passé littéralement produisent la même clé."""

    service.synthesize("%CALL%", values={"CALL": "F4AAA"}, owner="test")
    _wait_for_signal(service.synthesis_finished)

    service.synthesize("F4AAA", owner="test")
    args = _wait_for_signal(service.synthesis_finished)

    assert args is not None
    assert len(fake_engine.calls) == 1  # deuxième appel = cache hit, moteur jamais rappelé


# ------------------------------------------------------------------
# Cache HIT / MISS
# ------------------------------------------------------------------

def test_second_identical_call_is_a_cache_hit(service, fake_engine):
    service.synthesize("CQ", owner="test")
    _wait_for_signal(service.synthesis_finished)

    service.synthesize("CQ", owner="test")
    args = _wait_for_signal(service.synthesis_finished)

    assert len(fake_engine.calls) == 1
    assert args is not None


def test_different_params_produce_different_cache_entries(service, fake_engine):
    service.synthesize("CQ", params=VoiceParams(rate=150), owner="test")
    _wait_for_signal(service.synthesis_finished)

    service.synthesize("CQ", params=VoiceParams(rate=200), owner="test")
    _wait_for_signal(service.synthesis_finished)

    assert len(fake_engine.calls) == 2


def test_compute_cache_key_is_deterministic(service):
    params = VoiceParams(language="FR", rate=180)

    key1 = service._compute_cache_key("CQ Concours", "pyttsx3", params)
    key2 = service._compute_cache_key("CQ Concours", "pyttsx3", params)

    assert key1 == key2


def test_compute_cache_key_differs_for_different_text(service):
    params = VoiceParams()

    key1 = service._compute_cache_key("CQ", "pyttsx3", params)
    key2 = service._compute_cache_key("QRZ", "pyttsx3", params)

    assert key1 != key2


# ------------------------------------------------------------------
# cacheable=False
# ------------------------------------------------------------------

def test_cacheable_false_is_never_reused(service, fake_engine):
    service.synthesize("599 001", cacheable=False, owner="test")
    _wait_for_signal(service.synthesis_finished)

    service.synthesize("599 001", cacheable=False, owner="test")
    _wait_for_signal(service.synthesis_finished)

    assert len(fake_engine.calls) == 2  # jamais de cache hit


def test_cacheable_false_writes_to_the_tmp_subdirectory(service, fake_engine):
    service.synthesize("599 001", cacheable=False, owner="test")
    _wait_for_signal(service.synthesis_finished)

    assert fake_engine.calls[0][2].parent.name == "tmp"


def test_cacheable_true_is_the_default_and_does_not_use_tmp(service, fake_engine):
    service.synthesize("CQ", owner="test")
    _wait_for_signal(service.synthesis_finished)

    assert fake_engine.calls[0][2].parent.name != "tmp"


# ------------------------------------------------------------------
# Sélection de moteur
# ------------------------------------------------------------------

def test_default_engine_is_pyttsx3(service, fake_engine):
    service.synthesize("CQ", owner="test")
    _wait_for_signal(service.synthesis_finished)

    assert len(fake_engine.calls) == 1


def test_requesting_an_unknown_engine_falls_back_to_pyttsx3(service, fake_engine):
    service.synthesize("CQ", params=VoiceParams(engine="does_not_exist"), owner="test")
    args = _wait_for_signal(service.synthesis_finished)

    assert args is not None
    assert len(fake_engine.calls) == 1


def test_requesting_an_installed_but_unavailable_engine_falls_back(qapp, tmp_path):
    unavailable = _FakeEngine(available=False)
    fallback = _FakeEngine()

    svc = VoiceService(cache_dir=tmp_path / "voice_cache")
    svc._engines["xtts"] = unavailable
    svc._engines["pyttsx3"] = fallback

    svc.synthesize("CQ", params=VoiceParams(engine="xtts"), owner="test")
    _wait_for_signal(svc.synthesis_finished)

    assert unavailable.calls == []
    assert len(fallback.calls) == 1


# ------------------------------------------------------------------
# Erreurs
# ------------------------------------------------------------------

def test_engine_exception_emits_synthesis_error(qapp, tmp_path):
    failing = _FakeEngine(raise_error=RuntimeError("moteur en panne"))

    svc = VoiceService(cache_dir=tmp_path / "voice_cache")
    svc._engines["pyttsx3"] = failing

    request_id = svc.synthesize("CQ", owner="test")
    args = _wait_for_signal(svc.synthesis_error)

    assert args is not None
    received_id, message = args
    assert received_id == request_id
    assert "moteur en panne" in message


# ------------------------------------------------------------------
# prune_cache() — éviction par âge
# ------------------------------------------------------------------

def test_prune_cache_removes_old_files_from_permanent_cache_by_age(service):
    old_path = service._cache_dir / "old.wav"
    _write_wav(old_path, age_s=40 * 86400)  # 40 jours
    recent_path = service._cache_dir / "recent.wav"
    _write_wav(recent_path, age_s=0)

    result = service.prune_cache(max_cache_age_days=30, max_tmp_age_hours=None, max_total_size_mb=None)

    assert not old_path.exists()
    assert recent_path.exists()
    assert result.removed_files == 1


def test_prune_cache_removes_old_files_from_tmp_by_age(service):
    old_path = service._tmp_dir / "old.wav"
    _write_wav(old_path, age_s=30 * 3600)  # 30 heures
    recent_path = service._tmp_dir / "recent.wav"
    _write_wav(recent_path, age_s=0)

    result = service.prune_cache(max_cache_age_days=None, max_tmp_age_hours=24, max_total_size_mb=None)

    assert not old_path.exists()
    assert recent_path.exists()
    assert result.removed_files == 1


def test_prune_cache_age_criterion_disabled_by_none_keeps_old_files(service):
    old_path = service._cache_dir / "old.wav"
    _write_wav(old_path, age_s=100 * 86400)

    result = service.prune_cache(max_cache_age_days=None, max_tmp_age_hours=None, max_total_size_mb=None)

    assert old_path.exists()
    assert result.removed_files == 0
    assert result.freed_bytes == 0


# ------------------------------------------------------------------
# prune_cache() — éviction par taille totale
# ------------------------------------------------------------------

def test_prune_cache_evicts_oldest_first_when_over_size_budget(service):
    _write_wav(service._cache_dir / "a.wav", size=500, age_s=300)
    _write_wav(service._cache_dir / "b.wav", size=500, age_s=200)
    _write_wav(service._cache_dir / "c.wav", size=500, age_s=100)

    max_total_bytes = 1000
    result = service.prune_cache(
        max_cache_age_days=None,
        max_tmp_age_hours=None,
        max_total_size_mb=max_total_bytes / (1024 * 1024),
    )

    remaining = {p.name for p in service._cache_dir.glob("*.wav")}
    assert remaining == {"b.wav", "c.wav"}  # "a.wav" = le plus ancien, supprimé en premier
    assert result.removed_files == 1
    assert result.freed_bytes == 500


def test_prune_cache_size_criterion_disabled_by_none_keeps_oversized_cache(service):
    _write_wav(service._cache_dir / "a.wav", size=500, age_s=300)
    _write_wav(service._cache_dir / "b.wav", size=500, age_s=200)

    result = service.prune_cache(max_cache_age_days=None, max_tmp_age_hours=None, max_total_size_mb=None)

    assert len(list(service._cache_dir.glob("*.wav"))) == 2
    assert result.removed_files == 0


# ------------------------------------------------------------------
# prune_cache() — sécurité vis-à-vis d'une synthèse en cours
# ------------------------------------------------------------------

def test_prune_cache_never_removes_a_file_referenced_by_a_pending_task(service):
    protected_path = service._cache_dir / "in_progress.wav"
    _write_wav(protected_path, size=10_000, age_s=100 * 86400)

    service._pending_tasks["fake-request-id"] = SimpleNamespace(_output_path=protected_path)

    result = service.prune_cache(max_cache_age_days=1, max_tmp_age_hours=1, max_total_size_mb=0.0001)

    assert protected_path.exists()
    assert result.removed_files == 0


# ------------------------------------------------------------------
# prune_cache() — ne traite que les .wav
# ------------------------------------------------------------------

def test_prune_cache_ignores_non_wav_files(service):
    other_path = service._cache_dir / "notes.txt"
    other_path.write_text("keep me")
    old_timestamp = time.time() - 100 * 86400
    os.utime(other_path, (old_timestamp, old_timestamp))

    result = service.prune_cache(max_cache_age_days=1, max_tmp_age_hours=1, max_total_size_mb=0.0000001)

    assert other_path.exists()
    assert result.removed_files == 0


# ------------------------------------------------------------------
# prune_cache() — PruneResult toujours valide
# ------------------------------------------------------------------

def test_prune_cache_returns_prune_result_with_accurate_counts(service):
    _write_wav(service._cache_dir / "old.wav", size=123, age_s=40 * 86400)

    result = service.prune_cache(max_cache_age_days=30, max_tmp_age_hours=None, max_total_size_mb=None)

    assert result.removed_files == 1
    assert result.freed_bytes == 123


def test_prune_cache_returns_zeroed_result_when_nothing_removed(service):
    _write_wav(service._cache_dir / "recent.wav", age_s=0)

    result = service.prune_cache()

    assert result.removed_files == 0
    assert result.freed_bytes == 0


def test_prune_cache_returns_zeroed_result_on_an_empty_cache(service):
    result = service.prune_cache()

    assert result.removed_files == 0
    assert result.freed_bytes == 0


# ------------------------------------------------------------------
# prune_cache() — une seule référence de temps pour toutes les passes
# ------------------------------------------------------------------

def test_prune_cache_uses_a_single_time_reference_for_all_age_comparisons(service, monkeypatch):
    _write_wav(service._cache_dir / "old.wav", age_s=40 * 86400)
    _write_wav(service._tmp_dir / "old.wav", age_s=30 * 3600)

    call_count = {"n": 0}
    real_time = voice_service_module.time.time

    def counting_time():
        call_count["n"] += 1
        return real_time()

    monkeypatch.setattr(voice_service_module.time, "time", counting_time)

    service.prune_cache()

    assert call_count["n"] == 1


# ------------------------------------------------------------------
# prune_cache() — résilience si une suppression échoue
# ------------------------------------------------------------------

def test_prune_cache_continues_when_a_deletion_fails(service, monkeypatch):
    failing_path = service._cache_dir / "locked.wav"
    _write_wav(failing_path, age_s=40 * 86400)
    ok_path = service._cache_dir / "old.wav"
    _write_wav(ok_path, age_s=40 * 86400)

    real_unlink = Path.unlink

    def fake_unlink(self, *args, **kwargs):
        if self == failing_path:
            raise OSError("fichier verrouillé")
        return real_unlink(self, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", fake_unlink)

    result = service.prune_cache(max_cache_age_days=30, max_tmp_age_hours=None, max_total_size_mb=None)

    assert failing_path.exists()
    assert not ok_path.exists()
    assert result.removed_files == 1
