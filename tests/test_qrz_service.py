"""
Tests de libraries/qrz/service.py.

Se concentre sur save_credentials() : écriture, réinitialisation du
client mis en cache, et non-régression de client()/lookup()/_load_config().

_config_file() est systématiquement monkeypatché vers un fichier
temporaire : ces tests ne doivent jamais lire ni écrire le vrai
config/qrz.json du dépôt (identifiants réels).
"""

import json

import pytest

from libraries.qrz import service as qrz_service


@pytest.fixture(autouse=True)
def isolated_config_file(tmp_path, monkeypatch):
    """Redirige _config_file() vers un fichier temporaire pour chaque test."""

    fake_path = tmp_path / "qrz.json"
    monkeypatch.setattr(qrz_service, "_config_file", lambda: fake_path)

    # Le cache de client est un état module-niveau : jamais de fuite entre tests.
    monkeypatch.setattr(qrz_service, "_client", None)

    yield fake_path


def test_save_credentials_writes_expected_json(isolated_config_file):
    qrz_service.save_credentials("ON3RT", "secret123")

    assert isolated_config_file.exists()

    data = json.loads(isolated_config_file.read_text(encoding="utf-8"))
    assert data == {"username": "ON3RT", "password": "secret123"}


def test_save_credentials_resets_cached_client(isolated_config_file, monkeypatch):
    monkeypatch.setattr(qrz_service, "_client", object())  # simule un client déjà en cache

    qrz_service.save_credentials("ON3RT", "secret123")

    assert qrz_service._client is None


def test_load_config_reads_back_saved_credentials(isolated_config_file):
    qrz_service.save_credentials("ON3RT", "secret123")

    assert qrz_service._load_config() == {"username": "ON3RT", "password": "secret123"}


def test_load_config_still_raises_when_file_absent(isolated_config_file):
    """Non-régression : comportement de _load_config() inchangé quand le fichier n'existe pas."""

    with pytest.raises(FileNotFoundError):
        qrz_service._load_config()


def test_client_uses_credentials_written_by_save_credentials(isolated_config_file, monkeypatch):
    """
    Non-régression de client() : après save_credentials(), un appel à
    client() doit construire QRZClient avec exactement ces identifiants
    — sans appel réseau réel (QRZClient.login est monkeypatché).
    """

    captured = {}

    class FakeQRZClient:
        def __init__(self, username, password):
            captured["username"] = username
            captured["password"] = password
            self.last_error = ""

        def login(self):
            return True

    monkeypatch.setattr(qrz_service, "QRZClient", FakeQRZClient)

    qrz_service.save_credentials("ON3RT", "secret123")
    result = qrz_service.client()

    assert captured == {"username": "ON3RT", "password": "secret123"}
    assert isinstance(result, FakeQRZClient)


def test_lookup_returns_empty_dict_for_empty_callsign(isolated_config_file):
    """Non-régression : comportement de lookup() inchangé pour une entrée vide."""

    assert qrz_service.lookup("") == {}
