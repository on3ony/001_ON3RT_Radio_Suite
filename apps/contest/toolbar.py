"""
apps/contest/toolbar.py
ON3RT Radio Suite - Contest Logbook
"""

from PySide6.QtGui import QAction


def create_toolbar(window):
    toolbar = window.addToolBar("Principal")
    toolbar.setMovable(False)

    actions = [
        ("Nouveau", None),
        ("Ouvrir", None),
        ("Enregistrer", None),
        ("Import ADIF", None),
        ("Export Cabrillo", None),
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
