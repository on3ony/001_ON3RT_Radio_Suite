"""
Tests de apps/contest_assistant/window.py.

Vérifie : chargement initial correct, édition du nom de concours,
bascule de langue, CRUD des modèles (via une boîte de dialogue
simulée), envoi d'un message (résolution des variables incluant
%MYCALL% via StationService, avance du numéro, historique),
reset_contest() avec confirmation, restauration des modèles par
défaut, l'ergonomie des tableaux Messages/Historique (QTableView,
même présentation que DX Cluster), et le bouton "Annoncer" (étape 4e-3 :
pipeline asynchrone voice_service -> transmission_service, filtrage par
request_id, indépendance totale vis-à-vis de "Envoyer").

Les tests "Annoncer" utilisent des doubles de test (_FakeVoiceService/
_FakeTransmissionService, QObject réels avec de vrais Signal Qt) —
jamais les vrais services : mêmes principes que
tests/test_voice_service.py/test_transmission_service.py. Les
connexions de window.py sont directes (même thread) : émettre un
signal sur un double déclenche donc le slot immédiatement, sans boucle
d'événements à pomper.
"""

import pytest
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QDialog, QMessageBox

import apps.contest_assistant.window as window_module
from apps.contest_assistant.message_service import ContestMessageService
from apps.contest_assistant.window import ContestAssistantWindow
from libraries.station.station_service import StationService


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture(autouse=True)
def message_box_stubs(monkeypatch):
    """QMessageBox ouvrirait de vraies boîtes de dialogue modales : neutralisées pour les tests."""

    monkeypatch.setattr(window_module.QMessageBox, "information", lambda *args, **kwargs: None)

    state = {"answer": QMessageBox.StandardButton.Yes}
    monkeypatch.setattr(window_module.QMessageBox, "question", lambda *args, **kwargs: state["answer"])
    return state


@pytest.fixture
def fake_dialog_result(monkeypatch):
    """Contrôle le résultat du prochain _MessageTemplateDialog ouvert, sans ouvrir de vraie boîte."""

    result = {"accepted": True, "values": ("Nouveau", "texte fr", "texte en")}

    class FakeDialog:
        def __init__(self, parent=None, label="", text_fr="", text_en=""):
            pass

        def exec(self):
            return QDialog.DialogCode.Accepted if result["accepted"] else QDialog.DialogCode.Rejected

        def values(self):
            return result["values"]

    monkeypatch.setattr(window_module, "_MessageTemplateDialog", FakeDialog)
    return result


@pytest.fixture
def message_service(tmp_path):
    seed_path = tmp_path / "seed.json"
    seed_path.write_text(
        '[{"label": "CQ", "text_fr": "CQ Concours de %MYCALL%", "text_en": "CQ Contest %MYCALL%"}]',
        encoding="utf-8",
    )
    return ContestMessageService(config_path=tmp_path / "contest_assistant.json", seed_path=seed_path)


@pytest.fixture
def station_service(tmp_path):
    service = StationService(config_path=tmp_path / "station.json")
    service.callsign = "ON3RT"
    return service


class _FakeVoiceService(QObject):
    """
    Double de test pour VoiceService : mêmes signaux Qt réels
    (synthesis_finished/synthesis_error), mais synthesize() ne lance
    rien en arrière-plan -- il enregistre l'appel et retourne un
    request_id immédiatement. Le test déclenche lui-même le signal de
    fin (.emit()) au moment voulu, pour contrôler précisément le
    scénario (succès, erreur, requête étrangère).
    """

    synthesis_finished = Signal(str, str)
    synthesis_error = Signal(str, str)

    def __init__(self):
        super().__init__()
        self.calls = []
        self._next_id = 0

    def synthesize(self, text, values=None, params=None, cacheable=True, owner=None):
        self._next_id += 1
        request_id = f"req-{self._next_id}"
        self.calls.append(
            {
                "text": text,
                "values": values,
                "params": params,
                "cacheable": cacheable,
                "owner": owner,
                "request_id": request_id,
            }
        )
        return request_id


class _FakeTransmissionService(QObject):
    """Double de test pour TransmissionService -- mêmes signaux réels, transmit() enregistre l'appel et retourne True."""

    transmission_started = Signal()
    transmission_finished = Signal()
    transmission_stopped = Signal()
    transmission_error = Signal(str)

    def __init__(self):
        super().__init__()
        self.calls = []

    def transmit(self, source, owner=None):
        self.calls.append({"source": source, "owner": owner})
        return True


@pytest.fixture
def voice_service():
    return _FakeVoiceService()


@pytest.fixture
def transmission_service():
    return _FakeTransmissionService()


@pytest.fixture
def window(qapp, message_service, station_service):
    w = ContestAssistantWindow(message_service=message_service, station_service=station_service)
    yield w
    w.close()


@pytest.fixture
def window_with_voice(qapp, message_service, station_service, transmission_service, voice_service):
    w = ContestAssistantWindow(
        message_service=message_service,
        station_service=station_service,
        transmission_service=transmission_service,
        voice_service=voice_service,
    )
    yield w
    w.close()


def _template_label(window, row: int) -> str:
    return window.template_model.data(window.template_model.index(row, 0))


def _template_text(window, row: int) -> str:
    return window.template_model.data(window.template_model.index(row, 1))


def _history_text(window, row: int) -> str:
    return window.history_model.data(window.history_model.index(row, 2))


# ------------------------------------------------------------------
# Chargement initial
# ------------------------------------------------------------------

def test_window_loads_initial_state_from_the_service(window, message_service):
    assert window.edit_contest_name.currentText() == ""
    assert window.btn_language.text() == "Langue : Français"
    assert window.lbl_last_serial.text() == "000"
    assert window.lbl_next_serial.text() == "001"
    assert window.template_model.rowCount() == 1
    assert _template_label(window, 0) == "CQ"
    assert window.history_model.rowCount() == 0


def test_window_builds_without_a_station_service(qapp, message_service):
    w = ContestAssistantWindow(message_service=message_service, station_service=None)
    assert w.station_service is None
    w.close()


# ------------------------------------------------------------------
# Nom du concours
# ------------------------------------------------------------------

def test_contest_name_combo_is_prepopulated_with_contest_names(window):
    from apps.contest.contest_properties_dialog import CONTEST_NAMES

    items = [window.edit_contest_name.itemText(i) for i in range(window.edit_contest_name.count())]
    assert items == CONTEST_NAMES


def test_editing_contest_name_persists_to_the_service(window, message_service):
    window.edit_contest_name.setEditText("CQ WW DX SSB (custom)")
    window.edit_contest_name.lineEdit().editingFinished.emit()

    assert message_service.contest_name == "CQ WW DX SSB (custom)"


def test_selecting_an_existing_contest_name_persists_it(window, message_service):
    index = window.edit_contest_name.findText("CQ WW DX SSB")
    window.edit_contest_name.setCurrentIndex(index)

    window.edit_contest_name.activated.emit(index)

    assert message_service.contest_name == "CQ WW DX SSB"


def test_selecting_autre_clears_the_field_without_persisting_the_placeholder(window, message_service):
    index = window.edit_contest_name.findText("Autre...")
    window.edit_contest_name.setCurrentIndex(index)

    window.edit_contest_name.activated.emit(index)

    assert window.edit_contest_name.currentText() == ""
    assert message_service.contest_name == ""  # jamais "Autre..." enregistré comme nom réel


def test_contest_name_is_restored_from_the_service_on_reopen(qapp, message_service, station_service):
    message_service.contest_name = "CQ WW DX SSB"
    message_service.save()

    w = ContestAssistantWindow(message_service=message_service, station_service=station_service)

    assert w.edit_contest_name.currentText() == "CQ WW DX SSB"
    assert w.edit_contest_name.currentIndex() == w.edit_contest_name.findText("CQ WW DX SSB")

    w.close()


# ------------------------------------------------------------------
# Ergonomie des tableaux Messages / Historique
# ------------------------------------------------------------------

def test_message_and_history_tables_are_comfortably_sized_and_readable(window):
    """
    Messages a un minimumHeight explicite (mesuré pour ses 9 modèles
    par défaut). Répartis dans des onglets séparés, chaque tableau
    reçoit toute la hauteur de son propre onglet sans la partager avec
    l'autre — voir le docstring de apps/contest_assistant/window.py,
    point 3.
    """
    assert window.template_table.minimumHeight() >= 340
    assert window.history_table.minimumHeight() >= 140
    assert window.template_table.alternatingRowColors()
    assert window.history_table.alternatingRowColors()


def test_tabs_separate_messages_and_history_with_messages_as_the_default_tab(window):
    """
    Non-régression de la cause identifiée : Messages et Historique ne
    se partagent plus la hauteur disponible. Ils sont répartis dans un
    QTabWidget à deux onglets (même pattern que apps/settings/window.py),
    Messages ouvert par défaut car consulté en continu pendant un
    concours, Historique consulté seulement à la demande.
    """
    assert window.tabs.count() == 2
    assert window.tabs.tabText(0) == "Messages"
    assert window.tabs.tabText(1) == "Historique"
    assert window.tabs.currentIndex() == 0

    assert window.content_layout.indexOf(window.tabs) >= 0


def test_message_buttons_row_and_table_are_separate_items_within_the_messages_tab(window):
    """
    Non-régression de la cause identifiée à l'origine (les boutons se
    disputaient l'espace avec le tableau) : le tableau et sa rangée de
    boutons restent deux éléments indépendants, désormais à l'intérieur
    de l'onglet Messages plutôt que de content_layout directement.
    """
    messages_tab = window.tabs.widget(0)
    assert window.template_table.parentWidget() is messages_tab

    tab_layout = messages_tab.layout()
    table_index = tab_layout.indexOf(window.template_table)
    assert table_index >= 0
    # Un item de type widget (le tableau), pas de type layout : preuve
    # que ce n'est pas un widget composite contenant aussi les boutons.
    assert tab_layout.itemAt(table_index).widget() is window.template_table


def test_history_table_lives_in_its_own_tab(window):
    history_tab = window.tabs.widget(1)
    assert window.history_table.parentWidget() is history_tab


def test_tables_use_a_fixed_compact_row_height_matching_dx_cluster(window):
    """
    Même hauteur de ligne que DX Cluster (apps/dxcluster/window.py,
    setDefaultSectionSize(34)) : contrôlée par l'en-tête vertical du
    QTableView, pas par une taille d'item bricolée.
    """
    assert window.template_table.verticalHeader().defaultSectionSize() == 34
    assert window.history_table.verticalHeader().defaultSectionSize() == 34
    assert not window.template_table.verticalHeader().isVisible()
    assert not window.history_table.verticalHeader().isVisible()


def test_message_table_has_labelled_columns(window):
    from PySide6.QtCore import Qt

    assert window.template_model.headerData(0, Qt.Orientation.Horizontal) == "Libellé"
    assert window.template_model.headerData(1, Qt.Orientation.Horizontal) == "Message"


# ------------------------------------------------------------------
# Langue
# ------------------------------------------------------------------

def test_toggling_language_updates_button_and_template_table(window, message_service):
    window.btn_language.click()

    assert message_service.language == "EN"
    assert window.btn_language.text() == "Langue : English"
    assert _template_text(window, 0) == "CQ Contest %MYCALL%"


# ------------------------------------------------------------------
# CRUD des modèles
# ------------------------------------------------------------------

def test_add_template_via_dialog_adds_it_to_the_service_and_table(window, message_service, fake_dialog_result):
    fake_dialog_result["values"] = ("Merci", "Merci %CALL%", "Thank you %CALL%")

    window.btn_add_template.click()

    assert [t.label for t in message_service.templates] == ["CQ", "Merci"]
    assert window.template_model.rowCount() == 2


def test_add_template_with_empty_label_is_rejected(window, message_service, fake_dialog_result):
    fake_dialog_result["values"] = ("", "x", "y")

    window.btn_add_template.click()

    assert [t.label for t in message_service.templates] == ["CQ"]  # inchangé


def test_add_template_dialog_cancelled_changes_nothing(window, message_service, fake_dialog_result):
    fake_dialog_result["accepted"] = False

    window.btn_add_template.click()

    assert [t.label for t in message_service.templates] == ["CQ"]


def test_edit_template_without_selection_shows_a_message_and_changes_nothing(window, message_service, fake_dialog_result):
    window.btn_edit_template.click()  # aucune sélection dans le tableau

    assert message_service.templates[0].label == "CQ"


def test_edit_selected_template_updates_it(window, message_service, fake_dialog_result):
    window.template_table.selectRow(0)
    fake_dialog_result["values"] = ("CQ modifié", "Nouveau FR", "New EN")

    window.btn_edit_template.click()

    assert message_service.templates[0].label == "CQ modifié"
    assert message_service.templates[0].text_fr == "Nouveau FR"


def test_delete_selected_template_with_confirmation_removes_it(window, message_service, message_box_stubs):
    window.template_table.selectRow(0)
    message_box_stubs["answer"] = QMessageBox.StandardButton.Yes

    window.btn_delete_template.click()

    assert message_service.templates == []
    assert window.template_model.rowCount() == 0


def test_delete_selected_template_without_confirmation_keeps_it(window, message_service, message_box_stubs):
    window.template_table.selectRow(0)
    message_box_stubs["answer"] = QMessageBox.StandardButton.No

    window.btn_delete_template.click()

    assert len(message_service.templates) == 1


# ------------------------------------------------------------------
# Restauration des modèles par défaut
# ------------------------------------------------------------------

def test_restore_defaults_button_recreates_a_deleted_standard_template(window, message_service, message_box_stubs):
    window.template_table.selectRow(0)
    message_box_stubs["answer"] = QMessageBox.StandardButton.Yes
    window.btn_delete_template.click()
    assert message_service.templates == []

    window.btn_restore_defaults.click()

    assert [t.label for t in message_service.templates] == ["CQ"]
    assert window.template_model.rowCount() == 1
    assert _template_label(window, 0) == "CQ"


def test_restore_defaults_button_does_not_duplicate_when_nothing_is_missing(window, message_service):
    window.btn_restore_defaults.click()

    assert [t.label for t in message_service.templates] == ["CQ"]
    assert window.template_model.rowCount() == 1


def test_restore_defaults_button_never_removes_personal_templates(window, message_service, fake_dialog_result):
    fake_dialog_result["values"] = ("Perso", "texte perso", "personal text")
    window.btn_add_template.click()

    window.btn_restore_defaults.click()

    labels = [t.label for t in message_service.templates]
    assert "Perso" in labels
    assert "CQ" in labels


# ------------------------------------------------------------------
# Envoi
# ------------------------------------------------------------------

def test_send_without_selection_does_not_record_anything(window, message_service):
    window.btn_send.click()

    assert message_service.serial == 0
    assert message_service.history == []


def test_send_selected_message_resolves_variables_and_records_it(window, message_service):
    window.template_table.selectRow(0)
    window.edit_call.setText("F4XYZ")
    window.edit_rst.setText("599")

    window.btn_send.click()

    assert message_service.serial == 1
    assert len(message_service.history) == 1
    sent = message_service.history[0]
    assert sent.resolved_text == "CQ Concours de ON3RT"  # %MYCALL% résolu via StationService
    assert window.lbl_last_serial.text() == "001"
    assert window.lbl_next_serial.text() == "002"
    assert window.history_model.rowCount() == 1
    assert _history_text(window, 0) == "CQ Concours de ON3RT"


def test_send_with_no_station_service_resolves_mycall_to_empty_string(qapp, message_service):
    w = ContestAssistantWindow(message_service=message_service, station_service=None)
    w.template_table.selectRow(0)

    w.btn_send.click()

    assert message_service.history[0].resolved_text == "CQ Concours de "
    w.close()


# ------------------------------------------------------------------
# reset_contest()
# ------------------------------------------------------------------

def test_reset_with_confirmation_clears_name_serial_and_history_only(window, message_service, message_box_stubs):
    window.edit_contest_name.setEditText("CQ WW DX SSB (custom)")
    window.edit_contest_name.lineEdit().editingFinished.emit()
    window.template_table.selectRow(0)
    window.btn_send.click()
    window.btn_language.click()  # EN

    message_box_stubs["answer"] = QMessageBox.StandardButton.Yes
    window.btn_reset.click()

    assert message_service.contest_name == ""
    assert message_service.serial == 0
    assert message_service.history == []
    assert message_service.language == "EN"  # jamais touché
    assert len(message_service.templates) == 1  # jamais touchés

    assert window.edit_contest_name.currentText() == ""
    assert window.lbl_last_serial.text() == "000"
    assert window.history_model.rowCount() == 0


def test_reset_without_confirmation_changes_nothing(window, message_service, message_box_stubs):
    window.edit_contest_name.setEditText("CQ WW DX SSB (custom)")
    window.edit_contest_name.lineEdit().editingFinished.emit()

    message_box_stubs["answer"] = QMessageBox.StandardButton.No
    window.btn_reset.click()

    assert message_service.contest_name == "CQ WW DX SSB (custom)"


# ------------------------------------------------------------------
# Annoncer (étape 4e-3) — action indépendante de "Envoyer"
# ------------------------------------------------------------------

def test_announce_button_is_labelled(window):
    assert window.btn_announce.text() == "Annoncer"


def test_announce_button_disabled_when_services_are_not_provided(window):
    assert window.btn_announce.isEnabled() is False


def test_announce_button_enabled_when_both_services_are_provided(window_with_voice):
    assert window_with_voice.btn_announce.isEnabled() is True


def test_announce_click_is_a_safe_noop_when_services_are_absent(window):
    window.btn_announce.click()  # ne doit jamais lever, même appelé explicitement sur un bouton désactivé


def test_announce_without_selection_shows_a_message_and_does_not_synthesize(window_with_voice, voice_service):
    window_with_voice.btn_announce.click()

    assert voice_service.calls == []
    assert window_with_voice.btn_announce.isEnabled() is True


def test_announce_selected_message_starts_synthesis_with_resolved_text(window_with_voice, voice_service):
    window_with_voice.template_table.selectRow(0)
    window_with_voice.edit_call.setText("F4XYZ")
    window_with_voice.edit_rst.setText("599")

    window_with_voice.btn_announce.click()

    assert len(voice_service.calls) == 1
    call = voice_service.calls[0]
    assert call["text"] == "CQ Concours de ON3RT"
    assert call["cacheable"] is False  # échange dynamique, jamais mis en cache -- voir docstring du module
    assert call["owner"] == "contest_assistant"


def test_announce_disables_the_button_while_in_flight(window_with_voice):
    window_with_voice.template_table.selectRow(0)

    window_with_voice.btn_announce.click()

    assert window_with_voice.btn_announce.isEnabled() is False


def test_announce_never_touches_serial_or_history(window_with_voice, message_service, voice_service, transmission_service):
    """Indépendance totale vis-à-vis de 'Envoyer' -- voir docstring du module."""

    window_with_voice.template_table.selectRow(0)
    window_with_voice.btn_announce.click()

    request_id = voice_service.calls[0]["request_id"]
    voice_service.synthesis_finished.emit(request_id, "fake_output.wav")
    transmission_service.transmission_finished.emit()

    assert message_service.serial == 0
    assert message_service.history == []


def test_announce_full_pipeline_reaches_transmission_and_reenables_button(
    window_with_voice, voice_service, transmission_service
):
    window_with_voice.template_table.selectRow(0)
    window_with_voice.btn_announce.click()

    request_id = voice_service.calls[0]["request_id"]
    voice_service.synthesis_finished.emit(request_id, "fake_output.wav")

    assert len(transmission_service.calls) == 1
    assert transmission_service.calls[0] == {"source": "fake_output.wav", "owner": "contest_assistant"}
    assert window_with_voice.btn_announce.isEnabled() is False  # transmission encore en cours

    transmission_service.transmission_finished.emit()

    assert window_with_voice.btn_announce.isEnabled() is True


def test_announce_synthesis_error_reenables_button_and_never_calls_transmit(
    window_with_voice, voice_service, transmission_service
):
    window_with_voice.template_table.selectRow(0)
    window_with_voice.btn_announce.click()

    request_id = voice_service.calls[0]["request_id"]
    voice_service.synthesis_error.emit(request_id, "moteur en panne")

    assert transmission_service.calls == []
    assert window_with_voice.btn_announce.isEnabled() is True
    assert "moteur en panne" in window_with_voice.statusBar().currentMessage()


def test_announce_transmission_error_reenables_button(window_with_voice, voice_service, transmission_service):
    window_with_voice.template_table.selectRow(0)
    window_with_voice.btn_announce.click()

    request_id = voice_service.calls[0]["request_id"]
    voice_service.synthesis_finished.emit(request_id, "fake_output.wav")
    transmission_service.transmission_error.emit("PTT indisponible")

    assert window_with_voice.btn_announce.isEnabled() is True
    assert "PTT indisponible" in window_with_voice.statusBar().currentMessage()


def test_announce_ignores_synthesis_signals_for_a_different_request_id(
    window_with_voice, voice_service, transmission_service
):
    """VoiceService est partagé : cette fenêtre ne doit réagir qu'à sa propre requête."""

    window_with_voice.template_table.selectRow(0)
    window_with_voice.btn_announce.click()

    voice_service.synthesis_finished.emit("someone-elses-request", "not_ours.wav")

    assert transmission_service.calls == []
    assert window_with_voice.btn_announce.isEnabled() is False  # toujours en attente de SA requête


def test_announce_ignores_transmission_signals_when_not_announcing(window_with_voice, transmission_service):
    """TransmissionService est partagé : un signal reçu hors annonce ne doit rien perturber."""

    transmission_service.transmission_finished.emit()

    assert window_with_voice.btn_announce.isEnabled() is True


def test_send_button_behaviour_is_unaffected_by_the_presence_of_voice_and_transmission_services(window_with_voice, message_service):
    """Non-régression : 'Envoyer' se comporte à l'identique, même avec les deux services injectés."""

    window_with_voice.template_table.selectRow(0)
    window_with_voice.edit_call.setText("F4XYZ")
    window_with_voice.edit_rst.setText("599")

    window_with_voice.btn_send.click()

    assert message_service.serial == 1
    assert len(message_service.history) == 1
    assert message_service.history[0].resolved_text == "CQ Concours de ON3RT"


def test_announce_unexpected_exception_is_caught_and_reported(window_with_voice, voice_service, monkeypatch):
    def _boom(text, values):
        raise RuntimeError("boom")

    monkeypatch.setattr(window_module, "resolve_variables", _boom)

    window_with_voice.template_table.selectRow(0)
    window_with_voice.btn_announce.click()

    assert voice_service.calls == []
    assert window_with_voice.btn_announce.isEnabled() is True
    assert "boom" in window_with_voice.statusBar().currentMessage()
