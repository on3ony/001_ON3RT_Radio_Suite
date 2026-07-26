"""Tests pour apps/contest/cabrillo_export.py"""

from apps.contest.cabrillo_export import export_cabrillo


def _qso(**overrides):
    base = {
        "callsign": "ON4XYZ",
        "qso_date": "20260723",
        "time_on": "0815",
        "band": "20m",
        "freq": 14195000,
        "mode": "SSB",
        "rst_sent": "59",
        "rst_recv": "59",
        "exchange_sent": "001",
        "exchange_recv": "014",
    }
    base.update(overrides)
    return base


def test_export_writes_header_and_qso_lines(tmp_path):
    path = tmp_path / "contest.log"
    header = {
        "contest_name": "CQ-WW-SSB",
        "callsign": "ON3RT",
        "category_operator": "SINGLE-OP",
        "club": "ON3RT Radio Club",
        "claimed_score": "42",
    }

    count = export_cabrillo([_qso()], header, str(path))
    assert count == 1

    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()

    assert lines[0] == "START-OF-LOG: 3.0"
    assert "CONTEST: CQ-WW-SSB" in content
    assert "CALLSIGN: ON3RT" in content
    assert "CATEGORY-OPERATOR: SINGLE-OP" in content
    assert "CLUB: ON3RT Radio Club" in content
    assert "CLAIMED-SCORE: 42" in content
    assert lines[-1] == "END-OF-LOG:"

    qso_lines = [l for l in lines if l.startswith("QSO:")]
    assert len(qso_lines) == 1
    qso_line = qso_lines[0]
    assert "14195" in qso_line
    assert "PH" in qso_line
    assert "2026-07-23" in qso_line
    assert "0815" in qso_line
    assert "ON3RT" in qso_line
    assert "ON4XYZ" in qso_line


def test_empty_header_fields_are_omitted(tmp_path):
    path = tmp_path / "contest.log"
    export_cabrillo([_qso()], {"callsign": "ON3RT"}, str(path))
    content = path.read_text(encoding="utf-8")
    assert "CLUB:" not in content
    assert "CONTEST:" not in content


def test_mode_mapping_for_cw_and_digital(tmp_path):
    path = tmp_path / "contest.log"
    export_cabrillo(
        [_qso(mode="CW"), _qso(mode="FT8")],
        {"callsign": "ON3RT"},
        str(path),
    )
    lines = [l for l in path.read_text(encoding="utf-8").splitlines() if l.startswith("QSO:")]
    assert " CW " in lines[0]
    assert " RY " in lines[1]
