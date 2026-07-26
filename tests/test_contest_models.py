"""Tests unitaires pour apps/contest/models.py"""

from apps.contest.models import ContestQSO


def test_default_values():
    qso = ContestQSO()
    assert qso.callsign == ""
    assert qso.points == 1
    assert qso.multiplier == 0


def test_score_uses_multiplier_floor_of_one():
    qso = ContestQSO(points=3, multiplier=0)
    assert qso.score == 3

    qso = ContestQSO(points=3, multiplier=2)
    assert qso.score == 6


def test_to_dict_roundtrip():
    qso = ContestQSO(callsign="ON3RT", band="20m", mode="SSB")
    data = qso.to_dict()
    restored = ContestQSO.from_dict(data)
    assert restored == qso


def test_str_contains_key_fields():
    qso = ContestQSO(
        callsign="ON3RT", band="20m", mode="SSB",
        qso_date="20260723", time_on="0815",
    )
    text = str(qso)
    assert "ON3RT" in text
    assert "20m" in text
    assert "SSB" in text
