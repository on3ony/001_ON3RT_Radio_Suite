# Architecture du chantier CW (Morse) — ON3RT Radio Suite

**Statut : figée, validée par l'utilisateur le 2026-07-31. Aucune implémentation
ne doit s'en écarter sans repasser par une nouvelle validation explicite.**

Ce document décrit la conception retenue **après** les essais matériels réels
sur IC-7300 qui ont invalidé l'hypothèse de départ (voir « Historique » en fin
de document). Il fige l'architecture avant toute nouvelle ligne de code.

## 1. Principe fondateur

`CWService` ne doit jamais connaître :

- le matériel utilisé ;
- le backend utilisé ;
- le protocole utilisé (CI-V, ligne KEY, Winkeyer...) ;
- la manière dont le CW est réellement produit (élément par élément, ou texte
  confié à un keyer externe).

Cette ignorance n'est pas un vœu pieux : elle se traduit concrètement par le
fait que `CWService` ne construit et ne possède **ni** `MorseEncoder` **ni**
`TimingEngine` — ces deux briques deviennent la responsabilité exclusive du
driver qui en a besoin (`ElementDriver`).

## 2. Schéma des responsabilités

```
                core/application.py
                (SEUL endroit qui choisit)
                        |
                        v
                   CWService
                        |
                        v
                    CWDriver            <- contrat, duck-typé
                    /        \
            ElementDriver   TextDriver
                |                 |
                v                 v
           KeyerBackend      TextBackend    <- contrats, duck-typés
                |                 |
                v                 v
        PTTKeyerBackend   CIVTextKeyerBackend
        (apps/cat_server/) (apps/cat_server/, futur)
```

`core/application.py` est le **seul** endroit de toute la Suite qui sait
« quel matériel/backend est actif aujourd'hui » — exactement le même principe
de composition déjà appliqué à `RadioService`, `PTTGuard`, `AudioOutputService`.
Il lit `SettingsService.cw["keyer_backend"]`, construit le backend concret
adapté, l'enveloppe dans le driver correspondant, puis injecte ce driver (et
lui seul) dans `CWService`.

## 3. Responsabilités détaillées

### `CWService` (`libraries/cw/cw_service.py`)

Seule couche publique de tout le module. Ne change pas de rôle par rapport à
aujourd'hui, mais perd toute connaissance de `MorseEncoder`/`TimingEngine`.

- API publique : `send(text, owner=None) -> request_id | None`, `stop()`,
  `state`.
- Gestion d'état : `CWState` (IDLE/SENDING/STOPPED/ERROR).
- Gestion des `request_id` (génération, suivi de la demande active).
- Signaux Qt : `cw_started`, `cw_progress`, `cw_finished`, `cw_stopped`,
  `cw_error` — toujours émis de façon différée (`QTimer.singleShot(0, ...)`),
  convention Suite déjà en place.
- Refus de concurrence : une seule émission active à la fois, jamais mise en
  file d'attente.
- `stop()` : garantit un relâchement immédiat via le driver, quelle que soit
  la famille.
- Journalisation (`CWLogger`).
- Transformation d'une exception levée par le driver en signal `cw_error` —
  **c'est tout ce que `CWService` fait de la gestion d'erreur** : il ne sait
  jamais *pourquoi* le driver a échoué, seulement *qu'*il a échoué.

`CWService` détient : `self._driver` (le `CWDriver` injecté), `self.wpm`,
`self.farnsworth_wpm` (état de politique, modifiables à chaud — comme
aujourd'hui dans `validate_cw_keying.py`), transmis au driver à chaque appel.

### Contrat `CWDriver` (nouveau, `libraries/cw/`)

Duck-typé, comme tous les contrats de la Suite (pas d'ABC). Deux méthodes
suffisent à `CWService` :

```
driver.start(text, wpm, farnsworth_wpm, request_id, owner=None) -> None
    # Démarre l'émission. Peut lever une exception (n'importe laquelle) en
    # cas d'échec immédiat -- CWService la transforme en cw_error.
    # Émet ses propres signaux de progression/fin via des callbacks ou des
    # signaux Qt exposés par le driver, que CWService relaie tel quel
    # (mécanisme exact à trancher à l'écriture du code, pas ici).

driver.stop() -> None
    # Doit garantir un relâchement immédiat du matériel, jamais lever.
```

### `ElementDriver` (`libraries/cw/`)

Extraction pure de la logique actuelle de `CWService` — comportement,
timing et tests strictement identiques, seul l'emplacement change.

- Construit et possède `MorseEncoder` + `TimingEngine`.
- Pilotage élément par élément via une chaîne `QTimer.singleShot()` (inchangé).
- Appelle `backend.key_down(owner=None)` / `backend.key_up()` à chaque
  transition — contrat `KeyerBackend` **inchangé**.
- Émet la progression réelle, caractère par caractère (confirmée par le
  logiciel lui-même, puisque c'est lui qui pilote chaque élément).

### `TextDriver` (`libraries/cw/`, nouveau)

- Découpage éventuel du texte selon la limite propre au backend
  (`backend.max_chunk_chars` ou équivalent — jamais une constante codée en
  dur dans `TextDriver` ni dans `CWService` ; c'est une propriété du backend
  concret, ex. 30 caractères pour l'IC-7300).
- Réutilise `MorseEncoder` + `TimingEngine`, mais uniquement pour **estimer**
  une durée totale — jamais pour piloter un vrai keying, puisque c'est le
  matériel qui génère le timing réel.
- Pilotage du backend texte via `backend.send_text(chunk, wpm,
  farnsworth_wpm, owner=None)` / `backend.stop_sending()`.
- Progression et fin d'émission **simulées** à partir de l'estimation, pas
  confirmées par le matériel (CI-V ne renvoie aucun événement « message
  terminé ») — à documenter explicitement dans le code et, plus tard, dans
  l'UI, pour ne jamais laisser croire à une confirmation matérielle qui
  n'existe pas.

### Contrat `KeyerBackend` (`libraries/cw/keyer_backend.py`, inchangé)

```
name, is_available(), key_down(owner=None), key_up()
```

Couvre `NullKeyerBackend` (test double, inchangé) et `PTTKeyerBackend`
(`apps/cat_server/`, inchangé) — toujours valide pour tout matériel qui
accepte un pilotage bas niveau par élément (ligne KEY dédiée, GPIO, ou un
PTT qui gaterait réellement le CW sur une radio qui le permettrait).

### Contrat `TextBackend` (nouveau, `libraries/cw/`)

```
name, is_available(), max_chunk_chars, send_text(text, wpm, farnsworth_wpm, owner=None), stop_sending()
```

Couvre le futur `CIVTextKeyerBackend` (`apps/cat_server/`, IC-7300 CI-V
`0x17`), et plus tard un Winkeyer en mode host, ou un backend Hamlib. Un
`NullTextKeyerBackend` (test double, zéro dépendance matérielle) accompagnera
`NullKeyerBackend`.

## 4. Ce qui est préservé intégralement

| Élément | Sort |
|---|---|
| `MorseEncoder` | Inchangé — déplacé dans `ElementDriver`, réutilisé aussi (estimation) par `TextDriver` |
| `TimingEngine` | Inchangé — même sort |
| API publique de `CWService` | Inchangée |
| Contrat `KeyerBackend` | Inchangé |
| `NullKeyerBackend`, `PTTKeyerBackend` | Inchangés |
| `tests/test_morse_encoder.py`, `test_timing.py`, `test_keyer_backend.py`, `test_cw_ptt_backend.py` | Attendus verts sans modification |
| `tests/test_cw_service.py` | Attendu vert, mais nécessitera d'injecter un `ElementDriver(NullKeyerBackend())` au lieu d'un `NullKeyerBackend()` nu — seul changement mécanique, comportement testé identique |

## 5. Ce qui est nouveau (pas encore écrit)

- `libraries/cw/` : contrat `CWDriver`, `ElementDriver`, `TextDriver`,
  contrat `TextBackend`, `NullTextKeyerBackend`.
- `apps/cat_server/cw_civ_text_backend.py` : `CIVTextKeyerBackend`.
- Extension additive de la pile CAT existante (même schéma que
  `set_ptt()`/`set_mode()`) : un builder de trame CI-V `0x17`
  (`libraries/cat/cw_message.py`), exposé via `cat_engine.py` →
  `cat_controller.py` → `RadioService` comme `send_cw_message(text)` /
  `stop_cw_message()`, plus `set_keying_speed(wpm)` pour la commande de
  niveau `14 0C` (vitesse du keyer interne).
- `core/application.py` : lecture de `SettingsService.cw["keyer_backend"]`,
  construction du backend concret + du driver correspondant, injection dans
  `CWService`.

## 6. Points ouverts, assumés, non résolus ici

- Le Farnsworth n'a peut-être pas de sens pour un `TextBackend` (le keyer
  interne de l'IC-7300 ne gère peut-être qu'une seule vitesse globale). Un
  futur indicateur `backend.supports_farnsworth` (booléen duck-typé) serait
  l'endroit naturel pour l'exposer — pas construit aujourd'hui.
- `validate_cw_keying.py` devra être étendu (pas réécrit) pour couvrir un
  scénario `TextDriver` — la mesure de durée ne pourra plus s'appuyer sur les
  compteurs `key_down_calls`/`key_up_calls` d'un `KeyerBackend`, puisqu'un
  `TextBackend` n'en a pas.

## 7. Historique — pourquoi cette révision a eu lieu

Architecture initiale (chantier CW, étapes 1-8) : `CWService` pilotait
directement `MorseEncoder`/`TimingEngine`/`KeyerBackend.key_down()`/`key_up()`
en supposant qu'un simple gate PTT (CI-V `0x1C 0x00`) suffirait à produire du
CW réel sur l'IC-7300. Essais matériels réels (d'abord en mode USB par
erreur, puis en mode CW confirmé) : TX actif, mode CW confirmé, **aucun
sidetone, aucune puissance RF** — le PTT seul ne déclenche jamais le keyer
interne de l'IC-7300. Recherche approfondie (documentation CI-V officielle,
Hamlib, CQRLOG) : la commande CI-V `0x17` (« Sends CW messages », jusqu'à 30
caractères ASCII) existe et pilote réellement le keyer interne, sans aucune
interface matérielle dédiée — contredisant une recherche antérieure
insuffisante qui affirmait l'inverse. Cette découverte a rendu nécessaire le
support de plusieurs familles de backends, d'où la présente architecture.
