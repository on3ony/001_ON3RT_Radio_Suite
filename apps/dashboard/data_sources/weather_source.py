#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=========================================================
ON3RT Radio Suite
Dashboard — Weather Live Data Source
=========================================================
Description :
    Fournisseur LiveDataSource pour le service météo partagé de la
    suite (libraries/weather/weather_service.py — WeatherService,
    Open-Meteo, instancié une fois dans core/application.py).

    Se contente d'écouter les signaux weather_updated/connectionChanged
    de l'instance partagée et de relayer l'état courant sous les clés
    "weather_connected" et "weather_data" (dict conforme au contrat
    figé de WeatherService, ou None tant qu'aucune donnée n'a encore
    été reçue).

    Aucune logique HTTP ni Open-Meteo ici : WeatherService reste seul
    responsable de ces aspects. Ce fournisseur n'est qu'un adaptateur
    entre le service partagé et LiveService, exactement comme
    DXClusterLiveDataSource pour DXClusterService.
=========================================================
"""

from .base import LiveDataSource

# Champs dont CE fournisseur est responsable — volontairement
# distinct de DEFAULT_STATE (base.py, contrat partagé par tous les
# fournisseurs) : voir la mise en garde dans base.py, déjà rencontrée
# avec le CAT, le Logbook et le DX Cluster.
DEFAULT_WEATHER_STATE = {
    "weather_connected": False,
    "weather_data": None,
}


class WeatherLiveDataSource(LiveDataSource):
    """
    Adaptateur entre WeatherService (service Suite partagé) et
    LiveService. N'effectue aucune requête HTTP, ne parse aucune
    réponse, ne maintient qu'une simple copie du dernier relevé reçu
    (pour pouvoir la retransmettre lors d'un changement de connexion
    sans avoir à interroger WeatherService) : relaie systématiquement
    l'état déjà produit par le service, jamais une donnée recalculée.
    """

    def __init__(self, weather_service, parent=None):
        super().__init__(parent)

        self._service = weather_service
        self._last_weather = None

    # -----------------------------------------------------
    # Cycle de vie
    # -----------------------------------------------------

    def start(self):
        self._service.weather_updated.connect(self._on_weather_updated)
        self._service.connectionChanged.connect(self._on_connection_changed)
        self._emit_current_state()

    def stop(self):
        self._service.weather_updated.disconnect(self._on_weather_updated)
        self._service.connectionChanged.disconnect(self._on_connection_changed)

    # -----------------------------------------------------
    # Relais de WeatherService
    # -----------------------------------------------------

    def _on_weather_updated(self, weather):
        self._last_weather = weather
        self._emit_current_state()

    def _on_connection_changed(self, _connected):
        self._emit_current_state()

    def _emit_current_state(self):
        state = dict(DEFAULT_WEATHER_STATE)
        state["weather_connected"] = self._service.connected
        state["weather_data"] = self._last_weather

        self.updated.emit(state)
