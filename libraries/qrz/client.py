"""
ON3RT Radio Suite
libraries/qrz/client.py

Client QRZ XML
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

import requests


class QRZClient:

    QRZ_URL = "https://xmldata.qrz.com/xml/current/"
    XMLNS = {"qrz": "http://xmldata.qrz.com"}

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.session_key = None
        self.last_error = ""

    def login(self) -> bool:

        self.last_error = ""
        self.session_key = None

        try:

            response = requests.get(
                self.QRZ_URL,
                params={
                    "username": self.username,
                    "password": self.password,
                },
                timeout=10,
            )

            response.raise_for_status()

            print("\n========== REPONSE QRZ ==========")
            print(response.text)
            print("=================================\n")

            root = ET.fromstring(response.text)

            error = root.find(".//qrz:Error", self.XMLNS)
            if error is not None and error.text:
                self.last_error = error.text.strip()
                return False

            key = root.find(".//qrz:Key", self.XMLNS)
            if key is None or not key.text:
                self.last_error = "Aucune clé de session reçue."
                return False

            self.session_key = key.text.strip()
            return True

        except Exception as exc:
            self.last_error = str(exc)
            return False

    def lookup(self, callsign: str) -> dict:

        if not self.session_key:
            raise RuntimeError("QRZ non connecté.")

        response = requests.get(
            self.QRZ_URL,
            params={
                "s": self.session_key,
                "callsign": callsign.upper(),
            },
            timeout=10,
        )

        response.raise_for_status()

        print("\n========== LOOKUP QRZ ==========")
        print(response.text)
        print("================================\n")

        root = ET.fromstring(response.text)

        error = root.find(".//qrz:Error", self.XMLNS)
        if error is not None and error.text:
            raise RuntimeError(error.text.strip())

        cs = root.find(".//qrz:Callsign", self.XMLNS)

        if cs is None:
            return {}

        def value(tag: str) -> str:
            element = cs.find(f"qrz:{tag}", self.XMLNS)
            if element is None or element.text is None:
                return ""
            return element.text.strip()

        return {
            "callsign": value("call"),
            "name": value("fname"),
            "surname": value("name"),
            "qth": value("addr2"),
            "country": value("country"),
            "locator": value("grid"),
            "cq": value("cqzone"),
            "itu": value("ituzone"),
            "latitude": value("lat"),
            "longitude": value("lon"),
        }


if __name__ == "__main__":

    USERNAME = "on3rt"
    PASSWORD = "53aALE78"

    client = QRZClient(USERNAME, PASSWORD)

    if client.login():

        print("Connexion QRZ OK\n")

        info = client.lookup("ON3RT")

        if not info:
            print("Indicatif introuvable.")
        else:
            for key, value in info.items():
                print(f"{key:12} : {value}")

    else:

        print("Connexion QRZ impossible")
        print("Erreur :", client.last_error)