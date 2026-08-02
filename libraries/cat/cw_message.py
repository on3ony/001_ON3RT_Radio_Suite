"""
ON3RT Radio Suite
libraries/cat/cw_message.py

CWMessageManager -- builder de trames CI-V pour la commande 0x17
("Send CW message") de l'IC-7300, seule commande qui pilote réellement
le keyer interne de la radio (voir libraries/cw/ARCHITECTURE.md,
section Historique). Même forme exacte que PTTManager/ModeManager/
FrequencyManager (libraries/cat/) : un builder de trames pur, aucune
connaissance de CWService/TextDriver/RadioService.

Toutes les valeurs ci-dessous proviennent du guide de référence CI-V
officiel Icom (IC-7300MK2 CI-V Reference Guide, section "Codes for CW
message contents", p. 15-16) -- aucune valeur supposée.

Limite de 30 caractères par trame (protocole, pas une politique
applicative) : TextDriver (libraries/cw/text_driver.py) est responsable
du découpage via TextBackend.max_chunk_chars -- ce module se contente
de refuser explicitement un texte trop long plutôt que d'envoyer une
trame invalide en silence.

Jeu de caractères : la table officielle documente un sous-ensemble
précis (chiffres, lettres majuscules ET minuscules, espace, ponctuation
courante) dont les codes coïncident exactement avec l'ASCII standard --
`text.encode("ascii")` suffit donc, sans table de correspondance custom.
Ce module n'impose PAS de filtrage sur ce sous-ensemble documenté : un
caractère ASCII valide mais absent de cette table (ex. un symbole sans
équivalent Morse) est transmis tel quel -- la radio décide de son
propre comportement, exactement le même principe que TextDriver
lui-même ("envoie même du texte que MorseEncoder ne pourrait pas
encoder entièrement -- la responsabilité du backend, pas du driver").
Un texte non-ASCII lève UnicodeEncodeError, un refus honnête plutôt
qu'un encodage inventé.

Pas de commande de LECTURE pour 0x17 (asymétrique par rapport à
PTTManager/ModeManager/FrequencyManager) : la doc officielle ne décrit
que l'envoi, jamais une lecture -- "Send CW message" n'a pas d'état à
relire.

Arrêt d'émission : un unique octet de donnée 0xFF (confirmé par la doc
officielle, "'FF' stops sending CW messages") -- pas la chaîne ASCII
"FF", un seul octet dont la valeur est 0xFF.
"""

from __future__ import annotations

from libraries.cat.civ_protocol import CIVProtocol

MAX_MESSAGE_CHARS = 30

_STOP_BYTE = 0xFF


class CWMessageManager:

    SEND_COMMAND = bytes((0x17,))

    def __init__(self):
        self.civ = CIVProtocol()

    def build_send_command(self, text: str) -> bytes:
        if len(text) > MAX_MESSAGE_CHARS:
            raise ValueError(
                f"message CW trop long ({len(text)} caractères, maximum {MAX_MESSAGE_CHARS} par trame 0x17)"
            )

        data = text.encode("ascii")
        return self.civ.build(self.SEND_COMMAND, data)

    def build_stop_command(self) -> bytes:
        return self.civ.build(self.SEND_COMMAND, bytes((_STOP_BYTE,)))


if __name__ == "__main__":

    print("=" * 50)
    print("ON3RT Radio Suite")
    print("Test - cw_message.py")
    print("=" * 50)

    manager = CWMessageManager()

    print("Envoi 'CQ ON3RT' :")
    print(manager.build_send_command("CQ ON3RT").hex(" ").upper())

    print("\nArrêt :")
    print(manager.build_stop_command().hex(" ").upper())
