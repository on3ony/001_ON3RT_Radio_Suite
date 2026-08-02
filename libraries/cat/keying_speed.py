"""
ON3RT Radio Suite
libraries/cat/keying_speed.py

KeyingSpeedManager -- builder de trames CI-V pour la commande de
niveau 0x14 0x0C ("Sets or reads the keying speed") de l'IC-7300, qui
règle la vitesse du keyer interne utilisé par la commande 0x17 (voir
libraries/cat/cw_message.py). Même forme exacte que PTTManager/
ModeManager/FrequencyManager (libraries/cat/).

Toutes les valeurs ci-dessous proviennent du guide de référence CI-V
officiel Icom (IC-7300MK2 CI-V Reference Guide, p. 5) -- aucune valeur
supposée :

    14 0C  00 00 ~ 02 55  Sets or reads the keying speed.
                          (00 00 = 6 WPM ~ 02 55 = 48 WPM)

Format de donnée : 2 octets BCD, exactement le même format que tous
les autres réglages de "niveau" 0-255 de ce même guide (AF gain, RF
power, mic gain...) -- premier octet = centaines (00-02), second octet
= BCD des dizaines/unités (00-99), jamais un entier binaire brut.
Vitesse (WPM) et octet de niveau (0-255) sont liés par une relation
strictement linéaire sur la plage documentée [6, 48] WPM <-> [0, 255] :
aucune autre plage, aucun arrondi non documenté.

6-48 WPM est une limite protocolaire (documentée), pas une politique
applicative : ce module refuse explicitement un WPM hors plage plutôt
que d'envoyer une trame invalide en silence -- à charge du futur
CIVTextKeyerBackend de décider quoi faire d'un WPM demandé hors plage
(ex. ignorer, tronquer, ou remonter l'erreur), pas de ce module.

decode_wpm() : pure fonction de décodage (octets -> WPM), volontairement
incluse ici (même fichier que l'encodage) plutôt que dans
libraries/cat/parser.py -- ce module reste la seule source de vérité
sur la conversion WPM <-> octets pour cette commande, dans un sens
comme dans l'autre. Son câblage réel dans CIVParser/CATEngine viendra
à une étape ultérieure (hors périmètre de cette étape, volontairement
limitée aux builders de trames).
"""

from __future__ import annotations

from libraries.cat.civ_protocol import CIVProtocol

MIN_WPM = 6
MAX_WPM = 48

_MIN_LEVEL = 0
_MAX_LEVEL = 255


class KeyingSpeedManager:

    READ_COMMAND = bytes((0x14, 0x0C))
    WRITE_COMMAND = bytes((0x14, 0x0C))

    def __init__(self):
        self.civ = CIVProtocol()

    def build_read_command(self) -> bytes:
        return self.civ.build(self.READ_COMMAND)

    def build_set_command(self, wpm: int) -> bytes:
        level = self._wpm_to_level(wpm)
        return self.civ.build(self.WRITE_COMMAND, self._encode_level(level))

    def decode_wpm(self, data: bytes) -> int:
        level = self._decode_level(data)
        return self._level_to_wpm(level)

    # ------------------------------------------------------------------
    # WPM <-> niveau 0-255 (relation linéaire documentée, voir docstring)
    # ------------------------------------------------------------------

    @staticmethod
    def _wpm_to_level(wpm: int) -> int:
        if not (MIN_WPM <= wpm <= MAX_WPM):
            raise ValueError(f"vitesse hors plage ({wpm} WPM, plage documentée {MIN_WPM}-{MAX_WPM} WPM)")

        ratio = (wpm - MIN_WPM) / (MAX_WPM - MIN_WPM)
        return round(ratio * _MAX_LEVEL)

    @staticmethod
    def _level_to_wpm(level: int) -> int:
        ratio = level / _MAX_LEVEL
        return round(MIN_WPM + ratio * (MAX_WPM - MIN_WPM))

    # ------------------------------------------------------------------
    # Niveau 0-255 <-> 2 octets BCD (format partagé par tous les
    # réglages de niveau de ce guide CI-V, voir docstring)
    # ------------------------------------------------------------------

    @staticmethod
    def _encode_level(level: int) -> bytes:
        if not (_MIN_LEVEL <= level <= _MAX_LEVEL):
            raise ValueError(f"niveau hors plage ({level}, plage 0-255)")

        hundreds, remainder = divmod(level, 100)
        tens, units = divmod(remainder, 10)

        return bytes((hundreds, (tens << 4) | units))

    @staticmethod
    def _decode_level(data: bytes) -> int:
        if len(data) < 2:
            raise ValueError(f"donnée de niveau incomplète ({data!r}, 2 octets attendus)")

        hundreds = data[0]
        tens = data[1] >> 4
        units = data[1] & 0x0F

        return hundreds * 100 + tens * 10 + units


if __name__ == "__main__":

    print("=" * 50)
    print("ON3RT Radio Suite")
    print("Test - keying_speed.py")
    print("=" * 50)

    manager = KeyingSpeedManager()

    print("Lecture :")
    print(manager.build_read_command().hex(" ").upper())

    for wpm in (6, 20, 25, 48):
        print(f"\nRéglage {wpm} WPM :")
        print(manager.build_set_command(wpm).hex(" ").upper())
