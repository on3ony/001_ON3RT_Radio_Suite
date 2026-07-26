"""
apps/contest/toolbar.py
ON3RT Radio Suite - Contest Logbook
"""

from PySide6.QtGui import QAction


def create_toolbar(window):
    toolbar = window.addToolBar("Principal")
    toolbar.setMovable(False)

    actions = [
        ("Nouveau", window.new_contest),
        ("Ouvrir", window.open_contest),
        ("Enregistrer", window.save_contest_as),
        ("Import ADIF", window.import_adif),
        ("Export Cabrillo", window.export_cabrillo),
        ("QRZ", None),
        ("CAT", None),
    ]

    created = {}

    for text, slot in actions:
        action = QAction(text, window)
        if slot:
            action.triggered.connect(slot)
        toolbar.addAction(action)
        created[text] = action

    return toolbar, created
