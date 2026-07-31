"""
Tests de libraries/voice/engines.py.

Pyttsx3Engine.is_available() est vérifié contre le vrai pyttsx3
(dépendance de la Suite) — test rapide, aucune vraie synthèse ici.
_find_voice_for_language() est testé avec un moteur SAPI5 simulé
(jamais le vrai) pour rester rapide et déterministe, sans dépendre des
voix réellement installées sur la machine qui exécute les tests.
"""

from libraries.voice.engines import Pyttsx3Engine, _find_voice_for_language


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
