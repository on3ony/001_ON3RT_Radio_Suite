"""
ON3RT Radio Suite
apps/settings/settings_service.py

Source de vérité unique pour les préférences générales de la suite qui
n'ont pas déjà un service dédié. L'identité station reste dans
StationService (config/station.json), les identifiants QRZ restent
dans libraries/qrz/service.py (config/qrz.json) — ces domaines sont
volontairement laissés en dehors de ce fichier, pas oubliés.

Aucune dépendance à l'interface graphique ni à un autre module de la
suite : ce fichier ne connaît que json/pathlib, exactement comme
libraries/station/station_service.py.

Persistance : config/settings.json. Ce fichier est créé vide (aucune
valeur invention de configuration utilisateur) : SettingsService
fournit ses propres valeurs par défaut en mémoire, jamais écrites tant
que l'utilisateur n'a rien modifié depuis l'écran Settings.

Organisé en sections (network, services...) plutôt qu'en attributs à
plat : ajouter une nouvelle section plus tard (ex. "radio", quand ses
paramètres deviendront réellement configurables) ne casse jamais la
compatibilité avec un config/settings.json déjà existant — une clé
absente d'un fichier plus ancien garde sa valeur par défaut, une clé
présente dans le fichier mais inconnue de cette version est ignorée
(et donc naturellement supprimée au prochain save()).
"""

from __future__ import annotations

import json
from pathlib import Path

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "settings.json"

# Valeurs par défaut recopiées depuis les constantes réelles de chaque
# service au moment de l'écriture de ce fichier (jamais importées :
# SettingsService ne dépend d'aucun autre module de la suite). Si ces
# valeurs par défaut changent un jour côté service, les mettre à jour
# ici aussi.
_DEFAULT_OPEN_METEO_POLL_INTERVAL_MS = 10 * 60 * 1000  # libraries/weather/weather_service.py
_DEFAULT_HAMQSL_POLL_INTERVAL_MS = 60 * 60 * 1000  # libraries/propagation/propagation_service.py
_DEFAULT_DXCLUSTER_HOST = "dxfun.com"  # libraries/dxcluster/dxcluster_service.py
_DEFAULT_DXCLUSTER_PORT = 8000  # libraries/dxcluster/dxcluster_service.py
_DEFAULT_CW_WPM = 20  # libraries/cw/cw_service.py::CWService
_DEFAULT_CW_SIDETONE_HZ = 700  # sidetone CW (étape 10, à venir) -- pas encore de service réel
_CW_MACRO_COUNT = 12  # F1-F12, apps/cw/window.py (étape 2d)


class SettingsService:
    """
    Expose les préférences générales de la suite en sections (dicts),
    et via info() pour un instantané complet. Aucune classe métier
    intermédiaire : SettingsService est lui-même la source de vérité,
    comme StationService.
    """

    def __init__(self, config_path=None):

        self._path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH

        self.network = {
            "hamqth_username": "",
            "hamqth_password": "",
            "lotw_username": "",
            "lotw_password": "",
            "eqsl_username": "",
            "eqsl_password": "",
            "clublog_email": "",
            "clublog_password": "",
        }

        self.services = {
            "open_meteo_poll_interval_ms": _DEFAULT_OPEN_METEO_POLL_INTERVAL_MS,
            "hamqsl_poll_interval_ms": _DEFAULT_HAMQSL_POLL_INTERVAL_MS,
            "dxcluster_host": _DEFAULT_DXCLUSTER_HOST,
            "dxcluster_port": _DEFAULT_DXCLUSTER_PORT,
        }

        # Chantier CW (libraries/cw/) : farnsworth_wpm=None -- pas de
        # Farnsworth par defaut, comme CWService lui-meme. keyer_backend
        # reserve pour un futur selecteur (un seul backend reel existe
        # aujourd'hui, PTT) ; winkeyer_port reserve pour le futur backend
        # Winkeyer ; sidetone_hz reserve pour la future integration du
        # sidetone via AudioOutputService (etape 10) -- champs presents
        # des maintenant pour ne jamais casser la compatibilite d'un
        # config/settings.json deja existant quand ces fonctionnalites
        # arriveront. macros : 12 emplacements F1-F12 (apps/cw/window.py,
        # etape 2d), texte fixe uniquement -- aucune resolution de
        # variable (%CALL%/%RST%/...), ExchangeService reste differe.
        self.cw = {
            "wpm": _DEFAULT_CW_WPM,
            "farnsworth_wpm": None,
            "keyer_backend": "ptt",
            "winkeyer_port": "",
            "sidetone_hz": _DEFAULT_CW_SIDETONE_HZ,
            "macros": [""] * _CW_MACRO_COUNT,
        }

        self.load()

    # ---------------------------------------------------------
    # Persistance
    # ---------------------------------------------------------

    def load(self):
        """
        Charge config/settings.json. Si le fichier est absent, vide,
        illisible ou mal formé, les valeurs par défaut ci-dessus sont
        conservées : aucune donnée n'est inventée.

        Fusion clé par clé, section par section : une clé absente du
        fichier garde sa valeur par défaut, une clé présente dans le
        fichier mais inconnue de cette version est ignorée. C'est ce
        qui rend l'ajout d'une section ou d'un champ plus tard
        rétrocompatible dans les deux sens.
        """

        try:
            raw = self._path.read_text(encoding="utf-8")
            data = json.loads(raw)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return

        if not isinstance(data, dict):
            return

        self._merge_section(data, "network")
        self._merge_section(data, "services")
        self._merge_section(data, "cw")

    def _merge_section(self, data: dict, section_name: str) -> None:
        """Fusionne data[section_name] dans self.<section_name>, clé par clé."""

        section = getattr(self, section_name)
        raw_section = data.get(section_name)

        if not isinstance(raw_section, dict):
            return

        for key in section:
            if key in raw_section:
                section[key] = raw_section[key]

    def save(self):
        """
        Écrit l'état courant dans config/settings.json, en écriture
        atomique (fichier temporaire puis remplacement) — même
        mécanisme que StationService.save().
        """

        self._path.parent.mkdir(parents=True, exist_ok=True)

        tmp_path = self._path.with_suffix(".tmp")

        tmp_path.write_text(
            json.dumps(self.info(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        tmp_path.replace(self._path)

    # ---------------------------------------------------------
    # Lecture
    # ---------------------------------------------------------

    def info(self):
        """Retourne un instantané des préférences de la suite."""

        return {
            "network": dict(self.network),
            "services": dict(self.services),
            "cw": dict(self.cw),
        }
