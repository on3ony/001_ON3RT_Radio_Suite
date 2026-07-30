"""
Tests du raccourci "Plage de scan" de ScannerWindow.

Vérifie que le QComboBox est un pur raccourci de saisie : il remplit
Début/Fin sans jamais toucher à ScannerModel/ScannerEngine, et que les
en-têtes de catégorie ne sont pas sélectionnables.
"""

import pytest


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def window(qapp):
    from apps.scanner.window import ScannerWindow
    win = ScannerWindow()
    yield win
    win.close()


def test_scanner_window_builds(window):
    assert window.windowTitle()


def test_band_combo_contains_placeholder_and_all_bands(window):
    from apps.scanner.window import _SCAN_BANDS

    combo = window.combo_band
    categories = {category for category, _label, _start, _stop in _SCAN_BANDS}

    # 1 placeholder + 1 en-tête par catégorie + 1 entrée par bande.
    assert combo.count() == 1 + len(categories) + len(_SCAN_BANDS)
    assert combo.itemData(0) is None  # placeholder


def test_every_category_header_is_not_selectable(window):
    """
    Généralisé sur toutes les catégories présentes dans _SCAN_BANDS
    (pas seulement "Radioamateur") : reste valable sans modification
    quand une catégorie est ajoutée (PMR446, Marine, WARC...).
    """
    from PySide6.QtCore import Qt
    from apps.scanner.window import _SCAN_BANDS

    combo = window.combo_band
    expected_categories = []
    for category, _label, _start, _stop in _SCAN_BANDS:
        if category not in expected_categories:
            expected_categories.append(category)

    found_categories = []
    for i in range(1, combo.count()):  # 0 = placeholder
        if combo.itemData(i) is None:  # en-tête de catégorie, jamais une bande
            item = combo.model().item(i)
            assert not (item.flags() & Qt.ItemFlag.ItemIsSelectable)
            assert not (item.flags() & Qt.ItemFlag.ItemIsEnabled)
            found_categories.append(item.text())

    assert found_categories == expected_categories


def test_every_band_is_present_with_its_range_shown_in_the_label(window):
    """
    Généralisé sur _SCAN_BANDS entier : chaque bande doit être
    sélectionnable via son itemData exact (start_mhz, stop_mhz), et son
    libellé affiché doit annoncer clairement sa plage de fréquences
    (amélioration ergonomique demandée). Reste valable sans
    modification pour toute bande ajoutée plus tard.
    """
    from apps.scanner.window import _SCAN_BANDS

    combo = window.combo_band

    for _category, label, start_mhz, stop_mhz in _SCAN_BANDS:
        index = next(
            i for i in range(combo.count())
            if combo.itemData(i) == (start_mhz, stop_mhz)
        )
        text = combo.itemText(index)

        assert text.strip().startswith(label)
        assert f"{start_mhz:.3f}" in text
        assert f"{stop_mhz:.3f}" in text
        assert "MHz" in text


def test_selecting_a_band_fills_start_and_stop_fields_only(window):
    from apps.scanner.window import _SCAN_BANDS

    original_start_hz = window.model.start_freq_hz
    original_stop_hz = window.model.stop_freq_hz

    expected_range = next(
        (start, stop) for category, label, start, stop in _SCAN_BANDS
        if category == "Radioamateur" and label == "20 m"
    )
    index_20m = next(
        i for i in range(window.combo_band.count())
        if window.combo_band.itemData(i) == expected_range
    )

    window.combo_band.setCurrentIndex(index_20m)

    assert window.spin_start.value() == pytest.approx(14.000)
    assert window.spin_stop.value() == pytest.approx(14.350)

    # Le ScannerModel ne doit jamais être modifié par la seule
    # sélection dans le combo : seul "Appliquer" (_apply_settings) le
    # fait, comme pour une saisie manuelle dans les mêmes champs.
    assert window.model.start_freq_hz == original_start_hz
    assert window.model.stop_freq_hz == original_stop_hz


def test_selecting_placeholder_does_nothing(window):
    window.spin_start.setValue(1.234567)
    window.spin_stop.setValue(2.345678)

    window.combo_band.setCurrentIndex(0)

    assert window.spin_start.value() == pytest.approx(1.234567)
    assert window.spin_stop.value() == pytest.approx(2.345678)
