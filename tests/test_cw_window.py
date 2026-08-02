"""
Tests de apps/cw/window.py.

Vérifie : point d'entrée unique d'envoi, activation des boutons
strictement dérivée de CWService.state, affichage d'état honnête à
chaque signal, comportement sans service injecté, et absence de toute
connaissance du matériel/backend/driver dans ce module.

Réutilise le vrai CWService + ElementDriver + NullKeyerBackend (double
sans matériel déjà validé par tests/test_cw_service.py) plutôt qu'un
faux service : ce module est un consommateur, pas un composant à isoler
de CWService lui-même.
"""

import pytest

from apps.settings.settings_service import SettingsService
from libraries.cw.cw_service import CWService, CWState
from libraries.cw.element_driver import ElementDriver
from libraries.cw.keyer_backend import NullKeyerBackend


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def backend():
    return NullKeyerBackend()


@pytest.fixture
def cw_service(backend):
    return CWService(driver=ElementDriver(backend), wpm=60)


@pytest.fixture
def settings_service(tmp_path):
    return SettingsService(config_path=tmp_path / "settings.json")


@pytest.fixture
def window(qapp, cw_service):
    from apps.cw.window import CWWindow
    w = CWWindow(cw_service=cw_service)
    yield w
    w.close()


@pytest.fixture
def window_with_settings(qapp, cw_service, settings_service):
    from apps.cw.window import CWWindow
    w = CWWindow(cw_service=cw_service, settings_service=settings_service)
    yield w
    w.close()


def _process_events(qapp, ms=50):
    from PySide6.QtCore import QEventLoop, QTimer
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


# ------------------------------------------------------------------
# Architecture : aucune connaissance du matériel/backend/driver
# ------------------------------------------------------------------

def test_window_does_not_import_any_hardware_or_driver_module():
    import apps.cw.window as module

    forbidden_names = (
        "PTTKeyerBackend",
        "ElementDriver",
        "TextDriver",
        "NullKeyerBackend",
        "MorseEncoder",
        "TimingEngine",
        "PTTGuard",
        "RadioService",
    )

    for name in forbidden_names:
        assert not hasattr(module, name), f"{name} ne doit pas être importé dans cette fenêtre"


# ------------------------------------------------------------------
# Construction / états honnêtes
# ------------------------------------------------------------------

def test_window_builds_with_no_service(qapp):
    from apps.cw.window import CWWindow
    w = CWWindow(cw_service=None)

    assert w.lbl_state.text() == "État : inactif"
    assert w.btn_send.isEnabled()
    assert not w.btn_stop.isEnabled()

    w.close()


def test_window_reflects_idle_state_at_construction(window):
    assert window.lbl_state.text() == "État : inactif"
    assert window.btn_send.isEnabled()
    assert not window.btn_stop.isEnabled()


def test_send_with_no_service_shows_status_message_and_does_not_crash(qapp):
    from apps.cw.window import CWWindow
    w = CWWindow(cw_service=None)

    w.input_text.setText("TEST")
    w._on_send_clicked()

    assert w.statusBar().currentMessage() == "CWService indisponible"
    w.close()


def test_send_with_blank_text_does_nothing(window, cw_service):
    window.input_text.setText("   ")
    window._on_send_clicked()

    assert cw_service.state is CWState.IDLE


# ------------------------------------------------------------------
# Point d'entrée unique d'envoi -> CWService.send()
# ------------------------------------------------------------------

def test_send_button_calls_cw_service_send_with_stripped_text(window, cw_service, qapp):
    window.input_text.setText("  VVV TEST  ")
    window._on_send_clicked()

    assert cw_service.state is CWState.SENDING

    cw_service.stop()
    _process_events(qapp)


def test_enter_key_in_input_also_sends(window, cw_service, qapp):
    window.input_text.setText("E")
    window.input_text.returnPressed.emit()

    assert cw_service.state is CWState.SENDING

    cw_service.stop()
    _process_events(qapp)


def test_second_send_while_sending_shows_rejection_message(window, cw_service, qapp):
    window.input_text.setText("PARIS PARIS")
    window._on_send_clicked()

    window.input_text.setText("DEUXIEME")
    window._on_send_clicked()

    assert window.statusBar().currentMessage() == "Émission déjà en cours"

    cw_service.stop()
    _process_events(qapp)


# ------------------------------------------------------------------
# Boutons + label d'état pilotés par les signaux réels de CWService
# ------------------------------------------------------------------

def test_buttons_and_label_follow_started_and_stopped_signals(window, cw_service, qapp):
    window.input_text.setText("PARIS PARIS PARIS")
    window._on_send_clicked()
    _process_events(qapp)

    assert not window.btn_send.isEnabled()
    assert window.btn_stop.isEnabled()
    assert window.lbl_state.text() == "État : émission en cours"

    window._on_stop_clicked()
    _process_events(qapp)

    assert window.btn_send.isEnabled()
    assert not window.btn_stop.isEnabled()
    assert window.lbl_state.text() == "État : arrêté"


def test_progress_signal_updates_progress_bar(window, cw_service, qapp):
    window.input_text.setText("PARIS PARIS PARIS")
    window._on_send_clicked()

    _process_events(qapp, ms=300)

    assert window.progress.maximum() == len("PARIS PARIS PARIS")
    assert window.progress.value() >= 0

    cw_service.stop()
    _process_events(qapp)


def test_error_signal_shows_detail_and_disables_stop(qapp):
    """
    Déclenche une vraie erreur asynchrone via CWService.send() (backend
    dont key_down() lève après le premier élément) plutôt que d'émettre
    cw_error directement -- une émission manuelle ne passerait pas par
    _on_driver_error() et ne mettrait donc jamais réellement à jour
    cw_service.state, ce que cette fenêtre est censée refléter fidèlement.
    """
    from apps.cw.window import CWWindow

    class RaisingBackend(NullKeyerBackend):
        def key_down(self, owner=None):
            raise RuntimeError("panne simulée")

    service = CWService(driver=ElementDriver(RaisingBackend()), wpm=60)
    w = CWWindow(cw_service=service)

    w.input_text.setText("E")
    w._on_send_clicked()

    _process_events(qapp, ms=200)

    assert w.lbl_state.text() == "État : erreur — panne simulée"
    assert not w.btn_stop.isEnabled()
    assert w.btn_send.isEnabled()
    assert service.state is CWState.ERROR

    w.close()


# ------------------------------------------------------------------
# Cycle de vie
# ------------------------------------------------------------------

def test_close_disconnects_signals_without_raising(qapp, cw_service):
    from apps.cw.window import CWWindow
    w = CWWindow(cw_service=cw_service)
    w.close()

    # Après fermeture, émettre un signal ne doit plus rien faire planter
    # ni relancer un slot déconnecté.
    cw_service.cw_started.emit("req-x")


# ------------------------------------------------------------------
# Macros F1-F12 -- chargement, envoi, édition, persistance
# ------------------------------------------------------------------

def test_macros_default_to_twelve_empty_slots_without_settings_service(window):
    assert window._macros == [""] * 12
    assert len(window.macro_buttons) == 12


def test_macros_are_loaded_from_settings_service_at_construction(qapp, cw_service, settings_service):
    settings_service.cw["macros"] = ["CQ CQ DE ON3RT"] + [""] * 11

    from apps.cw.window import CWWindow
    w = CWWindow(cw_service=cw_service, settings_service=settings_service)

    assert w._macros[0] == "CQ CQ DE ON3RT"
    assert w.macro_buttons[0].toolTip() == "CQ CQ DE ON3RT"
    assert w.macro_buttons[1].toolTip() == "(vide)"

    w.close()


def test_clicking_a_macro_button_sends_its_text(window_with_settings, cw_service, settings_service, qapp):
    settings_service.cw["macros"] = ["E"] + [""] * 11
    window_with_settings._macros = window_with_settings._load_macros()

    window_with_settings._on_macro_button_clicked(0)

    assert cw_service.state is CWState.SENDING

    cw_service.stop()
    _process_events(qapp)


def test_clicking_an_empty_macro_button_shows_status_message_and_does_not_send(window_with_settings, cw_service):
    window_with_settings._on_macro_button_clicked(5)

    assert window_with_settings.statusBar().currentMessage() == "Macro F6 vide"
    assert cw_service.state is CWState.IDLE


def test_f_key_shortcut_triggers_the_same_macro_as_its_button(window_with_settings, cw_service, settings_service, qapp):
    settings_service.cw["macros"] = ["T"] + [""] * 11
    window_with_settings._macros = window_with_settings._load_macros()

    window_with_settings._macro_shortcuts[0].activated.emit()

    assert cw_service.state is CWState.SENDING

    cw_service.stop()
    _process_events(qapp)


def test_macro_buttons_disabled_while_sending(window_with_settings, cw_service, settings_service, qapp):
    settings_service.cw["macros"] = ["PARIS PARIS PARIS"] + [""] * 11
    window_with_settings._macros = window_with_settings._load_macros()

    window_with_settings._on_macro_button_clicked(0)
    _process_events(qapp)

    assert all(not button.isEnabled() for button in window_with_settings.macro_buttons)

    cw_service.stop()
    _process_events(qapp)

    assert all(button.isEnabled() for button in window_with_settings.macro_buttons)


# ------------------------------------------------------------------
# Édition des macros -- boîte de dialogue séparée
# ------------------------------------------------------------------

def test_editing_macros_saves_to_settings_service_and_refreshes_tooltips(window_with_settings, settings_service, monkeypatch):
    import apps.cw.window as window_module

    edited = ["73 DE ON3RT"] + [""] * 11

    class FakeAcceptedDialog:
        def __init__(self, macros, parent=None):
            pass

        def exec(self):
            return window_module.QDialog.DialogCode.Accepted

        def edited_macros(self):
            return edited

    monkeypatch.setattr(window_module, "MacroEditDialog", FakeAcceptedDialog)

    window_with_settings._on_edit_macros_clicked()

    assert window_with_settings._macros == edited
    assert settings_service.cw["macros"] == edited
    assert window_with_settings.macro_buttons[0].toolTip() == "73 DE ON3RT"


def test_cancelling_macro_edit_leaves_macros_and_settings_unchanged(window_with_settings, settings_service, monkeypatch):
    import apps.cw.window as window_module

    original_macros = list(window_with_settings._macros)
    original_saved = list(settings_service.cw["macros"])

    class FakeRejectedDialog:
        def __init__(self, macros, parent=None):
            pass

        def exec(self):
            return window_module.QDialog.DialogCode.Rejected

        def edited_macros(self):
            raise AssertionError("edited_macros() ne doit pas être lu si la boîte est annulée")

    monkeypatch.setattr(window_module, "MacroEditDialog", FakeRejectedDialog)

    window_with_settings._on_edit_macros_clicked()

    assert window_with_settings._macros == original_macros
    assert settings_service.cw["macros"] == original_saved


def test_editing_macros_without_settings_service_shows_status_message(window, monkeypatch):
    import apps.cw.window as window_module

    edited = ["TEST"] + [""] * 11

    class FakeAcceptedDialog:
        def __init__(self, macros, parent=None):
            pass

        def exec(self):
            return window_module.QDialog.DialogCode.Accepted

        def edited_macros(self):
            return edited

    monkeypatch.setattr(window_module, "MacroEditDialog", FakeAcceptedDialog)

    window._on_edit_macros_clicked()

    assert window._macros == edited  # mis à jour en mémoire tout de même
    assert window.statusBar().currentMessage() == "Macros non sauvegardées -- SettingsService indisponible"
