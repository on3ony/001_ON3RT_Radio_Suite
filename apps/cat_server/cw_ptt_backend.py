"""
ON3RT Radio Suite
apps/cat_server/cw_ptt_backend.py

PTTKeyerBackend : premier backend réel de keying CW (voir contrat
KeyerBackend, libraries/cw/keyer_backend.py) — réutilise le PTTGuard
existant (apps/cat_server/ptt_guard.py), jamais une seconde instance.

Emplacement — choix actuel, pas une règle définitive : ce fichier vit
dans apps/cat_server/ parce qu'il dépend directement de PTTGuard (même
package) — le sens normal des dépendances dans cette Suite est
apps/ -> libraries/, jamais l'inverse (même raisonnement déjà appliqué
à TransmissionService à l'étape 3 de Voix, et documenté dans sa
docstring). libraries/cw/ ne connaît donc jamais ce fichier ; c'est
PTTKeyerBackend qui importe le contrat depuis libraries/cw/, jamais
l'inverse.

Contrat minimal, AUCUNE connaissance du Morse ni du timing : key_down()/
key_up() sont de pures primitives bas niveau, appelées par CWService au
moment exact où il le décide — ce fichier ne sait ni ce qu'est un dit,
un dah, un WPM, ni combien de temps la clé doit rester activée. Toute
l'intelligence de timing reste exclusivement dans CWService (étape 5,
prochaine). Un futur backend (Winkeyer, Arduino, interface USB...)
pourra donc remplacer celui-ci sans qu'une seule ligne de CWService
n'ait à changer.

is_available() : toujours True — PTTGuard existe dès que la Suite est
démarrée (voir core/application.py), qu'une radio soit ou non
réellement connectée à cet instant. Un échec réel (radio déconnectée)
se manifeste par une PTTError levée depuis key_down() — jamais
absorbée ici, à charge de CWService de la transformer proprement en
signal d'erreur, jamais un plantage (même philosophie que
is_available() pour Pyttsx3Engine/PiperEngine, qui ne vérifient pas non
plus si une synthèse réussira réellement au moment de l'appel).

owner sur key_down() : transmis tel quel à PTTGuard.key(), même
convention de traçabilité que TransmissionService/VoiceService dans le
reste de la Suite.
"""

from __future__ import annotations

from apps.cat_server.ptt_guard import PTTGuard


class PTTKeyerBackend:
    """Backend de keying CW réutilisant PTTGuard — voir docstring du module pour l'ensemble des garanties."""

    name = "ptt"

    def __init__(self, ptt_guard: PTTGuard) -> None:
        self._ptt_guard = ptt_guard

    def is_available(self) -> bool:
        return True

    def key_down(self, owner: str | None = None) -> None:
        self._ptt_guard.key(owner=owner)

    def key_up(self) -> None:
        self._ptt_guard.release()
