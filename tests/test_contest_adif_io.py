"""Tests pour apps/contest/adif_io.py"""

from apps.contest.adif_io import export_adif, import_adif


def test_export_then_import_roundtrip(tmp_path):
    qsos = [
        {
            "callsign": "ON3RT",
            "qso_date": "20260723",
            "time_on": "0815",
            "band": "20m",
            "freq": 14195000,
            "mode": "SSB",
            "rst_sent": "59",
            "rst_recv": "59",
            "serial_sent": 1,
            "serial_recv": 14,
            "exchange_sent": "001",
            "exchange_recv": "014",
        }
    ]

    path = tmp_path / "export.adi"
    count = export_adif(qsos, str(path))
    assert count == 1
    assert path.exists()

    content = path.read_text(encoding="utf-8")
    assert "<CALL:5>ON3RT" in content
    assert "<FREQ:9>14.195000" in content

    imported = import_adif(str(path))
    assert len(imported) == 1
    qso = imported[0]
    assert qso["callsign"] == "ON3RT"
    assert qso["band"] == "20m"
    assert qso["serial_sent"] == 1
    assert qso["serial_recv"] == 14
    assert qso["exchange_recv"] == "014"
    assert abs(qso["freq"] - 14195000) < 1


def test_import_missing_callsign_defaults_to_empty(tmp_path):
    path = tmp_path / "broken.adi"
    path.write_text(
        "<QSO_DATE:8>20260723<EOR>\n", encoding="utf-8"
    )
    imported = import_adif(str(path))
    assert imported[0]["callsign"] == ""
