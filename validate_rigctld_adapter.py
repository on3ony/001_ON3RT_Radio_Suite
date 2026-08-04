#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
validate_rigctld_adapter.py
-------------------------------------------------
ON3RT Radio Suite - Capture reelle du protocole rigctld/Hamlib (chantier
CAT Sharing, etape RigctldAdapter -- mode diagnostic)

Outil de validation autonome pour observer, sur trafic reel, la
sequence exacte de commandes qu'envoie WSJT-X quand il est configure en
"Hamlib NET rigctl" -- avant d'implementer le moindre bout du protocole
rigctld sur la base de suppositions (\\dump_state en particulier, dont
le format exact n'est pas certain -- voir l'audit du chantier).

Construit UNIQUEMENT un RigctldAdapter (libraries/cat/cat_adapters/
rigctld_adapter.py) : aucun RadioService, aucune radio pilotee -- ce
script n'a besoin d'aucun materiel pour tourner. RigctldAdapter
journalise chaque ligne recue (RX) et chaque reponse envoyee (TX) dans
logs/cat_server.log (meme fichier que le CAT Server, voir
apps/cat_server/logger.py).

Depuis que "f"/"t"/"m"/"F" interrogent reellement CatSharingService
(voir rigctld_adapter.py), ce script fournit un faux CatSharingService
a valeurs fixes (_ValidationCatSharingService ci-dessous) -- uniquement
pour permettre a WSJT-X de derouler une capture complete sans plus
jamais planter sur cat_sharing_service=None, jamais pour piloter une
radio reelle ni pour valider les valeurs elles-memes (ca reste le
role d'une capture avec la vraie Suite). "F" (set_freq) est acceptee
sans jamais rien piloter : set_frequency_hz() renvoie toujours True
(valide le protocole, jamais un echec materiel simule a ce stade) et
memorise seulement la derniere valeur recue (last_frequency_hz),
disponible pour une journalisation ulterieure si besoin.

Usage :
    python validate_rigctld_adapter.py [--host 127.0.0.1] [--port 4532]

Puis, dans WSJT-X : Settings > Radio > Rig = "Hamlib NET rigctl",
Network Server = <host>:<port> (127.0.0.1:4532 par defaut), et ouvrir la
connexion CAT depuis WSJT-X. Observer ensuite logs/cat_server.log (ou la
console, les deux recoivent les memes lignes) pour la sequence RX/TX
reelle.

Ctrl+C pour arreter proprement (RigctldAdapter.stop()).
"""

from __future__ import annotations

import argparse
import sys

from PySide6.QtCore import QCoreApplication

from apps.cat_server.logger import logger as _cat_logger  # noqa: F401  (attache les handlers fichier+console)
from libraries.cat.cat_adapters.rigctld_adapter import DEFAULT_HOST, DEFAULT_PORT, RigctldAdapter


class _ValidationCatSharingService:
    """
    Double de validation, uniquement destiné aux essais du protocole
    rigctld dans ce script -- pas un vrai CatSharingService, aucune
    radio derrière : valeurs fixes, juste de quoi laisser WSJT-X
    dérouler une capture complète sur "f"/"t"/"m"/"F" sans planter.
    """

    def __init__(self):
        self.last_frequency_hz = None

    def get_frequency_hz(self):
        return 14074000

    def get_mode(self):
        return "USB"

    def get_ptt(self):
        return False

    def set_frequency_hz(self, frequency_hz):
        self.last_frequency_hz = frequency_hz
        return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()

    app = QCoreApplication(sys.argv)

    adapter = RigctldAdapter(cat_sharing_service=_ValidationCatSharingService(), host=args.host, port=args.port)
    adapter.start()

    print(f"RigctldAdapter (diagnostic) en écoute sur {args.host}:{adapter.actual_port}")
    print("WSJT-X : Settings > Radio > Rig = 'Hamlib NET rigctl'")
    print(f"         Network Server = {args.host}:{adapter.actual_port}")
    print("Ctrl+C pour arrêter.")
    print("Journal : logs/cat_server.log (et cette console)")

    try:
        app.exec()
    except KeyboardInterrupt:
        pass
    finally:
        adapter.stop()


if __name__ == "__main__":
    main()
