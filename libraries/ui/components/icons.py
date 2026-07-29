"""
ON3RT Radio Suite
Fabrique d'icones vectorielles.

Jeu d'icones "outline" homogene, dessine au QPainter afin de ne
dependre d'aucune police d'icones ni ressource externe. Utilisable par
toutes les applications de la suite via ``icon(name)``.
"""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPainterPath, QPen, QPixmap

from libraries.ui.colors import TEXT_PRIMARY

_DEFAULT_SIZE = 24


def _pen(color: str, width: float) -> QPen:
    pen = QPen(QColor(color))
    pen.setWidthF(width)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    return pen


def _draw_file(p: QPainter, r: QRectF) -> None:
    path = QPainterPath()
    fold = r.width() * 0.32
    path.moveTo(r.left(), r.top())
    path.lineTo(r.right() - fold, r.top())
    path.lineTo(r.right(), r.top() + fold)
    path.lineTo(r.right(), r.bottom())
    path.lineTo(r.left(), r.bottom())
    path.closeSubpath()
    p.drawPath(path)
    p.drawLine(QPointF(r.right() - fold, r.top()), QPointF(r.right() - fold, r.top() + fold))
    p.drawLine(QPointF(r.right() - fold, r.top() + fold), QPointF(r.right(), r.top() + fold))


def _draw_antenna(p: QPainter, r: QRectF) -> None:
    cx = r.center().x()
    top = QPointF(cx, r.top())
    base_y = r.bottom()
    p.drawLine(top, QPointF(cx, base_y))
    p.drawLine(top, QPointF(r.left(), base_y))
    p.drawLine(top, QPointF(r.right(), base_y))
    p.drawLine(QPointF(r.left(), base_y), QPointF(r.right(), base_y))
    dot_r = r.width() * 0.07
    p.setBrush(QColor(p.pen().color()))
    p.drawEllipse(QPointF(cx, r.top()), dot_r, dot_r)
    p.setBrush(Qt.BrushStyle.NoBrush)


def _draw_trophy(p: QPainter, r: QRectF) -> None:
    bowl = QRectF(r.left() + r.width() * 0.18, r.top(), r.width() * 0.64, r.height() * 0.55)
    p.drawArc(bowl.toRect(), 0, -180 * 16)
    p.drawLine(bowl.topLeft(), QPointF(bowl.left(), bowl.top() + bowl.height() * 0.35))
    p.drawLine(bowl.topRight(), QPointF(bowl.right(), bowl.top() + bowl.height() * 0.35))
    handle_l = QRectF(r.left(), bowl.top() + bowl.height() * 0.05, bowl.width() * 0.26, bowl.height() * 0.6)
    handle_r = QRectF(bowl.right() - bowl.width() * 0.26, bowl.top() + bowl.height() * 0.05, bowl.width() * 0.26, bowl.height() * 0.6)
    p.drawArc(handle_l.toRect(), 90 * 16, 180 * 16)
    p.drawArc(handle_r.toRect(), -90 * 16, 180 * 16)
    stem_bottom = r.bottom() - r.height() * 0.08
    p.drawLine(QPointF(r.center().x(), bowl.bottom()), QPointF(r.center().x(), stem_bottom))
    base_w = r.width() * 0.44
    p.drawLine(QPointF(r.center().x() - base_w / 2, r.bottom()), QPointF(r.center().x() + base_w / 2, r.bottom()))
    p.drawLine(QPointF(r.center().x() - base_w / 2, r.bottom()), QPointF(r.center().x() - base_w * 0.28, stem_bottom))
    p.drawLine(QPointF(r.center().x() + base_w / 2, r.bottom()), QPointF(r.center().x() + base_w * 0.28, stem_bottom))


def _draw_book(p: QPainter, r: QRectF) -> None:
    cx = r.center().x()
    path = QPainterPath()
    path.moveTo(cx, r.top() + r.height() * 0.12)
    path.cubicTo(cx - r.width() * 0.15, r.top(), r.left(), r.top(), r.left(), r.top() + r.height() * 0.1)
    path.lineTo(r.left(), r.bottom() - r.height() * 0.05)
    path.cubicTo(r.left(), r.bottom() - r.height() * 0.12, cx - r.width() * 0.1, r.bottom() - r.height() * 0.12, cx, r.bottom())
    p.drawPath(path)
    path2 = QPainterPath()
    path2.moveTo(cx, r.top() + r.height() * 0.12)
    path2.cubicTo(cx + r.width() * 0.15, r.top(), r.right(), r.top(), r.right(), r.top() + r.height() * 0.1)
    path2.lineTo(r.right(), r.bottom() - r.height() * 0.05)
    path2.cubicTo(r.right(), r.bottom() - r.height() * 0.12, cx + r.width() * 0.1, r.bottom() - r.height() * 0.12, cx, r.bottom())
    p.drawPath(path2)
    p.drawLine(QPointF(cx, r.top() + r.height() * 0.16), QPointF(cx, r.bottom() - r.height() * 0.02))


def _draw_gear(p: QPainter, r: QRectF, teeth: int = 8) -> None:
    cx, cy = r.center().x(), r.center().y()
    radius = min(r.width(), r.height()) / 2
    inner = radius * 0.55
    tooth_len = radius * 0.24
    for i in range(teeth):
        angle = (2 * math.pi / teeth) * i
        x1 = cx + radius * math.cos(angle)
        y1 = cy + radius * math.sin(angle)
        x2 = cx + (radius + tooth_len) * math.cos(angle)
        y2 = cy + (radius + tooth_len) * math.sin(angle)
        p.drawLine(QPointF(x1, y1), QPointF(x2, y2))
    p.drawEllipse(QPointF(cx, cy), radius, radius)
    p.drawEllipse(QPointF(cx, cy), inner * 0.45, inner * 0.45)


def _draw_tool(p: QPainter, r: QRectF) -> None:
    p.drawLine(r.topLeft(), r.bottomRight())
    head_r = r.width() * 0.16
    p.drawEllipse(r.topLeft(), head_r, head_r)
    p.drawEllipse(r.bottomRight(), head_r, head_r)
    p.drawEllipse(QPointF(r.left() + r.width() * 0.3, r.top() + r.height() * 0.3), head_r * 0.55, head_r * 0.55)


def _draw_layout(p: QPainter, r: QRectF) -> None:
    gap = r.width() * 0.12
    half_w = (r.width() - gap) / 2
    half_h = (r.height() - gap) / 2
    for ox in (0, half_w + gap):
        for oy in (0, half_h + gap):
            p.drawRoundedRect(QRectF(r.left() + ox, r.top() + oy, half_w, half_h), 2, 2)


def _draw_help(p: QPainter, r: QRectF) -> None:
    p.drawEllipse(r)
    font = QFont(p.font())
    font.setPixelSize(int(r.height() * 0.62))
    font.setBold(True)
    p.setFont(font)
    p.drawText(r, Qt.AlignmentFlag.AlignCenter, "?")


def _draw_broadcast(p: QPainter, r: QRectF) -> None:
    cx = r.center().x()
    base_y = r.bottom()
    dot_r = r.width() * 0.07
    p.setBrush(QColor(p.pen().color()))
    p.drawEllipse(QPointF(cx, base_y), dot_r, dot_r)
    p.setBrush(Qt.BrushStyle.NoBrush)
    for i, frac in enumerate((0.45, 0.72, 1.0)):
        rad = r.height() * frac
        arc_rect = QRectF(cx - rad, base_y - rad, rad * 2, rad * 2)
        p.drawArc(arc_rect.toRect(), 35 * 16, 110 * 16)


def _draw_sun(p: QPainter, r: QRectF) -> None:
    cx, cy = r.center().x(), r.center().y()
    radius = min(r.width(), r.height()) * 0.28
    p.drawEllipse(QPointF(cx, cy), radius, radius)
    ray_len = r.width() * 0.16
    for i in range(8):
        angle = (2 * math.pi / 8) * i
        x1 = cx + (radius + r.width() * 0.06) * math.cos(angle)
        y1 = cy + (radius + r.width() * 0.06) * math.sin(angle)
        x2 = x1 + ray_len * math.cos(angle)
        y2 = y1 + ray_len * math.sin(angle)
        p.drawLine(QPointF(x1, y1), QPointF(x2, y2))


def _draw_radar(p: QPainter, r: QRectF) -> None:
    cx, cy = r.center().x(), r.center().y()
    for frac in (0.35, 0.65, 1.0):
        radius = min(r.width(), r.height()) / 2 * frac
        p.drawEllipse(QPointF(cx, cy), radius, radius)
    radius = min(r.width(), r.height()) / 2
    p.drawLine(QPointF(cx, cy), QPointF(cx + radius * 0.75, cy - radius * 0.75))
    dot_r = r.width() * 0.055
    p.setBrush(QColor(p.pen().color()))
    p.drawEllipse(QPointF(cx, cy), dot_r, dot_r)
    p.setBrush(Qt.BrushStyle.NoBrush)


def _draw_wave(p: QPainter, r: QRectF) -> None:
    path = QPainterPath()
    steps = 4
    step_w = r.width() / (steps * 2)
    x = r.left()
    y_top = r.top() + r.height() * 0.2
    y_bot = r.bottom() - r.height() * 0.2
    path.moveTo(x, y_bot)
    for i in range(steps):
        path.lineTo(x, y_top)
        path.lineTo(x + step_w, y_top)
        path.lineTo(x + step_w, y_bot)
        path.lineTo(x + step_w * 2, y_bot)
        x += step_w * 2
    p.drawPath(path)


def _draw_mail(p: QPainter, r: QRectF) -> None:
    p.drawRoundedRect(r, 3, 3)
    path = QPainterPath()
    path.moveTo(r.left(), r.top())
    path.lineTo(r.center().x(), r.center().y() + r.height() * 0.08)
    path.lineTo(r.right(), r.top())
    p.drawPath(path)


def _draw_arrow_right(p: QPainter, r: QRectF) -> None:
    y = r.center().y()
    p.drawLine(QPointF(r.left(), y), QPointF(r.right(), y))
    p.drawLine(QPointF(r.right() - r.width() * 0.4, r.top() + r.height() * 0.15), QPointF(r.right(), y))
    p.drawLine(QPointF(r.right() - r.width() * 0.4, r.bottom() - r.height() * 0.15), QPointF(r.right(), y))


def _draw_cpu(p: QPainter, r: QRectF) -> None:
    inset = r.width() * 0.18
    body = r.adjusted(inset, inset, -inset, -inset)
    p.drawRoundedRect(body, 2, 2)
    p.drawRoundedRect(body.adjusted(body.width() * 0.28, body.height() * 0.28, -body.width() * 0.28, -body.height() * 0.28), 1, 1)
    pin_len = inset * 0.9
    for frac in (0.25, 0.5, 0.75):
        y = body.top() + body.height() * frac
        p.drawLine(QPointF(body.left() - pin_len, y), QPointF(body.left(), y))
        p.drawLine(QPointF(body.right(), y), QPointF(body.right() + pin_len, y))
        x = body.left() + body.width() * frac
        p.drawLine(QPointF(x, body.top() - pin_len), QPointF(x, body.top()))
        p.drawLine(QPointF(x, body.bottom()), QPointF(x, body.bottom() + pin_len))


def _draw_server(p: QPainter, r: QRectF) -> None:
    gap = r.height() * 0.14
    h = (r.height() - gap) / 2
    for oy in (0, h + gap):
        rect = QRectF(r.left(), r.top() + oy, r.width(), h)
        p.drawRoundedRect(rect, 2, 2)
        dot_r = h * 0.12
        p.setBrush(QColor(p.pen().color()))
        p.drawEllipse(QPointF(rect.left() + rect.width() * 0.16, rect.center().y()), dot_r, dot_r)
        p.setBrush(Qt.BrushStyle.NoBrush)


def _draw_world(p: QPainter, r: QRectF) -> None:
    p.drawEllipse(r)
    ellipse = QRectF(r.left() + r.width() * 0.28, r.top(), r.width() * 0.44, r.height())
    p.drawEllipse(ellipse)
    p.drawLine(QPointF(r.left(), r.center().y()), QPointF(r.right(), r.center().y()))


def _draw_plug(p: QPainter, r: QRectF) -> None:
    body = QRectF(r.left() + r.width() * 0.18, r.top() + r.height() * 0.28, r.width() * 0.64, r.height() * 0.5)
    p.drawRoundedRect(body, 4, 4)
    prong_top = r.top()
    p.drawLine(QPointF(body.left() + body.width() * 0.28, body.top()), QPointF(body.left() + body.width() * 0.28, prong_top))
    p.drawLine(QPointF(body.right() - body.width() * 0.28, body.top()), QPointF(body.right() - body.width() * 0.28, prong_top))
    p.drawLine(QPointF(body.center().x(), body.bottom()), QPointF(body.center().x(), r.bottom()))


def _draw_list(p: QPainter, r: QRectF) -> None:
    rows = 3
    gap = r.height() / rows
    for i in range(rows):
        y = r.top() + gap * i + gap / 2
        dot_r = r.width() * 0.035
        p.setBrush(QColor(p.pen().color()))
        p.drawEllipse(QPointF(r.left() + dot_r, y), dot_r, dot_r)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawLine(QPointF(r.left() + dot_r * 3, y), QPointF(r.right(), y))


def _draw_signal(p: QPainter, r: QRectF) -> None:
    bars = 4
    gap = r.width() * 0.08
    bar_w = (r.width() - gap * (bars - 1)) / bars
    for i in range(bars):
        h = r.height() * ((i + 1) / bars)
        x = r.left() + i * (bar_w + gap)
        rect = QRectF(x, r.bottom() - h, bar_w, h)
        p.drawRoundedRect(rect, 1, 1)


_DRAWERS = {
    "file": _draw_file,
    "antenna": _draw_antenna,
    "trophy": _draw_trophy,
    "book": _draw_book,
    "tool": _draw_tool,
    "layout": _draw_layout,
    "help": _draw_help,
    "broadcast": _draw_broadcast,
    "sun": _draw_sun,
    "radar": _draw_radar,
    "wave": _draw_wave,
    "mail": _draw_mail,
    "arrow-right": _draw_arrow_right,
    "cpu": _draw_cpu,
    "server": _draw_server,
    "world": _draw_world,
    "plug": _draw_plug,
    "list": _draw_list,
    "signal": _draw_signal,
    "settings": lambda p, r: _draw_gear(p, r, teeth=8),
}


def pixmap(name: str, color: str = TEXT_PRIMARY, size: int = _DEFAULT_SIZE) -> QPixmap:
    """Rend une icone nommee en QPixmap transparent, couleur ``color``."""

    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pm)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(_pen(color, max(1.3, size * 0.075)))

    drawer = _DRAWERS.get(name)
    if drawer is not None:
        margin = size * 0.14
        rect = QRectF(margin, margin, size - 2 * margin, size - 2 * margin)
        drawer(painter, rect)

    painter.end()
    return pm


def icon(name: str, color: str = TEXT_PRIMARY, size: int = _DEFAULT_SIZE) -> QIcon:
    """Retourne une QIcon pour le nom donne (voir _DRAWERS pour la liste)."""

    return QIcon(pixmap(name, color, size))
