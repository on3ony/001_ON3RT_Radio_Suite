"""
Tests de apps/dashboard/data_sources/band_activity_source.py.

Chantier "Tuile Activité par bande", étape 4. Trois niveaux :
    - color_for_spot_count() : seuils de couleur validés par
      l'utilisateur, en isolation ;
    - compute_band_counts() : agrégation par bande sur la fenêtre
      glissante, en isolation (aucun Qt, aucun service) ;
    - BandActivityLiveDataSource : relais événementiel réel, avec un
      double minimal de DXClusterService (vrai signal Qt, comme le
      service réel) -- vérifie qu'aucune connexion/stockage propre
      n'est créé, seulement un recalcul à partir de recent_spots().
"""

from datetime import datetime, timedelta, timezone

import pytest
from PySide6.QtCore import QObject, Signal

from apps.dashboard.data_sources.band_activity_source import (
    COLOR_HIGH,
    COLOR_LOW,
    COLOR_MEDIUM,
    COLOR_NONE,
    THRESHOLD_LOW_MAX,
    THRESHOLD_MEDIUM_MAX,
    WINDOW_MINUTES,
    BandActivityLiveDataSource,
    color_for_spot_count,
    compute_band_counts,
)
from libraries.radio.band_manager import BandManager


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


def _spot(band, minutes_ago=0, received_at=None):
    if received_at is None:
        received_at = (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).isoformat(timespec="seconds").replace("+00:00", "Z")
    return {"band": band, "received_at": received_at}


# ------------------------------------------------------------------
# color_for_spot_count() -- seuils validés par l'utilisateur
# ------------------------------------------------------------------

@pytest.mark.parametrize("count", [0, -1])
def test_zero_or_negative_is_grey(count):
    assert color_for_spot_count(count) == COLOR_NONE


@pytest.mark.parametrize("count", [1, 2, 3])
def test_one_to_three_is_green(count):
    assert color_for_spot_count(count) == COLOR_LOW


@pytest.mark.parametrize("count", [4, 6, 8])
def test_four_to_eight_is_yellow(count):
    assert color_for_spot_count(count) == COLOR_MEDIUM


@pytest.mark.parametrize("count", [9, 50])
def test_nine_or_more_is_red(count):
    assert color_for_spot_count(count) == COLOR_HIGH


def test_thresholds_match_the_constants_exactly():
    """Non-régression : les seuils testés ci-dessus doivent rester alignés sur les constantes ajustables."""

    assert color_for_spot_count(THRESHOLD_LOW_MAX) == COLOR_LOW
    assert color_for_spot_count(THRESHOLD_LOW_MAX + 1) == COLOR_MEDIUM
    assert color_for_spot_count(THRESHOLD_MEDIUM_MAX) == COLOR_MEDIUM
    assert color_for_spot_count(THRESHOLD_MEDIUM_MAX + 1) == COLOR_HIGH


# ------------------------------------------------------------------
# compute_band_counts() -- agrégation pure, fenêtre glissante
# ------------------------------------------------------------------

def test_counts_spots_within_the_window_per_band():
    spots = [_spot("20m", minutes_ago=1), _spot("20m", minutes_ago=5), _spot("15m", minutes_ago=2)]

    result = compute_band_counts(spots)

    assert result["20m"]["count"] == 2
    assert result["15m"]["count"] == 1


def test_excludes_spots_older_than_the_window():
    spots = [_spot("20m", minutes_ago=WINDOW_MINUTES + 1)]

    result = compute_band_counts(spots)

    assert result["20m"]["count"] == 0


def test_includes_a_spot_exactly_at_the_window_boundary():
    """cutoff = now - WINDOW_MINUTES ; un spot reçu pile à cutoff est inclus (limite inférieure ou égale)."""

    now = datetime(2026, 8, 5, 12, 0, 0, tzinfo=timezone.utc)
    at_boundary = (now - timedelta(minutes=WINDOW_MINUTES)).isoformat().replace("+00:00", "Z")
    spots = [{"band": "20m", "received_at": at_boundary}]

    result = compute_band_counts(spots, now=now)

    assert result["20m"]["count"] == 1


def test_excludes_a_spot_one_second_past_the_window_boundary():
    now = datetime(2026, 8, 5, 12, 0, 0, tzinfo=timezone.utc)
    past_boundary = (now - timedelta(minutes=WINDOW_MINUTES, seconds=1)).isoformat().replace("+00:00", "Z")
    spots = [{"band": "20m", "received_at": past_boundary}]

    result = compute_band_counts(spots, now=now)

    assert result["20m"]["count"] == 0


def test_every_band_manager_band_is_present_even_with_zero_spots():
    result = compute_band_counts([])

    assert set(result.keys()) == {b.name for b in BandManager.BANDS}
    assert all(entry["count"] == 0 for entry in result.values())
    assert all(entry["color"] == COLOR_NONE for entry in result.values())


def test_spot_with_unknown_band_is_ignored_without_crashing():
    spots = [_spot("999m", minutes_ago=1)]

    result = compute_band_counts(spots)

    assert "999m" not in result
    assert all(entry["count"] == 0 for entry in result.values())


def test_spot_with_missing_received_at_is_ignored_without_crashing():
    spots = [{"band": "20m"}]

    result = compute_band_counts(spots)

    assert result["20m"]["count"] == 0


def test_spot_with_malformed_received_at_is_ignored_without_crashing():
    spots = [{"band": "20m", "received_at": "not-a-date"}]

    result = compute_band_counts(spots)

    assert result["20m"]["count"] == 0


def test_resulting_color_matches_the_computed_count():
    spots = [_spot("10m", minutes_ago=1) for _ in range(5)]

    result = compute_band_counts(spots)

    assert result["10m"]["count"] == 5
    assert result["10m"]["color"] == COLOR_MEDIUM


def test_custom_window_minutes_is_respected():
    spots = [_spot("20m", minutes_ago=4)]

    assert compute_band_counts(spots, window_minutes=3)["20m"]["count"] == 0
    assert compute_band_counts(spots, window_minutes=5)["20m"]["count"] == 1


# ------------------------------------------------------------------
# BandActivityLiveDataSource -- relais événementiel réel
# ------------------------------------------------------------------

class _FakeDXClusterService(QObject):
    """
    Double minimal de DXClusterService : vrai signal Qt spot_received
    (comme le service réel), et recent_spots() piloté par le test --
    pas de stockage/connexion propre côté BandActivityLiveDataSource,
    qui doit se contenter d'appeler recent_spots().
    """

    spot_received = Signal(dict)

    def __init__(self):
        super().__init__()
        self._spots = []

    def recent_spots(self):
        return list(self._spots)

    def push(self, spot):
        self._spots.append(spot)
        self.spot_received.emit(spot)


@pytest.fixture
def fake_service(qapp):
    return _FakeDXClusterService()


def test_start_emits_an_initial_state_from_existing_recent_spots(fake_service):
    fake_service._spots = [_spot("20m", minutes_ago=1)]
    source = BandActivityLiveDataSource(fake_service)

    received = []
    source.updated.connect(lambda state: received.append(state))

    source.start()

    assert len(received) == 1
    assert received[0]["bands"]["20m"]["count"] == 1


def test_new_spot_triggers_a_recomputed_emission(fake_service):
    source = BandActivityLiveDataSource(fake_service)
    received = []
    source.updated.connect(lambda state: received.append(state))
    source.start()

    received.clear()
    fake_service.push(_spot("15m", minutes_ago=0))

    assert len(received) == 1
    assert received[0]["bands"]["15m"]["count"] == 1


def test_never_stores_its_own_spot_list():
    """Non-régression architecturale explicitement demandée : aucun doublon de données côté source."""

    source = BandActivityLiveDataSource(_FakeDXClusterService())

    assert not any("spot" in name.lower() for name in vars(source) if name != "_service")


def test_stop_disconnects_from_the_shared_service(fake_service):
    source = BandActivityLiveDataSource(fake_service)
    source.start()
    source.stop()

    received = []
    source.updated.connect(lambda state: received.append(state))

    fake_service.push(_spot("20m", minutes_ago=0))

    assert received == []
