#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=========================================================
ON3RT Radio Suite
Dashboard — Widgets — SMeterBar
=========================================================
Description :
    Barre horizontale animée représentant l'intensité du signal reçu,
    style ON3RT Dark, avec l'échelle graduée d'un vrai S-mètre de
    transceiver (repères S1/S3/S5/S7/S9/+20/+40/+60 au-dessus de la
    barre). Consomme UNIQUEMENT smeter_level (entier brut 0-255, la
    donnée de référence exposée par apps/cat_server/radio_service.py --
    voir CATEngine.read_smeter()/libraries/cat/smeter.py) -- jamais le
    texte "smeter" ("S9" etc.), qui reste une simple étiquette affichée
    à côté par le panneau appelant (RadioPanel), sans lien avec ce widget.

    Réutilisable tel quel par tout futur panneau ayant besoin d'un
    indicateur de niveau visuel (ex. panneau "Mesures"/"Instrumentation"
    évoqué pour le SWR/la puissance instantanée) -- ne connaît rien du
    CAT, de la radio, ni de la Suite au-delà de sa palette de couleurs.

    Échelle visuelle volontairement recadrée sur [S1, S9+60dB] plutôt
    que sur [0, 255] (2026-08-02, ajustement demandé) : le tracé
    (graduations ET remplissage) commence exactement au repère S1 et se
    termine exactement au repère +60 -- un niveau en dessous de S1 (pas
    de signal significatif) laisse la barre vide, jamais un
    "avant-repère" visuel qui ne correspond à rien sur l'échelle. Une
    marge fixe (_LABEL_HALF_WIDTH) est réservée de chaque côté pour que
    le texte des repères d'extrémité (S1, +60) ne déborde jamais du
    widget -- voir _scale_rect().

    Répartition de largeur délibérément inégale entre les deux moitiés
    de l'échelle (_S9_BOUNDARY_FRACTION, 2026-08-02, ajustement demandé) :
    S9/+20/+40/+60 (la partie la plus lue -- signal fort) reçoivent
    plus de place que S1/S3/S5/S7, purement pour l'aisance de lecture --
    ce n'est PAS une proportion CI-V, seulement où le point S9 est
    positionné à l'écran. _level_to_fraction() reste continue et
    définie pour n'importe quel niveau, pas seulement les 8 repères.

    Animation : chaque appel à set_target_level() lance une
    QPropertyAnimation depuis la valeur actuellement affichée (jamais
    depuis 0) vers la nouvelle cible, avec une courbe d'accélération
    douce (OutCubic) -- jamais un setValue() direct qui ferait sauter
    la barre d'un état à l'autre sans transition. La propriété animée
    ne déclenche qu'un repaint (self.update()), jamais un recalcul de
    layout : c'est ce qui garantit l'absence de scintillement.

    Couleur : verte de S0 à S9 (frontière officiellement documentée par
    Icom, niveau 120 -- voir smeter.py), puis dégradé PROGRESSIF (jamais
    de coupure nette) jaune -> orange -> rouge au-delà, jusqu'à S9+60dB
    (niveau 241, également documenté) -- vert/rouge reprennent les
    teintes déjà associées ailleurs dans la Suite (vert=bon signal,
    rouge=très fort/alarme). Le dégradé est ancré sur l'étendue FIXE de
    la zone au-delà de S9 (jamais sur la largeur du remplissage
    courant), points d'arrêt alignés exactement sur les graduations
    +20/+40/+60.

    Graduations : S1/S3/S5/S7/S9/+20/+40/+60, avec leur texte, affichées
    au-dessus de la barre (convention d'un vrai S-mètre : l'échelle
    surplombe l'indicateur de niveau).
=========================================================
"""

from PySide6.QtCore import QEasingCurve, QPointF, QPropertyAnimation, QRectF, Qt, Property
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

# Points d'ancrage officiellement documentés (guide CI-V IC-7300MK2, voir
# libraries/cat/smeter.py) -- jamais des valeurs supposées.
_S9_LEVEL = 120
_S9_PLUS_60DB_LEVEL = 241

# Échelle visuelle : [S1, S9+60dB], jamais [0, 255] -- voir docstring du
# module. S1 vaut 1/9 de la distance 0->S9 (repli standard de S-mètre,
# comme SMeterManager.level_to_s_display).
_SCALE_MIN_LEVEL = _S9_LEVEL * (1 / 9)
_SCALE_MAX_LEVEL = _S9_PLUS_60DB_LEVEL

# Part de la largeur totale allouée à la zone S1->S9 ; le reste
# (S9->+60) en profite davantage -- voir docstring du module, purement
# esthétique, jamais une proportion CI-V.
_S9_BOUNDARY_FRACTION = 0.35

# Graduations affichées, avec leur texte et le niveau CI-V réel qu'elles
# représentent -- voir docstring du module.
_LOW_TICKS = tuple((f"S{n}", _S9_LEVEL * n / 9) for n in (1, 3, 5, 7, 9))
_HIGH_TICKS = tuple(
    (f"+{n}", _S9_LEVEL + n / 60 * (_S9_PLUS_60DB_LEVEL - _S9_LEVEL))
    for n in (20, 40, 60)
)

_TRACK_COLOR = QColor("#0d1a32")
_BORDER_COLOR = QColor("#1a2c4d")
_FILL_COLOR_GREEN = QColor("#00ff88")
_FILL_COLOR_YELLOW = QColor("#ffe066")
_FILL_COLOR_ORANGE = QColor("#ffb454")
_FILL_COLOR_RED = QColor("#ff6666")
_TICK_LINE_COLOR = QColor("#7d92b8")
_TICK_LABEL_COLOR = QColor("#9beeff")

# Relief très discret (reflet clair en haut, ombre légère en bas) --
# évoque le boîtier d'un vrai S-mètre plutôt qu'une simple barre de
# progression plate (2026-08-02, ajustement demandé). Toujours visible,
# même barre vide -- c'est un trait du boîtier, pas du remplissage.
_RELIEF_HIGHLIGHT_COLOR = QColor(255, 255, 255, 28)
_RELIEF_SHADOW_COLOR = QColor(0, 0, 0, 40)

_BAR_HEIGHT = 7
_SCALE_HEIGHT = 14
_SCALE_GAP = 2
_LABEL_HALF_WIDTH = 14  # réserve de marge pour que S1/+60 ne débordent jamais du widget

_ANIMATION_DURATION_MS = 220


def _level_to_fraction(level: float) -> float:
    """
    Position 0.0-1.0 sur l'échelle visuelle [S1, S9+60dB] -- voir
    docstring du module. Deux segments linéaires distincts (S1->S9 puis
    S9->+60dB), chacun proportionnel au NIVEAU réel à l'intérieur de sa
    moitié, mais la largeur allouée à chaque moitié est délibérément
    inégale (_S9_BOUNDARY_FRACTION) -- continue et bien définie pour
    n'importe quel niveau, pas seulement les 8 repères affichés.
    """

    if level <= _S9_LEVEL:
        span = _S9_LEVEL - _SCALE_MIN_LEVEL
        local = max(0.0, min(1.0, (level - _SCALE_MIN_LEVEL) / span))
        return local * _S9_BOUNDARY_FRACTION

    span = _SCALE_MAX_LEVEL - _S9_LEVEL
    local = max(0.0, min(1.0, (level - _S9_LEVEL) / span))
    return _S9_BOUNDARY_FRACTION + local * (1.0 - _S9_BOUNDARY_FRACTION)


class SMeterBar(QWidget):
    """Voir docstring du module pour l'ensemble des garanties fournies."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self._level = 0.0

        self.setMinimumHeight(_SCALE_HEIGHT + _SCALE_GAP + _BAR_HEIGHT)
        self.setMinimumWidth(140)

        self._tick_font = QFont()
        self._tick_font.setPointSize(8)

        self._tick_pen = QPen(_TICK_LINE_COLOR)
        self._tick_pen.setWidthF(1.4)

        self._animation = QPropertyAnimation(self, b"level", self)
        self._animation.setDuration(_ANIMATION_DURATION_MS)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    # ------------------------------------------------------------------
    # Propriété animée -- ne déclenche qu'un repaint, jamais un layout
    # ------------------------------------------------------------------

    def _get_level(self) -> float:
        return self._level

    def _set_level(self, value: float) -> None:
        self._level = value
        self.update()

    level = Property(float, _get_level, _set_level)

    # ------------------------------------------------------------------
    # API publique
    # ------------------------------------------------------------------

    def set_target_level(self, raw_level) -> None:
        """
        Anime la barre depuis sa valeur actuellement affichée vers
        raw_level (0-255, smeter_level -- voir docstring du module).
        raw_level=None (aucune lecture disponible) anime vers 0, jamais
        une valeur inventée.
        """

        if raw_level is None:
            target = 0.0
        else:
            target = max(0.0, min(255.0, float(raw_level)))

        self._animation.stop()
        self._animation.setStartValue(self._level)
        self._animation.setEndValue(target)
        self._animation.start()

    # ------------------------------------------------------------------
    # Rendu
    # ------------------------------------------------------------------

    def _scale_rect(self) -> QRectF:
        """
        Zone utile pour les positions de graduation/barre -- le widget
        complet moins la marge réservée aux libellés d'extrémité (voir
        docstring du module, _LABEL_HALF_WIDTH).
        """

        return QRectF(self.rect()).adjusted(_LABEL_HALF_WIDTH, 0, -_LABEL_HALF_WIDTH, 0)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        scale_rect = self._scale_rect()
        s9_x = scale_rect.left() + scale_rect.width() * _level_to_fraction(_S9_LEVEL)

        self._paint_scale(painter, scale_rect)

        bar_rect = QRectF(
            scale_rect.left() + 0.5,
            scale_rect.top() + _SCALE_HEIGHT + _SCALE_GAP,
            scale_rect.width() - 1,
            _BAR_HEIGHT,
        )
        self._paint_bar(painter, bar_rect, s9_x)

    def _paint_scale(self, painter, scale_rect) -> None:
        painter.setFont(self._tick_font)

        for label, level in _LOW_TICKS + _HIGH_TICKS:
            tick_x = scale_rect.left() + scale_rect.width() * _level_to_fraction(level)
            self._draw_tick(painter, scale_rect, tick_x, label)

    def _draw_tick(self, painter, scale_rect, tick_x, label) -> None:
        text_rect = QRectF(tick_x - _LABEL_HALF_WIDTH, scale_rect.top(), 2 * _LABEL_HALF_WIDTH, _SCALE_HEIGHT - 3)
        painter.setPen(_TICK_LABEL_COLOR)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, label)

        line_top = scale_rect.top() + _SCALE_HEIGHT - 2
        line_bottom = scale_rect.top() + _SCALE_HEIGHT + _SCALE_GAP
        painter.setPen(self._tick_pen)
        painter.drawLine(QPointF(tick_x, line_top), QPointF(tick_x, line_bottom))

    def _paint_bar(self, painter, rect, s9_x) -> None:
        radius = rect.height() / 2.0

        track_path = QPainterPath()
        track_path.addRoundedRect(rect, radius, radius)

        painter.setPen(_BORDER_COLOR)
        painter.setBrush(_TRACK_COLOR)
        painter.drawPath(track_path)

        ratio = _level_to_fraction(self._level)
        fill_width = rect.width() * ratio

        painter.setClipPath(track_path)
        painter.setPen(Qt.PenStyle.NoPen)

        if fill_width > 0:
            s9_offset = max(0.0, s9_x - rect.left())

            low_width = min(fill_width, s9_offset)
            if low_width > 0:
                painter.setBrush(_FILL_COLOR_GREEN)
                painter.drawRect(QRectF(rect.left(), rect.top(), low_width, rect.height()))

            if fill_width > s9_offset:
                # Dégradé ancré sur l'étendue FIXE de la zone au-delà de
                # S9 (jamais sur fill_width), points d'arrêt alignés sur
                # les graduations +20/+40/+60 -- voir docstring du module.
                gradient = QLinearGradient(rect.left() + s9_offset, 0, rect.right(), 0)
                gradient.setColorAt(0.0, _FILL_COLOR_GREEN)
                gradient.setColorAt(1 / 3, _FILL_COLOR_YELLOW)
                gradient.setColorAt(2 / 3, _FILL_COLOR_ORANGE)
                gradient.setColorAt(1.0, _FILL_COLOR_RED)

                painter.setBrush(gradient)
                painter.drawRect(QRectF(rect.left() + s9_offset, rect.top(), fill_width - s9_offset, rect.height()))

        self._paint_relief(painter, rect)

        painter.setClipping(False)

    def _paint_relief(self, painter, rect) -> None:
        """Voir docstring du module (_RELIEF_*) -- dessiné par-dessus fond ET remplissage, appelant a déjà posé le clip arrondi."""

        highlight_height = rect.height() * 0.35
        painter.setBrush(_RELIEF_HIGHLIGHT_COLOR)
        painter.drawRect(QRectF(rect.left(), rect.top(), rect.width(), highlight_height))

        shadow_height = rect.height() * 0.25
        painter.setBrush(_RELIEF_SHADOW_COLOR)
        painter.drawRect(QRectF(rect.left(), rect.bottom() - shadow_height, rect.width(), shadow_height))
