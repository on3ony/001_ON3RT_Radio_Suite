"""
Tests de libraries/cw/keyer_backend.py.

NullKeyerBackend/NullTextKeyerBackend n'ont aucune dépendance (ni Qt,
ni matériel, ni PTTGuard/RadioService) -- testés entièrement isolés,
comme le reste du chantier CW.
"""

from libraries.cw.keyer_backend import NullKeyerBackend, NullTextKeyerBackend


def test_is_available_is_always_true():
    assert NullKeyerBackend().is_available() is True


def test_name_is_null():
    assert NullKeyerBackend.name == "null"


def test_starts_not_keyed():
    backend = NullKeyerBackend()
    assert backend.is_keyed is False


def test_key_down_sets_is_keyed_true():
    backend = NullKeyerBackend()
    backend.key_down()
    assert backend.is_keyed is True


def test_key_up_sets_is_keyed_false():
    backend = NullKeyerBackend()
    backend.key_down()
    backend.key_up()
    assert backend.is_keyed is False


def test_key_up_without_a_prior_key_down_does_not_raise():
    backend = NullKeyerBackend()
    backend.key_up()  # ne doit jamais lever, meme sans key_down() prealable
    assert backend.is_keyed is False


def test_key_down_records_the_owner():
    backend = NullKeyerBackend()
    backend.key_down(owner="cw_service")
    assert backend.last_owner == "cw_service"


def test_key_down_without_owner_defaults_to_none():
    backend = NullKeyerBackend()
    backend.key_down()
    assert backend.last_owner is None


def test_call_counts_are_tracked_independently():
    backend = NullKeyerBackend()
    backend.key_down()
    backend.key_up()
    backend.key_down()
    backend.key_up()
    backend.key_down()
    assert backend.key_down_calls == 3
    assert backend.key_up_calls == 2


def test_two_instances_do_not_share_state():
    a = NullKeyerBackend()
    b = NullKeyerBackend()
    a.key_down(owner="a")
    assert b.is_keyed is False
    assert b.last_owner is None
    assert b.key_down_calls == 0


# ------------------------------------------------------------------
# NullTextKeyerBackend -- famille "text" (contrat TextBackend)
# ------------------------------------------------------------------

def test_text_backend_is_available_is_always_true():
    assert NullTextKeyerBackend().is_available() is True


def test_text_backend_name_is_null_text():
    assert NullTextKeyerBackend.name == "null_text"


def test_text_backend_default_max_chunk_chars_is_30():
    assert NullTextKeyerBackend().max_chunk_chars == 30


def test_text_backend_max_chunk_chars_is_configurable():
    assert NullTextKeyerBackend(max_chunk_chars=10).max_chunk_chars == 10


def test_text_backend_starts_with_no_sent_chunks():
    backend = NullTextKeyerBackend()
    assert backend.sent_chunks == []


def test_text_backend_send_text_records_the_chunk():
    backend = NullTextKeyerBackend()
    backend.send_text("CQ DX", wpm=20, farnsworth_wpm=None, owner="test")
    assert backend.sent_chunks == ["CQ DX"]


def test_text_backend_send_text_records_wpm_and_farnsworth():
    backend = NullTextKeyerBackend()
    backend.send_text("CQ", wpm=25, farnsworth_wpm=15, owner="test")
    assert backend.last_wpm == 25
    assert backend.last_farnsworth_wpm == 15


def test_text_backend_send_text_records_the_owner():
    backend = NullTextKeyerBackend()
    backend.send_text("CQ", wpm=20, farnsworth_wpm=None, owner="cw_service")
    assert backend.last_owner == "cw_service"


def test_text_backend_send_text_without_owner_defaults_to_none():
    backend = NullTextKeyerBackend()
    backend.send_text("CQ", wpm=20, farnsworth_wpm=None)
    assert backend.last_owner is None


def test_text_backend_several_send_text_calls_are_all_recorded_in_order():
    backend = NullTextKeyerBackend()
    backend.send_text("CQ DX ", wpm=20, farnsworth_wpm=None)
    backend.send_text("DE ON3RT", wpm=20, farnsworth_wpm=None)
    assert backend.sent_chunks == ["CQ DX ", "DE ON3RT"]


def test_text_backend_stop_sending_is_tracked():
    backend = NullTextKeyerBackend()
    backend.stop_sending()
    backend.stop_sending()
    assert backend.stop_sending_calls == 2


def test_text_backend_stop_sending_without_a_prior_send_text_does_not_raise():
    backend = NullTextKeyerBackend()
    backend.stop_sending()  # ne doit jamais lever
    assert backend.stop_sending_calls == 1


def test_text_backend_two_instances_do_not_share_state():
    a = NullTextKeyerBackend()
    b = NullTextKeyerBackend()
    a.send_text("CQ", wpm=20, farnsworth_wpm=None, owner="a")
    assert b.sent_chunks == []
    assert b.last_owner is None
