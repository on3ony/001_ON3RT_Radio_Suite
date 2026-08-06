"""
Tests de libraries/cat/cat_adapters/rigctld_adapter.py (RigctldAdapter,
mode diagnostic).

Vérifie le contrat de cette étape (voir docstring du module) :
    - ouvre un vrai serveur TCP (127.0.0.1, port éphémère) et accepte
      plusieurs vraies connexions clientes simultanées (socket
      standard, pas un double), chacune servie indépendamment ;
    - journalise chaque ligne reçue, dans l'ordre réel, avec l'adresse
      (ip:port) de la connexion d'origine ;
    - répond systématiquement une réponse générique minimale après
      chaque ligne encore non implémentée (aucune sémantique rigctld
      réelle à ce stade) ;
    - "f" (get_freq), "t" (get_ptt), "m" (get_mode) et "F" (set_freq,
      seule commande d'écriture) sont les seules commandes interrogeant
      réellement cat_sharing_service ; "v" (get_vfo) reçoit une réponse
      statique ("VFOA") sans jamais l'interroger -- toute autre
      commande ne le touche JAMAIS non plus, vérifié avec un double qui
      enregistre tout accès plutôt que d'en lever une exception (une
      exception levée dans un slot Qt ne remonterait pas forcément
      jusqu'au test).
"""

import logging
import socket

import pytest
from PySide6.QtCore import QEventLoop, QTimer

from libraries.cat.cat_adapters.rigctld_adapter import RigctldAdapter


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


def _pump_events(ms=200):
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


class _RecordingCatSharingService:
    """
    Double qui n'enregistre que les attributs accédés, sans jamais lever
    -- une exception levée dans un slot Qt ne remonterait pas forcément
    jusqu'au test, contrairement à une liste vérifiée explicitement.
    """

    def __init__(self):
        self.accessed_attributes = []

    def __getattr__(self, name):
        self.accessed_attributes.append(name)
        return lambda *args, **kwargs: None


@pytest.fixture
def cat_sharing_service():
    return _RecordingCatSharingService()


class _StubCatSharingService:
    """Double renvoyant une fréquence/un état PTT/un mode/un état DATA contrôlés, pour tester "f" (get_freq), "t" (get_ptt), "m" (get_mode), "F" (set_freq), "M" (set_mode) et "T" (set_ptt) -- distinct de _RecordingCatSharingService (qui ne renvoie jamais de valeur exploitable)."""

    def __init__(
        self,
        frequency_hz=0,
        ptt=False,
        mode="---",
        data_mode=False,
        set_frequency_result=True,
        set_mode_result=True,
        set_data_mode_result=True,
        set_ptt_result=True,
    ):
        self._frequency_hz = frequency_hz
        self._ptt = ptt
        self._mode = mode
        self._data_mode = data_mode
        self._set_frequency_result = set_frequency_result
        self._set_mode_result = set_mode_result
        self._set_data_mode_result = set_data_mode_result
        self._set_ptt_result = set_ptt_result
        self.get_frequency_hz_calls = 0
        self.get_ptt_calls = 0
        self.get_mode_calls = 0
        self.get_data_mode_calls = 0
        self.set_frequency_hz_calls = []
        self.set_mode_calls = []
        self.set_data_mode_calls = []
        self.set_ptt_calls = []

    def get_frequency_hz(self):
        self.get_frequency_hz_calls += 1
        return self._frequency_hz

    def get_ptt(self):
        self.get_ptt_calls += 1
        return self._ptt

    def get_mode(self):
        self.get_mode_calls += 1
        return self._mode

    def get_data_mode(self):
        self.get_data_mode_calls += 1
        return self._data_mode

    def set_frequency_hz(self, frequency_hz):
        self.set_frequency_hz_calls.append(frequency_hz)
        return self._set_frequency_result

    def set_mode(self, mode):
        self.set_mode_calls.append(mode)
        return self._set_mode_result

    def set_data_mode(self, enabled):
        self.set_data_mode_calls.append(enabled)
        return self._set_data_mode_result

    def set_ptt(self, state):
        self.set_ptt_calls.append(state)
        return self._set_ptt_result


@pytest.fixture
def adapter(qapp, cat_sharing_service):
    adapter = RigctldAdapter(cat_sharing_service=cat_sharing_service, host="127.0.0.1", port=0)
    adapter.start()
    yield adapter
    adapter.stop()


def _rx_log_line(peer: str, command: str) -> str:
    return f"RigctldAdapter (diagnostic) RX [{peer}] : {command!r}"


def _client_peer(client_socket) -> str:
    """Adresse "ip:port" telle que le serveur la verra comme peer -- extrémité locale du socket client."""

    host, port = client_socket.getsockname()
    return f"{host}:{port}"


# ------------------------------------------------------------------
# Écoute réseau
# ------------------------------------------------------------------

def test_start_listens_on_an_actual_ephemeral_port(adapter):
    assert adapter.actual_port != 0

    client = socket.create_connection(("127.0.0.1", adapter.actual_port), timeout=2)
    client.close()


def test_stop_closes_the_listening_socket(qapp, cat_sharing_service):
    adapter = RigctldAdapter(cat_sharing_service=cat_sharing_service, host="127.0.0.1", port=0)
    adapter.start()
    port = adapter.actual_port

    adapter.stop()
    _pump_events()

    with pytest.raises(OSError):
        socket.create_connection(("127.0.0.1", port), timeout=1)


def test_two_simultaneous_connections_are_both_accepted_and_served_independently(adapter):
    """Huitième étape : plusieurs connexions simultanées sont désormais acceptées (voir docstring du module), chacune servie indépendamment sans mélange de réponses."""

    first = socket.create_connection(("127.0.0.1", adapter.actual_port), timeout=2)
    _pump_events()

    second = socket.create_connection(("127.0.0.1", adapter.actual_port), timeout=2)
    _pump_events()

    first.sendall(b"\\get_powerstat\n")
    _pump_events()
    second.sendall(b"v\n")
    _pump_events()

    assert first.recv(1024) == b"1\n"
    assert second.recv(1024) == b"VFOA\n"

    first.close()
    second.close()


def test_fragmented_command_from_one_client_never_leaks_into_another_clients_buffer(adapter):
    first = socket.create_connection(("127.0.0.1", adapter.actual_port), timeout=2)
    _pump_events()

    second = socket.create_connection(("127.0.0.1", adapter.actual_port), timeout=2)
    _pump_events()

    # Commande incomplète (pas de "\n") sur le premier client -- ne doit
    # jamais être confondue avec ce que reçoit le second, ni traitée
    # prématurément.
    first.sendall(b"\\get_pow")
    _pump_events()

    second.sendall(b"v\n")
    _pump_events()

    assert second.recv(1024) == b"VFOA\n"

    # Complète la commande du premier client -- son buffer doit avoir
    # été préservé intact, indépendamment de ce que "second" a envoyé
    # entre-temps.
    first.sendall(b"erstat\n")
    _pump_events()

    assert first.recv(1024) == b"1\n"

    first.close()
    second.close()


def test_stop_closes_all_active_connections(qapp, cat_sharing_service):
    adapter = RigctldAdapter(cat_sharing_service=cat_sharing_service, host="127.0.0.1", port=0)
    adapter.start()

    first = socket.create_connection(("127.0.0.1", adapter.actual_port), timeout=2)
    second = socket.create_connection(("127.0.0.1", adapter.actual_port), timeout=2)
    _pump_events()

    adapter.stop()
    _pump_events()

    assert first.recv(1024) == b""
    assert second.recv(1024) == b""

    first.close()
    second.close()


# ------------------------------------------------------------------
# Journalisation RX, dans l'ordre réel
# ------------------------------------------------------------------

def test_logs_each_received_command_in_order(adapter, caplog):
    client = socket.create_connection(("127.0.0.1", adapter.actual_port), timeout=2)
    peer = _client_peer(client)
    _pump_events()

    with caplog.at_level(logging.INFO, logger="CAT_SERVER"):
        client.sendall(b"\\dump_state\n")
        _pump_events()
        client.sendall(b"\\get_freq\n")
        _pump_events()
        client.sendall(b"\\get_ptt\n")
        _pump_events()

    rx_messages = [record.message for record in caplog.records if "RX [" in record.message]

    assert rx_messages == [
        _rx_log_line(peer, "\\dump_state"),
        _rx_log_line(peer, "\\get_freq"),
        _rx_log_line(peer, "\\get_ptt"),
    ]

    client.close()


def test_splits_multiple_commands_received_in_a_single_tcp_chunk(adapter, caplog):
    """Hamlib peut envoyer plusieurs commandes dans un seul paquet TCP -- le découpage sur '\\n' doit tenir."""

    client = socket.create_connection(("127.0.0.1", adapter.actual_port), timeout=2)
    peer = _client_peer(client)
    _pump_events()

    with caplog.at_level(logging.INFO, logger="CAT_SERVER"):
        client.sendall(b"\\get_freq\n\\get_mode\n")
        _pump_events()

    rx_messages = [record.message for record in caplog.records if "RX [" in record.message]

    assert rx_messages == [
        _rx_log_line(peer, "\\get_freq"),
        _rx_log_line(peer, "\\get_mode"),
    ]

    client.close()


# ------------------------------------------------------------------
# \get_powerstat -- première commande protocolaire réellement traitée
# (capture WSJT-X réelle du 2026-08-03 : répondre "0" ici bloquait
# toute la suite de la négociation côté client Hamlib)
# ------------------------------------------------------------------

def test_get_powerstat_replies_rig_power_on_not_the_generic_placeholder(adapter):
    client = socket.create_connection(("127.0.0.1", adapter.actual_port), timeout=2)
    _pump_events()

    client.sendall(b"\\get_powerstat\n")
    _pump_events()

    assert client.recv(1024) == b"1\n"

    client.close()


def test_other_commands_still_receive_the_generic_diagnostic_reply(adapter):
    """Non-régression : seules \\get_powerstat et \\dump_state sont traitées spécifiquement, tout le reste reçoit encore le placeholder générique."""

    client = socket.create_connection(("127.0.0.1", adapter.actual_port), timeout=2)
    _pump_events()

    client.sendall(b"\\get_freq\n")
    _pump_events()

    assert client.recv(1024) == b"0\n"

    client.close()


# ------------------------------------------------------------------
# \dump_state -- deuxième commande protocolaire réellement traitée
# (capture WSJT-X réelle du 2026-08-03 : la négociation progresse
# jusqu'ici après le correctif \get_powerstat, puis bloque à son tour)
# ------------------------------------------------------------------

def test_dump_state_replies_the_full_protocol_version_0_response(adapter):
    """
    Format vérifié directement dans le code source réel de
    netrigctl_open() (dépôt Hamlib/Hamlib, rigs/dummy/netrigctl.c),
    jamais supposé -- voir _DUMP_STATE_REPLY dans rigctld_adapter.py
    pour le détail champ par champ.
    """

    client = socket.create_connection(("127.0.0.1", adapter.actual_port), timeout=2)
    _pump_events()

    client.sendall(b"\\dump_state\n")
    _pump_events()

    expected = (
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

    assert client.recv(4096) == expected

    client.close()


def test_dump_state_reply_uses_protocol_version_zero_on_the_first_line():
    """
    Choix délibéré : la version 0 est la plus simple possible côté
    client Hamlib (RETURNFUNC(RIG_OK) dès la ligne 1) -- évite toute la
    section d'extension clé=valeur du protocole v1+ ("done" terminé),
    jamais nécessaire pour la négociation de base.
    """
    from libraries.cat.cat_adapters.rigctld_adapter import _DUMP_STATE_REPLY

    first_line = _DUMP_STATE_REPLY.split(b"\n", 1)[0]

    assert first_line == b"0"


def test_dump_state_range_and_list_terminators_match_hamlib_end_macros():
    """
    Vérifie les 4 lignes de fin de liste contre les macros réelles de
    hamlib/rig.h : RIG_IS_FRNG_END exige startf==0 et endf==0 (7 champs
    à zéro suffisent) ; RIG_IS_TS_END/RIG_IS_FLT_END exigent modes==0
    (2 champs à zéro suffisent) -- jamais supposé, lu directement dans
    l'en-tête Hamlib.
    """
    from libraries.cat.cat_adapters.rigctld_adapter import _DUMP_STATE_REPLY

    lines = _DUMP_STATE_REPLY.split(b"\n")

    # Lignes 4/5 (index 3/4) : fin de plage RX/TX -- 7 champs.
    assert lines[3] == b"0 0 0 0 0 0 0"
    assert lines[4] == b"0 0 0 0 0 0 0"

    # Lignes 6/7 (index 5/6) : fin des pas de syntonisation/filtres -- 2 champs.
    assert lines[5] == b"0 0"
    assert lines[6] == b"0 0"


# ------------------------------------------------------------------
# Commande "f" (get_freq) -- première commande à quitter le mode
# diagnostic (capture réelle WSJT-X du 2026-08-04, boucle continue
# observée avec "v"/"t" à environ 1 Hz)
# ------------------------------------------------------------------

def test_f_replies_the_real_frequency_from_cat_sharing_service(qapp):
    cat_sharing_service = _StubCatSharingService(frequency_hz=14074000)
    adapter = RigctldAdapter(cat_sharing_service=cat_sharing_service, host="127.0.0.1", port=0)
    adapter.start()

    client = socket.create_connection(("127.0.0.1", adapter.actual_port), timeout=2)
    _pump_events()

    client.sendall(b"f\n")
    _pump_events()

    assert client.recv(1024) == b"14074000\n"
    assert cat_sharing_service.get_frequency_hz_calls == 1

    client.close()
    adapter.stop()


def test_f_replies_zero_when_cat_sharing_service_reports_zero(qapp):
    """Valeur par défaut de RadioStatus.frequency (radio non connectée/pas encore pollée) -- relayée telle quelle, sans erreur ni interprétation (même discipline que read_frequency()/read_mode())."""

    cat_sharing_service = _StubCatSharingService(frequency_hz=0)
    adapter = RigctldAdapter(cat_sharing_service=cat_sharing_service, host="127.0.0.1", port=0)
    adapter.start()

    client = socket.create_connection(("127.0.0.1", adapter.actual_port), timeout=2)
    _pump_events()

    client.sendall(b"f\n")
    _pump_events()

    assert client.recv(1024) == b"0\n"

    client.close()
    adapter.stop()


def test_other_commands_still_never_touch_cat_sharing_service(adapter, cat_sharing_service):
    """Non-régression : "\\chk_vfo"/"s"/"q" (commandes encore génériques après f/t/v/m/F/M/T) ne déclenchent aucun accès à cat_sharing_service. "T" en est volontairement exclue depuis la dixième étape (voir section "T" dédiée plus bas -- elle touche désormais réellement cat_sharing_service.set_ptt())."""

    client = socket.create_connection(("127.0.0.1", adapter.actual_port), timeout=2)
    _pump_events()

    client.sendall(b"\\chk_vfo\ns\nq\n")
    _pump_events()

    assert client.recv(1024) == b"0\n0\n0\n"
    assert cat_sharing_service.accessed_attributes == []

    client.close()


# ------------------------------------------------------------------
# Commande "t" (get_ptt) -- deuxième commande à quitter le mode
# diagnostic (même boucle continue réelle que "f")
# ------------------------------------------------------------------

def test_t_replies_1_when_cat_sharing_service_reports_ptt_on(qapp):
    cat_sharing_service = _StubCatSharingService(ptt=True)
    adapter = RigctldAdapter(cat_sharing_service=cat_sharing_service, host="127.0.0.1", port=0)
    adapter.start()

    client = socket.create_connection(("127.0.0.1", adapter.actual_port), timeout=2)
    _pump_events()

    client.sendall(b"t\n")
    _pump_events()

    assert client.recv(1024) == b"1\n"
    assert cat_sharing_service.get_ptt_calls == 1

    client.close()
    adapter.stop()


def test_t_replies_0_when_cat_sharing_service_reports_ptt_off(qapp):
    cat_sharing_service = _StubCatSharingService(ptt=False)
    adapter = RigctldAdapter(cat_sharing_service=cat_sharing_service, host="127.0.0.1", port=0)
    adapter.start()

    client = socket.create_connection(("127.0.0.1", adapter.actual_port), timeout=2)
    _pump_events()

    client.sendall(b"t\n")
    _pump_events()

    assert client.recv(1024) == b"0\n"

    client.close()
    adapter.stop()


# ------------------------------------------------------------------
# Commande "v" (get_vfo) -- dernière commande de la boucle continue
# réelle, réponse statique (aucune notion de VFO dans la Suite)
# ------------------------------------------------------------------

def test_v_replies_vfoa_statically(adapter):
    client = socket.create_connection(("127.0.0.1", adapter.actual_port), timeout=2)
    _pump_events()

    client.sendall(b"v\n")
    _pump_events()

    assert client.recv(1024) == b"VFOA\n"

    client.close()


def test_v_never_touches_cat_sharing_service(adapter, cat_sharing_service):
    """Garde de l'architecture : CatSharingService n'expose aucune notion de VFO -- "v" ne doit jamais l'interroger."""

    client = socket.create_connection(("127.0.0.1", adapter.actual_port), timeout=2)
    _pump_events()

    client.sendall(b"v\n")
    _pump_events()

    assert cat_sharing_service.accessed_attributes == []

    client.close()


# ------------------------------------------------------------------
# Commande "m" (get_mode) -- format à deux lignes vérifié directement
# dans le code source réel de netrigctl_get_mode() (dépôt
# Hamlib/Hamlib, rigs/dummy/netrigctl.c) : une réponse à une seule
# ligne laisse le client Hamlib bloqué en lecture de la deuxième ligne
# (passband), jamais envoyée jusqu'à cette étape.
# ------------------------------------------------------------------

def test_m_replies_the_real_mode_from_cat_sharing_service_and_a_static_passband(qapp):
    cat_sharing_service = _StubCatSharingService(mode="USB")
    adapter = RigctldAdapter(cat_sharing_service=cat_sharing_service, host="127.0.0.1", port=0)
    adapter.start()

    client = socket.create_connection(("127.0.0.1", adapter.actual_port), timeout=2)
    _pump_events()

    client.sendall(b"m\n")
    _pump_events()

    assert client.recv(1024) == b"USB\n0\n"
    assert cat_sharing_service.get_mode_calls == 1

    client.close()
    adapter.stop()


def test_m_relays_the_default_placeholder_mode_unchanged(qapp):
    """RadioStatus.mode vaut "---" tant que la radio n'est pas connectée/pollée -- relayé tel quel, jamais traduit (même discipline que "f"/"t"). Un jeton non reconnu ne provoque qu'un debug WARN côté client Hamlib (rig_parse_mode(), src/misc.c), aucune déconnexion."""

    cat_sharing_service = _StubCatSharingService(mode="---")
    adapter = RigctldAdapter(cat_sharing_service=cat_sharing_service, host="127.0.0.1", port=0)
    adapter.start()

    client = socket.create_connection(("127.0.0.1", adapter.actual_port), timeout=2)
    _pump_events()

    client.sendall(b"m\n")
    _pump_events()

    assert client.recv(1024) == b"---\n0\n"

    client.close()
    adapter.stop()


def test_m_passband_line_is_always_rig_passband_normal():
    """Deuxième ligne toujours "0" (RIG_PASSBAND_NORMAL, include/hamlib/rig.h) -- aucune largeur de bande réelle n'existe dans le chemin de données de la Suite."""

    from libraries.cat.cat_adapters.rigctld_adapter import _MODE_PASSBAND_NORMAL

    assert _MODE_PASSBAND_NORMAL == 0


# ------------------------------------------------------------------
# Commande "m" -- traduction inverse PKTxxx (neuvième étape), reproduit
# icom_get_mode() : PKTUSB/PKTLSB/PKTAM/PKTFM reconstruits UNIQUEMENT
# lorsque get_data_mode() est actif ET le mode de base fait partie des
# 4 modes traduits ; ignoré silencieusement pour tout autre mode de
# base (ex. CW), même avec data_mode actif.
# ------------------------------------------------------------------

def test_m_replies_pktusb_when_base_mode_is_usb_and_data_mode_is_active(qapp):
    cat_sharing_service = _StubCatSharingService(mode="USB", data_mode=True)
    adapter = RigctldAdapter(cat_sharing_service=cat_sharing_service, host="127.0.0.1", port=0)
    adapter.start()

    client = socket.create_connection(("127.0.0.1", adapter.actual_port), timeout=2)
    _pump_events()

    client.sendall(b"m\n")
    _pump_events()

    assert client.recv(1024) == b"PKTUSB\n0\n"
    assert cat_sharing_service.get_data_mode_calls == 1

    client.close()
    adapter.stop()


@pytest.mark.parametrize(
    "base_mode, expected_pkt_mode",
    [("USB", "PKTUSB"), ("LSB", "PKTLSB"), ("AM", "PKTAM"), ("FM", "PKTFM")],
)
def test_m_replies_every_pkt_variant_when_data_mode_is_active(qapp, base_mode, expected_pkt_mode):
    cat_sharing_service = _StubCatSharingService(mode=base_mode, data_mode=True)
    adapter = RigctldAdapter(cat_sharing_service=cat_sharing_service, host="127.0.0.1", port=0)
    adapter.start()

    client = socket.create_connection(("127.0.0.1", adapter.actual_port), timeout=2)
    _pump_events()

    client.sendall(b"m\n")
    _pump_events()

    assert client.recv(1024) == f"{expected_pkt_mode}\n0\n".encode()

    client.close()
    adapter.stop()


def test_m_replies_the_base_mode_unchanged_when_data_mode_is_inactive(qapp):
    cat_sharing_service = _StubCatSharingService(mode="USB", data_mode=False)
    adapter = RigctldAdapter(cat_sharing_service=cat_sharing_service, host="127.0.0.1", port=0)
    adapter.start()

    client = socket.create_connection(("127.0.0.1", adapter.actual_port), timeout=2)
    _pump_events()

    client.sendall(b"m\n")
    _pump_events()

    assert client.recv(1024) == b"USB\n0\n"

    client.close()
    adapter.stop()


def test_m_never_translates_a_base_mode_with_no_pkt_variant_even_when_data_mode_is_active(qapp):
    """Reproduit icom_get_mode() : data_mode actif mais mode de base sans variante PKT (ex. CW, scénario où data_mode serait resté actif après un changement de mode hors rigctld) -- aucune traduction, mode de base renvoyé tel quel."""

    cat_sharing_service = _StubCatSharingService(mode="CW", data_mode=True)
    adapter = RigctldAdapter(cat_sharing_service=cat_sharing_service, host="127.0.0.1", port=0)
    adapter.start()

    client = socket.create_connection(("127.0.0.1", adapter.actual_port), timeout=2)
    _pump_events()

    client.sendall(b"m\n")
    _pump_events()

    assert client.recv(1024) == b"CW\n0\n"

    client.close()
    adapter.stop()


# ------------------------------------------------------------------
# Commande "F" (set_freq) -- première commande d'ÉCRITURE réelle,
# première commande à argument analysé. Format "RPRT <code>" vérifié
# directement dans le code source réel de netrigctl_transaction() et
# netrigctl_set_freq() (dépôt Hamlib/Hamlib, rigs/dummy/netrigctl.c) :
# une réponse générique ("0\n") provoquait "Protocol error while
# setting frequency." côté WSJT-X (capture réelle du 2026-08-04).
# ------------------------------------------------------------------

def test_F_sets_the_real_frequency_via_cat_sharing_service_and_replies_rprt_0(qapp):
    cat_sharing_service = _StubCatSharingService(set_frequency_result=True)
    adapter = RigctldAdapter(cat_sharing_service=cat_sharing_service, host="127.0.0.1", port=0)
    adapter.start()

    client = socket.create_connection(("127.0.0.1", adapter.actual_port), timeout=2)
    _pump_events()

    client.sendall(b"F 14074055.000000\n")
    _pump_events()

    assert client.recv(1024) == b"RPRT 0\n"
    assert cat_sharing_service.set_frequency_hz_calls == [14074055]

    client.close()
    adapter.stop()


def test_F_rounds_the_decimal_frequency_to_the_nearest_integer_hz(qapp):
    cat_sharing_service = _StubCatSharingService(set_frequency_result=True)
    adapter = RigctldAdapter(cat_sharing_service=cat_sharing_service, host="127.0.0.1", port=0)
    adapter.start()

    client = socket.create_connection(("127.0.0.1", adapter.actual_port), timeout=2)
    _pump_events()

    client.sendall(b"F 14074055.600000\n")
    _pump_events()

    client.recv(1024)
    assert cat_sharing_service.set_frequency_hz_calls == [14074056]

    client.close()
    adapter.stop()


def test_F_replies_rprt_minus1_for_an_unparseable_frequency_and_never_touches_cat_sharing_service(qapp):
    cat_sharing_service = _StubCatSharingService()
    adapter = RigctldAdapter(cat_sharing_service=cat_sharing_service, host="127.0.0.1", port=0)
    adapter.start()

    client = socket.create_connection(("127.0.0.1", adapter.actual_port), timeout=2)
    _pump_events()

    client.sendall(b"F not_a_number\n")
    _pump_events()

    assert client.recv(1024) == b"RPRT -1\n"
    assert cat_sharing_service.set_frequency_hz_calls == []

    client.close()
    adapter.stop()


def test_F_replies_rprt_minus1_for_a_negative_frequency_and_never_touches_cat_sharing_service(qapp):
    """Une fréquence négative est un paramètre invalide, pas une erreur d'E/S -- rejetée avant toute conversion en entier ou appel à cat_sharing_service (décision explicite, voir docstring du module)."""

    cat_sharing_service = _StubCatSharingService()
    adapter = RigctldAdapter(cat_sharing_service=cat_sharing_service, host="127.0.0.1", port=0)
    adapter.start()

    client = socket.create_connection(("127.0.0.1", adapter.actual_port), timeout=2)
    _pump_events()

    client.sendall(b"F -100.000000\n")
    _pump_events()

    assert client.recv(1024) == b"RPRT -1\n"
    assert cat_sharing_service.set_frequency_hz_calls == []

    client.close()
    adapter.stop()


def test_F_replies_rprt_minus6_when_set_frequency_hz_returns_false(qapp):
    cat_sharing_service = _StubCatSharingService(set_frequency_result=False)
    adapter = RigctldAdapter(cat_sharing_service=cat_sharing_service, host="127.0.0.1", port=0)
    adapter.start()

    client = socket.create_connection(("127.0.0.1", adapter.actual_port), timeout=2)
    _pump_events()

    client.sendall(b"F 14074055.000000\n")
    _pump_events()

    assert client.recv(1024) == b"RPRT -6\n"

    client.close()
    adapter.stop()


# ------------------------------------------------------------------
# Commande "M" (set_mode) -- deuxième commande d'ÉCRITURE réelle,
# neuvième étape (chantier DATA mode). Capture réelle du 2026-08-04
# (logs/cat_server.log) : WSJT-X, DATA/USB-D sélectionné, envoie
# exactement "M PKTUSB -1". Format vérifié dans netrigctl_set_mode()/
# declare_proto_rig(set_mode) (dépôt Hamlib/Hamlib) ; traduction
# PKTxxx -> mode de base + DATA vérifiée dans icom_set_mode()
# (rigs/icom/icom.c) -- voir docstring du module pour le détail complet.
# ------------------------------------------------------------------

def test_M_translates_pktusb_into_usb_plus_data_mode_and_replies_rprt_0(qapp):
    cat_sharing_service = _StubCatSharingService()
    adapter = RigctldAdapter(cat_sharing_service=cat_sharing_service, host="127.0.0.1", port=0)
    adapter.start()

    client = socket.create_connection(("127.0.0.1", adapter.actual_port), timeout=2)
    _pump_events()

    client.sendall(b"M PKTUSB -1\n")
    _pump_events()

    assert client.recv(1024) == b"RPRT 0\n"
    assert cat_sharing_service.set_mode_calls == ["USB"]
    assert cat_sharing_service.set_data_mode_calls == [True]

    client.close()
    adapter.stop()


@pytest.mark.parametrize(
    "pkt_mode, expected_base_mode",
    [("PKTUSB", "USB"), ("PKTLSB", "LSB"), ("PKTAM", "AM"), ("PKTFM", "FM")],
)
def test_M_translates_every_pkt_variant_into_its_base_mode_plus_data_mode(qapp, pkt_mode, expected_base_mode):
    cat_sharing_service = _StubCatSharingService()
    adapter = RigctldAdapter(cat_sharing_service=cat_sharing_service, host="127.0.0.1", port=0)
    adapter.start()

    client = socket.create_connection(("127.0.0.1", adapter.actual_port), timeout=2)
    _pump_events()

    client.sendall(f"M {pkt_mode} -1\n".encode())
    _pump_events()

    assert client.recv(1024) == b"RPRT 0\n"
    assert cat_sharing_service.set_mode_calls == [expected_base_mode]
    assert cat_sharing_service.set_data_mode_calls == [True]

    client.close()
    adapter.stop()


def test_M_sets_data_mode_false_for_a_plain_non_pkt_mode(qapp):
    """Reproduit icom_set_mode() : la transaction DATA est envoyée à CHAQUE changement de mode, avec datamode=0x00 explicite pour un mode non-PKT -- pas seulement ignorée."""

    cat_sharing_service = _StubCatSharingService()
    adapter = RigctldAdapter(cat_sharing_service=cat_sharing_service, host="127.0.0.1", port=0)
    adapter.start()

    client = socket.create_connection(("127.0.0.1", adapter.actual_port), timeout=2)
    _pump_events()

    client.sendall(b"M USB -1\n")
    _pump_events()

    assert client.recv(1024) == b"RPRT 0\n"
    assert cat_sharing_service.set_mode_calls == ["USB"]
    assert cat_sharing_service.set_data_mode_calls == [False]

    client.close()
    adapter.stop()


def test_M_passes_through_an_unrecognized_mode_token_unchanged_to_cat_sharing_service(qapp):
    """Aucune liste de modes valides dupliquée dans cette couche (voir docstring du module) -- un jeton inconnu est transmis tel quel, laissé à RadioService/ModeManager."""

    cat_sharing_service = _StubCatSharingService()
    adapter = RigctldAdapter(cat_sharing_service=cat_sharing_service, host="127.0.0.1", port=0)
    adapter.start()

    client = socket.create_connection(("127.0.0.1", adapter.actual_port), timeout=2)
    _pump_events()

    client.sendall(b"M CW -1\n")
    _pump_events()

    assert client.recv(1024) == b"RPRT 0\n"
    assert cat_sharing_service.set_mode_calls == ["CW"]
    assert cat_sharing_service.set_data_mode_calls == [False]

    client.close()
    adapter.stop()


def test_M_replies_rprt_minus6_when_set_mode_fails_and_never_attempts_set_data_mode(qapp):
    cat_sharing_service = _StubCatSharingService(set_mode_result=False)
    adapter = RigctldAdapter(cat_sharing_service=cat_sharing_service, host="127.0.0.1", port=0)
    adapter.start()

    client = socket.create_connection(("127.0.0.1", adapter.actual_port), timeout=2)
    _pump_events()

    client.sendall(b"M PKTUSB -1\n")
    _pump_events()

    assert client.recv(1024) == b"RPRT -6\n"
    assert cat_sharing_service.set_mode_calls == ["USB"]
    assert cat_sharing_service.set_data_mode_calls == []

    client.close()
    adapter.stop()


def test_M_replies_rprt_minus6_when_set_data_mode_fails_after_a_successful_set_mode(qapp):
    cat_sharing_service = _StubCatSharingService(set_data_mode_result=False)
    adapter = RigctldAdapter(cat_sharing_service=cat_sharing_service, host="127.0.0.1", port=0)
    adapter.start()

    client = socket.create_connection(("127.0.0.1", adapter.actual_port), timeout=2)
    _pump_events()

    client.sendall(b"M PKTUSB -1\n")
    _pump_events()

    assert client.recv(1024) == b"RPRT -6\n"
    assert cat_sharing_service.set_mode_calls == ["USB"]
    assert cat_sharing_service.set_data_mode_calls == [True]

    client.close()
    adapter.stop()


def test_M_replies_rprt_minus1_for_an_unparseable_width_and_never_touches_cat_sharing_service(qapp):
    cat_sharing_service = _StubCatSharingService()
    adapter = RigctldAdapter(cat_sharing_service=cat_sharing_service, host="127.0.0.1", port=0)
    adapter.start()

    client = socket.create_connection(("127.0.0.1", adapter.actual_port), timeout=2)
    _pump_events()

    client.sendall(b"M PKTUSB not_a_number\n")
    _pump_events()

    assert client.recv(1024) == b"RPRT -1\n"
    assert cat_sharing_service.set_mode_calls == []
    assert cat_sharing_service.set_data_mode_calls == []

    client.close()
    adapter.stop()


def test_M_replies_rprt_minus1_for_a_malformed_command_missing_the_width_argument(qapp):
    cat_sharing_service = _StubCatSharingService()
    adapter = RigctldAdapter(cat_sharing_service=cat_sharing_service, host="127.0.0.1", port=0)
    adapter.start()

    client = socket.create_connection(("127.0.0.1", adapter.actual_port), timeout=2)
    _pump_events()

    client.sendall(b"M PKTUSB\n")
    _pump_events()

    assert client.recv(1024) == b"RPRT -1\n"
    assert cat_sharing_service.set_mode_calls == []

    client.close()
    adapter.stop()


def test_M_accepts_a_positive_width_argument_without_ever_using_its_value(qapp):
    """Aucune notion de largeur de bande n'existe dans le chemin de données de la Suite (même constat que pour "m") -- seule la validité syntaxique de l'argument est vérifiée, jamais sa valeur."""

    cat_sharing_service = _StubCatSharingService()
    adapter = RigctldAdapter(cat_sharing_service=cat_sharing_service, host="127.0.0.1", port=0)
    adapter.start()

    client = socket.create_connection(("127.0.0.1", adapter.actual_port), timeout=2)
    _pump_events()

    client.sendall(b"M USB 2400\n")
    _pump_events()

    assert client.recv(1024) == b"RPRT 0\n"
    assert cat_sharing_service.set_mode_calls == ["USB"]

    client.close()
    adapter.stop()


# ------------------------------------------------------------------
# Commande "T" (set_ptt) -- troisième commande d'ÉCRITURE réelle,
# dixième étape. Capture réelle du 2026-08-04 (logs/cat_server.log,
# connexion 127.0.0.1:63767) : WSJT-X envoie "T 1" puis "T 0" lors du
# Test PTT, réponse générique "0\n" (sans préfixe "RPRT ") provoquait
# "Protocol error / while setting PTT on" -- même cause que "F"/"M"
# avant leur correction. Codes RPRT et valeurs ptt_t valides (0/1/2/3)
# vérifiés dans le serveur de référence Hamlib (tests/rigctl_parse.c,
# declare_proto_rig(set_ptt)) -- voir docstring du module.
# ------------------------------------------------------------------

def test_T_1_sets_ptt_on_via_cat_sharing_service_and_replies_rprt_0(qapp):
    cat_sharing_service = _StubCatSharingService()
    adapter = RigctldAdapter(cat_sharing_service=cat_sharing_service, host="127.0.0.1", port=0)
    adapter.start()

    client = socket.create_connection(("127.0.0.1", adapter.actual_port), timeout=2)
    _pump_events()

    client.sendall(b"T 1\n")
    _pump_events()

    assert client.recv(1024) == b"RPRT 0\n"
    assert cat_sharing_service.set_ptt_calls == [True]

    client.close()
    adapter.stop()


def test_T_0_sets_ptt_off_via_cat_sharing_service_and_replies_rprt_0(qapp):
    cat_sharing_service = _StubCatSharingService()
    adapter = RigctldAdapter(cat_sharing_service=cat_sharing_service, host="127.0.0.1", port=0)
    adapter.start()

    client = socket.create_connection(("127.0.0.1", adapter.actual_port), timeout=2)
    _pump_events()

    client.sendall(b"T 0\n")
    _pump_events()

    assert client.recv(1024) == b"RPRT 0\n"
    assert cat_sharing_service.set_ptt_calls == [False]

    client.close()
    adapter.stop()


@pytest.mark.parametrize("ptt_value", [2, 3])
def test_T_translates_mic_and_data_ptt_sources_to_ptt_on(qapp, ptt_value):
    """RIG_PTT_ON_MIC (2) et RIG_PTT_ON_DATA (3) -- aucune notion de source PTT distincte n'existe dans la Suite (voir docstring du module) : les deux sont traduits vers True, comme RIG_PTT_ON (1)."""

    cat_sharing_service = _StubCatSharingService()
    adapter = RigctldAdapter(cat_sharing_service=cat_sharing_service, host="127.0.0.1", port=0)
    adapter.start()

    client = socket.create_connection(("127.0.0.1", adapter.actual_port), timeout=2)
    _pump_events()

    client.sendall(f"T {ptt_value}\n".encode())
    _pump_events()

    assert client.recv(1024) == b"RPRT 0\n"
    assert cat_sharing_service.set_ptt_calls == [True]

    client.close()
    adapter.stop()


def test_T_replies_rprt_minus6_when_set_ptt_returns_false(qapp):
    cat_sharing_service = _StubCatSharingService(set_ptt_result=False)
    adapter = RigctldAdapter(cat_sharing_service=cat_sharing_service, host="127.0.0.1", port=0)
    adapter.start()

    client = socket.create_connection(("127.0.0.1", adapter.actual_port), timeout=2)
    _pump_events()

    client.sendall(b"T 1\n")
    _pump_events()

    assert client.recv(1024) == b"RPRT -6\n"

    client.close()
    adapter.stop()


def test_T_replies_rprt_minus1_for_an_unparseable_argument_and_never_touches_cat_sharing_service(qapp):
    cat_sharing_service = _StubCatSharingService()
    adapter = RigctldAdapter(cat_sharing_service=cat_sharing_service, host="127.0.0.1", port=0)
    adapter.start()

    client = socket.create_connection(("127.0.0.1", adapter.actual_port), timeout=2)
    _pump_events()

    client.sendall(b"T not_a_number\n")
    _pump_events()

    assert client.recv(1024) == b"RPRT -1\n"
    assert cat_sharing_service.set_ptt_calls == []

    client.close()
    adapter.stop()


def test_T_replies_rprt_minus1_for_a_malformed_command_missing_the_argument(qapp):
    """"T" seul (sans espace) ne correspond pas au préfixe "T " et reçoit donc la réponse générique (même comportement qu'un "M" seul, jamais testé pour cette raison) -- ce cas teste "T " suivi d'un argument vide, qui atteint bien la validation."""

    cat_sharing_service = _StubCatSharingService()
    adapter = RigctldAdapter(cat_sharing_service=cat_sharing_service, host="127.0.0.1", port=0)
    adapter.start()

    client = socket.create_connection(("127.0.0.1", adapter.actual_port), timeout=2)
    _pump_events()

    client.sendall(b"T \n")
    _pump_events()

    assert client.recv(1024) == b"RPRT -1\n"
    assert cat_sharing_service.set_ptt_calls == []

    client.close()
    adapter.stop()


@pytest.mark.parametrize("ptt_value", [-1, 4, 99])
def test_T_replies_rprt_minus1_for_a_value_outside_the_valid_ptt_t_set_and_never_touches_cat_sharing_service(qapp, ptt_value):
    """Toute valeur hors {0,1,2,3} est rejetée par le serveur de référence Hamlib lui-même (switch(ptt) default -> -RIG_EINVAL, tests/rigctl_parse.c), avant tout appel à rig_set_ptt() -- reproduit ici à l'identique."""

    cat_sharing_service = _StubCatSharingService()
    adapter = RigctldAdapter(cat_sharing_service=cat_sharing_service, host="127.0.0.1", port=0)
    adapter.start()

    client = socket.create_connection(("127.0.0.1", adapter.actual_port), timeout=2)
    _pump_events()

    client.sendall(f"T {ptt_value}\n".encode())
    _pump_events()

    assert client.recv(1024) == b"RPRT -1\n"
    assert cat_sharing_service.set_ptt_calls == []

    client.close()
    adapter.stop()


# ------------------------------------------------------------------
# Réponse générique de maintien de connexion
# ------------------------------------------------------------------

def test_sends_the_generic_diagnostic_reply_after_each_command(adapter):
    client = socket.create_connection(("127.0.0.1", adapter.actual_port), timeout=2)
    _pump_events()

    client.sendall(b"\\get_freq\n")
    _pump_events()

    assert client.recv(1024) == b"0\n"

    client.close()


def test_sends_one_reply_per_command_not_one_reply_for_the_whole_chunk(adapter):
    client = socket.create_connection(("127.0.0.1", adapter.actual_port), timeout=2)
    _pump_events()

    client.sendall(b"\\get_freq\n\\get_ptt\n")
    _pump_events()

    assert client.recv(1024) == b"0\n0\n"

    client.close()


# ------------------------------------------------------------------
# CatSharingService -- jamais touché en mode diagnostic
# ------------------------------------------------------------------

def test_never_touches_cat_sharing_service(adapter, cat_sharing_service):
    client = socket.create_connection(("127.0.0.1", adapter.actual_port), timeout=2)
    _pump_events()

    client.sendall(b"\\dump_state\n\\get_freq\n\\get_ptt\n\\set_freq 14195000\n\\get_mode\n")
    _pump_events()

    client.close()
    _pump_events()

    assert cat_sharing_service.accessed_attributes == []


# ------------------------------------------------------------------
# Déconnexion client
# ------------------------------------------------------------------

def test_client_disconnect_is_logged_and_does_not_affect_other_active_connections(adapter, caplog):
    """Huitième étape : plusieurs clients pouvant désormais coexister, la déconnexion de l'un ne doit jamais affecter une session déjà active pour un autre."""

    first = socket.create_connection(("127.0.0.1", adapter.actual_port), timeout=2)
    _pump_events()

    second = socket.create_connection(("127.0.0.1", adapter.actual_port), timeout=2)
    _pump_events()

    with caplog.at_level(logging.INFO, logger="CAT_SERVER"):
        first.close()
        _pump_events()

    assert any("client déconnecté" in record.message for record in caplog.records)

    second.sendall(b"v\n")
    _pump_events()

    assert second.recv(1024) == b"VFOA\n"

    second.close()
