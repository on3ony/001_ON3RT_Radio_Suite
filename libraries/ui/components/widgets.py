"""
ON3RT Radio Suite
Mini-widgets graphiques : sparkline, jauge en arc, S-metre.

Composants legers (QPainter) destines a donner une impression
d'application "vivante" dans les tableaux de bord de la suite.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from libraries.ui import colors


class Sparkline(QWidget):
    """Courbe compacte (ex: activite de decodage WSJT-X)."""

    def __init__(self, values: list[float] | None = None, color: str = colors.ACCENT_CYAN, parent: QWidget | None = None):
        super().__init__(parent)
        self._values = values or []
        self._color = color
        self.setMinimumHeight(46)
        self.setMaximumHeight(46)

    def set_values(self, values: list[float]) -> None:
        self._values = values
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        if len(self._values) < 2:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(2, 4, -2, -4)
        lo, hi = min(self._values), max(self._values)
        span = (hi - lo) or 1.0

        step_x = rect.width() / (len(self._values) - 1)
        points = []
        for i, v in enumerate(self._values):
            x = rect.left() + i * step_x
            y = rect.bottom() - ((v - lo) / span) * rect.height()
            points.append((x, y))

        path = QPainterPath()
        path.moveTo(*points[0])
        for x, y in points[1:]:
            path.lineTo(x, y)

        pen = QPen(QColor(self._color))
        pen.setWidthF(2.0)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawPath(path)

        last_x, last_y = points[-1]
        painter.setBrush(QColor(self._color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QRectF(last_x - 3, last_y - 3, 6, 6))


class ArcGauge(QWidget):
    """Jauge en arc (ex: K-index, SFI)."""

    def __init__(
        self,
        label: str,
        value: float,
        maximum: float = 9.0,
        color: str = colors.ACCENT_CYAN,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._label = label
        self._value = value
        self._maximum = maximum
        self._color = color
        self.setFixedSize(100, 94)

    def set_value(self, value: float) -> None:
        self._value = value
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        diameter = max(40.0, min(w - 16, 2 * (h - 40)))
        arc_rect = QRectF((w - diameter) / 2, 4, diameter, diameter)

        pen_bg = QPen(QColor(colors.BORDER))
        pen_bg.setWidthF(6)
        pen_bg.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen_bg)
        painter.drawArc(arc_rect, 0 * 16, 180 * 16)

        frac = max(0.0, min(1.0, self._value / self._maximum if self._maximum else 0))
        pen_fg = QPen(QColor(self._color))
        pen_fg.setWidthF(6)
        pen_fg.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen_fg)
        painter.drawArc(arc_rect, 0 * 16, int(180 * frac * 16))

        painter.setPen(QColor(colors.TEXT_PRIMARY))
        value_font = QFont(painter.font())
        value_font.setPointSizeF(11)
        value_font.setBold(True)
        painter.setFont(value_font)
        value_rect = QRectF(0, arc_rect.top() + arc_rect.height() / 2 + 2, w, 20)
        painter.drawText(value_rect, Qt.AlignmentFlag.AlignCenter, str(self._value).rstrip("0").rstrip(".") if isinstance(self._value, float) else str(self._value))

        painter.setPen(QColor(colors.TEXT_MUTED))
        label_font = QFont(painter.font())
        label_font.setPointSizeF(7.5)
        label_font.setBold(False)
        painter.setFont(label_font)
        label_rect = QRectF(0, value_rect.bottom() + 2, w, 14)
        painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, self._label.upper())


class SMeter(QWidget):
    """S-metre classique (S1..S9, +10/+20/+30/+40 dB)."""

    _TICKS = ["S1", "3", "5", "7", "9", "+10", "+20", "+30", "+40"]

    def __init__(self, value: float = 0.0, parent: QWidget | None = None):
        super().__init__(parent)
        self._value = value  # 0..13 (9 crans S + 4 crans dB)
        self.setMinimumHeight(54)

    def set_value(self, value: float) -> None:
        self._value = max(0.0, min(13.0, value))
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(2, 18, -2, -16)
        segments = len(self._TICKS)
        gap = 3
        seg_w = (rect.width() - gap * (segments - 1)) / segments

        for i in range(segments):
            x = rect.left() + i * (seg_w + gap)
            seg_rect = QRectF(x, rect.top(), seg_w, rect.height())
            filled = (i + 1) <= self._value
            if filled:
                color = QColor(colors.STATE_RED if i >= 5 else colors.ACCENT_CYAN)
            else:
                color = QColor(colors.BG_PANEL_2)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawRoundedRect(seg_rect, 2, 2)

            painter.setPen(QColor(colors.TEXT_MUTED))
            tick_font = QFont(painter.font())
            tick_font.setPointSizeF(7)
            painter.setFont(tick_font)
            painter.drawText(
                QRectF(x - 4, rect.bottom() + 2, seg_w + 8, 14),
                Qt.AlignmentFlag.AlignCenter,
                self._TICKS[i],
            )

        painter.setPen(QColor(colors.TEXT_PRIMARY))
        title_font = QFont(painter.font())
        title_font.setPointSizeF(8)
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.drawText(
            QRectF(rect.left(), 0, rect.width(), 16),
            Qt.AlignmentFlag.AlignLeft,
            "S-METRE",
        )
