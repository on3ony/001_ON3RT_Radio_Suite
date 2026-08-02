"""
ON3RT Radio Suite
libraries/cw/keyer_backend.py

Contrat KeyerBackend — quatrième brique du chantier CW. Duck-type,
sans héritage imposé (même philosophie que libraries/voice/engines.py
pour les moteurs de synthèse vocale) :

    name: str
    is_available() -> bool
    key_down(owner: str | None = None) -> None
    key_up() -> None

Aucune notion de Morse, de timing, ni de vitesse (WPM) dans un backend
— ce sont deux primitives bas niveau, rien de plus : "activer la
clé/le PTT maintenant" et "la relâcher maintenant". TOUTE
l'intelligence (quand clencher, combien de temps, dans quel ordre)
reste dans CWService (étape 5, prochaine), qui pilote un backend sans
jamais connaître son fonctionnement interne. Un nouveau backend pourra
donc être ajouté plus tard (Winkeyer, keyer CAT si un jour disponible
sur un autre transceiver...) sans modifier une seule ligne de
CWService — exactement la contrainte validée avant cette étape.

is_available() : comme Pyttsx3Engine.is_available() ne vérifie que
l'installation du paquet (pas qu'une voix précise existe), un backend
ne vérifie ici que sa propre disponibilité STRUCTURELLE (le matériel
qu'il représente existe-t-il en principe), jamais l'état runtime exact
(ex. la radio est-elle réellement connectée à cet instant). Un échec
réel au moment de clencher (ex. radio déconnectée) se manifeste par une
exception levée depuis key_down(), à charge de CWService de la
transformer proprement en signal d'erreur — jamais un plantage.

owner sur key_down() : même convention de traçabilité que PTTGuard/
TransmissionService/VoiceService dans le reste de la Suite.

Emplacement de PTTKeyerBackend (le premier backend réel) : PAS ici,
volontairement. Il dépend de PTTGuard (apps/cat_server/), et la règle
de dépendance de la Suite est stricte -- apps/ peut dépendre de
libraries/, jamais l'inverse (même raisonnement déjà documenté dans
apps/cat_server/transmission_service.py, qui vit dans apps/cat_server/
pour la même raison). PTTKeyerBackend vit donc dans
apps/cat_server/cw_ptt_backend.py, pas ici.

NullKeyerBackend (ci-dessous) : implémentation de référence, sans
aucune dépendance -- un exemple concret et fonctionnel du contrat,
et un double directement réutilisable par les futurs tests de
CWService (étape 5), pour ne jamais dupliquer un faux backend dans
chaque fichier de test.

---

Contrat TextBackend -- seconde famille de backends (voir
libraries/cw/ARCHITECTURE.md), pour tout matériel où c'est le
matériel lui-même qui génère le timing Morse à partir d'un texte brut
(ex. CI-V 0x17 de l'IC-7300, un Winkeyer en mode host). Duck-type,
même philosophie que KeyerBackend ci-dessus :

    name: str
    is_available() -> bool
    max_chunk_chars: int
    send_text(text: str, wpm: int, farnsworth_wpm: int | None, owner: str | None = None) -> None
    stop_sending() -> None

max_chunk_chars : limite du nombre de caractères qu'un seul appel à
send_text() peut transporter -- propriété du backend concret (30 pour
l'IC-7300), jamais une constante codée en dur ailleurs. Le DÉCOUPAGE
d'un texte plus long en plusieurs morceaux n'est pas la responsabilité
du backend : c'est TextDriver (étape 4) qui lit max_chunk_chars et
découpe en conséquence, puis appelle send_text() autant de fois que
nécessaire -- le backend ne fait qu'exécuter un envoi, jamais un texte
entier composé de plusieurs morceaux.

wpm/farnsworth_wpm sur send_text() : transmis à chaque appel, jamais
mémorisés par CWService pour le compte du backend -- c'est au backend
de traduire cette vitesse vers son propre protocole (ex. commande CI-V
de niveau 14 0C pour l'IC-7300), CWService restant l'unique source de
vérité de la politique de vitesse.

is_available()/owner : mêmes conventions que KeyerBackend ci-dessus.

stop_sending() : doit interrompre l'envoi en cours côté matériel
(ex. "FF" pour l'IC-7300) -- symétrique de key_up() pour la famille
élément, mais jamais garanti aussi instantané par nature (certains
protocoles n'ont pas de moyen d'interrompre un caractère déjà en cours
de transmission) ; cette limite reste à la charge du backend concret
de documenter, pas de ce contrat.

NullTextKeyerBackend (ci-dessous) : implémentation de référence, sans
aucune dépendance -- même rôle que NullKeyerBackend pour la famille
élément, réutilisable par les futurs tests de TextDriver (étape 4)
sans dépendre d'aucun matériel réel.
"""

from __future__ import annotations


class NullKeyerBackend:
    """
    Backend de référence, sans aucun matériel : key_down()/key_up() ne
    font rien d'autre que mémoriser leur dernier appel. Toujours
    disponible (is_available() retourne True). Utile pour tester
    CWService sans dépendre de PTTGuard ni d'aucun matériel réel — voir
    docstring du module.
    """

    name = "null"

    def __init__(self) -> None:
        self.is_keyed = False
        self.last_owner: str | None = None
        self.key_down_calls = 0
        self.key_up_calls = 0

    def is_available(self) -> bool:
        return True

    def key_down(self, owner: str | None = None) -> None:
        self.is_keyed = True
        self.last_owner = owner
        self.key_down_calls += 1

    def key_up(self) -> None:
        self.is_keyed = False
        self.key_up_calls += 1


class NullTextKeyerBackend:
    """
    Backend de référence pour la famille "text", sans aucun matériel :
    send_text()/stop_sending() ne font rien d'autre que mémoriser leurs
    appels. Toujours disponible (is_available() retourne True). Utile
    pour tester TextDriver sans dépendre d'aucun matériel réel — voir
    docstring du module.
    """

    name = "null_text"

    def __init__(self, max_chunk_chars: int = 30) -> None:
        self.max_chunk_chars = max_chunk_chars
        self.sent_chunks: list[str] = []
        self.last_owner: str | None = None
        self.last_wpm: int | None = None
        self.last_farnsworth_wpm: int | None = None
        self.stop_sending_calls = 0

    def is_available(self) -> bool:
        return True

    def send_text(self, text: str, wpm: int, farnsworth_wpm: int | None, owner: str | None = None) -> None:
        self.sent_chunks.append(text)
        self.last_owner = owner
        self.last_wpm = wpm
        self.last_farnsworth_wpm = farnsworth_wpm

    def stop_sending(self) -> None:
        self.stop_sending_calls += 1
