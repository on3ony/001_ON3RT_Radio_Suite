# ON3RT Radio Suite

**Suite logicielle radioamateur tout-en-un**, développée par ON3RT — pilotage radio (CAT), journal de trafic, concours, DX Cluster, banque de fréquences, scanner et supervision temps réel de la station, réunis dans une seule application cohérente.

> Projet personnel en développement actif, construit de manière strictement incrémentale : chaque évolution est conçue, testée et validée avant la suivante. Voir [Philosophie du projet](#philosophie-du-projet).

---

## Sommaire

- [Présentation](#présentation)
- [Objectifs du projet](#objectifs-du-projet)
- [Fonctionnalités principales](#fonctionnalités-principales)
- [Architecture générale](#architecture-générale)
- [Captures d'écran](#captures-décran)
- [Prérequis](#prérequis)
- [Installation](#installation)
- [Lancement](#lancement)
- [Structure du projet](#structure-du-projet)
- [Modules disponibles](#modules-disponibles)
- [Modules prévus](#modules-prévus)
- [État actuel du développement](#état-actuel-du-développement)
- [Philosophie du projet](#philosophie-du-projet)

---

## Présentation

**ON3RT Radio Suite** est une application de bureau (Windows, Python/PySide6) destinée à remplacer la multitude d'outils séparés qu'un radioamateur utilise habituellement — logiciel CAT, logbook, calepin de contest, moniteur de DX Cluster, plan de fréquences, scanner — par une seule suite intégrée, avec un pilotage radio (CAT) partagé et cohérent entre tous ses modules.

Le projet est né du constat qu'un radioamateur actif jongle en permanence entre plusieurs logiciels indépendants, chacun avec sa propre connexion CAT, sa propre base de données, sa propre interface — sources fréquentes de conflits (deux logiciels qui tentent d'ouvrir le même port série), de données dupliquées et d'incohérences. ON3RT Radio Suite répond à ce problème par une architecture à **services partagés** : un seul point d'accès à la radio, une seule source de vérité pour les fréquences, un seul flux de données DX Cluster — consommés par autant de modules que nécessaire, sans jamais se marcher dessus.

## Objectifs du projet

- **Unifier** les outils du quotidien radioamateur dans une seule application cohérente et sobre.
- **Éliminer les connexions CAT concurrentes** grâce à un service radio unique, partagé par tous les modules.
- **Garantir l'honnêteté des données affichées** : aucune valeur n'est jamais inventée, extrapolée ou calculée arbitrairement — quand une information n'est pas disponible, l'interface l'indique clairement plutôt que d'afficher une donnée fictive.
- **Construire une base durable et extensible**, module après module, sans dette technique cachée.
- **Rester utilisable dès aujourd'hui**, y compris avec un développement encore en cours sur certains modules.

## Fonctionnalités principales

Fonctionnalités réellement opérationnelles à ce jour, pilotant une radio IC-7300 réelle en CAT (CI-V) :

- **Pilotage CAT temps réel** (fréquence, mode, PTT) partagé par l'ensemble de la suite.
- **Contest** : journal de concours, calcul d'échange, export Cabrillo, import/export ADIF.
- **Logbook** : journal général des contacts, lookup QRZ.com, horodatage UTC automatique.
- **Banque de fréquences** : catégories hiérarchiques personnalisables, profils, favoris, recherche, envoi direct d'une fréquence à la radio.
- **DX Cluster** : flux de spots en direct (DXFun), envoi de la fréquence d'un spot à la radio en un double-clic.
- **Scanner** : balayage réel de plage de fréquences avec pilotage effectif de la radio (aucune simulation), mémoires alimentées par la Banque de fréquences.
- **Dashboard temps réel** : état radio/CAT, derniers QSO, activité par bande, météo de la station, indices solaires/géomagnétiques et conditions de propagation HF par bande (données HamQSL), spots DX Cluster récents.

## Architecture générale

La suite repose sur un principe simple, appliqué systématiquement à chaque module :

> **Un service fournit les données. Une fenêtre ou un panneau les affiche. Aucune logique métier dans l'interface.**

### Services partagés

Chaque service est instancié **une seule fois** au démarrage (`core/application.py`) et **injecté** dans les modules qui en ont besoin — aucun module ne crée sa propre connexion :

| Service | Rôle |
|---|---|
| `RadioService` | Point d'entrée CAT unique vers la radio (fréquence, mode, PTT). |
| `FrequencyService` | Source unique des fréquences de référence (Banque de fréquences, mémoires du Scanner). |
| `DXClusterService` | Connexion Telnet unique vers le cluster DX, spots en temps réel. |
| `WeatherService` | Météo de la station (Open-Meteo), selon la position déclarée. |
| `PropagationService` | Indices solaires/géomagnétiques et conditions de bande HF (HamQSL). |
| `StationService` | Source de vérité pour l'identité de la station (indicatif, locator, position). |

### Modules

Chaque module applicatif hérite d'une fenêtre de base commune (`BaseWindow`) et reçoit ses services par injection de dépendances depuis `core/main_window.py`, garantissant une seule instance de chaque service pour toute la suite.

```
launcher.py
  └── core/application.py        (instancie les services partagés)
        └── core/main_window.py  (fenêtre principale, ouvre les modules)
              ├── Dashboard (panneaux temps réel)
              ├── Contest
              ├── Radio Control
              ├── Logbook
              ├── Banque de fréquences
              ├── DX Cluster
              └── Scanner
```

## Captures d'écran

*Emplacements réservés — captures à ajouter dans `docs/screenshots/`.*

| Dashboard | Banque de fréquences |
|---|---|
| `docs/screenshots/dashboard.png` | `docs/screenshots/frequency_bank.png` |

| DX Cluster | Scanner |
|---|---|
| `docs/screenshots/dxcluster.png` | `docs/screenshots/scanner.png` |

## Prérequis

- **Windows** (testé sur Windows 11) — la suite dépend de ports COM pour le CAT.
- **Python 3.10 ou supérieur** (développé et testé sous Python 3.13).
- Une radio compatible CAT/CI-V (développé et validé sur **Icom IC-7300**) — la suite reste utilisable sans radio connectée, avec un affichage honnête de l'état "déconnecté".
- Dépendances Python tierces :
  - [`PySide6`](https://pypi.org/project/PySide6/) — interface graphique (Qt).
  - [`requests`](https://pypi.org/project/requests/) — client QRZ.com.
  - [`pyserial`](https://pypi.org/project/pyserial/) — communication série CAT.

## Installation

```bash
git clone https://github.com/on3ony/ON3RT_Radio_Suite.git
cd ON3RT_Radio_Suite

python -m venv .venv
.venv\Scripts\activate

pip install PySide6 requests pyserial
```

*Un fichier `requirements.txt` figera prochainement ces versions.*

## Lancement

```bash
python launcher.py
```

Ou, sous Windows, double-cliquer sur `ON3RT_Radio_Suite.bat`.

Au premier lancement, la station (indicatif, position) n'est pas configurée : le Dashboard et les services associés (météo, propagation) fonctionnent, mais affichent honnêtement leur état "non configuré" tant que ces informations ne sont pas renseignées.

## Structure du projet

```
ON3RT_Radio_Suite/
├── launcher.py                  # Point d'entrée unique
├── core/                        # Application, fenêtre principale, gestion des modules
│   ├── application.py           # Instanciation des services partagés
│   ├── main_window.py           # Fenêtre principale, ouverture des modules
│   └── module_manager.py
├── apps/                        # Modules applicatifs (un dossier par module)
│   ├── contest/
│   ├── radio_control/
│   ├── logbook/
│   ├── cat_server/
│   ├── frequency_bank/
│   ├── dxcluster/
│   ├── scanner/
│   └── dashboard/                # Page d'accueil temps réel (panneaux)
├── libraries/                   # Bibliothèques partagées (CAT, radio, services globaux, UI)
│   ├── cat/                      # Protocole CI-V, contrôleur CAT
│   ├── radio/                    # BandManager, ModeManager, gestion des bandes
│   ├── dxcluster/                # DXClusterService
│   ├── weather/                  # WeatherService
│   ├── propagation/              # PropagationService
│   ├── station/                  # StationService
│   └── ui/                       # Fenêtre de base, thème, composants communs
├── data/                        # Données locales (bases SQLite, jeux de données de référence)
├── config/                      # Configuration locale (station, préférences)
├── assets/                      # Thème, logos, ressources graphiques
└── docs/                        # Documentation, captures d'écran
```

## Modules disponibles

### Modules applicatifs (fenêtres dédiées)

| Module | État | Description |
|---|:---:|---|
| Contest | ✅ Terminé | Journal de concours, calcul d'échange, export Cabrillo, import/export ADIF. |
| Radio Control | ✅ Terminé | Pilotage CAT direct : fréquence, mode, ports COM. |
| Logbook | ✅ Terminé | Journal général des QSO, lookup QRZ.com. |
| CAT Server | ✅ Terminé | Service CAT en arrière-plan, fenêtre de supervision. |
| Banque de fréquences | ✅ Terminé | Catégories, profils, favoris, envoi direct à la radio. |
| DX Cluster | ✅ Terminé | Spots en direct, envoi de fréquence en un double-clic. |
| Scanner | ✅ Terminé | Balayage réel de fréquences, mémoires via la Banque de fréquences. |
| Propagation (fenêtre dédiée) | ⬜ Prévu | Les données sont déjà disponibles et affichées sur le Dashboard (voir ci-dessous) ; une fenêtre dédiée n'est pas encore planifiée. |
| WSJT-X Bridge | ⬜ Prévu | Pont UDP vers WSJT-X, décodage et journalisation automatique. |
| QSL Manager | ⬜ Prévu | Suivi des cartes QSL, envoi et bureau QSL. |
| Settings | ⬜ Prévu | Préférences générales, configuration de la station. |
| BandMap | ⬜ Prévu | Visualisation graphique de l'activité par bande. |

### Dashboard (panneaux temps réel)

| Panneau | État | Description |
|---|:---:|---|
| Radio / CAT | ✅ Terminé | État CAT en direct (fréquence, mode, connexion). |
| Logbook | ✅ Terminé | Derniers QSO enregistrés. |
| Activité par bande | ✅ Terminé | Répartition de l'activité par bande. |
| DX Cluster | ✅ Terminé | Spots récents en direct. |
| Météo | ✅ Terminé | Conditions météo de la station (Open-Meteo). |
| Propagation | ✅ Terminé | Indices solaires/géomagnétiques + conditions HF par bande (HamQSL), affichage compact par pastilles colorées. |
| Carte | ⬜ Prévu | Emplacement réservé sur le Dashboard. |
| WSJT-X | ⬜ Prévu | Emplacement réservé sur le Dashboard. |
| Messages | ⬜ Prévu | Emplacement réservé sur le Dashboard. |

## Modules prévus

Par ordre indicatif (non figé — le développement suit les priorités du moment, sans se concentrer trop longtemps sur un seul axe) :

- **Fenêtre Propagation dédiée** (historique, éventuelle visualisation graphique).
- **WSJT-X Bridge** — intégration FT8/FT4 en temps réel.
- **QSL Manager** — dépend du Logbook déjà en place.
- **Settings** — configuration centralisée de la station (indicatif, position, préférences), actuellement absente de l'interface.
- **BandMap** — visualisation graphique de l'activité radio.

## État actuel du développement

Le socle de l'application est stable : point d'entrée unique, architecture à services partagés, sept modules applicatifs pleinement opérationnels et un Dashboard temps réel couvrant six panneaux sur neuf emplacements prévus. Le développement se poursuit module par module, avec un contrôle de non-régression systématique sur l'ensemble de la suite à chaque intégration touchant le cœur de l'application (`core/application.py`, `core/main_window.py`), validé sur matériel réel (Icom IC-7300).

Le projet n'est pas figé : de nouveaux modules et évolutions sont ajoutés régulièrement, en gardant toujours la stabilité de l'existant comme priorité absolue.

## Philosophie du projet

ON3RT Radio Suite est développée selon une méthode volontairement stricte et incrémentale :

- **Une évolution à la fois.** Chaque fonctionnalité est conçue, développée puis validée avant d'entamer la suivante — jamais plusieurs chantiers ouverts en parallèle.
- **Fichiers complets, jamais de correctifs partiels.** Chaque modification est livrée comme un fichier entier et immédiatement lisible.
- **Tests avant validation.** Aucune évolution n'est considérée acquise sans test réel, souvent réalisé sur matériel radio effectif plutôt qu'en simulation.
- **Aucune donnée inventée.** Quand une information est indisponible (radio déconnectée, service non configuré, donnée absente d'un flux externe), l'interface l'indique honnêtement plutôt que d'afficher une valeur par défaut trompeuse.
- **Aucune duplication de logique.** Une donnée a toujours une seule source de vérité dans toute la suite ; les modules consomment, ils ne recalculent jamais ce qu'un service fournit déjà.
- **Pas de régression.** Toute évolution touchant le cœur de l'application est vérifiée sur l'ensemble des modules déjà en place avant d'être considérée terminée.

---

**Auteur :** ON3RT
