"""
ON3RT Radio Suite
libraries/qrz/service.py

Service QRZ
"""

from __future__ import annotations

import json
from pathlib import Path

from libraries.qrz.client import QRZClient


_client = None


def _config_file() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "config"
        / "qrz.json"
    )


def _load_config():

    cfg = _config_file()

    if not cfg.exists():
        raise FileNotFoundError(
            f"Configuration QRZ introuvable : {cfg}"
        )

    with open(cfg, "r", encoding="utf-8") as f:
        return json.load(f)


def client() -> QRZClient:
    global _client

    if _client is not None:
        return _client

    cfg = _load_config()

    _client = QRZClient(
        cfg["username"],
        cfg["password"],
    )

    if not _client.login():
        raise RuntimeError(_client.last_error)

    return _client


def lookup(callsign: str):

    if not callsign:
        return {}

    try:
        return client().lookup(
            callsign.strip().upper()
        )
    except Exception as exc:
        print("QRZ :", exc)
        return {}