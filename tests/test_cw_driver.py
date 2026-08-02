"""
Tests de libraries/cw/cw_driver.py.

Ce module ne définit qu'un contrat (docstring), aucune classe ni
fonction -- ces tests vérifient statiquement (analyse du code source)
l'indépendance totale explicitement exigée : ni Qt, ni RadioService,
ni aucun backend concret, ni MorseEncoder, ni TimingEngine. Même
principe que test_cw_ptt_backend.py::test_module_never_imports_morse_or_timing_related_code.
"""

import ast
import inspect

import libraries.cw.cw_driver as cw_driver_module


def _imported_module_names(module) -> list[str]:
    source = inspect.getsource(module)
    tree = ast.parse(source)

    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)

    return names


def test_module_only_imports_the_standard_library_future_import():
    """Aucune dépendance du tout -- ni Qt, ni RadioService, ni backend, ni Morse/TimingEngine."""

    assert _imported_module_names(cw_driver_module) == ["__future__"]


def test_module_never_imports_qt_radio_or_morse_related_code():
    """
    Vérification explicite par sous-chaînes interdites, en complément du
    test d'égalité stricte ci-dessus -- ceinture et bretelles si la
    liste d'imports autorisés venait à évoluer un jour.
    """

    forbidden_substrings = (
        "pyside6",
        "qt",
        "radio_service",
        "ptt_guard",
        "keyer_backend",
        "morse",
        "timing",
        "cw_service",
    )
    imported_names = _imported_module_names(cw_driver_module)

    for name in imported_names:
        lowered = name.lower()
        for forbidden in forbidden_substrings:
            assert forbidden not in lowered, f"import interdit trouvé dans cw_driver.py : {name}"


def test_module_defines_no_classes_or_functions_yet():
    """
    Étape 1 du chantier CWDriver : uniquement le contrat (docstring),
    aucune implémentation -- ElementDriver/TextDriver viendront dans
    des fichiers dédiés (étapes suivantes), jamais ici.
    """

    members = [
        name
        for name, value in inspect.getmembers(cw_driver_module)
        if not name.startswith("__") and (inspect.isclass(value) or inspect.isfunction(value))
    ]

    assert members == []
