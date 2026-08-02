"""
ON3RT Radio Suite
apps/cat_server/cw_civ_text_backend.py

CIVTextKeyerBackend : second backend réel de keying CW, famille "texte"
(contrat TextBackend, libraries/cw/keyer_backend.py) — pilote le keyer
interne de l'IC-7300 via la commande CI-V 0x17 ("Send CW message"),
consommée exclusivement à travers les trois nouvelles méthodes de
RadioService (send_cw_message/stop_cw_message/set_keying_speed,
apps/cat_server/radio_service.py, étape 2) — jamais CATController ni
CATEngine ni les managers CI-V directement, même discipline de couches
que PTTKeyerBackend.

Emplacement — même raisonnement que PTTKeyerBackend (voir sa docstring,
apps/cat_server/cw_ptt_backend.py) : ce fichier vit dans
apps/cat_server/ parce qu'il dépend de RadioService/PTTGuard (même
package). libraries/cw/ ne connaît donc jamais ce fichier, ni aucune
ligne de libraries/cw/*, apps/cat_server/cw_ptt_backend.py n'a été
modifiée pour cette étape : les deux backends coexistent, inchangés
l'un par rapport à l'autre.

PTT explicitement piloté ici, volontairement -- validé après recherche
dans le guide de référence CI-V officiel Icom (IC-7300MK2) : "When the
transceiver is transmitting or the Break-in function is ON in the CW
mode, a message will be transmitted as CW code..." -- la commande 0x17
seule NE met PAS la radio en émission. Compter sur le Break-in
(réglage manuel côté radio, hors contrôle logiciel) aurait été fragile
et implicite ; ce backend active donc PTTGuard lui-même autour de
chaque envoi, exactement comme PTTKeyerBackend le fait pour la famille
élément, mais à la granularité du message entier plutôt que de
l'élément individuel.

Sécurité PTT : PTT est acquis en tout premier dans send_text(), avant
toute commande CI-V. Si la suite (réglage de vitesse ou envoi du
message) échoue, PTT est explicitement relâché avant de relever
l'exception -- TextDriver (libraries/cw/text_driver.py) n'appelle PAS
stop_sending() sur un échec de send_text() (seul un stop() explicite le
fait), ce backend ne peut donc compter sur personne d'autre pour
garantir qu'un PTT resté actif après un échec partiel soit relâché.

Farnsworth ignoré, volontairement (point ouvert d'ARCHITECTURE.md,
maintenant tranché) : la commande 14 0C ne règle qu'une vitesse unique
du keyer interne -- aucune commande CI-V documentée officiellement ne
permet un espacement Farnsworth séparé sur l'IC-7300. farnsworth_wpm
est donc accepté (contrat TextBackend) mais jamais transmis à la radio.

Erreurs : set_keying_speed()/send_cw_message()/stop_cw_message() de
RadioService ne lèvent jamais -- elles retournent False et journalisent
en interne. Ce backend traduit un False en exception (RuntimeError),
exactement comme PTTGuard.key() le fait déjà pour RadioService.set_ptt()
-- TextDriver/CWService transforment ensuite cette exception en
cw_error, sans jamais savoir ce qui a précisément échoué côté CAT.

is_available() : toujours True -- même logique que PTTKeyerBackend
(structure disponible dès que la Suite est démarrée, pas un état
matériel réel instantané).

max_chunk_chars : réutilise MAX_MESSAGE_CHARS de
libraries/cat/cw_message.py (limite protocolaire CI-V documentée, 30
caractères) plutôt que de la redéfinir ici en dur.
"""

from __future__ import annotations

from apps.cat_server.ptt_guard import PTTGuard
from apps.cat_server.radio_service import RadioService
from libraries.cat.cw_message import MAX_MESSAGE_CHARS


class CIVTextKeyerBackend:
    """Backend de keying CW famille "texte", pilotant l'IC-7300 via CI-V 0x17 -- voir docstring du module."""

    name = "civ_text"
    max_chunk_chars = MAX_MESSAGE_CHARS

    def __init__(self, radio_service: RadioService, ptt_guard: PTTGuard) -> None:
        self._radio_service = radio_service
        self._ptt_guard = ptt_guard

    def is_available(self) -> bool:
        return True

    def send_text(self, text: str, wpm: int, farnsworth_wpm: int | None = None, owner: str | None = None) -> None:
        self._ptt_guard.key(owner=owner)

        try:
            if not self._radio_service.set_keying_speed(wpm):
                raise RuntimeError("échec de la commande CI-V (vitesse du keyer, 14 0C)")

            if not self._radio_service.send_cw_message(text):
                raise RuntimeError("échec de la commande CI-V (envoi du message CW, 0x17)")
        except Exception:
            self._ptt_guard.release()
            raise

    def stop_sending(self) -> None:
        self._radio_service.stop_cw_message()
        self._ptt_guard.release()


if __name__ == "__main__":

    print("=" * 50)
    print("ON3RT Radio Suite")
    print("Test - cw_civ_text_backend.py")
    print("=" * 50)
    print(f"name = {CIVTextKeyerBackend.name!r}")
    print(f"max_chunk_chars = {CIVTextKeyerBackend.max_chunk_chars}")
