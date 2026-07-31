"""
Tests de libraries/voice/engines.py.

Pyttsx3Engine.is_available() est vérifié contre le vrai pyttsx3
(dépendance de la Suite) — test rapide, aucune vraie synthèse ici.
_find_voice_for_language() est testé avec un moteur SAPI5 simulé
(jamais le vrai) pour rester rapide et déterministe, sans dépendre des
voix réellement installées sur la machine qui exécute les tests.

PiperEngine est testé avec un module "piper" entièrement simulé
(fixture fake_piper_module) — jamais de vrai modèle ONNX ni de vrai
paquet piper-tts installé. Le faux module est injecté dans
sys.modules le temps du test (monkeypatch.setitem, retrait automatique
à la fin, y compris si "piper" n'existait pas avant) : PiperEngine
importe "piper"/PiperVoice/SynthesisConfig exactement comme si le
paquet réel était installé, sans jamais en avoir besoin.
test_piper_is_not_available_when_piper_module_is_absent() est le seul
test qui compte sur l'absence réelle de piper-tts sur la machine de
développement (aucune fixture appliquée) — cohérent avec le fait que
Piper reste un moteur strictement optionnel de la Suite.
"""

import sys
import types
import wave
from pathlib import Path

import pytest

from libraries.voice.engines import (
    _DEFAULT_LENGTH_SCALE,
    PiperEngine,
    Pyttsx3Engine,
    _find_voice_for_language,
)
from libraries.voice.voice_params import VoiceParams


def test_pyttsx3_is_available():
    assert Pyttsx3Engine.is_available() is True


class _FakeVoice:
    def __init__(self, id, languages):
        self.id = id
        self.languages = languages


class _FakeSapiEngine:
    def __init__(self, voices):
        self._voices = voices

    def getProperty(self, name):
        assert name == "voices"
        return self._voices


def test_find_voice_for_language_matches_prefix():
    voices = [
        _FakeVoice("voice-en", ["en-US"]),
        _FakeVoice("voice-fr", ["fr-FR"]),
    ]
    engine = _FakeSapiEngine(voices)

    assert _find_voice_for_language(engine, "FR") == "voice-fr"
    assert _find_voice_for_language(engine, "EN") == "voice-en"


def test_find_voice_for_language_handles_bytes_language_codes():
    """Certaines versions de pyttsx3/pywin32 exposent languages en bytes plutôt qu'en str."""

    voices = [_FakeVoice("voice-fr", [b"fr-FR"])]
    engine = _FakeSapiEngine(voices)

    assert _find_voice_for_language(engine, "FR") == "voice-fr"


def test_find_voice_for_language_returns_none_when_no_match():
    voices = [_FakeVoice("voice-en", ["en-US"])]
    engine = _FakeSapiEngine(voices)

    assert _find_voice_for_language(engine, "DE") is None


def test_find_voice_for_language_returns_none_for_empty_language():
    voices = [_FakeVoice("voice-en", ["en-US"])]
    engine = _FakeSapiEngine(voices)

    assert _find_voice_for_language(engine, "") is None


# ------------------------------------------------------------------
# PiperEngine -- double de test du module "piper"
# ------------------------------------------------------------------

@pytest.fixture
def fake_piper_module(monkeypatch):
    """
    Installe un faux module "piper" dans sys.modules (retiré
    automatiquement à la fin du test par monkeypatch, que "piper" ait
    existé avant ou non) : PiperEngine importe "piper"/PiperVoice/
    SynthesisConfig exactement comme si le vrai paquet piper-tts était
    installé, sans jamais en avoir besoin réellement. PiperVoice.load()
    ne charge aucun modèle ONNX -- il trace juste ses appels.
    """

    load_calls: list[str] = []
    raise_on_load = {"path": None, "exc": None}

    class _FakeSynthesisConfig:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class _FakePiperVoice:
        def __init__(self, model_path):
            self.model_path = model_path
            self.synthesize_calls: list[dict] = []

        @classmethod
        def load(cls, model_path):
            load_calls.append(model_path)
            if raise_on_load["path"] is not None and model_path == raise_on_load["path"]:
                raise raise_on_load["exc"]
            return cls(model_path)

        def synthesize_wav(self, text, wav_file, syn_config=None):
            self.synthesize_calls.append({"text": text, "syn_config": syn_config})
            # Ecrit un WAV minimal mais valide, pour que le fichier
            # produit par PiperEngine.synthesize() soit reellement lisible.
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(22050)
            wav_file.writeframes(b"\x00\x00" * 100)

    fake_module = types.ModuleType("piper")
    fake_module.PiperVoice = _FakePiperVoice
    fake_module.SynthesisConfig = _FakeSynthesisConfig

    monkeypatch.setitem(sys.modules, "piper", fake_module)

    return types.SimpleNamespace(
        PiperVoice=_FakePiperVoice,
        SynthesisConfig=_FakeSynthesisConfig,
        load_calls=load_calls,
        raise_on_load=raise_on_load,
    )


def _touch_model(voices_dir: Path, name: str) -> Path:
    voices_dir.mkdir(parents=True, exist_ok=True)
    model_path = voices_dir / f"{name}.onnx"
    model_path.write_bytes(b"FAKE_ONNX")
    return model_path


# ------------------------------------------------------------------
# is_available()
# ------------------------------------------------------------------

def test_piper_is_available_when_module_installed_and_model_present(tmp_path, fake_piper_module):
    _touch_model(tmp_path, "fr_FR-siwis-medium")
    engine = PiperEngine(voices_dir=tmp_path)

    assert engine.is_available() is True


def test_piper_is_not_available_when_piper_module_is_absent(tmp_path):
    """Aucune fixture fake_piper_module ici : le vrai paquet piper-tts n'est pas installe sur cette machine."""

    _touch_model(tmp_path, "fr_FR-siwis-medium")
    engine = PiperEngine(voices_dir=tmp_path)

    assert engine.is_available() is False


def test_piper_is_not_available_without_any_model_file(tmp_path, fake_piper_module):
    engine = PiperEngine(voices_dir=tmp_path)  # tmp_path existe mais est vide

    assert engine.is_available() is False


def test_piper_is_not_available_when_voices_dir_does_not_exist(tmp_path, fake_piper_module):
    engine = PiperEngine(voices_dir=tmp_path / "does_not_exist")

    assert engine.is_available() is False


# ------------------------------------------------------------------
# Selection du modele (voice_profile / repli par langue)
# ------------------------------------------------------------------

def test_synthesize_uses_voice_profile_when_given(tmp_path, fake_piper_module):
    model_path = _touch_model(tmp_path, "custom_profile")
    engine = PiperEngine(voices_dir=tmp_path)

    engine.synthesize("Bonjour", VoiceParams(voice_profile="custom_profile"), tmp_path / "out.wav")

    assert fake_piper_module.load_calls == [str(model_path)]


def test_synthesize_falls_back_to_default_model_for_the_language(tmp_path, fake_piper_module):
    model_path = _touch_model(tmp_path, "fr_FR-siwis-medium")
    engine = PiperEngine(voices_dir=tmp_path)

    engine.synthesize("Bonjour", VoiceParams(language="FR"), tmp_path / "out.wav")

    assert fake_piper_module.load_calls == [str(model_path)]


def test_synthesize_raises_when_no_profile_and_no_language_mapping(tmp_path, fake_piper_module):
    engine = PiperEngine(voices_dir=tmp_path)

    with pytest.raises(ValueError):
        engine.synthesize("Hallo", VoiceParams(language="DE"), tmp_path / "out.wav")

    assert fake_piper_module.load_calls == []


def test_synthesize_raises_when_resolved_model_file_is_missing(tmp_path, fake_piper_module):
    engine = PiperEngine(voices_dir=tmp_path)  # aucun fichier .onnx cree

    with pytest.raises(FileNotFoundError):
        engine.synthesize("Bonjour", VoiceParams(voice_profile="missing_model"), tmp_path / "out.wav")

    assert fake_piper_module.load_calls == []


def test_missing_model_error_message_points_to_the_manual_install_directory(tmp_path, fake_piper_module):
    """Jamais de telechargement automatique -- le message doit orienter vers une installation manuelle."""

    engine = PiperEngine(voices_dir=tmp_path)

    with pytest.raises(FileNotFoundError) as exc_info:
        engine.synthesize("Bonjour", VoiceParams(voice_profile="missing_model"), tmp_path / "out.wav")

    assert str(tmp_path) in str(exc_info.value)


# ------------------------------------------------------------------
# Mise en cache des PiperVoice deja charges
# ------------------------------------------------------------------

def test_synthesize_loads_the_model_only_once_across_several_calls(tmp_path, fake_piper_module):
    _touch_model(tmp_path, "fr_FR-siwis-medium")
    engine = PiperEngine(voices_dir=tmp_path)

    engine.synthesize("Premier appel", VoiceParams(language="FR"), tmp_path / "out1.wav")
    engine.synthesize("Deuxieme appel", VoiceParams(language="FR"), tmp_path / "out2.wav")

    assert len(fake_piper_module.load_calls) == 1  # le modele n'est charge qu'une seule fois


def test_synthesize_reuses_the_same_cached_voice_instance(tmp_path, fake_piper_module):
    model_path = _touch_model(tmp_path, "fr_FR-siwis-medium")
    engine = PiperEngine(voices_dir=tmp_path)

    engine.synthesize("Premier appel", VoiceParams(language="FR"), tmp_path / "out1.wav")
    engine.synthesize("Deuxieme appel", VoiceParams(language="FR"), tmp_path / "out2.wav")

    cached_voice = engine._voices[str(model_path)]
    assert len(cached_voice.synthesize_calls) == 2


def test_different_models_are_cached_separately(tmp_path, fake_piper_module):
    _touch_model(tmp_path, "fr_FR-siwis-medium")
    _touch_model(tmp_path, "en_US-lessac-medium")
    engine = PiperEngine(voices_dir=tmp_path)

    engine.synthesize("Bonjour", VoiceParams(language="FR"), tmp_path / "out_fr.wav")
    engine.synthesize("Hello", VoiceParams(language="EN"), tmp_path / "out_en.wav")

    assert len(fake_piper_module.load_calls) == 2
    assert len(engine._voices) == 2


# ------------------------------------------------------------------
# Synthese
# ------------------------------------------------------------------

def test_synthesize_writes_a_readable_wav_file(tmp_path, fake_piper_module):
    _touch_model(tmp_path, "fr_FR-siwis-medium")
    engine = PiperEngine(voices_dir=tmp_path)
    output_path = tmp_path / "sub" / "out.wav"

    engine.synthesize("Bonjour tout le monde", VoiceParams(language="FR"), output_path)

    assert output_path.exists()
    with wave.open(str(output_path), "rb") as f:
        assert f.getnframes() > 0


def test_synthesize_passes_the_resolved_text_to_the_model(tmp_path, fake_piper_module):
    model_path = _touch_model(tmp_path, "fr_FR-siwis-medium")
    engine = PiperEngine(voices_dir=tmp_path)

    engine.synthesize("Un texte precis", VoiceParams(language="FR"), tmp_path / "out.wav")

    cached_voice = engine._voices[str(model_path)]
    assert cached_voice.synthesize_calls[0]["text"] == "Un texte precis"


def test_synthesize_passes_volume_via_synthesis_config_when_given(tmp_path, fake_piper_module):
    model_path = _touch_model(tmp_path, "fr_FR-siwis-medium")
    engine = PiperEngine(voices_dir=tmp_path)

    engine.synthesize("Bonjour", VoiceParams(language="FR", volume=0.5), tmp_path / "out.wav")

    cached_voice = engine._voices[str(model_path)]
    syn_config = cached_voice.synthesize_calls[0]["syn_config"]
    assert isinstance(syn_config, fake_piper_module.SynthesisConfig)
    assert syn_config.kwargs == {"length_scale": _DEFAULT_LENGTH_SCALE, "volume": 0.5}


def test_synthesize_always_applies_the_default_length_scale_even_without_volume(tmp_path, fake_piper_module):
    """
    Debit radio par defaut (voir docstring du module) applique a CHAQUE
    synthese Piper, que volume soit fourni ou non -- jamais de
    syn_config=None depuis l'ajout de _DEFAULT_LENGTH_SCALE.
    """

    model_path = _touch_model(tmp_path, "fr_FR-siwis-medium")
    engine = PiperEngine(voices_dir=tmp_path)

    engine.synthesize("Bonjour", VoiceParams(language="FR"), tmp_path / "out.wav")

    cached_voice = engine._voices[str(model_path)]
    syn_config = cached_voice.synthesize_calls[0]["syn_config"]
    assert isinstance(syn_config, fake_piper_module.SynthesisConfig)
    assert syn_config.kwargs == {"length_scale": _DEFAULT_LENGTH_SCALE}


# ------------------------------------------------------------------
# Gestion des erreurs
# ------------------------------------------------------------------

def test_synthesize_propagates_a_model_loading_error(tmp_path, fake_piper_module):
    model_path = _touch_model(tmp_path, "fr_FR-siwis-medium")
    fake_piper_module.raise_on_load["path"] = str(model_path)
    fake_piper_module.raise_on_load["exc"] = RuntimeError("modele corrompu")

    engine = PiperEngine(voices_dir=tmp_path)

    with pytest.raises(RuntimeError, match="modele corrompu"):
        engine.synthesize("Bonjour", VoiceParams(language="FR"), tmp_path / "out.wav")

    # Rien n'a ete mis en cache suite a un chargement en echec.
    assert str(model_path) not in engine._voices


def test_synthesize_does_not_cache_a_model_that_failed_to_load(tmp_path, fake_piper_module):
    """Un echec de chargement ne doit jamais laisser une entree partielle/invalide dans le cache."""

    model_path = _touch_model(tmp_path, "fr_FR-siwis-medium")
    fake_piper_module.raise_on_load["path"] = str(model_path)
    fake_piper_module.raise_on_load["exc"] = RuntimeError("modele corrompu")

    engine = PiperEngine(voices_dir=tmp_path)

    with pytest.raises(RuntimeError):
        engine.synthesize("Bonjour", VoiceParams(language="FR"), tmp_path / "out.wav")

    # Une fois le probleme corrige (plus d'erreur simulee), la synthese doit pouvoir reussir normalement.
    fake_piper_module.raise_on_load["path"] = None
    engine.synthesize("Bonjour", VoiceParams(language="FR"), tmp_path / "out.wav")

    assert str(model_path) in engine._voices
