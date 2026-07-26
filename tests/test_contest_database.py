"""Tests unitaires pour apps/contest/database.py"""

import pytest

from apps.contest.database import ContestDatabase


@pytest.fixture
def db(tmp_path):
    database = ContestDatabase(db_path=tmp_path / "contest_test.db")
    yield database
    database.close()


def test_next_serial_starts_at_one(db):
    assert db.get_next_serial() == 1


def test_add_and_get_qso(db):
    qso_id = db.add_qso(callsign="ON3RT", qso_date="20260723", time_on="0815",
                         band="20m", mode="SSB", serial_sent=1)
    qso = db.get_qso(qso_id)
    assert qso["callsign"] == "ON3RT"
    assert qso["band"] == "20m"


def test_next_serial_increments_after_insert(db):
    db.add_qso(callsign="ON3RT", serial_sent=1)
    assert db.get_next_serial() == 2


def test_update_qso(db):
    qso_id = db.add_qso(callsign="ON3RT", serial_sent=1)
    db.update_qso(qso_id, callsign="ON4XYZ")
    qso = db.get_qso(qso_id)
    assert qso["callsign"] == "ON4XYZ"


def test_delete_qso(db):
    qso_id = db.add_qso(callsign="ON3RT", serial_sent=1)
    db.delete_qso(qso_id)
    assert db.get_qso(qso_id) is None


def test_search_callsign_is_case_insensitive(db):
    db.add_qso(callsign="ON3RT", serial_sent=1)
    results = db.search_callsign("on3rt")
    assert len(results) == 1


def test_get_statistics(db):
    db.add_qso(callsign="ON3RT", serial_sent=1, points=1, multiplier=1)
    db.add_qso(callsign="ON4XYZ", serial_sent=2, points=1, multiplier=1)
    stats = db.get_statistics()
    assert stats["qsos"] == 2
    assert stats["points"] == 2
    assert stats["multipliers"] == 2
    # score = somme(points) * somme(multiplicateurs) -- formule actuelle de get_statistics()
    assert stats["score"] == 4
