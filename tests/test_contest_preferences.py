"""Tests pour apps/contest/contest_preferences.py"""

from apps.contest.contest_preferences import (
    load_last_contest_properties, save_last_contest_properties, FIELDS,
)


def test_load_returns_empty_values_when_nothing_saved(tmp_path):
    path = tmp_path / "prefs.ini"
    values = load_last_contest_properties(path)
    assert values == {key: "" for key in FIELDS}


def test_save_then_load_roundtrip(tmp_path):
    path = tmp_path / "prefs.ini"
    saved = {
        "contest_name": "CQ WW DX SSB",
        "callsign": "ON4XYZ",
        "operator": "Multi Operator",
        "category": "Multi",
        "power": "1000 W (HIGH)",
        "club": "ON3RT Radio Club",
    }

    save_last_contest_properties(saved, path)
    loaded = load_last_contest_properties(path)

    assert loaded == saved


def test_save_overwrites_previous_values(tmp_path):
    path = tmp_path / "prefs.ini"
    save_last_contest_properties({"contest_name": "CQ WW DX SSB"}, path)
    save_last_contest_properties({"contest_name": "REF HF"}, path)

    assert load_last_contest_properties(path)["contest_name"] == "REF HF"
