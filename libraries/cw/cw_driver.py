"""
ON3RT Radio Suite
libraries/cw/cw_driver.py

Contrat CWDriver -- voir libraries/cw/ARCHITECTURE.md pour le schéma
complet des responsabilités (CWService -> CWDriver ->
ElementDriver/TextDriver -> KeyerBackend/TextBackend). Duck-type, sans
héritage imposé -- même philosophie que KeyerBackend
(libraries/cw/keyer_backend.py) et que les moteurs de synthèse vocale
(libraries/voice/engines.py) : ce fichier ne définit aucune classe,
uniquement la forme attendue.

    start(
        text: str,
        wpm: int,
        farnsworth_wpm: int | None,
        owner: str | None,
        on_started: Callable[[], None],
        on_progress: Callable[[int], None],
        on_finished: Callable[[], None],
        on_error: Callable[[str], None],
    ) -> None

    stop() -> None

Indépendance totale, imposée dès ce contrat -- CE FICHIER ne dépend et
ne dépendra jamais :
  - de Qt (aucun Signal, aucun QTimer, aucun QObject) ;
  - de RadioService, PTTGuard, ou de tout autre accès matériel ;
  - d'un backend concret (KeyerBackend, TextBackend, ou toute future
    famille) ;
  - de MorseEncoder ;
  - de TimingEngine.
Un driver concret (ElementDriver, TextDriver, ou une future famille)
dépendra nécessairement de certaines de ces briques pour faire son
travail réel -- c'est attendu et normal, ce sont des IMPLÉMENTATIONS du
contrat, pas le contrat lui-même. Ce fichier ne décrit qu'une forme,
jamais une implémentation.

Callbacks plutôt que signaux Qt : CWService est un QObject et expose
des signaux Qt (cw_started/cw_progress/cw_finished/cw_stopped/
cw_error), mais le contrat CWDriver n'en a et n'en aura jamais
connaissance. start() reçoit de simples fonctions Python ; c'est
CWService qui construit ces callbacks (par exemple des fermetures qui
appellent self.cw_progress.emit(...) via QTimer.singleShot(0, ...),
selon la convention déjà en place pour l'émission différée des
signaux) et les passe au driver à chaque appel. Un driver n'a donc
jamais besoin d'importer PySide6 pour respecter ce contrat -- y compris
ElementDriver, qui pourra utiliser QTimer en interne pour son propre
pilotage (détail d'implémentation qui lui appartient), sans que cela
transparaisse dans la forme du contrat.

Ce qu'un driver ne doit jamais connaître (responsabilités qui restent
exclusivement celles de CWService, jamais dupliquées dans un driver) :
  - l'état global de l'émission (CWState / IDLE-SENDING-STOPPED-ERROR) ;
  - la génération et le suivi des request_id ;
  - le refus d'une émission concurrente (CWService ne doit JAMAIS
    appeler start() tant qu'une émission précédente est active -- un
    driver n'a donc pas à s'en soucier, et n'a pas à exposer d'état
    "occupé") ;
  - la journalisation (CWLogger) ;
  - le choix du backend/driver à utiliser -- ce choix est fait UNE
    SEULE FOIS, dans core/application.py, jamais par CWService ni par
    un driver.

Rôle exact de chaque méthode :

start() démarre une émission pour request_id désigné implicitement par
les callbacks fournis (chaque appel à send() sur CWService construit
de nouvelles fermetures liées à son propre request_id -- le driver n'a
jamais besoin de connaître ni de manipuler un request_id lui-même,
seulement d'appeler les callbacks qu'on lui donne). Les callbacks sont
invoqués par le driver aux moments suivants :
  - on_started() : une fois, quand l'émission démarre réellement
    (immédiatement pour un driver élément par élément ; potentiellement
    différé pour un driver texte si le backend a besoin d'un délai
    avant confirmation) ;
  - on_progress(char_index) : zéro ou plusieurs fois, jamais avec un
    index qui recule. Un driver élément par élément l'appelle sur une
    progression réelle et confirmée ; un driver texte peut l'appeler
    sur une progression estimée (voir TimingEngine) -- dans ce cas, la
    distinction "réel/estimé" doit être documentée par le driver
    concret lui-même, jamais supposée implicitement par CWService ;
  - on_finished() : une fois, sur une fin d'émission réussie -- exclusif
    avec on_error() (jamais les deux pour un même request_id) ;
  - on_error(message) : une fois, sur un échec -- exclusif avec
    on_finished().

start() peut également lever une exception de façon synchrone, pour un
échec immédiat détectable avant même de démarrer quoi que ce soit (par
exemple un WPM invalide) -- CWService attrape cette exception et la
transforme en cw_error, exactement comme il le fait déjà aujourd'hui
pour un backend direct. Un échec survenant après un démarrage réussi
(donc après le retour de start()) passe uniquement par on_error(), pas
par une exception.

stop() doit garantir un relâchement immédiat de la ressource pilotée
(quelle qu'elle soit) et ne DOIT JAMAIS lever -- même garantie que
_safe_key_up() aujourd'hui, mais portée par le driver lui-même
désormais. stop() n'invoque aucun callback : CWService gère seul la
transition d'état et l'émission de cw_stopped autour de cet appel,
puisque la garantie de relâchement immédiat est synchrone par contrat.
stop() doit être sûr à appeler même si aucune émission n'est en cours
(idempotent), et sûr à appeler plusieurs fois de suite.

Règle générale (résume et généralise tout ce qui précède) : un
CWDriver n'a droit qu'à trois actions, jamais une de plus --
1) exécuter sa propre stratégie d'émission (à sa façon, avec ses
propres dépendances internes) ; 2) appeler les callbacks prévus ;
3) lever une exception si nécessaire. Un driver ne doit JAMAIS modifier
un état global de l'application -- ni le sien propre au sens de
CWService (CWState, request_id, refus de concurrence), ni aucun autre
état partagé de la Suite (journalisation comprise : un driver
n'écrit jamais dans un logger, c'est exclusivement CWService qui
journalise, à partir de ce que les callbacks lui rapportent). Un
driver ne connaît que sa propre stratégie d'émission ; toute décision
de politique reste exclusivement dans CWService.
"""

from __future__ import annotations
