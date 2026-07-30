"""
core/application.py
-------------------------------------------------
ON3RT Radio Suite V3

Cœur de l'application.

Responsabilités :
    - gestion du ModuleManager
    - démarrage en arrière-plan du service CAT (radio_service), pour que
      le Dashboard dispose immédiatement de données réelles sans avoir
      à ouvrir la fenêtre CAT Server
    - informations générales
    - fermeture propre des modules
"""

from PySide6.QtCore import QSettings

from apps.cat_server.radio_service import RadioService
from apps.contest_assistant.message_service import ContestMessageService
from apps.frequency_bank.frequency_service import FrequencyService
from apps.settings.settings_service import SettingsService
from core.module_manager import ModuleManager
from libraries.dxcluster.dxcluster_service import DXClusterService
from libraries.propagation.propagation_service import PropagationService
from libraries.station.station_service import StationService
from libraries.weather.weather_service import WeatherService

DEFAULT_CAT_BAUDRATE = 19200


class Application:
    """Classe principale de la Radio Suite."""

    def __init__(self):
        self.module_manager = ModuleManager()
        self.name = "ON3RT Radio Suite"
        self.version = "3.0.0"
        self.author = "ON3RT"

        self.radio_service = self._start_radio_service()

        # Source de vérité unique pour l'identité et les caractéristiques
        # permanentes de la station (indicatif, locator, QTH...). Ne
        # contient aucun paramètre de connexion CAT (voir radio_service
        # ci-dessus) ni aucun état dynamique d'un autre service.
        self.station_service = StationService()

        # Service DX Cluster partagé de la suite (connexion Telnet unique
        # vers DXFun) : login avec l'indicatif de station_service, lu à
        # chaque tentative de connexion. Connexion automatique au
        # démarrage, comme radio_service ci-dessus — mais seulement si un
        # indicatif est configuré : un login vide est refusé par le
        # cluster, qui coupe la connexion aussitôt, ce qui déclencherait
        # sinon une boucle de reconnexion perpétuelle contre ce service
        # communautaire partagé tant que la station n'est pas configurée.
        self.dxcluster_service = DXClusterService(station_service=self.station_service)
        if self.station_service.callsign:
            self.dxcluster_service.connect()

        # Service météo partagé de la suite (Open-Meteo) : position lue
        # dans station_service à chaque sondage, jamais copiée. Démarrage
        # sans condition externe — contrairement à dxcluster_service
        # ci-dessus, WeatherService se protège déjà lui-même en interne
        # (_poll() ne fait aucune requête tant que latitude/longitude
        # valent None) : aucune requête ratée, aucun garde-fou à dupliquer
        # ici.
        self.weather_service = WeatherService(station_service=self.station_service)
        self.weather_service.start()

        # Service de propagation partagé de la suite (HamQSL) : indices
        # solaires/géomagnétiques globaux, aucune dépendance à
        # station_service (contrairement à weather_service ci-dessus).
        # Démarrage sans condition, comme weather_service.
        self.propagation_service = PropagationService()
        self.propagation_service.start()

        # Service partagé de la Banque de fréquences : base SQLite
        # locale (data/frequency_bank.db), aucune dépendance à
        # station_service, aucune connexion externe. Contrairement à
        # weather_service/propagation_service ci-dessus, aucun start()
        # n'est nécessaire : pas de minuterie, la base est interrogée
        # à la demande par la fenêtre du module.
        self.frequency_service = FrequencyService()

        # Service partagé des préférences générales de la suite (écran
        # Settings) : fichier JSON local (config/settings.json),
        # aucune dépendance à station_service ni à aucun autre
        # service, aucune connexion externe. Comme frequency_service
        # ci-dessus, aucun start() n'est nécessaire : pas de
        # minuterie, le fichier est lu une seule fois à la
        # construction et interrogé à la demande par la fenêtre du
        # module.
        self.settings_service = SettingsService()

        # Service partagé du module Contest Assistant : modèles de
        # message, langue, nom du concours, numéro progressif et
        # historique. Aucune dépendance à station_service ni à aucun
        # autre service (voir sa conception — %MYCALL% est résolu par
        # la fenêtre, pas par ce service). Comme settings_service
        # ci-dessus, aucun start() n'est nécessaire.
        self.contest_message_service = ContestMessageService()

    # ---------------------------------------------------------
    # Service CAT (arrière-plan)
    # ---------------------------------------------------------

    @staticmethod
    def _start_radio_service():
        """
        Démarre le service CAT en arrière-plan, sans jamais ouvrir la
        fenêtre CAT Server. Reprend le dernier port/baudrate utilisés
        (mêmes réglages QSettings que CATServerWindow) : si aucun port
        n'a jamais été configuré, le service reste créé mais déconnecté
        — le Dashboard affichera honnêtement "déconnecté" jusqu'à ce que
        l'utilisateur se connecte une première fois depuis la Station.
        """

        settings = QSettings("ON3RT", "CATServer")
        last_port = settings.value("last_port", "")
        last_baudrate = settings.value("last_baudrate", DEFAULT_CAT_BAUDRATE, type=int)

        service = RadioService(port=last_port or "COM3", baudrate=last_baudrate)

        if last_port:
            service.connect()

        return service

    # ---------------------------------------------------------
    # Informations
    # ---------------------------------------------------------

    def info(self):
        """Retourne les informations de l'application."""

        return {
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "modules": self.module_manager.count(),
        }

    # ---------------------------------------------------------
    # Modules
    # ---------------------------------------------------------

    def register_module(self, name, window):
        """Enregistre un module."""

        self.module_manager.register(name, window)

    def show_module(self, name):
        """Affiche un module."""

        return self.module_manager.show(name)

    def close_module(self, name):
        """Ferme un module."""

        self.module_manager.close(name)

    def close_all(self):
        """Ferme tous les modules."""

        self.module_manager.close_all()