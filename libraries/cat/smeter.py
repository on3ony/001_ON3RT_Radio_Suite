"""
ON3RT Radio Suite
libraries/cat/smeter.py

SMeterManager -- builder/décodeur pour la commande CI-V 0x15 0x02
("Reads the S-meter level") de l'IC-7300. Même forme que
KeyingSpeedManager (libraries/cat/keying_speed.py) : lecture seule
(un S-mètre ne se règle pas, contrairement à la vitesse de keyer),
même encodage BCD 2 octets que tous les réglages "niveau" 0-255 de ce
guide CI-V.

Valeurs ci-dessous, TOUTES issues du guide de référence CI-V officiel
Icom (IC-7300MK2 CI-V Reference Guide, p. 5) -- aucune valeur supposée :

    15 02  00 00 ~ 02 55  Reads the S-meter level.
                          (00 00=S0 ~ 01 20=S9 ~ 02 41=S9+60 dB)

Trois points d'ancrage SEULEMENT sont documentés par Icom : S0 (niveau
0), S9 (niveau 120) et S9+60dB (niveau 241). Les niveaux intermédiaires
(S1 à S8, et les paliers +dB au-delà de S9) ne sont PAS documentés par
Icom -- level_to_s_display() les obtient par interpolation linéaire
entre ces trois points (convention standard de S-mètre : paliers
réguliers de S1 à S9, puis échelle linéaire en dB au-delà de S9) --
une approximation raisonnable, PAS une valeur garantie par le
constructeur. Ne jamais présenter ce résultat interpolé comme un fait
CI-V documenté au même titre que les trois points d'ancrage eux-mêmes.

decode_level()/decode_s_display() ne lèvent jamais silencieusement une
mauvaise valeur : une donnée incomplète ou hors plage documentée lève
ValueError, à charge de l'appelant (CATEngine.read_smeter()) de ne
jamais l'invoquer sur une réponse manquante/malformée -- même
discipline que KeyingSpeedManager.decode_wpm().
"""

from __future__ import annotations

from libraries.cat.civ_protocol import CIVProtocol

_MIN_LEVEL = 0
_MAX_LEVEL = 255

# Points d'ancrage officiellement documentés (voir docstring du module)
_LEVEL_S0 = 0
_LEVEL_S9 = 120
_LEVEL_S9_PLUS_60DB = 241


class SMeterManager:

    READ_COMMAND = bytes((0x15, 0x02))

    def __init__(self):
        self.civ = CIVProtocol()

    def build_read_command(self) -> bytes:
        return self.civ.build(self.READ_COMMAND)

    def decode_level(self, data: bytes) -> int:
        if len(data) < 2:
            raise ValueError(f"donnée de S-mètre incomplète ({data!r}, 2 octets attendus)")

        hundreds = data[0]
        tens = data[1] >> 4
        units = data[1] & 0x0F

        level = hundreds * 100 + tens * 10 + units

        if not (_MIN_LEVEL <= level <= _MAX_LEVEL):
            raise ValueError(f"niveau de S-mètre hors plage ({level}, plage documentée 0-255)")

        return level

    def decode_s_display(self, data: bytes) -> str:
        return self.level_to_s_display(self.decode_level(data))

    @staticmethod
    def level_to_s_display(level: int) -> str:
        """Voir docstring du module -- interpolation linéaire entre les 3 seuls points documentés."""

        if level <= _LEVEL_S0:
            return "S0"

        if level < _LEVEL_S9:
            s_unit = min(8, round(level / _LEVEL_S9 * 9))
            return f"S{s_unit}"

        if level <= _LEVEL_S9_PLUS_60DB:
            db_over_s9 = round(
                (level - _LEVEL_S9) / (_LEVEL_S9_PLUS_60DB - _LEVEL_S9) * 60
            )
            return "S9" if db_over_s9 == 0 else f"S9+{db_over_s9}dB"

        return "S9+60dB"


if __name__ == "__main__":

    print("=" * 50)
    print("ON3RT Radio Suite")
    print("Test - smeter.py")
    print("=" * 50)

    manager = SMeterManager()

    print("Lecture :")
    print(manager.build_read_command().hex(" ").upper())

    for data, label in (
        (bytes((0x00, 0x00)), "attendu S0"),
        (bytes((0x00, 0x60)), "attendu ~S4-S5"),
        (bytes((0x01, 0x20)), "attendu S9"),
        (bytes((0x01, 0x80)), "attendu ~S9+30dB"),
        (bytes((0x02, 0x41)), "attendu S9+60dB"),
    ):
        print(f"\n{data.hex(' ').upper()} ({label}) :")
        print(manager.decode_s_display(data))
