"""
ON3RT Radio Suite
Cartes reutilisables : StatCard (dashboard), ModuleCard (acces modules),
LivePanel (panneaux d'activite).
"""

from __future__ import annotations

from PySide6.QtCore import QPropertyAnimation, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from libraries.ui import colors
from libraries.ui.components.icons import icon as make_icon


class StatCard(QFrame):
    """Carte de valeur de tableau de bord (frequence, mode, CAT, PTT...)."""

    def __init__(
        self,
        label: str,
        value: str,
        sub: str = "",
        unit: str = "",
        accent: str = colors.BORDER_STRONG,
        value_color: str = colors.TEXT_PRIMARY,
        emphasis: bool = False,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setObjectName("StatCard")

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        bar = QFrame()
        bar.setFixedWidth(4)
        bar.setStyleSheet(f"background:{accent}; border-radius:2px;")

        body = QWidget()
        body.setStyleSheet("background: transparent;")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(18, 16, 18, 14)
        body_layout.setSpacing(6)

        lbl = QLabel(label.upper())
        lbl.setStyleSheet(
            f"background:transparent; color:{colors.TEXT_MUTED}; font-size:10.5px; font-weight:600; letter-spacing:1.4px;"
        )

        value_row = QHBoxLayout()
        value_row.setSpacing(4)
        value_row.setContentsMargins(0, 0, 0, 0)

        self._value_label = QLabel(value)
        size = 30 if emphasis else 22
        self._value_label.setStyleSheet(
            f"background:transparent; color:{value_color}; font-family:'Cascadia Mono','Consolas',monospace;"
            f" font-size:{size}px; font-weight:600;"
        )
        value_row.addWidget(self._value_label)

        if unit:
            unit_lbl = QLabel(unit)
            unit_lbl.setStyleSheet(f"background:transparent; color:{colors.TEXT_MUTED}; font-size:13px;")
            value_row.addWidget(unit_lbl, 0, Qt.AlignmentFlag.AlignBottom)
        value_row.addStretch(1)

        self._sub_label = QLabel(sub)
        self._sub_label.setStyleSheet(f"background:transparent; color:{colors.TEXT_SECONDARY}; font-size:11px;")

        body_layout.addWidget(lbl)
        body_layout.addLayout(value_row)
        body_layout.addWidget(self._sub_label)

        root.addWidget(bar)
        root.addWidget(body, 1)

        self.setStyleSheet(
            f"""
            QFrame#StatCard {{
                background: {colors.BG_CARD};
                border: 1px solid {colors.BORDER};
                border-radius: 12px;
            }}
            """
        )

    def set_value(self, text: str) -> None:
        self._value_label.setText(text)

    def set_sub(self, text: str) -> None:
        self._sub_label.setText(text)


class LivePanel(QFrame):
    """Panneau titre generique (activite WSJT-X, DX Cluster, propagation...)."""

    def __init__(self, title: str, icon_name: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("LivePanel")

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(10)

        header = QHBoxLayout()
        header.setSpacing(8)

        title_lbl = QLabel(title.upper())
        title_lbl.setStyleSheet(
            f"background:transparent; color:{colors.TEXT_SECONDARY}; font-size:11px; font-weight:600; letter-spacing:1px;"
        )

        icon_tile = QLabel()
        icon_tile.setFixedSize(26, 26)
        icon_tile.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_tile.setPixmap(make_icon(icon_name, colors.ACCENT_CYAN, 14).pixmap(14, 14))
        icon_tile.setStyleSheet(
            f"background:{colors.BG_PANEL_2}; border:1px solid {colors.BORDER}; border-radius:7px;"
        )

        header.addWidget(title_lbl)
        header.addStretch(1)
        header.addWidget(icon_tile)

        self.body = QVBoxLayout()
        self.body.setSpacing(6)

        root.addLayout(header)
        root.addLayout(self.body)
        root.addStretch(1)

        self.setStyleSheet(
            f"""
            QFrame#LivePanel {{
                background: {colors.BG_CARD};
                border: 1px solid {colors.BORDER};
                border-radius: 12px;
            }}
            """
        )


def feed_row(primary: str, secondary: str, tag: str, tag_color: str = colors.TEXT_MUTED) -> QWidget:
    """Ligne de flux compacte (indicatif / bande / valeur), style tableau."""

    row = QWidget()
    row.setStyleSheet("background: transparent;")
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 4)
    layout.setSpacing(8)

    primary_lbl = QLabel(primary)
    primary_lbl.setStyleSheet(
        f"background:transparent; color:{colors.TEXT_PRIMARY};"
        f" font-family:'Cascadia Mono','Consolas',monospace; font-size:11.5px;"
    )
    secondary_lbl = QLabel(secondary)
    secondary_lbl.setStyleSheet(
        f"color:{colors.ACCENT_CYAN}; background:rgba(34,211,238,20); border-radius:4px;"
        f" font-size:9.5px; font-weight:600; padding:2px 6px;"
    )
    tag_lbl = QLabel(tag)
    tag_lbl.setStyleSheet(
        f"background:transparent; color:{tag_color};"
        f" font-family:'Cascadia Mono','Consolas',monospace; font-size:11px;"
    )
    tag_lbl.setMinimumWidth(46)
    tag_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

    layout.addWidget(primary_lbl, 1)
    layout.addWidget(secondary_lbl)
    layout.addWidget(tag_lbl)

    underline = QFrame()
    underline.setFixedHeight(1)
    underline.setStyleSheet(f"background:{colors.BORDER};")

    wrapper = QWidget()
    wrapper.setStyleSheet("background: transparent;")
    wrapper_layout = QVBoxLayout(wrapper)
    wrapper_layout.setContentsMargins(0, 0, 0, 0)
    wrapper_layout.setSpacing(4)
    wrapper_layout.addWidget(row)
    wrapper_layout.addWidget(underline)
    return wrapper


class ModuleCard(QFrame):
    """Carte d'acces a un module de la suite (icone, titre, description, bouton)."""

    opened = Signal()

    def __init__(
        self,
        icon_name: str,
        title: str,
        description: str,
        accent: str = colors.ACCENT_CYAN,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setObjectName("ModuleCard")
        self._accent = accent
        self._icon_name = icon_name

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 18)
        root.setSpacing(10)

        self._accent_line = QFrame()
        self._accent_line.setFixedHeight(2)
        self._accent_line.setStyleSheet("background: transparent;")

        self._icon_tile = QLabel()
        self._icon_tile.setFixedSize(52, 52)
        self._icon_tile.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._set_icon_color(accent)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(
            f"background:transparent; color:{colors.TEXT_PRIMARY}; font-size:15px; font-weight:600;"
        )

        desc_lbl = QLabel(description)
        desc_lbl.setWordWrap(True)
        desc_lbl.setMinimumHeight(38)
        desc_lbl.setStyleSheet(f"background:transparent; color:{colors.TEXT_SECONDARY}; font-size:12px;")

        self._button = QPushButton("Ouvrir")
        self._button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._button.setFixedHeight(32)
        self._set_button_style(hovered=False)
        self._button.clicked.connect(self.opened.emit)

        root.addWidget(self._accent_line)
        root.addWidget(self._icon_tile)
        root.addWidget(title_lbl)
        root.addWidget(desc_lbl)
        root.addWidget(self._button, 0, Qt.AlignmentFlag.AlignLeft)

        self.setStyleSheet(
            f"""
            QFrame#ModuleCard {{
                background: {colors.BG_CARD};
                border: 1px solid {colors.BORDER};
                border-radius: 14px;
            }}
            """
        )

        self._shadow = None
        self._shadow_anim = None

    def _set_icon_color(self, color: str) -> None:
        self._icon_tile.setPixmap(make_icon(self._icon_name, color, 26).pixmap(26, 26))
        self._icon_tile.setStyleSheet(
            f"background:{colors.BG_PANEL_2}; border:1px solid {colors.BORDER_STRONG}; border-radius:12px;"
        )

    def _set_button_style(self, hovered: bool) -> None:
        if hovered:
            self._button.setStyleSheet(
                f"""
                QPushButton {{
                    background:{self._accent}; color:#04222a; border:1px solid {self._accent};
                    border-radius:7px; padding:0 16px; font-size:11.5px; font-weight:600;
                }}
                """
            )
        else:
            self._button.setStyleSheet(
                f"""
                QPushButton {{
                    background:transparent; color:{self._accent}; border:1px solid {colors.BORDER_STRONG};
                    border-radius:7px; padding:0 16px; font-size:11.5px; font-weight:600;
                }}
                """
            )

    def enterEvent(self, event) -> None:  # noqa: N802
        self.setStyleSheet(
            f"""
            QFrame#ModuleCard {{
                background: {colors.BG_CARD_HOVER};
                border: 1px solid {colors.BORDER_STRONG};
                border-radius: 14px;
            }}
            """
        )
        self._accent_line.setStyleSheet(f"background:{self._accent}; border-radius:1px;")
        self._set_icon_color("#ffffff")
        self._set_button_style(hovered=True)

        shadow = QGraphicsDropShadowEffect(self)
        shadow_color = QColor(self._accent)
        shadow_color.setAlpha(110)
        shadow.setColor(shadow_color)
        shadow.setOffset(0, 10)
        shadow.setBlurRadius(0)
        self.setGraphicsEffect(shadow)
        self._shadow = shadow

        self._shadow_anim = QPropertyAnimation(shadow, b"blurRadius", self)
        self._shadow_anim.setDuration(180)
        self._shadow_anim.setStartValue(0)
        self._shadow_anim.setEndValue(28)
        self._shadow_anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self.setStyleSheet(
            f"""
            QFrame#ModuleCard {{
                background: {colors.BG_CARD};
                border: 1px solid {colors.BORDER};
                border-radius: 14px;
            }}
            """
        )
        self._accent_line.setStyleSheet("background: transparent;")
        self._set_icon_color(self._accent)
        self._set_button_style(hovered=False)
        if self._shadow_anim is not None:
            self._shadow_anim.stop()
        self.setGraphicsEffect(None)
        self._shadow = None
        self._shadow_anim = None
        super().leaveEvent(event)
