"""
ON3RT Radio Suite
libraries/cat/data_mode.py

DataModeManager -- builder pour la commande CI-V 1A 06 ("DATA mode",
C_CTL_MEM / S_MEM_DATA_MODE dans la nomenclature Hamlib) de l'IC-7300.
Écriture seule, comme PTTManager (libraries/cat/ptt.py) : aucune
commande de lecture ici, par choix d'architecture -- voir plus bas.

Format de la commande vérifié par analyse du code source réel de
Hamlib (rigs/icom/icom.c::icom_set_mode(), dépôt Hamlib/Hamlib),
jamais supposé. Hamlib traduit un mode "PKTUSB" (et PKTLSB/PKTAM/
PKTFM) en mode de base (USB/LSB/AM/FM, voir
libraries/cat/mode.py::ModeManager, inchangé par ce fichier) PLUS une
commande CI-V séparée pour activer/désactiver l'indicateur DATA :

    ret = icom_transaction(rig, C_CTL_MEM, dm_sub_cmd, datamode, 2, ...)

avec C_CTL_MEM = 0x1A, dm_sub_cmd = S_MEM_DATA_MODE = 0x06 pour tout
rig autre que l'IC-7200 (non concerné ici, hors périmètre de cette
Suite). datamode[0] = 1 pour activer DATA, 0 pour le désactiver ;
datamode[1] est un numéro de filtre.

Numéro de filtre : 0x00 pour DATA=OFF (repris du code source Hamlib
lui-même, qui force cette valeur -- "the only good combo possible
according to manual", commentaire réel du code icom_set_mode()) et
0x01 pour DATA=ON. Cette dissymétrie N'ÉTAIT PAS le comportement
d'origine de ce fichier : la version précédente envoyait 0x00 dans les
deux cas, faute de référence confirmée pour le cas ON -- ce choix
avait été explicitement identifié comme un risque nécessitant une
validation matérielle réelle avant mise en production.

Cette validation a eu lieu (chantier "Correction DATA Mode IC-7300",
2026-08-05, IC-7300 réel, voir validate_data_mode_civ.py) : la radio
rejette (NG, FA) 0x00 comme numéro de filtre pour DATA=ON, et accepte
(ACK, FB) 0x01, 0x02 et 0x03. C'est ce rejet silencieux qui causait le
bug réel observé (WSJT-X croyait le mode DATA actif -- micro utilisé
pendant l'émission au lieu de l'entrée USB). 0x01 est retenu ici par
convention (FIL1, premier emplacement de filtre) : les trois valeurs
acceptées étant fonctionnellement équivalentes pour ce qui concerne
l'activation du mode DATA lui-même (aucune n'a d'effet démontré sur le
routage audio TX, qui dépend uniquement du bit DATA ON/OFF), le choix
entre elles n'a pas d'incidence connue -- à réévaluer si un besoin de
sélection de filtre DSP explicite apparaît un jour.

Aucune commande de lecture (pas de build_read_command()) : dans
l'architecture actuelle de cette Suite, aucun cycle de sondage
périodique ne relit l'état DATA de la radio -- ce n'est pas propre à
ce module ni un renoncement définitif, seulement l'état présent du
dépôt (même situation, avant ce chantier, pour le VFO : jamais
interrogé faute de consommateur). Vérifié aux sources Hamlib que ce
choix reste conforme au comportement réel d'un vrai rigctld pour
l'IC-7300 : icom_get_mode() n'effectue pas non plus de lecture CI-V
fraîche pour ce rig précis (RIG_TARGETABLE_MODE), il réutilise une
valeur mise en cache côté logiciel (priv->datamode) après la dernière
commande d'écriture -- exactement le principe retenu ici (cache côté
RadioService, pas dans ce fichier).
"""

from __future__ import annotations

from libraries.cat.civ_protocol import CIVProtocol

# Numéro de filtre : distinct selon l'état demandé -- voir docstring du
# module (validation matérielle réelle du 2026-08-05 : 0x00 rejeté par
# la radio pour DATA=ON, 0x01 accepté).
_FILTER_DATA_OFF = 0x00
_FILTER_DATA_ON = 0x01


class DataModeManager:

    WRITE_COMMAND = bytes((0x1A, 0x06))

    def __init__(self):
        self.civ = CIVProtocol()

    def build_set_command(self, enabled: bool) -> bytes:
        state = 0x01 if enabled else 0x00
        filter_byte = _FILTER_DATA_ON if enabled else _FILTER_DATA_OFF
        return self.civ.build(self.WRITE_COMMAND, bytes((state, filter_byte)))


if __name__ == "__main__":

    print("=" * 50)
    print("ON3RT Radio Suite")
    print("Test - data_mode.py")
    print("=" * 50)

    manager = DataModeManager()

    print("DATA ON :")
    print(manager.build_set_command(True).hex(" ").upper())

    print("\nDATA OFF :")
    print(manager.build_set_command(False).hex(" ").upper())
