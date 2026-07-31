"""
Tests de libraries/voice/voice_params.py.
"""

import dataclasses

import pytest

from libraries.voice.voice_params import VoiceParams


def test_default_values():
    params = VoiceParams()

    assert params.language == "FR"
    assert params.engine is None
    assert params.voice_profile is None
    assert params.rate is None
    assert params.volume is None


def test_is_immutable():
    params = VoiceParams()

    with pytest.raises(dataclasses.FrozenInstanceError):
        params.language = "EN"


def test_custom_values_are_kept_as_given():
    params = VoiceParams(language="EN", engine="pyttsx3", voice_profile="cloned_main", rate=150, volume=0.8)

    assert params.language == "EN"
    assert params.engine == "pyttsx3"
    assert params.voice_profile == "cloned_main"
    assert params.rate == 150
    assert params.volume == 0.8
