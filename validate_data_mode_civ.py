#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
validate_data_mode_civ.py
-------------------------------------------------
ON3RT Radio Suite - Chantier "Correction DATA Mode IC-7300", etape 1

Diagnostic materiel autonome pour determiner la VRAIE valeur d'octet
de filtre acceptee par l'IC-7300 pour la commande CI-V 1A 06 (DATA
mode -- voir libraries/cat/data_mode.py). Ce fichier n'est pas encore
corrige par ce script : aucune modification de code de production ici,
seulement une mesure empirique reelle contre la radio.

Contexte (voir memoire projet project_datamode_civ_bugfix) : le
logiciel envoie actuellement "1A 06 01 00" (DATA=ON, filtre=0x00) et
la radio repond systematiquement FA (NG, rejete) -- confirme par
14 occurrences dans logs/cat_server.log entre le 2026-08-04 et le
2026-08-05. Consequence : WSJT-X croit passer en USB-D (donnees) alors
que la radio reste en USB voix (micro actif pendant l'emission).

Ce script envoie directement, via la meme couche bas niveau que la
production (SerialTransport + CIVProtocol, reutilisees telles quelles,
aucune reimplementation), la commande 1A 06 avec plusieurs valeurs de
filtre candidates (0x00 a 0x03) pour DATA=ON puis DATA=OFF, et
rapporte objectivement la reponse de la radio (FB=ACK / FA=NG) --
aucun jugement de l'operateur necessaire pour cette mesure, la reponse
CI-V est la preuve.

Risque materiel : minimal. Change uniquement le mode DATA de la radio
(reversible, aucune emission RF, PTT jamais touche). Le mode de base
(USB/LSB/etc) n'est pas modifie par ce script.

Usage :
    python validate_data_mode_civ.py [--port COM3] [--baudrate 19200]
"""

from __future__ import annotations

import argparse
import time

from libraries.cat.civ_protocol import CIVProtocol
from libraries.cat.serial_transport import SerialTransport

_CANDIDATE_FILTERS = (0x00, 0x01, 0x02, 0x03)

_ACK = 0xFB
_NG = 0xFA

_DATA_MODE_COMMAND = bytes((0x1A, 0x06))


def _select_port(default_port: str | None) -> str:
    if default_port:
        return default_port

    ports = SerialTransport.available_ports()

    if not ports:
        raise SystemExit("ECHEC : aucun port serie detecte.")

    print("\nPorts serie disponibles :")
    for i, p in enumerate(ports):
        print(f"  [{i}] {p}")

    while True:
        choice = input("Numero du port CAT de l'IC-7300 : ").strip()
        if choice.isdigit() and 0 <= int(choice) < len(ports):
            return ports[int(choice)]
        print("Choix invalide, reessayez.")


def _classify_response(response: bytes) -> str:
    if not response:
        return "TIMEOUT (aucune reponse)"
    if len(response) >= 5 and response[4] == _ACK:
        return "ACK (FB) -- accepte"
    if len(response) >= 5 and response[4] == _NG:
        return "NG (FA) -- rejete"
    return f"INATTENDU ({response.hex(' ').upper()})"


def _try_data_mode(civ: CIVProtocol, transport: SerialTransport, enabled: bool, filter_byte: int) -> str:
    state = 0x01 if enabled else 0x00
    frame = civ.build(_DATA_MODE_COMMAND, bytes((state, filter_byte)))

    response = transport.transact(frame)
    verdict = _classify_response(response)

    label = "DATA=ON " if enabled else "DATA=OFF"
    print(f"  {label}  filtre=0x{filter_byte:02X}  ->  TX={frame.hex(' ').upper()}  ->  {verdict}")

    time.sleep(0.3)  # laisse la radio respirer entre deux commandes de mode

    return verdict


def main() -> int:
    parser = argparse.ArgumentParser(description="Determine la valeur de filtre CI-V correcte pour DATA mode (IC-7300)")
    parser.add_argument("--port", default=None, help="Port serie CAT (ex. COM3). Si omis, liste interactive.")
    parser.add_argument("--baudrate", type=int, default=19200, help="Vitesse (bauds), defaut 19200")
    args = parser.parse_args()

    print("=" * 70)
    print("ON3RT Radio Suite - Diagnostic DATA Mode CI-V (IC-7300)")
    print("=" * 70)
    print("Ce script change uniquement le mode DATA de la radio (reversible).")
    print("Aucune emission, PTT jamais touche, mode de base (USB/LSB) inchange.")
    print("=" * 70)

    port = _select_port(args.port)

    transport = SerialTransport(port=port, baudrate=args.baudrate)
    civ = CIVProtocol()

    if not transport.connect():
        print(f"\nECHEC : impossible d'ouvrir {port}.")
        return 1

    print(f"\nConnecte sur {port} @ {args.baudrate} bauds.\n")

    results: dict[str, str] = {}

    try:
        print("-- Balayage DATA=ON avec chaque filtre candidat --")
        for filter_byte in _CANDIDATE_FILTERS:
            key = f"ON  filtre=0x{filter_byte:02X}"
            results[key] = _try_data_mode(civ, transport, enabled=True, filter_byte=filter_byte)

        print("\n-- Retour a DATA=OFF (nettoyage, meme filtre que Hamlib pour OFF) --")
        results["OFF filtre=0x00"] = _try_data_mode(civ, transport, enabled=False, filter_byte=0x00)

    finally:
        transport.disconnect()

    print("\n" + "=" * 70)
    print("RESUME")
    print("=" * 70)
    accepted = []
    for key, verdict in results.items():
        print(f"  [{verdict.split(' ')[0]:>7}] {key} -- {verdict}")
        if verdict.startswith("ACK"):
            accepted.append(key)

    print()
    if accepted:
        print(f"Filtre(s) accepte(s) par la radio : {', '.join(accepted)}")
        print("-> Utiliser cette valeur dans libraries/cat/data_mode.py (etape 2 du chantier).")
        return 0
    else:
        print("Aucun filtre candidat n'a ete accepte -- investigation complementaire necessaire")
        print("(adresse CI-V, cablage, ou commande elle-meme a revalider contre le manuel Icom).")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
