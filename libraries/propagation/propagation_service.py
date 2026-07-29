"""
ON3RT Radio Suite
libraries/propagation/propagation_service.py

Service de propagation partagé de la suite : interroge périodiquement
le flux HamQSL (hamqsl.com/solarxml.php — N0NBH, aucune clé API
requise), une agrégation ham-radio des indices solaires/géomagnétiques
publics.

Aucune dépendance à StationService : les indices solaires et
géomagnétiques sont globaux, pas liés à une position — contrairement
à WeatherService, PropagationService peut démarrer sans condition.

Contrat de données publié (figé) — strictement factuel, aucune
interprétation, aucune donnée calculée, aucune recommandation :
    received_at            str    ISO 8601 UTC, horodatage de réception
    solar_flux              float | None
    sunspot_number           int | None
    a_index                  int | None
    k_index                  int | None
    x_ray_class              str | None   classification standard (A/B/C/M/X)
    proton_flux              float | None
    electron_flux            float | None
    aurora_index             int | None
    solar_wind_kms           float | None
    magnetic_field_nt        float | None
    geomagnetic_status       str | None   texte fourni tel quel par HamQSL
                                         (ex. "QUIET"), jamais recalculé
    source                   str          constante "HamQSL", jamais déduite

Volontairement exclu du contrat V1 (décision explicite) : les
évaluations de conditions par bande ("calculatedconditions" /
"calculatedvhfconditions" du flux XML) — ce sont des interprétations
déjà réalisées par HamQSL lui-même, pas des mesures physiques brutes.
Reportées à une éventuelle V2.

Le XML brut de la dernière requête réussie est conservé uniquement en
interne (propriété `last_raw_response`, usage débogage) — jamais
inclus dans le dict publié via `propagation_updated`.

Fréquence de sondage par défaut : 1 heure (recommandation de HamQSL
lui-même ; le flux solaire est par nature une mesure quasi
quotidienne, interroger plus souvent n'apporterait rien).
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime, timezone

from PySide6.QtCore import QObject, QTimer, QUrl, Signal
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

DEFAULT_POLL_INTERVAL_MS = 60 * 60 * 1000  # 1 heure

SOURCE_NAME = "HamQSL"

FEED_URL = "https://www.hamqsl.com/solarxml.php"

_UNAVAILABLE_TOKENS = ("no report", "norpt")


def _parse_int(text):
    text = _clean(text)
    if text is None:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _parse_float(text):
    text = _clean(text)
    if text is None:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _parse_str(text):
    return _clean(text)


def _clean(text):
    if text is None:
        return None
    text = text.strip()
    if not text or text.lower() in _UNAVAILABLE_TOKENS:
        return None
    return text


class PropagationService(QObject):
    """
    Interroge périodiquement le flux HamQSL. Émet `propagation_updated`
    (dict conforme au contrat) et `connectionChanged(bool)`. Aucune
    dépendance à StationService : données globales, pas locales.
    """

    propagation_updated = Signal(dict)
    connectionChanged = Signal(bool)

    def __init__(self, poll_interval_ms=DEFAULT_POLL_INTERVAL_MS, parent=None):
        super().__init__(parent)

        self._connected = False
        self._last_raw_response = None

        self._manager = QNetworkAccessManager(self)
        self._reply = None

        self._timer = QTimer(self)
        self._timer.setInterval(poll_interval_ms)
        self._timer.timeout.connect(self._poll)

    # ------------------------------------------------------------------
    # Cycle de vie
    # ------------------------------------------------------------------

    def start(self):
        """Démarre le sondage périodique (sonde immédiatement, puis à intervalle régulier)."""

        if not self._timer.isActive():
            self._timer.start()

        self._poll()

    def stop(self):
        """Arrête le sondage périodique. N'annule pas une requête déjà en vol."""

        self._timer.stop()

    @property
    def connected(self):
        return self._connected

    @property
    def last_raw_response(self):
        """
        Réponse XML brute (texte) de la dernière requête réussie, pour
        débogage uniquement — jamais publiée via `propagation_updated`.
        """

        return self._last_raw_response

    # ------------------------------------------------------------------
    # Sondage
    # ------------------------------------------------------------------

    def _poll(self):
        if self._reply is not None:
            # Une requête est déjà en vol : ne pas en superposer une autre.
            return

        self._reply = self._manager.get(QNetworkRequest(QUrl(FEED_URL)))
        self._reply.finished.connect(self._on_reply_finished)

    def _on_reply_finished(self):
        reply = self._reply
        self._reply = None

        if reply is None:
            return

        try:
            if reply.error() != QNetworkReply.NetworkError.NoError:
                self._set_connected(False)
                return

            raw_text = bytes(reply.readAll()).decode("utf-8", errors="replace")

            try:
                root = ET.fromstring(raw_text)
            except ET.ParseError:
                self._set_connected(False)
                return

            self._last_raw_response = raw_text

            self.propagation_updated.emit(self._build_propagation_dict(root))
            self._set_connected(True)
        finally:
            reply.deleteLater()

    def _set_connected(self, connected):
        if connected != self._connected:
            self._connected = connected
            self.connectionChanged.emit(connected)

    # ------------------------------------------------------------------
    # Construction du contrat publié
    # ------------------------------------------------------------------

    @staticmethod
    def _build_propagation_dict(root):
        # Note : le tag XML source du flux d'électrons est
        # littéralement "electonflux" (sans "r") — coquille du flux
        # HamQSL lui-même, pas une erreur de notre part. Conservé tel
        # quel ici pour extraire correctement la donnée réelle.
        return {
            "received_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "solar_flux": _parse_float(root.findtext("solardata/solarflux")),
            "sunspot_number": _parse_int(root.findtext("solardata/sunspots")),
            "a_index": _parse_int(root.findtext("solardata/aindex")),
            "k_index": _parse_int(root.findtext("solardata/kindex")),
            "x_ray_class": _parse_str(root.findtext("solardata/xray")),
            "proton_flux": _parse_float(root.findtext("solardata/protonflux")),
            "electron_flux": _parse_float(root.findtext("solardata/electonflux")),
            "aurora_index": _parse_int(root.findtext("solardata/aurora")),
            "solar_wind_kms": _parse_float(root.findtext("solardata/solarwind")),
            "magnetic_field_nt": _parse_float(root.findtext("solardata/magneticfield")),
            "geomagnetic_status": _parse_str(root.findtext("solardata/geomagfield")),
            "source": SOURCE_NAME,
        }
