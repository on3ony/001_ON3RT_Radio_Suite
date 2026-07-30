"""
ON3RT Radio Suite
apps/bandmap/band_map_widget.py

Composant graphique BandMap — rendu pur, aucune dépendance à
RadioService/DXClusterService/BandManager. Ne connaît que des
primitives (nom de bande + bornes Hz, fréquence Hz, liste de spots)
fournies par l'appelant (BandMapWindow), qui reste seul responsable de
la lecture des services partagés et du filtrage par bande.

set_band() ne touche jamais à la liste des spots : c'est à l'appelant
d'appeler set_spots() avec les spots déjà filtrés pour cette bande,
juste après. Ce composant ne filtre ni ne réinterprète rien lui-même.

Contrat des spots reçus (identique à celui de DXClusterService,
jamais réinterprété ici) : chaque dict doit contenir "frequency_khz"
(int/float) pour être positionnable — un spot sans ce champ, ou avec
une valeur non numérique, est silencieusement ignoré (jamais de
position inventée). "dx_callsign", "spotter", "comment", "time_utc"
sont utilisés pour l'étiquette et l'infobulle si présents.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QToolTip, QWidget

from libraries.ui import colors

_MARGIN_LEFT = 20
_MARGIN_RIGHT = 20
_MARGIN_TOP = 34
_MARGIN_BOTTOM = 20
_AXIS_Y_RATIO = 0.5  # position verticale de l'axe, en fraction de la hauteur utile

_FREQUENCY_MARKER_HALF_HEIGHT = 14
_SPOT_MARKER_RADIUS = 4
_SPOT_HIT_RADIUS_PX = 10


class BandMapWidget(QWidget):
    """
    Échelle graphique d'une bande radioamateur : marqueur de fréquence
    radio + marqueurs de spots DX Cluster. Purement visuel — aucun
    accès à un service, aucune logique de filtrage ou de décision.
    """

    spot_double_clicked = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setMouseTracking(True)
        self.setMinimumHeight(160)

        self._band_name: str | None = None
        self._lower_hz: int | None = None
        self._upper_hz: int | None = None
        self._frequency_hz: int | None = None
        self._spots: list[dict] = []

    # ------------------------------------------------------------------
    # API publique — bande active
    # ------------------------------------------------------------------

    def set_band(self, name: str, lower_hz: int, upper_hz: int) -> None:
        self._band_name = name
        self._lower_hz = int(lower_hz)
        self._upper_hz = int(upper_hz)
        self.update()

    def clear_band(self) -> None:
        """Aucune bande active (radio déconnectée ou hors plan de bandes) : rien à afficher."""

        self._band_name = None
        self._lower_hz = None
        self._upper_hz = None
        self._frequency_hz = None
        self._spots = []
        self.update()

    # ------------------------------------------------------------------
    # API publique — fréquence radio
    # ------------------------------------------------------------------

    def set_frequency(self, frequency_hz: int | None) -> None:
        self._frequency_hz = int(frequency_hz) if frequency_hz is not None else None
        self.update()

    # ------------------------------------------------------------------
    # API publique — spots
    # ------------------------------------------------------------------

    def set_spots(self, spots: list[dict]) -> None:
        self._spots = list(spots)
        self.update()

    def add_spot(self, spot: dict) -> None:
        self._spots.append(spot)
        self.update()

    # ------------------------------------------------------------------
    # Géométrie
    # ------------------------------------------------------------------

    def _has_band(self) -> bool:
        return self._band_name is not None and self._lower_hz is not None and self._upper_hz is not None

    def _axis_rect(self) -> QRectF:
        return QRectF(
            _MARGIN_LEFT,
            _MARGIN_TOP,
            max(0.0, self.width() - _MARGIN_LEFT - _MARGIN_RIGHT),
            max(0.0, self.height() - _MARGIN_TOP - _MARGIN_BOTTOM),
        )

    def _axis_y(self) -> float:
        rect = self._axis_rect()
        return rect.top() + rect.height() * _AXIS_Y_RATIO

    def _x_for_frequency(self, frequency_hz: int) -> float | None:
        """Position horizontale d'une fréquence sur l'axe, ou None hors bande active."""

        if not self._has_band():
            return None

        span = self._upper_hz - self._lower_hz
        if span <= 0:
            return None

        rect = self._axis_rect()
        ratio = (frequency_hz - self._lower_hz) / span
        ratio = min(1.0, max(0.0, ratio))
        return rect.left() + ratio * rect.width()

    def _spot_positions(self):
        """Génère (x, spot) pour chaque spot positionnable de _spots."""

        for spot in self._spots:
            frequency_khz = spot.get("frequency_khz")
            if not isinstance(frequency_khz, (int, float)):
                continue

            frequency_hz = int(round(frequency_khz * 1000))
            x = self._x_for_frequency(frequency_hz)

            if x is None:
                continue

            yield x, spot

    def _spot_at(self, pos: QPointF) -> dict | None:
        """Retourne le spot le plus proche de `pos`, si dans la tolérance de clic, sinon None."""

        axis_y = self._axis_y()

        closest_spot = None
        closest_distance = None

        for x, spot in self._spot_positions():
            distance = ((pos.x() - x) ** 2 + (pos.y() - axis_y) ** 2) ** 0.5

            if distance <= _SPOT_HIT_RADIUS_PX and (closest_distance is None or distance < closest_distance):
                closest_distance = distance
                closest_spot = spot

        return closest_spot

    # ------------------------------------------------------------------
    # Rendu
    # ------------------------------------------------------------------

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.fillRect(self.rect(), QColor(colors.BG_PANEL))

        if not self._has_band():
            self._paint_empty_state(painter)
            painter.end()
            return

        self._paint_header(painter)
        self._paint_axis(painter)
        self._paint_frequency_marker(painter)
        self._paint_spots(painter)

        painter.end()

    def _paint_empty_state(self, painter: QPainter) -> None:
        painter.setPen(QColor(colors.TEXT_MUTED))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Aucune bande active")

    def _paint_header(self, painter: QPainter) -> None:
        painter.setPen(QColor(colors.TEXT_PRIMARY))
        label = (
            f"{self._band_name} — "
            f"{self._lower_hz / 1_000_000:.3f} - {self._upper_hz / 1_000_000:.3f} MHz"
        )
        painter.drawText(
            QRectF(_MARGIN_LEFT, 4, max(0.0, self.width() - _MARGIN_LEFT - _MARGIN_RIGHT), 22),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            label,
        )

    def _paint_axis(self, painter: QPainter) -> None:
        rect = self._axis_rect()
        axis_y = self._axis_y()

        pen = QPen(QColor(colors.BORDER_STRONG))
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawLine(QPointF(rect.left(), axis_y), QPointF(rect.right(), axis_y))

    def _paint_frequency_marker(self, painter: QPainter) -> None:
        if self._frequency_hz is None:
            return

        x = self._x_for_frequency(self._frequency_hz)
        if x is None:
            return

        axis_y = self._axis_y()

        pen = QPen(QColor(colors.ACCENT_CYAN))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawLine(
            QPointF(x, axis_y - _FREQUENCY_MARKER_HALF_HEIGHT),
            QPointF(x, axis_y + _FREQUENCY_MARKER_HALF_HEIGHT),
        )

    def _paint_spots(self, painter: QPainter) -> None:
        axis_y = self._axis_y()

        for x, spot in self._spot_positions():
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(colors.ACCENT))
            painter.drawEllipse(QPointF(x, axis_y), _SPOT_MARKER_RADIUS, _SPOT_MARKER_RADIUS)

            painter.setPen(QColor(colors.TEXT_SECONDARY))
            painter.drawText(
                QRectF(x - 30, axis_y + 8, 60, 16),
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                spot.get("dx_callsign") or "?",
            )

    # ------------------------------------------------------------------
    # Interactions utilisateur
    # ------------------------------------------------------------------

    def mouseDoubleClickEvent(self, event) -> None:
        spot = self._spot_at(event.position())

        if spot is not None:
            self.spot_double_clicked.emit(spot)

        super().mouseDoubleClickEvent(event)

    def mouseMoveEvent(self, event) -> None:
        spot = self._spot_at(event.position())

        if spot is not None:
            QToolTip.showText(event.globalPosition().toPoint(), _spot_tooltip(spot), self)
        else:
            QToolTip.hideText()

        super().mouseMoveEvent(event)


def _spot_tooltip(spot: dict) -> str:
    """Texte d'infobulle pour un spot — n'affiche que les champs présents, jamais inventés."""

    dx_callsign = spot.get("dx_callsign") or "--"

    frequency_khz = spot.get("frequency_khz")
    frequency_text = f"{frequency_khz:.1f} kHz" if isinstance(frequency_khz, (int, float)) else "--"

    spotter = spot.get("spotter") or "--"
    time_utc = spot.get("time_utc") or "--"
    comment = spot.get("comment") or ""

    lines = [
        f"{dx_callsign} — {frequency_text}",
        f"Spotter : {spotter}   {time_utc}Z",
    ]

    if comment:
        lines.append(comment)

    return "\n".join(lines)
