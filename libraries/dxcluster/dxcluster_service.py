"""
ON3RT Radio Suite
libraries/dxcluster/dxcluster_service.py

Service DX Cluster partagé de la suite : une seule connexion Telnet
vers un cluster DX (DXFun — dxfun.com:8000, nœud DXSpider EA4RCH-5),
au même titre que RadioService pour le CAT et StationService pour
l'identité de la station. Tout consommateur (Dashboard, futurs
DataSources, Contest, BandActivity...) passe par cette instance
partagée, jamais par une connexion Telnet propre.

Contrat de données d'un spot (figé, voir échanges de conception) :
    received_at    str    ISO 8601 UTC, horodatage de réception réel
    time_utc       str    "HH:MM", heure transmise par le cluster
    frequency_khz  float  fréquence telle que transmise (kHz)
    band           str | None   dérivé via libraries.radio.band_manager
                                (même composant que RadioService pour le CAT)
    dx_callsign    str    indicatif spotté
    spotter        str    indicatif du spotter, brut (SSID de nœud inclus
                          si présent, jamais découpé)
    comment        str    texte libre du spotter (peut être vide, jamais
                          interprété comme une donnée structurée)
    mode           str | None   toujours None (non fourni par le protocole
                                DXSpider standard) — jamais déduit de comment
    dxcc           str | None   toujours None (nécessiterait un futur
                                enrichissement, hors périmètre)
    locator        str | None   toujours None (idem)
    source         str    constante de configuration ("DXFun"), jamais
                          déduite des données reçues
    raw            str    ligne Telnet brute reçue, fins de ligne retirées

Aucun champ non fourni par le protocole n'est jamais déduit de
`comment` : un champ que le cluster ne fournit pas reste `None`.

Authentification : login par indicatif, lu sur station_service à
chaque tentative de connexion (jamais figé à la construction), pour
rester cohérent avec une éventuelle configuration ultérieure de la
station. Aucun mot de passe n'est envoyé (non requis par ce cluster).

Format du protocole (vérifié par connexion Telnet réelle lors de la
conception) :
    - Prompt de connexion : "login: " (sans saut de ligne, à détecter
      directement dans le buffer brut).
    - Une fois connecté : bannière DXSpider, puis un prompt interactif
      répété après chaque commande — jamais utilisé ici, ce service
      n'envoie que l'indicatif de login.
    - Annonces de spot en direct, format DXSpider standard :
          DX de <spotter>:    <freq kHz>  <dx_call>   <commentaire>   <HHMM>Z
      Ce format n'a pas pu être capturé en direct lors de la
      conception (aucun spot en temps réel reçu pendant les fenêtres
      de test, seule la commande sh/dx — non utilisée par ce service
      — a confirmé le nœud DXSpider et le format des champs) : il
      s'agit du format standard DXSpider documenté et utilisé par
      l'ensemble des logiciels de cluster DX depuis plus de 20 ans,
      pas d'une supposition ad hoc. Le parseur est conçu pour ignorer
      silencieusement (retourner None) toute ligne qui ne correspond
      pas exactement à ce format plutôt que de risquer une donnée mal
      interprétée.

Reconnexion : backoff progressif (5s, 10s, 20s, 40s, plafonné à 60s),
reinitialisé dès qu'une connexion réussit. Pendant une déconnexion,
`connected` reste honnêtement False et recent_spots() ne retourne que
l'historique déjà reçu (jamais de donnée inventée pour combler
l'absence de connexion).
"""

from __future__ import annotations

import re
from collections import deque
from datetime import datetime, timezone

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtNetwork import QTcpSocket

from libraries.radio.band_manager import BandManager

DEFAULT_HOST = "dxfun.com"
DEFAULT_PORT = 8000
SOURCE_NAME = "DXFun"

MAX_SPOTS = 100

MIN_RECONNECT_DELAY_S = 5
MAX_RECONNECT_DELAY_S = 60

# Annonce de spot DXSpider standard :
#   DX de EA4RCH-5:    14025.0  EA1XYZ       CQ zone 14              1234Z
_SPOT_RE = re.compile(
    r"^DX de (?P<spotter>\S+):\s+"
    r"(?P<freq>[\d.]+)\s+"
    r"(?P<dx>\S+)\s*"
    r"(?P<comment>.*?)\s*"
    r"(?P<time>\d{4})Z\s*$"
)


class DXClusterService(QObject):
    """
    Connexion Telnet partagée vers un cluster DX. Émet `spot_received`
    pour chaque nouveau spot (dict conforme au contrat ci-dessus) et
    `connectionChanged` à chaque changement d'état de connexion.
    """

    spot_received = Signal(dict)
    connectionChanged = Signal(bool)

    def __init__(self, station_service=None, host=DEFAULT_HOST, port=DEFAULT_PORT, parent=None):
        super().__init__(parent)

        self._station_service = station_service
        self._host = host
        self._port = port

        self._socket = QTcpSocket(self)
        self._socket.connected.connect(self._on_socket_connected)
        self._socket.disconnected.connect(self._on_socket_disconnected)
        self._socket.readyRead.connect(self._on_ready_read)
        self._socket.errorOccurred.connect(self._on_socket_error)

        self._buffer = b""
        self._logged_in = False
        self._connected = False
        self._manual_disconnect = False
        self._reconnect_delay_s = MIN_RECONNECT_DELAY_S

        self._spots = deque(maxlen=MAX_SPOTS)
        self._band_manager = BandManager()

        self._reconnect_timer = QTimer(self)
        self._reconnect_timer.setSingleShot(True)
        self._reconnect_timer.timeout.connect(self._attempt_connect)

    # ------------------------------------------------------------------
    # Connexion
    # ------------------------------------------------------------------

    def connect(self):
        """Démarre (ou relance) la connexion. Sans effet si déjà connecté."""

        self._manual_disconnect = False
        self._reconnect_timer.stop()

        if self._socket.state() == QTcpSocket.SocketState.UnconnectedState:
            self._attempt_connect()

    def disconnect(self):
        """Ferme la connexion volontairement : aucune reconnexion automatique."""

        self._manual_disconnect = True
        self._reconnect_timer.stop()
        self._socket.disconnectFromHost()

    @property
    def connected(self):
        return self._connected

    def recent_spots(self, limit=MAX_SPOTS):
        """Retourne les `limit` derniers spots connus (plus récent en dernier)."""

        spots = list(self._spots)
        return spots[-limit:] if limit else spots

    # ------------------------------------------------------------------
    # Cycle de connexion bas niveau
    # ------------------------------------------------------------------

    def _attempt_connect(self):
        self._buffer = b""
        self._logged_in = False
        self._socket.connectToHost(self._host, self._port)

    def _on_socket_connected(self):
        # Rien à envoyer ici : on attend le prompt "login: " (sans saut
        # de ligne, voir _on_ready_read) avant d'envoyer l'indicatif.
        pass

    def _on_socket_disconnected(self):
        was_connected = self._connected
        self._connected = False
        self._logged_in = False

        if was_connected:
            self.connectionChanged.emit(False)

        if not self._manual_disconnect:
            self._schedule_reconnect()

    def _on_socket_error(self, _error):
        if self._connected:
            self._connected = False
            self.connectionChanged.emit(False)

        if not self._manual_disconnect:
            self._schedule_reconnect()

    def _schedule_reconnect(self):
        self._reconnect_timer.start(self._reconnect_delay_s * 1000)
        self._reconnect_delay_s = min(self._reconnect_delay_s * 2, MAX_RECONNECT_DELAY_S)

    # ------------------------------------------------------------------
    # Réception
    # ------------------------------------------------------------------

    def _on_ready_read(self):
        self._buffer += bytes(self._socket.readAll())

        if not self._logged_in:
            # Le prompt "login: " n'est jamais suivi d'un saut de ligne
            # (il attend une saisie immédiate) : détection directe dans
            # le buffer brut plutôt que par découpage en lignes.
            if self._buffer.rstrip().endswith(b"login:"):
                self._buffer = b""
                self._send_login()
            return

        while b"\n" in self._buffer:
            line, self._buffer = self._buffer.split(b"\n", 1)
            self._handle_line(line)

    def _handle_line(self, raw_bytes):
        line = raw_bytes.decode("utf-8", errors="replace").rstrip("\r")

        spot = self._parse_spot(line)
        if spot is not None:
            self._spots.append(spot)
            self.spot_received.emit(spot)

    def _send_login(self):
        callsign = ""
        if self._station_service is not None:
            callsign = getattr(self._station_service, "callsign", "") or ""

        self._socket.write((callsign + "\r\n").encode("utf-8"))
        self._logged_in = True

        self._reconnect_delay_s = MIN_RECONNECT_DELAY_S
        self._connected = True
        self.connectionChanged.emit(True)

    # ------------------------------------------------------------------
    # Parsing des spots
    # ------------------------------------------------------------------

    def _parse_spot(self, line):
        """
        Retourne un dict conforme au contrat de spot si `line` est une
        annonce DXSpider valide, sinon None (toute autre ligne — prompt,
        message système, annonce non-DX — est silencieusement ignorée).
        """

        match = _SPOT_RE.match(line)
        if not match:
            return None

        try:
            frequency_khz = float(match.group("freq"))
        except ValueError:
            return None

        time_raw = match.group("time")
        time_utc = f"{time_raw[:2]}:{time_raw[2:]}"

        band = self._band_manager.get_band(int(frequency_khz * 1000))

        return {
            "received_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "time_utc": time_utc,
            "frequency_khz": frequency_khz,
            "band": band,
            "dx_callsign": match.group("dx"),
            "spotter": match.group("spotter"),
            "comment": match.group("comment").strip(),
            "mode": None,
            "dxcc": None,
            "locator": None,
            "source": SOURCE_NAME,
            "raw": line,
        }
