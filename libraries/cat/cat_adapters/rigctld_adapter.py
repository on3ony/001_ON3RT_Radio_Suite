#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=========================================================
ON3RT Radio Suite
libraries/cat/cat_adapters/rigctld_adapter.py
=========================================================
Description :
    Première implémentation concrète du contrat CatAdapter (voir
    libraries/cat/cat_adapters/base.py), pour le protocole rigctld/
    Hamlib ("Hamlib NET rigctl" côté WSJT-X).

    ÉTAPE ACTUELLE -- MODE DIAGNOSTIC UNIQUEMENT, PAS ENCORE LE VRAI
    PROTOCOLE :

        Avant d'implémenter \\dump_state/\\get_freq/etc. sur la base de
        suppositions, cette étape se contente d'ouvrir un serveur TCP
        minimal, d'accepter une connexion réelle de WSJT-X (configuré
        en "Hamlib NET rigctl"), et de journaliser INTÉGRALEMENT, dans
        l'ordre réel, chaque commande reçue -- exactement la méthode
        qui a permis de trouver la cause réelle du bug DX Cluster
        (capture de trafic réel avant toute correction, voir
        libraries/dxcluster/dxcluster_service.py).

        Aucune commande n'est interprétée ni exécutée. Après chaque
        ligne reçue, une réponse générique minimale (_DIAGNOSTIC_REPLY)
        est renvoyée -- uniquement pour éviter que le client Hamlib ne
        reste bloqué en attente d'une réponse avant d'envoyer sa
        commande suivante, ce qui empêcherait d'observer la suite de la
        séquence. Cette réponse n'a AUCUNE sémantique rigctld réelle
        (ni valeur de fréquence, ni code RPRT) : elle sera remplacée
        par de vraies réponses protocolaires à l'étape suivante, une
        fois la séquence réelle de commandes connue.

        cat_sharing_service est reçu par injection (même contrat que
        la future implémentation réelle) mais n'est JAMAIS interrogé
        ni modifié ici : cette étape ne pilote aucune radio, ne lit et
        n'écrit aucun état de CatSharingService.

    Usage prévu : construire RigctldAdapter, connecter WSJT-X dessus
    ("Hamlib NET rigctl", 127.0.0.1:4532 par défaut), lire
    logs/cat_server.log (voir apps/cat_server/logger.py) pour observer
    la séquence RX/TX réelle, puis définir le plus petit sous-ensemble
    du protocole à implémenter réellement à l'étape suivante.

    Première correction ponctuelle apportée suite à une capture réelle
    (2026-08-03) : \\get_powerstat est la toute première commande
    envoyée par WSJT-X, et répondre "0" (RIG_POWER_OFF, la réponse
    générique de diagnostic) fait échouer tout le reste de la
    négociation côté client Hamlib -- test CAT WSJT-X resté rouge,
    session interrompue après 3 commandes (\\get_powerstat, "T 0",
    "q"). Cette commande précise reçoit donc désormais une vraie
    réponse protocolaire ("1", RIG_POWER_ON) ; tout le reste continue
    de recevoir la réponse générique de diagnostic, une commande à la
    fois, jusqu'à la prochaine capture réelle.

    Deuxième correction ponctuelle (2026-08-03, capture suivante) : la
    négociation progresse ensuite jusqu'à \\dump_state, qui bloquait à
    son tour avec la réponse générique. Format de réponse vérifié
    directement dans le code source réel de netrigctl_open()
    (dépôt Hamlib/Hamlib, rigs/dummy/netrigctl.c) -- jamais supposé,
    voir _DUMP_STATE_REPLY ci-dessous pour le détail champ par champ.
    Protocole version 0 délibérément choisi (le plus simple : évite
    toute la section d'extension clé=valeur du protocole v1+).

    Troisième étape (2026-08-04) : "f" (get_freq), observée en boucle
    continue dans la capture réelle WSJT-X (environ une fois par
    seconde, avec "v" et "t"), est la première commande à sortir du
    mode diagnostic pur -- elle interroge désormais réellement
    cat_sharing_service.get_frequency_hz() et renvoie la fréquence
    courante en Hz, sur une seule ligne terminée par "\\n" (aucune
    conversion d'unité : CatSharingService expose déjà des Hz). Toute
    autre commande, y compris "v" et "t" observées dans la même
    boucle, continue de recevoir la réponse générique de diagnostic
    ci-dessus -- une commande à la fois, même discipline que pour
    \\get_powerstat/\\dump_state.

    Quatrième étape (2026-08-04) : "t" (get_ptt), également observée
    dans la même boucle continue, interroge désormais réellement
    cat_sharing_service.get_ptt() -- contrairement à "f", la valeur est
    un bool (jamais None, voir RadioStatus.ptt), converti en "1"/"0"
    (jamais str(bool) qui donnerait "True"/"False", invalide pour
    rigctld). Lecture seule, aucun rapport avec set_ptt()/PTTGuard, qui
    restent hors périmètre de cette étape. "v" reste la seule commande
    de la boucle continue encore générique.

    Cinquième étape (2026-08-04) : "v" (get_vfo), dernière commande de
    la boucle continue réelle, reçoit une réponse statique ("VFOA",
    voir _VFO_REPLY) -- contrairement à "f"/"t", jamais depuis
    cat_sharing_service. Aucune notion de VFO n'existe dans le chemin
    de données réel de la Suite : CatSharingService n'expose aucune
    méthode get_vfo/set_vfo (choix d'architecture délibéré) et
    RadioStatus.vfo n'est jamais mis à jour par RadioService.poll()
    (commentaire explicite dans le code : le VFO n'y est volontairement
    pas interrogé). "VFOA" correspond en outre à ce que WSJT-X
    sélectionne lui-même via "V VFOA" dans la capture réelle. Après
    cette étape, les trois commandes de la boucle continue ("v", "f",
    "t") reçoivent toutes une réponse réelle ou statique cohérente,
    plus aucune réponse générique dans ce cycle.

    Sixième étape (2026-08-04) : "m" (get_mode) interroge désormais
    réellement cat_sharing_service.get_mode(), avec une contrainte que
    "f"/"t" n'avaient pas -- format vérifié directement dans le code
    source réel de netrigctl_get_mode() (dépôt Hamlib/Hamlib,
    rigs/dummy/netrigctl.c), jamais supposé : la fonction cliente lit
    INCONDITIONNELLEMENT une deuxième ligne (read_string() séparé,
    passband) après la première (mode) -- une réponse à une seule ligne
    la laisse bloquée en lecture. Une capture réelle ultérieure a
    montré que l'écart de ~10 s persistait malgré cette correction,
    simplement déplacé avant "m" : cause probable révisée, voir
    ci-dessous ("s"). La réponse comporte deux lignes : le mode tel que
    renvoyé par cat_sharing_service (y compris "---" si la radio n'est
    pas encore connectée -- jamais traduit, même discipline que "f"/
    "t" ; un jeton non reconnu ne fait que déclencher un debug WARN
    côté client Hamlib, vérifié dans rig_parse_mode(), src/misc.c,
    aucune déconnexion), puis "0" (RIG_PASSBAND_NORMAL, macro Hamlib
    définie dans include/hamlib/rig.h -- la valeur normale/par défaut,
    pas un simple repli arbitraire, aucune largeur de bande n'existant
    nulle part dans le chemin de données réel de la Suite).

    Point de méthode confirmé par une capture réelle du 2026-08-04
    (après la sixième étape) : l'écart de ~10 s ne se situait pas après
    "m" mais avant, entre "s" et "m" -- "s" (get_split_vfo, toujours
    générique à ce stade) suit le même schéma bloquant que "m"
    (vérifié dans netrigctl_get_split_vfo(), même fichier
    netrigctl.c : transaction puis read_string() séparé et
    inconditionnel pour une deuxième ligne). Cet écart est donc
    attendu et non traité tant que "s" n'est pas implémentée -- hors
    périmètre de cette étape.

    Septième étape (2026-08-04) : "F <fréquence>" (set_freq) est la
    première commande à ÉCRIRE réellement sur la radio (toutes les
    précédentes ne faisaient que lire), et la première dont l'argument
    doit être analysé plutôt que la commande reconnue telle quelle.
    Format vérifié directement dans le code source réel de
    netrigctl_set_freq() (rigs/dummy/netrigctl.c) : la fréquence est
    envoyée en Hz sous forme décimale (ex. "F 14074055.000000"), une
    capture réelle ayant confirmé ce format exact. Notre réponse
    générique précédente ("0\n", sans le préfixe "RPRT ") provoquait
    "Protocol error while setting frequency." côté WSJT-X -- vérifié
    dans netrigctl_transaction() : une réponse qui ne commence pas par
    NETRIGCTL_RET ("RPRT ", include/hamlib/rig.h) fait retourner le
    nombre d'octets lus (positif) plutôt qu'un code, et
    netrigctl_set_freq() traduit tout retour positif en -RIG_EPROTO.

    Codes RPRT retenus, vérifiés contre le serveur de référence Hamlib
    (tests/rigctl_parse.c, declare_proto_rig(set_freq)) et l'énumération
    rig_errcode_e (include/hamlib/rig.h) :
        - argument non numérique OU numérique mais négatif -> "RPRT -1"
          (RIG_EINVAL = 1) -- le serveur de référence rejette un
          argument invalide via CHKSCN1ARG avant même d'appeler
          rig_set_freq(), jamais de contact avec le matériel dans ce
          cas ; une fréquence négative est traitée de la même façon,
          par décision explicite (paramètre invalide, pas une erreur
          d'E/S), donc rejetée avant toute conversion en entier ou
          appel à cat_sharing_service ;
        - échec de cat_sharing_service.set_frequency_hz() -> "RPRT -6"
          (RIG_EIO = 6, "IO error, including open failed") ;
        - succès -> "RPRT 0".
    Conversion Hz : arrondi à l'entier le plus proche (round()), jamais
    une troncature -- le CI-V n'a qu'une résolution de 1 Hz, tronquer
    biaiserait systématiquement vers le bas.

    Huitième étape (2026-08-04) : plusieurs connexions TCP simultanées
    sont désormais acceptées, au lieu d'une seule (la connexion
    supplémentaire était jusqu'ici immédiatement refusée). Correction
    d'une simplification assumée à l'origine ("suffisant pour une
    session WSJT-X manuelle") après vérification aux sources du
    serveur rigctld de référence (tests/rigctld.c) : sa boucle
    d'acceptation lance un thread détaché par connexion
    (pthread_create), sans jamais en rejeter une pour la seule raison
    qu'une autre est active -- seul l'accès au RIG* partagé est
    sérialisé (mutex_rigctld), pas les connexions elles-mêmes. Cette
    évolution fait suite à une capture réelle où WSJT-X ouvrait une
    seconde connexion pendant la fermeture de la première (juste avant
    "q"), rejetée par l'ancienne politique -- hypothèse retenue comme
    cause probable du message "IO error while opening connection to
    rig" affiché côté WSJT-X, sans certitude absolue tant que cette
    étape n'a pas été validée par une nouvelle capture réelle.

    L'accès à cat_sharing_service reste sérialisé de fait, sans code
    supplémentaire : tout s'exécute sur le thread Qt unique
    (CommandQueue, définie dans libraries/cat/command_queue.py et
    utilisée par CATEngine.queue_command()/execute_queue(), reste du
    code mort pour ce chemin -- jamais appelée ailleurs dans le dépôt,
    vérifié). L'état auparavant unique (un seul socket, un seul buffer)
    devient une collection self._connections associant chaque
    QTcpSocket actif à son propre buffer de reconstruction de lignes --
    sans quoi un fragment de commande d'un client pourrait se mélanger
    avec celui d'un autre. Chaque ligne RX/TX du journal identifie
    désormais son adresse d'origine (ip:port), indispensable pour
    rester diagnosticable avec plusieurs clients actifs.

    Tentative faite, puis annulée après preuve empirique : appeler
    socket.deleteLater() dans _on_client_disconnected()/stop(), pour
    limiter le risque de fuite mémoire déjà identifié (objets
    QTcpSocket jamais détruits explicitement à la déconnexion).
    Provoque un crash bas niveau ("Windows fatal exception: access
    violation") reproduit de façon certaine par deux tests précis
    exécutés en séquence -- lié au motif de connexion par lambda
    (socket.readyRead.connect(lambda s=socket: ...)), qui maintient une
    référence Python vers le socket au-delà de sa suppression de
    self._connections ; l'objet C++ Qt supprimé par deleteLater() reste
    ensuite référencé par cette fermeture lors d'un tour ultérieur de
    la boucle d'événements. Retiré dans cette étape -- le risque de
    fuite mémoire déjà signalé (voir chantier séparé) reste donc
    entier, pas résolu ici ; une correction demanderait de revoir le
    motif de connexion des signaux (ex. sender() plutôt qu'une lambda
    capturant le socket), hors périmètre de cette étape.

    Neuvième étape (2026-08-04) : "M <mode> <largeur>" (set_mode) est la
    deuxième commande d'écriture (après "F"), et la seule à nécessiter
    une traduction avant d'atteindre cat_sharing_service -- chantier
    DATA mode complet (libraries/cat/data_mode.py,
    CATEngine.set_data_mode(), CATController.set_data_mode(),
    RadioService.set_data_mode()/data_mode, CatSharingService.
    set_data_mode()/get_data_mode(), toutes les étapes précédentes déjà
    validées). Capture réelle du 2026-08-04 (logs/cat_server.log) :
    WSJT-X, DATA/USB-D sélectionné, envoie exactement "M PKTUSB -1",
    suivi immédiatement de "T 0" puis "q" (test CAT ponctuel, pas de
    "m" observée dans la même session pour confirmer la relecture réelle
    -- validation matérielle complète nécessaire après cette étape).
    Réponse générique précédente ("0\\n") provoquait "Protocol error /
    while setting current VFO mode" côté WSJT-X, exactement comme pour
    "F" avant sa correction (même cause : absence du préfixe "RPRT ").

    Format vérifié directement dans netrigctl_set_mode()/
    netrigctl_get_mode() (dépôt Hamlib/Hamlib, rigs/dummy/netrigctl.c) :
    client envoie "M<vfo> <mode> <largeur>\\n" (aucun préfixe VFO observé
    dans la capture réelle, comme pour "F"/"f"/"t") et attend une seule
    ligne "RPRT <code>". Codes de retour et validation de l'argument
    largeur vérifiés dans le serveur de référence Hamlib
    (tests/rigctl_parse.c, declare_proto_rig(set_mode)) : la largeur est
    lue via sscanf("%ld", ...) AVANT tout appel à rig_set_mode() --
    argument non numérique -> "RPRT -1" (RIG_EINVAL), sans jamais
    toucher cat_sharing_service, exactement le même principe que pour
    l'argument de "F". La valeur numérique elle-même n'est ensuite
    jamais utilisée : aucune notion de largeur de bande n'existe dans le
    chemin de données de la Suite (même constat que pour "m", sixième
    étape) -- seule sa validité syntaxique est vérifiée.

    Traduction "PKTxxx" -> mode de base + DATA : vérifiée directement
    dans le code source réel de icom_set_mode() (dépôt Hamlib/Hamlib,
    rigs/icom/icom.c), pas supposée. Point capital confirmé par lecture
    intégrale de la fonction : la transaction CI-V DATA (C_CTL_MEM=0x1A,
    S_MEM_DATA_MODE=0x06) est envoyée à CHAQUE changement de mode, pas
    seulement pour les modes PKT* -- "datamode[0] = is_data_mode ? 0x01
    : 0x00" est calculé pour tout mode, y compris les modes non-DATA
    (0x00 explicite). Un "M USB -1" reçu après un "M PKTUSB -1"
    désactive donc réellement DATA, exactement comme le ferait un vrai
    IC-7300 -- ce comportement est donc reproduit ici : set_data_mode()
    est appelée après CHAQUE "M" réussi, avec True pour les 4 modes
    PKTUSB/PKTLSB/PKTAM/PKTFM (traduits respectivement vers USB/LSB/AM/
    FM, seuls modes PKT* gérés par icom_set_mode()) et False pour tout
    autre mode, jamais seulement lorsque l'état DATA change réellement
    (icom_set_mode() ne compare jamais l'ancien et le nouvel état DATA
    non plus, seulement mode != current_mode).

    Ordre des deux appels -- mode de base d'abord, puis DATA -- reproduit
    fidèlement l'ordre réel de icom_set_mode() (le bloc DATA n'est
    atteint que "if (retval == RIG_OK && ...)" après le set du mode de
    base) : si cat_sharing_service.set_mode(mode_de_base) échoue, DATA
    n'est jamais tenté, "RPRT -6" est renvoyé immédiatement -- même
    codes RPRT que "F" (RIG_EIO=6 en cas d'échec de
    cat_sharing_service, quelle qu'en soit la cause réelle, y compris un
    mode de base non reconnu par ModeManager.MODES : cette couche ne
    duplique délibérément aucune liste de modes valides, laissée à
    RadioService/ModeManager, seule source de vérité -- voir aussi
    architecture study validée pour ce chantier).

    Mise à jour symétrique de "m" (get_mode, sixième étape) : traduction
    inverse vérifiée dans icom_get_mode() (même fichier icom.c, lecture
    intégrale) -- le mode PKTxxx n'est reconstruit QUE si le mode de
    base lu vaut USB/LSB/AM/FM ET si l'indicateur DATA est actif ; si
    DATA est actif mais que le mode de base est autre chose (ex. CW,
    scénario où data_mode aurait été laissé à True par un "M PKTUSB -1"
    puis le mode changé hors rigctld sans jamais repasser par "M"), la
    traduction est silencieusement ignorée et le mode de base est
    renvoyé tel quel -- comportement reproduit ici à l'identique, plutôt
    que de deviner une correspondance PKT pour un mode qui n'en a pas.
    cat_sharing_service.get_data_mode() (dernière étape du chantier
    DATA) est interrogée à chaque "m", sans coût matériel (valeur mise
    en cache côté RadioService, jamais une transaction CI-V, voir
    docstring de DataModeManager) -- cohérent avec l'appel déjà répété
    à chaque "m" dans la boucle continue observée en capture réelle.

    Dixième étape (2026-08-04) : "T <ptt>" (set_ptt) -- validation
    matérielle réelle du chantier DATA (Test PTT WSJT-X, IC-7300 réel),
    changement de mode PKTUSB confirmé sans erreur, mais nouvelle
    "Protocol error / while setting PTT on". Capture réelle
    (logs/cat_server.log, connexion 127.0.0.1:63767) : séquence
    "m" -> "PKTUSB\\n0\\n" (DATA toujours actif, hérité d'un "M" antérieur
    sur une autre connexion), "t" -> "0\\n" (get_ptt, correctement
    formaté, aucun préfixe attendu pour cette commande de lecture), puis
    "T 1" reçoit encore la réponse générique "0\\n" -- cause identique à
    "F"/"M" avant leur correction : "T" (set_ptt, écriture) n'a jamais
    été implémentée depuis la quatrième étape (seule "t", lecture,
    l'avait été) ; retombe dans la branche générique, réponse sans
    préfixe "RPRT " -> netrigctl_set_ptt() traduit tout retour positif
    en -RIG_EPROTO (même mécanisme documenté à la septième étape pour
    "F"), WSJT-X enchaîne "T 0" puis "q" (fermeture immédiate de la
    session de test), exactement le motif déjà observé pour "F"/"M".

    Format vérifié directement dans netrigctl_set_ptt() (dépôt
    Hamlib/Hamlib, rigs/dummy/netrigctl.c) : client envoie
    "T<vfo> <ptt>\\n" (aucun préfixe VFO observé en capture réelle,
    comme pour "F"/"M"/"f"/"t") avec <ptt> un entier décimal, valeur
    passée telle quelle depuis ptt_t (aucune notion de largeur/passband
    ici, contrairement à "M"). Validation et codes RPRT vérifiés dans le
    serveur de référence Hamlib (tests/rigctl_parse.c,
    declare_proto_rig(set_ptt)) : l'argument est lu par
    sscanf(arg1, "%d", &scr) -- non numérique -> "RPRT -1" (RIG_EINVAL),
    sans jamais toucher cat_sharing_service (même principe que pour la
    largeur de "M" et la fréquence de "F") ; la valeur entière obtenue
    est ensuite validée contre un switch() explicite -- seules
    RIG_PTT_OFF=0, RIG_PTT_ON=1, RIG_PTT_ON_MIC=2 et RIG_PTT_ON_DATA=3
    sont acceptées, toute autre valeur (y compris négative) retombe
    dans le "default" -> "RPRT -1" également, avant tout appel à
    rig_set_ptt().

    Traduction vers CatSharingService.set_ptt(bool) : aucune notion de
    source PTT (micro/data, distincte du PTT direct) n'existe nulle
    part dans le chemin de données réel de la Suite -- PTTManager
    (libraries/cat/ptt.py) et CatSharingService.set_ptt() n'acceptent
    qu'un booléen. Les 3 valeurs "actives" du protocole (1, 2, 3) sont
    donc toutes traduites vers True, seule 0 vers False -- même
    principe de collapse Hamlib-spécifique -> Suite déjà appliqué pour
    la traduction des modes PKTxxx à la neuvième étape (traduction
    strictement locale à cette couche, jamais propagée plus bas).
    Valeur hors {0,1,2,3} (ou non numérique) -> "RPRT -1", sans jamais
    appeler cat_sharing_service.set_ptt() -- même discipline que pour
    "F"/"M". Échec de cat_sharing_service.set_ptt() (RadioService non
    connectée ou exception CI-V) -> "RPRT -6" ; succès -> "RPRT 0".
=========================================================
"""

from __future__ import annotations

import logging

from PySide6.QtNetwork import QHostAddress, QTcpServer

from libraries.cat.cat_adapters.base import CatAdapter

# Même logger que apps/cat_server/logger.py ("CAT_SERVER") : cette
# couche basse ne dépend pas de apps/ (respect des couches, voir
# libraries/cat/serial_transport.py), mais réutilise le logging
# standard sous le même nom, ce qui route automatiquement vers les
# mêmes handlers une fois CATLogger initialisé.
_log = logging.getLogger("CAT_SERVER")

# Port rigctld conventionnel (Hamlib) -- WSJT-X, configuré en "Hamlib
# NET rigctl", s'y connecte par défaut.
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 4532

# Réponse générique minimale, envoyée après CHAQUE ligne reçue non
# spécifiquement traitée ci-dessous, dans ce mode diagnostic -- voir
# docstring du module. Aucune sémantique rigctld réelle : sert
# uniquement à maintenir la connexion active pour observer la suite de
# la séquence.
_DIAGNOSTIC_REPLY = b"0\n"

# Réponse rigctld conforme pour \get_powerstat -- RIG_POWER_ON (1),
# jamais la réponse générique ci-dessus (qui vaudrait RIG_POWER_OFF et
# fait échouer la négociation côté client Hamlib, voir docstring du
# module). Seule commande traitée spécifiquement à ce stade.
_POWERSTAT_ON_REPLY = b"1\n"

# Réponse statique pour "v" (get_vfo) -- "VFOA", jamais interrogée
# depuis cat_sharing_service : aucune notion de VFO n'existe dans le
# chemin de données réel de la Suite (CatSharingService n'expose ni
# get_vfo ni set_vfo, RadioStatus.vfo n'est jamais mis à jour par
# RadioService.poll()). Correspond en outre au VFO que WSJT-X
# sélectionne lui-même via "V VFOA" dans la capture réelle.
_VFO_REPLY = b"VFOA\n"

# Deuxième ligne statique de la réponse à "m" (get_mode) -- 0, soit
# RIG_PASSBAND_NORMAL (macro Hamlib, include/hamlib/rig.h : "Macro for
# bandpass to be set to normal"), pas un simple repli arbitraire.
# Aucune largeur de bande réelle n'existe dans le chemin de données de
# la Suite (voir docstring du module, sixième étape).
_MODE_PASSBAND_NORMAL = 0

# Codes RPRT (protocole rigctld) pour "F"/"M" (set_freq/set_mode) --
# commandes d'écriture. Format "RPRT <code>\n" vérifié dans
# netrigctl_transaction() (rigs/dummy/netrigctl.c) et NETRIGCTL_RET
# (include/hamlib/rig.h) : une réponse qui ne commence pas par
# "RPRT " n'est pas reconnue comme un code de retour, voir docstring
# du module, septième étape. Valeurs numériques issues de
# rig_errcode_e (include/hamlib/rig.h) : RIG_OK=0, RIG_EINVAL=1,
# RIG_EIO=6.
_RPRT_SUCCESS = b"RPRT 0\n"
_RPRT_INVALID_PARAM = b"RPRT -1\n"
_RPRT_IO_ERROR = b"RPRT -6\n"

# Traduction "PKTxxx" -> mode de base, pour "M" (set_mode). Les 4 seuls
# modes PKT* traduits par icom_set_mode() (dépôt Hamlib/Hamlib,
# rigs/icom/icom.c, switch(mode) vérifié par lecture intégrale de la
# fonction, voir docstring du module, neuvième étape) -- tout autre
# jeton de mode (USB, LSB, AM, FM, CW, RTTY, CW-R, RTTY-R, DV, ou
# inconnu) est transmis tel quel à cat_sharing_service.set_mode(),
# jamais traduit ni validé localement (aucune liste de modes valides
# dupliquée ici, voir docstring du module).
_PKT_MODE_TO_BASE_MODE = {
    "PKTUSB": "USB",
    "PKTLSB": "LSB",
    "PKTAM": "AM",
    "PKTFM": "FM",
}

# Traduction inverse, pour "m" (get_mode) : reconstruit "PKTxxx" à
# partir du mode de base UNIQUEMENT lorsque get_data_mode() est actif
# ET que le mode de base courant fait partie des 4 clés ci-dessus --
# reproduit fidèlement icom_get_mode() (même fichier icom.c), qui
# ignore silencieusement la reconstruction PKT pour tout autre mode de
# base (ex. CW), même si l'indicateur DATA est resté actif. Un simple
# dict.get(mode, mode) suffit : absence de clé -> mode de base renvoyé
# inchangé, comportement identique.
_BASE_MODE_TO_PKT_MODE = {base: pkt for pkt, base in _PKT_MODE_TO_BASE_MODE.items()}

# Valeurs ptt_t acceptées par "T" (set_ptt), vérifiées dans le serveur
# de référence Hamlib (tests/rigctl_parse.c, declare_proto_rig(set_ptt),
# switch(ptt) explicite) : RIG_PTT_OFF=0, RIG_PTT_ON=1,
# RIG_PTT_ON_MIC=2, RIG_PTT_ON_DATA=3 -- toute autre valeur entière
# (y compris négative) est rejetée par le serveur de référence
# lui-même ("RPRT -1"), jamais seulement par cette couche. Traduction
# vers le booléen accepté par cat_sharing_service.set_ptt() : aucune
# distinction micro/data n'existe dans le chemin de données de la
# Suite (voir docstring du module, dixième étape) -- les 3 valeurs
# "actives" (1, 2, 3) valent toutes True, seule 0 vaut False.
_VALID_PTT_VALUES = {0, 1, 2, 3}

# Réponse rigctld conforme pour \dump_state -- format vérifié dans le
# code source réel de netrigctl_open() (Hamlib/Hamlib,
# rigs/dummy/netrigctl.c), pas supposé. Protocole version 0
# délibérément choisi : c'est la forme la plus simple possible --
# RETURNFUNC(RIG_OK) est atteint côté client dès que la ligne 1 vaut
# "0", ce qui évite toute la section d'extension clé=valeur du
# protocole v1+ (jamais nécessaire pour la négociation de base).
#
# Champs, dans l'ordre exact lu par netrigctl_open() :
#   1. version de protocole (0)
#   2. ligne "modèle" -- lue mais son contenu n'est jamais utilisé par
#      le client, doit juste être non vide
#   3. région ITU
#   4. plage de fréquences RX -- ligne de fin (7 champs à zéro :
#      RIG_IS_FRNG_END exige startf==0 et endf==0, voir hamlib/rig.h)
#   5. plage de fréquences TX -- même format de fin
#   6. pas de syntonisation -- ligne de fin (2 champs à zéro :
#      RIG_IS_TS_END exige modes==0 et ts==0)
#   7. filtres -- ligne de fin (2 champs à zéro : RIG_IS_FLT_END
#      exige modes==0)
#   8-11. max_rit, max_xit, max_ifshift, announces
#   12-13. préamplis, atténuateurs -- une ligne non vide suffit, le
#      client ne valide pas le nombre de valeurs parsées ici
#   14-19. has_get_func / has_set_func / has_get_level / has_set_level /
#      has_get_parm / has_set_parm
_DUMP_STATE_REPLY = (
    b"0\n"
    b"0\n"
    b"0\n"
    b"0 0 0 0 0 0 0\n"
    b"0 0 0 0 0 0 0\n"
    b"0 0\n"
    b"0 0\n"
    b"0\n"
    b"0\n"
    b"0\n"
    b"0\n"
    b"0\n"
    b"0\n"
    b"0\n"
    b"0\n"
    b"0\n"
    b"0\n"
    b"0\n"
    b"0\n"
)


class RigctldAdapter(CatAdapter):
    """
    Voir docstring du module -- mode diagnostic : journalise chaque
    commande reçue. Seules exceptions, depuis les troisième/quatrième/
    sixième/septième/neuvième/dixième étapes : "f" (get_freq), "t"
    (get_ptt), "m" (get_mode), "F" (set_freq), "M" (set_mode) et "T"
    (set_ptt) interrogent réellement cat_sharing_service -- toute autre
    commande ne pilote jamais RadioService/CatSharingService. "v"
    (get_vfo, cinquième étape) reçoit une réponse statique ("VFOA"),
    sans jamais toucher cat_sharing_service non plus. "F", "M" et "T"
    sont les seules à écrire réellement (set_frequency_hz(),
    set_mode()/set_data_mode(), set_ptt()), toutes les autres ne font
    que lire. "M" traduit les modes "PKTxxx" en mode de base +
    activation DATA (voir _PKT_MODE_TO_BASE_MODE et docstring du
    module, neuvième étape) ; "m" applique la traduction inverse via
    get_data_mode(). "T" traduit les 4 valeurs ptt_t Hamlib (0/1/2/3)
    en booléen (voir _VALID_PTT_VALUES et docstring du module, dixième
    étape).
    """

    def __init__(self, cat_sharing_service, host=DEFAULT_HOST, port=DEFAULT_PORT, parent=None):
        super().__init__(parent)

        # Reçu par injection (contrat CatAdapter) -- partagé entre
        # toutes les connexions actives, interrogé uniquement pour "f"
        # (get_freq), "t" (get_ptt), "m" (get_mode), "F" (set_freq),
        # "M" (set_mode/set_data_mode) et "T" (set_ptt), voir docstring
        # du module.
        self._cat_sharing_service = cat_sharing_service

        self._host = host
        self._port = port

        self._server = QTcpServer(self)
        self._server.newConnection.connect(self._on_new_connection)

        # Plusieurs connexions simultanées acceptées (huitième étape,
        # voir docstring du module) : chaque QTcpSocket actif est
        # associé à son propre buffer de reconstruction de lignes,
        # jamais partagé entre connexions.
        self._connections = {}

    def _peer(self, socket) -> str:
        """Identifiant "ip:port" d'une connexion, pour journaliser sans ambiguïté quand plusieurs clients sont actifs."""

        return f"{socket.peerAddress().toString()}:{socket.peerPort()}"

    # ------------------------------------------------------------------
    # Contrat CatAdapter
    # ------------------------------------------------------------------

    def start(self) -> None:
        listening = self._server.listen(QHostAddress(self._host), self._port)

        if listening:
            _log.info(f"RigctldAdapter (diagnostic) : écoute sur {self._host}:{self.actual_port}")
        else:
            _log.warning(
                f"RigctldAdapter (diagnostic) : échec d'écoute sur {self._host}:{self._port}"
                f" -- {self._server.errorString()}"
            )

    def stop(self) -> None:
        for socket in list(self._connections):
            socket.disconnectFromHost()

        self._connections.clear()

        self._server.close()
        _log.info("RigctldAdapter (diagnostic) : arrêté")

    @property
    def actual_port(self) -> int:
        """Port réellement utilisé (utile en test, avec port=0 pour un port éphémère)."""

        return self._server.serverPort()

    # ------------------------------------------------------------------
    # Connexion
    # ------------------------------------------------------------------

    def _on_new_connection(self) -> None:
        socket = self._server.nextPendingConnection()

        if socket is None:
            return

        _log.info(f"RigctldAdapter (diagnostic) : client connecté ({self._peer(socket)})")

        self._connections[socket] = b""
        socket.readyRead.connect(lambda s=socket: self._on_ready_read(s))
        socket.disconnected.connect(lambda s=socket: self._on_client_disconnected(s))

    def _on_ready_read(self, socket) -> None:
        if socket not in self._connections:
            return

        self._connections[socket] += bytes(socket.readAll())

        while b"\n" in self._connections[socket]:
            line, self._connections[socket] = self._connections[socket].split(b"\n", 1)
            self._handle_line(socket, line)

    def _handle_line(self, socket, raw_line: bytes) -> None:
        decoded = raw_line.decode("utf-8", errors="replace").rstrip("\r")
        peer = self._peer(socket)
        _log.info(f"RigctldAdapter (diagnostic) RX [{peer}] : {decoded!r}")

        if decoded == "\\get_powerstat":
            reply = _POWERSTAT_ON_REPLY
        elif decoded == "\\dump_state":
            reply = _DUMP_STATE_REPLY
        elif decoded == "f":
            reply = f"{self._cat_sharing_service.get_frequency_hz()}\n".encode()
        elif decoded == "t":
            reply = b"1\n" if self._cat_sharing_service.get_ptt() else b"0\n"
        elif decoded == "v":
            reply = _VFO_REPLY
        elif decoded == "m":
            mode = self._cat_sharing_service.get_mode()
            if self._cat_sharing_service.get_data_mode():
                mode = _BASE_MODE_TO_PKT_MODE.get(mode, mode)
            reply = f"{mode}\n{_MODE_PASSBAND_NORMAL}\n".encode()
        elif decoded.startswith("F "):
            try:
                frequency_hz = float(decoded.removeprefix("F "))
            except ValueError:
                reply = _RPRT_INVALID_PARAM
            else:
                if frequency_hz < 0:
                    reply = _RPRT_INVALID_PARAM
                elif self._cat_sharing_service.set_frequency_hz(round(frequency_hz)):
                    reply = _RPRT_SUCCESS
                else:
                    reply = _RPRT_IO_ERROR
        elif decoded.startswith("M "):
            parts = decoded.split()
            if len(parts) != 3:
                reply = _RPRT_INVALID_PARAM
            else:
                _, mode_token, width_token = parts
                try:
                    int(width_token)
                except ValueError:
                    reply = _RPRT_INVALID_PARAM
                else:
                    if mode_token in _PKT_MODE_TO_BASE_MODE:
                        base_mode = _PKT_MODE_TO_BASE_MODE[mode_token]
                        data_enabled = True
                    else:
                        base_mode = mode_token
                        data_enabled = False

                    if not self._cat_sharing_service.set_mode(base_mode):
                        reply = _RPRT_IO_ERROR
                    elif not self._cat_sharing_service.set_data_mode(data_enabled):
                        reply = _RPRT_IO_ERROR
                    else:
                        reply = _RPRT_SUCCESS
        elif decoded.startswith("T "):
            parts = decoded.split()
            if len(parts) != 2:
                reply = _RPRT_INVALID_PARAM
            else:
                try:
                    ptt_value = int(parts[1])
                except ValueError:
                    reply = _RPRT_INVALID_PARAM
                else:
                    if ptt_value not in _VALID_PTT_VALUES:
                        reply = _RPRT_INVALID_PARAM
                    elif self._cat_sharing_service.set_ptt(ptt_value != 0):
                        reply = _RPRT_SUCCESS
                    else:
                        reply = _RPRT_IO_ERROR
        else:
            reply = _DIAGNOSTIC_REPLY

        if socket in self._connections:
            socket.write(reply)
            _log.info(f"RigctldAdapter (diagnostic) TX [{peer}] : {reply!r}")

    def _on_client_disconnected(self, socket) -> None:
        _log.info(f"RigctldAdapter (diagnostic) : client déconnecté ({self._peer(socket)})")
        self._connections.pop(socket, None)
