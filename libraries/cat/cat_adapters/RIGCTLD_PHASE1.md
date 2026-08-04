# Chantier CAT Sharing / rigctld — Phase 1 « Sous-ensemble lecture »

**Statut : implémentation et tests unitaires terminés (2026-08-04). Validation
réelle avec WSJT-X : capture initiale du 4 août validée pour `\get_powerstat`/
`\dump_state` ; nouvelle capture pour `f`/`t`/`v`/`m` préparée (grille de
validation dédiée) mais son compte rendu n'est pas encore consigné dans ce
document — section 7 à compléter après la session.**

Ce document trace la Phase 1 du chantier CAT Sharing (`libraries/cat/
cat_sharing_service.py`, `libraries/cat/cat_adapters/`). Il ne remplace pas
les docstrings des fichiers concernés (qui restent la référence pour le détail
ligne à ligne de chaque étape) — il sert de vue d'ensemble et de point de
passage avant la Phase 2.

## 1. Objectifs initiaux

Permettre à WSJT-X (et, plus généralement, à tout logiciel tiers parlant le
protocole Hamlib `rigctld`) de piloter la même radio que ON3RT Radio Suite
**sans** conflit d'accès au port série physique.

Déclencheur : bug réel — Windows n'autorise qu'un seul propriétaire par port
COM, et `RadioService` (`apps/cat_server/radio_service.py`) ouvre déjà ce
port en direct (`serial_transport.py`, `serial.Serial()`). WSJT-X ne peut donc
pas se connecter en série sur le même port que la Suite.

Contrainte fixée dès le départ, jamais remise en cause depuis : `RadioService`
reste l'unique propriétaire du port physique, **sans aucune modification**.
Deux alternatives ont été explicitement écartées avant de choisir l'approche
retenue :
- un splitter VSPE (dépendance à un driver noyau externe, nouveau point de
  défaillance unique entre la radio et la Suite elle-même) ;
- un hub OmniRig (aurait obligé `RadioService` à devenir client COM/OLE au
  lieu de propriétaire direct du port — la « modification profonde de
  l'architecture » explicitement écartée).

## 2. Commandes implémentées

| Commande | Type | Comportement |
|---|---|---|
| `\get_powerstat` | statique | `1\n` (RIG_POWER_ON codé en dur) |
| `\dump_state` | statique | dump complet, protocole version 0 |
| `f` (get_freq) | dynamique | `CatSharingService.get_frequency_hz()`, relayé tel quel (Hz, entier) |
| `t` (get_ptt) | dynamique | `CatSharingService.get_ptt()`, converti en `1`/`0` |
| `v` (get_vfo) | statique | `VFOA\n` (aucune notion de VFO dans la Suite) |
| `m` (get_mode) | dynamique + statique | ligne 1 : `CatSharingService.get_mode()`, relayé tel quel (y compris `"---"`) ; ligne 2 : `0` (RIG_PASSBAND_NORMAL) |

Toute autre commande reçoit encore la réponse générique de diagnostic
(`_DIAGNOSTIC_REPLY = b"0\n"`), sans aucune interprétation.

## 3. Sources Hamlib utilisées pour valider le protocole

Chaque format de réponse a été vérifié contre le code source réel du dépôt
`Hamlib/Hamlib` (jamais supposé), en miroir du rôle client que joue WSJT-X :

- `rigs/dummy/netrigctl.c` :
  - `netrigctl_open()` — format exact de `\dump_state` (19 lignes, protocole
    version 0, macros de fin de liste `RIG_IS_FRNG_END`/`RIG_IS_TS_END`/
    `RIG_IS_FLT_END`).
  - `netrigctl_get_mode()` — a révélé que `m` doit renvoyer **deux lignes**
    (mode, puis largeur de bande via un second `read_string()`
    inconditionnel) ; explique très probablement l'écart de ~10 s observé
    dans la capture réelle du 4 août avant cette correction.
  - `netrigctl_get_split_vfo()` — confirme que `s` (non encore implémentée)
    suit le même schéma à deux lignes que `m`, ce qui permet d'anticiper un
    écart de délai similaire et encore présent sur cette commande.
- `src/misc.c` : `rig_parse_mode()` — confirme qu'un jeton de mode non
  reconnu (ex. `"---"`) ne provoque ni crash ni déconnexion côté client,
  seulement un `RIG_MODE_NONE` et un debug niveau WARN — a validé la
  décision de relayer `"---"` tel quel sans traduction.
- `include/hamlib/rig.h` : définitions `RIG_PASSBAND_NORMAL` (`s_Hz(0)`,
  « bandpass to be set to normal ») et `RIG_PASSBAND_NOCHANGE` (`s_Hz(-1)`)
  — confirme que `0` n'est pas un simple repli arbitraire mais la valeur
  canonique Hamlib pour « largeur par défaut », et les macros de fin de
  liste citées plus haut.

## 4. Choix d'architecture retenus

- Couche générique `CatSharingService` (`libraries/cat/cat_sharing_service.py`)
  entre `RadioService` et les adaptateurs : façade **volontairement réduite**
  (fréquence, mode, PTT, état de connexion) — n'expose **jamais** CW,
  S-mètre ni VFO, par décision explicite, pas par oubli.
- Contrat `CatAdapter` (`libraries/cat/cat_adapters/base.py`) : `start()`/
  `stop()`, même forme que `MapLayer`/`LiveDataSource` déjà éprouvés ailleurs
  dans la Suite. `RigctldAdapter` est le premier et seul adaptateur concret à
  ce jour.
- `CatSharingService` ne modifie ni ne remplace `RadioService` — délégation
  pure vers son API déjà publique, jamais de second propriétaire de port
  (vérifié par test : `CatSharingService` n'appelle jamais
  `connect()`/`disconnect()`).
- Méthode de travail systématique tout au long de la Phase 1 : capturer le
  trafic réel avant d'écrire la moindre réponse protocolaire, une commande à
  la fois, jamais sur la base d'une supposition — chaque étape (`\get_powerstat`,
  `\dump_state`, `f`, `t`, `v`, `m`) a été validée indépendamment, avec ses
  propres tests, avant de passer à la suivante.
- Distinction explicite « réponse dynamique vs statique » par commande,
  décidée au cas par cas selon ce que `CatSharingService` expose réellement
  (ex. `v` reste statique parce qu'aucune donnée VFO n'existe nulle part dans
  le chemin de données réel de la Suite — pas un choix de simplicité, une
  contrainte de l'architecture existante).

## 5. Risques écartés

- Double propriétaire du port série : structurellement impossible par
  construction (`CatSharingService` ne fait que déléguer, jamais connecter).
- Réintroduction du Virtual Bridge / VSPE : écartée dès l'audit initial,
  confirmée code mort et non réintégrée à aucune étape.
- Désynchronisation protocolaire sur `m` (réponse à une seule ligne
  bloquant le client Hamlib) : résolue par la vérification aux sources
  Hamlib avant implémentation, plutôt que découverte après coup.
- Passband inventé arbitrairement : écarté, `0` correspond à la constante
  Hamlib officielle `RIG_PASSBAND_NORMAL`, vérifiée aux sources.
- Traduction risquée du mode `"---"` (radio non connectée) vers un mode
  Hamlib arbitraire : écartée après vérification que `rig_parse_mode()`
  gère un jeton inconnu sans casser la connexion — la valeur réelle est
  relayée telle quelle, jamais inventée.
- Crash de `validate_rigctld_adapter.py` sur `cat_sharing_service=None` dès
  que `f`/`t`/`m` interrogeraient réellement le service : anticipé par audit
  dédié avant implémentation, résolu par un faux `CatSharingService` à
  valeurs fixes, strictement cantonné à ce script de validation.

## 6. Tests unitaires réalisés

- `tests/test_cat_sharing_service.py` — 12 tests, inchangés depuis le
  commit `54e4d16` (facade, registre d'adaptateurs, jamais de second
  propriétaire de port).
- `tests/test_rigctld_adapter.py` — 24 tests, construits étape par étape :
  écoute réseau, journalisation RX dans l'ordre réel, découpage multi-lignes
  sur un même paquet TCP, `\get_powerstat`/`\dump_state` (formats figés),
  `f`/`t`/`m` (valeurs réelles via un double contrôlé, cas de valeur par
  défaut/radio non connectée), `v` (réponse statique, garde explicite
  qu'elle ne touche jamais `cat_sharing_service`), non-régression sur les
  commandes encore génériques, déconnexion client.
- Suite complète (36 tests) exécutée et passante après chaque étape, sans
  aucune régression relevée à ce jour.

## 7. Validations réelles réalisées avec WSJT-X

- **Capture du 2026-08-04 (avant Phase 1)** : session réelle WSJT-X ↔
  `RigctldAdapter` en mode diagnostic. A permis de découvrir et corriger
  `\get_powerstat` (négociation bloquée sinon) puis `\dump_state` (format
  vérifié aux sources) avant même le début de cette phase. Session stable
  ~58 s, séquence complète capturée et documentée.
- **Capture post-implémentation `f`/`t`/`v`/`m`** : procédure et grille de
  validation préparées (phases connexion / commandes / dynamique / durée),
  double `_ValidationCatSharingService` mis en place pour permettre à la
  capture d'aboutir sans crash. *Compte rendu à consigner ici une fois la
  session réalisée — ne pas considérer la Phase 1 comme validée en conditions
  réelles tant que cette section n'est pas complétée.*

## 8. Limites connues

- `\get_powerstat` reste codé en dur à `1` (RIG_POWER_ON), indépendamment de
  l'état réel de connexion de `RadioService` — pas encore relié à
  `CatSharingService.is_connected`.
- `v` (VFO) et `s` (split) : aucune notion de VFO/split n'existe dans le
  chemin de données réel de la Suite — `v` répond statiquement, `s` n'est pas
  encore implémentée.
- `m` ne transmet que le nom du mode ; la largeur de bande est toujours
  `0` (RIG_PASSBAND_NORMAL), jamais une valeur réelle — aucune source de
  largeur de bande n'existe dans le dépôt à ce jour.
- Un seul client TCP accepté à la fois — pas de partage simultané entre
  WSJT-X et un second logiciel (ex. Log4OM) sans fermeture préalable de la
  première connexion.
- `RigctldAdapter`/`CatSharingService` ne sont **pas encore câblés** dans
  `core/application.py` : aucune instance ne tourne en usage réel de la
  Suite, uniquement via le script `validate_rigctld_adapter.py`.
- Aucune section de configuration (`SettingsService`) ni d'interface
  utilisateur pour activer/configurer ce partage CAT.
- `T` (set_ptt, écriture PTT) n'est pas implémentée ; le risque déjà identifié
  (`CatSharingService.set_ptt()` contourne `PTTGuard`) n'est pas résolu, il
  est délibérément reporté à une décision d'architecture dédiée.

## 9. Commandes restant à développer

- Commandes secondaires statiques : `\chk_vfo`, `V` (set_vfo), `s` (get_split_vfo),
  `q` (quit) — même discipline que `v` (réponses fixes, aucun accès à
  `CatSharingService`), format de `s` déjà anticipé (deux lignes, voir §3).
- `\get_powerstat` dynamique — le faire dépendre de
  `CatSharingService.is_connected`.
- `T` (set_ptt) — seule commande d'écriture de tout ce sous-ensemble,
  volontairement isolée : nécessite une décision préalable sur le passage ou
  non par `PTTGuard` avant toute ligne de code.
- Câblage en production dans `core/application.py` (construction de
  `CatSharingService`, `add_adapter(RigctldAdapter(...))`) et extension de
  `core/main_window.py.closeEvent()` pour appeler `cat_sharing_service.stop_all()`.
- Section `SettingsService` dédiée (activation/port), sur le modèle déjà
  suivi pour `live`/`cw_decode`.

## 10. Recommandations pour la Phase 2

1. Terminer le sous-ensemble « commandes secondaires » (`\chk_vfo`, `V`, `s`,
   `q`) en une seule étape groupée, cohérente avec la Phase 1 (toutes
   statiques, aucun accès à `CatSharingService`) — risque faible, complète le
   protocole de négociation/lecture.
2. Rendre `\get_powerstat` dynamique — petite étape isolée, faible risque.
3. Ouvrir une discussion d'architecture dédiée sur `T`/`PTTGuard` **avant**
   toute implémentation — ce n'est pas un choix technique mineur, il engage
   la sécurité d'émission et l'arbitrage entre modules concurrents de la
   Suite.
4. Ne câbler `CatSharingService`/`RigctldAdapter` dans `core/application.py`
   qu'une fois le sous-ensemble lecture **et** `T` validés en conditions
   réelles — éviter d'exposer un service partiellement fonctionnel en usage
   normal de la Suite.
5. Conserver la méthode de travail qui a fait ses preuves sur toute la
   Phase 1 : capture réelle avant implémentation, une commande à la fois,
   vérification aux sources Hamlib plutôt que par supposition, tests unitaires
   systématiques avant toute validation matérielle.
