"""
apps/contest/cabrillo_export_dialog.py
ON3RT Radio Suite - Contest Logbook
"""

from apps.contest.simple_form_dialog import SimpleFormDialog


class CabrilloExportDialog(SimpleFormDialog):

    FIELDS = [
        ("contest_name", "Concours (CONTEST)"),
        ("callsign", "Indicatif (CALLSIGN)"),
        ("category_operator", "Catégorie opérateur"),
        ("category_assisted", "Assisted"),
        ("category_band", "Bande"),
        ("category_power", "Puissance"),
        ("category_mode", "Mode"),
        ("category_station", "Station"),
        ("club", "Club"),
        ("name", "Nom"),
        ("email", "Email"),
        ("location", "Localisation"),
        ("operators", "Opérateurs"),
        ("claimed_score", "Score revendiqué"),
    ]

    def __init__(self, defaults: dict, parent=None):
        super().__init__(defaults, "Export Cabrillo", parent)
