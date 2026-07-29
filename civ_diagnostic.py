#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
civ_diagnostic.py
-------------------------------------------------
ON3RT Radio Suite - Diagnostic CI-V isole

Test autonome de la communication CI-V brute avec l'IC-7300 : utilise
exclusivement SerialTransport et CATEngine (libraries/cat), exactement
la meme chaine que la version v1.0 validee du CAT Server.

Volontairement SANS :
    - RadioService
    - Application / MainWindow / Dashboard
    - QTimer / QThread
    - tout autre module de la Radio Suite

Usage :
    python civ_diagnostic.py [PORT] [BAUDRATE]

Par defaut : COM3, 19200 bauds.
"""

import logging
import sys

from libraries.cat.cat_engine import CATEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def main() -> int:
    port = sys.argv[1] if len(sys.argv) > 1 else "COM3"
    baudrate = int(sys.argv[2]) if len(sys.argv) > 2 else 19200

    print("=" * 60)
    print("ON3RT Radio Suite - Diagnostic CI-V isole")
    print(f"Port : {port}  |  Baudrate : {baudrate}")
    print("=" * 60)

    engine = CATEngine(port=port, baudrate=baudrate)

    print("\n[1/5] Ouverture du port...")
    try:
        ok = engine.connect()
    except Exception as exc:
        print(f"  -> EXCEPTION a l'ouverture : {exc!r}")
        return 1

    print(f"  -> connect() = {ok}  (engine.connected = {engine.connected})")

    if not ok:
        print("\nEchec de l'ouverture du port. Arret du diagnostic.")
        return 1

    results = {}

    try:
        print("\n[2/5] Lecture frequence (commande CI-V 0x03)...")
        try:
            freq = engine.read_frequency()
            results["frequency"] = freq
            if freq:
                print(f"  -> {freq} Hz ({freq / 1_000_000:.6f} MHz)")
            else:
                print("  -> aucune reponse exploitable (0 Hz)")
        except Exception as exc:
            results["frequency"] = None
            print(f"  -> EXCEPTION : {exc!r}")

        print("\n[3/5] Lecture mode (commande CI-V 0x04)...")
        try:
            mode = engine.read_mode()
            results["mode"] = mode
            print(f"  -> {mode}")
        except Exception as exc:
            results["mode"] = None
            print(f"  -> EXCEPTION : {exc!r}")

        print("\n[4/5] Lecture PTT (commande CI-V 0x1C 0x00)...")
        try:
            ptt = engine.read_ptt()
            results["ptt"] = ptt
            print(f"  -> {ptt}")
        except Exception as exc:
            results["ptt"] = None
            print(f"  -> EXCEPTION : {exc!r}")

    finally:
        print("\n[5/5] Fermeture du port...")
        engine.disconnect()
        print(f"  -> engine.connected = {engine.connected}")

    print("\n" + "=" * 60)
    print("RESUME")
    print("=" * 60)
    print(f"Frequence : {results.get('frequency')}")
    print(f"Mode      : {results.get('mode')}")
    print(f"PTT       : {results.get('ptt')}")

    got_any_response = any(
        v not in (None, 0, "UNKNOWN")
        for v in (results.get("frequency"), results.get("mode"))
    )

    if got_any_response:
        print("\n=> La radio a repondu : la communication CI-V brute fonctionne.")
    else:
        print("\n=> Aucune reponse exploitable recue (voir les TIMEOUT ci-dessus).")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
