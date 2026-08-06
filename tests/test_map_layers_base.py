"""
Tests de apps/dashboard/map_layers/base.py (disk_geometry/unit_to_pixel).

Fonctions utilitaires pures, partagées par toute couche -- vérifie la
géométrie du disque (centré, avec la marge documentée) et la conversion
coordonnée normalisée -> pixel (notamment l'inversion de l'axe y, seule
responsabilité de cette fonction et jamais de Projection).
"""

from PySide6.QtCore import QRect

from apps.dashboard.map_layers.base import disk_geometry, unit_to_pixel


def test_disk_geometry_centers_on_the_rect_center():
    rect = QRect(0, 0, 300, 200)

    center, radius = disk_geometry(rect)

    assert center.x() == rect.center().x()
    assert center.y() == rect.center().y()


def test_disk_geometry_radius_uses_the_smaller_dimension_with_margin():
    from apps.dashboard.map_layers.base import _DISK_MARGIN_RATIO

    rect = QRect(0, 0, 300, 200)

    _, radius = disk_geometry(rect)

    # plus petite dimension = hauteur (200) ; rayon = 100 * la marge courante
    assert radius == 100.0 * _DISK_MARGIN_RATIO


def test_disk_geometry_radius_never_exceeds_the_unmargined_half_dimension():
    rect = QRect(0, 0, 300, 200)

    _, radius = disk_geometry(rect)

    assert radius < 100.0


def test_unit_to_pixel_center_maps_to_disk_center():
    rect = QRect(0, 0, 300, 200)
    center, radius = disk_geometry(rect)

    point = unit_to_pixel(0.0, 0.0, center, radius)

    assert point.x() == center.x()
    assert point.y() == center.y()


def test_unit_to_pixel_north_is_up_on_screen():
    """y positif (nord, voir Projection) doit donner un y ÉCRAN plus PETIT (vers le haut)."""

    rect = QRect(0, 0, 300, 200)
    center, radius = disk_geometry(rect)

    point = unit_to_pixel(0.0, 1.0, center, radius)

    assert point.y() < center.y()


def test_unit_to_pixel_east_is_right_on_screen():
    rect = QRect(0, 0, 300, 200)
    center, radius = disk_geometry(rect)

    point = unit_to_pixel(1.0, 0.0, center, radius)

    assert point.x() > center.x()


def test_unit_to_pixel_edge_of_disk_lands_at_exactly_radius_distance():
    import math

    rect = QRect(0, 0, 300, 200)
    center, radius = disk_geometry(rect)

    point = unit_to_pixel(1.0, 0.0, center, radius)

    distance = math.hypot(point.x() - center.x(), point.y() - center.y())
    assert distance == radius
