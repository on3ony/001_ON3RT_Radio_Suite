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

from apps.cat_server.cw_civ_text_backend import CIVTextKeyerBackend
from apps.cat_server.cw_ptt_backend import PTTKeyerBackend
from apps.cat_server.ptt_guard import PTTGuard
from apps.cat_server.radio_service import RadioService
from apps.cat_server.transmission_service import TransmissionService
from apps.contest_assistant.message_service import ContestMessageService
from apps.dashboard.data_sources.band_activity_source import BandActivityLiveDataSource
from apps.dashboard.data_sources.dxcluster_source import DXClusterLiveDataSource
from apps.dashboard.data_sources.local_file_source import LocalFileLiveDataSource
from apps.dashboard.data_sources.logbook_source import LogbookLiveDataSource
from apps.dashboard.data_sources.propagation_source import PropagationLiveDataSource
from apps.dashboard.data_sources.weather_source import WeatherLiveDataSource
from apps.dashboard.live_service import LiveService
from apps.frequency_bank.frequency_service import FrequencyService
from apps.settings.settings_service import SettingsService
from core.module_manager import ModuleManager
from libraries.audio.audio_output_service import AudioOutputService
from libraries.cw.cw_service import CWService
from libraries.cw.element_driver import ElementDriver
from libraries.cw.text_driver import TextDriver
from libraries.dxcluster.dxcluster_service import DXClusterService
from libraries.propagation.propagation_service import PropagationService
from libraries.station.station_service import StationService
from libraries.voice.voice_service import VoiceService
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

        # Service partagé LiveService (Dashboard / futur ON3RT Live) :
        # agrège CAT (fichier-pont), Logbook, DX Cluster, activité par
        # bande, météo et propagation en un seul état diffusé via
        # state_changed. Remonté ici depuis DashboardPage, qui le
        # construisait auparavant en privé (source list minimale,
        # CAT+Logbook seulement), pour que dxcluster_service/
        # weather_service/propagation_service ci-dessus -- déjà
        # partagés par le reste de la suite -- alimentent aussi le
        # Dashboard sans ouvrir de deuxième connexion à chacun.
        #
        # BandActivityLiveDataSource partage dxcluster_service avec
        # DXClusterLiveDataSource juste au-dessus (même instance, même
        # signal spot_received) : aucune connexion DX Cluster
        # supplémentaire n'est ouverte pour alimenter la tuile
        # "Activité par bande" (chantier dédié, 2026-08-05).
        live_sources = [
            LocalFileLiveDataSource(),
            LogbookLiveDataSource(),
            DXClusterLiveDataSource(self.dxcluster_service),
            BandActivityLiveDataSource(self.dxcluster_service),
            WeatherLiveDataSource(self.weather_service),
            PropagationLiveDataSource(self.propagation_service),
        ]
        self.live_service = LiveService(source=live_sources)

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

        # Infrastructure partagée de l'architecture Voix (AudioOutputService
        # / PTTGuard / TransmissionService / VoiceService) : quatre
        # briques déjà validées unitairement et matériellement (étapes
        # 1 à 4d), mais qu'aucun module applicatif ne consommait encore
        # avant l'étape 4e. ptt_guard réutilise self.radio_service
        # ci-dessus — la même instance CAT déjà partagée avec
        # ScannerWindow/SettingsWindow/BandMapWindow, aucune connexion
        # supplémentaire créée ici. Pure plomberie à ce stade (4e-1) :
        # comme chaque service partagé lors de son introduction, rien
        # ne les utilise encore — leur premier vrai consommateur
        # (bouton "Annoncer" du Contest Assistant) arrive à l'étape 4e-3.
        self.audio_output_service = AudioOutputService()
        self.ptt_guard = PTTGuard(radio_service=self.radio_service)
        self.transmission_service = TransmissionService(
            audio_service=self.audio_output_service, ptt_guard=self.ptt_guard
        )
        self.voice_service = VoiceService()

        # Service partagé CWService (chantier CW, libraries/cw/) : moteur
        # figé et validé unitairement (109 tests) — cette instanciation
        # n'y touche pas, elle réutilise seulement self.ptt_guard/
        # self.radio_service ci-dessus, exactement comme
        # transmission_service. Le choix du couple driver/backend
        # concret reste ici, et ici seulement, comme documenté dans
        # ARCHITECTURE.md ("core/application.py, seul endroit qui
        # choisit") : settings_service.cw["keyer_backend"] sélectionne
        # entre "civ_text" (CIVTextKeyerBackend, commande CI-V 0x17 —
        # étape 3) et tout autre valeur, y compris le défaut "ptt"
        # (PTTKeyerBackend inchangé, ElementDriver inchangé). Ni
        # CWService ni TextDriver ni ElementDriver ne sont modifiés par
        # ce choix : ils ignorent totalement quel backend leur est
        # injecté. wpm/farnsworth_wpm proviennent de settings_service.cw,
        # déjà persistés depuis l'onglet CW de Settings.
        if self.settings_service.cw["keyer_backend"] == "civ_text":
            cw_driver = TextDriver(CIVTextKeyerBackend(self.radio_service, self.ptt_guard))
        else:
            cw_driver = ElementDriver(PTTKeyerBackend(self.ptt_guard))

        self.cw_service = CWService(
            driver=cw_driver,
            wpm=self.settings_service.cw["wpm"],
            farnsworth_wpm=self.settings_service.cw["farnsworth_wpm"],
        )

        # Coordination RadioService <-> CWService (bug matériel réel,
        # trouvé lors de la première validation IC-7300 le 2026-08-02) :
        # radio_service.timer interroge la radio en continu (250 ms,
        # trois échanges CI-V bloquants par cycle -- fréquence/mode/PTT)
        # sur la même liaison série que celle utilisée par
        # PTTKeyerBackend pendant le keying CW. Les deux flux étant
        # synchrones sur le même thread Qt, ils entrent en concurrence
        # pour le port série : la boucle d'événements se bloque par
        # intermittence pendant une émission CW (barre de progression
        # figée, bouton Stop qui semble ne rien faire), symptôme observé
        # uniquement sur matériel réel (NullKeyerBackend ne touche à
        # aucun port série -- jamais reproduit par les 109 tests du
        # moteur). validate_cw_keying.py évitait déjà ce problème en
        # appelant radio_service.timer.stop() juste après connect() ;
        # ce réflexe n'avait pas été reporté ici, où radio_service doit
        # au contraire continuer à alimenter le Dashboard en temps
        # normal -- d'où cette pause strictement limitée à la durée
        # d'une émission CW. Aucun fichier de libraries/cw/ ni
        # apps/cat_server/cw_ptt_backend.py n'est concerné : pure
        # coordination entre deux services déjà partagés, au même
        # endroit que le reste du câblage CW (étape 2a).
        self._cw_polling_paused = False
        self.cw_service.cw_started.connect(self._on_cw_started)
        self.cw_service.cw_finished.connect(self._on_cw_transmission_ended)
        self.cw_service.cw_stopped.connect(self._on_cw_transmission_ended)
        self.cw_service.cw_error.connect(self._on_cw_transmission_ended)

    # ---------------------------------------------------------
    # Coordination RadioService <-> CWService (voir commentaire ci-dessus)
    # ---------------------------------------------------------

    def _on_cw_started(self, request_id=None) -> None:
        self._cw_polling_paused = True
        self.radio_service.timer.stop()

    def _on_cw_transmission_ended(self, *args) -> None:
        if not self._cw_polling_paused:
            return

        self._cw_polling_paused = False

        if self.radio_service.connected:
            self.radio_service.timer.start()

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