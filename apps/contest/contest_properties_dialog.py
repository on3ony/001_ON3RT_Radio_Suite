"""
apps/contest/contest_properties_dialog.py
ON3RT Radio Suite - Contest Logbook
"""

from apps.contest.simple_form_dialog import SimpleFormDialog


class ContestPropertiesDialog(SimpleFormDialog):

    FIELDS = [
        ("contest_name", "Concours"),
        ("callsign", "Indicatif"),
        ("operator", "Opérateur"),
        ("category", "Catégorie"),
        ("power", "Puissance"),
        ("club", "Club"),
    ]

    def __init__(self, info: dict, parent=None):
        super().__init__(info, "Propriétés du concours", parent)
