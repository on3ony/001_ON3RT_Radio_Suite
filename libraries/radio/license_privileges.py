"""
ON3RT Radio Suite
libraries/radio/license_privileges.py

Registre des classes de licence radioamateur et des bandes autorisées
pour chacune -- source de vérité unique et évolutive pour tout module
souhaitant filtrer une liste de bandes selon la classe de licence
active de l'opérateur (StationService.license_class), sans jamais
coder cette logique dans le module consommateur lui-même (premier
consommateur : apps/dashboard/panels/band_activity_panel.py, chantier
"Tuile Activité par bande").

Ajouter une nouvelle classe de licence = ajouter une entrée dans
LICENSE_CLASSES ci-dessous, jamais modifier un module consommateur.

Vocabulaire des bandes : toujours les noms de
libraries.radio.band_manager.BandManager.BANDS (ex. "20m", "80m"),
jamais une liste indépendante -- voir le travers déjà identifié dans
apps/logbook/qso_dialog.py et l'ancienne version de BandActivityPanel,
qui dupliquaient chacun leur propre liste de bandes.

"allowed_bands": None signifie "aucune restriction" (toutes les
bandes de BandManager.BANDS sont autorisées) -- cas HAREC ou classe
inconnue. Une classe avec restrictions donne un frozenset explicite
des noms de bandes autorisées.
"""

from __future__ import annotations

from libraries.radio.band_manager import BandManager

DEFAULT_LICENSE_CLASS = "HAREC"

LICENSE_CLASSES = {
    "HAREC": {
        "label": "HAREC / sans restriction",
        "allowed_bands": None,
    },
    "ON3": {
        "label": "Belgique -- ON3 (novice)",
        "allowed_bands": frozenset({"80m", "40m", "20m", "15m", "10m"}),
    },
}


def allowed_bands(license_class: str) -> frozenset:
    """
    Retourne l'ensemble des noms de bandes autorisées pour
    `license_class` (vocabulaire de BandManager.BANDS).

    Une classe inconnue, vide ou None se comporte comme
    DEFAULT_LICENSE_CLASS -- jamais d'exception, jamais d'ensemble
    vide inventé : même discipline que le reste de la Suite (ne
    jamais planter sur une donnée de configuration absente/invalide).
    """

    entry = LICENSE_CLASSES.get(license_class) or LICENSE_CLASSES[DEFAULT_LICENSE_CLASS]

    restricted = entry["allowed_bands"]
    if restricted is None:
        return frozenset(band.name for band in BandManager.BANDS)

    return frozenset(restricted)


def available_license_classes() -> list:
    """Retourne [(id, label), ...] dans l'ordre de déclaration, pour peupler un sélecteur (Settings)."""

    return [(key, entry["label"]) for key, entry in LICENSE_CLASSES.items()]


if __name__ == "__main__":

    print("=" * 50)
    print("ON3RT Radio Suite")
    print("Test - license_privileges.py")
    print("=" * 50)

    for class_id, label in available_license_classes():
        print(f"{class_id} ({label}) :", sorted(allowed_bands(class_id)))
