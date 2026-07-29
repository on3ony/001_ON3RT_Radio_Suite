"""
ON3RT Radio Suite
Barre de navigation latérale (Sidebar) — Dashboard / Applications / Station.

Composant partagé, conçu pour être repris à l'identique par toutes les
applications de la suite lors de l'harmonisation graphique (même
palette, mêmes icônes, même comportement que le reste de la charte).
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QButtonGroup, QPushButton, QVBoxLayout, QWidget

from libraries.ui import colors
from libraries.ui.components.icons import icon as make_icon

# (clé, libellé, icône)
PAGES = (
    ("dashboard", "Dashboard", "signal"),
    ("applications", "Applications", "layout"),
    ("station", "Station", "antenna"),
)


class _NavButton(QPushButton):
    def __init__(self, key: str, label: str, icon_name: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.key = key
        self._icon_name = icon_name

        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setText(f"  {label}")
        self.setFixedHeight(44)
        self.setIconSize(self.iconSize() * 1)
        self.setIcon(make_icon(icon_name, colors.TEXT_SECONDARY, 18))
        self._apply_style(False)
        self.toggled.connect(self._apply_style)

    def _apply_style(self, checked: bool) -> None:
        self.setIcon(
            make_icon(self._icon_name, colors.TEXT_PRIMARY if checked else colors.TEXT_SECONDARY, 18)
        )
        if checked:
            self.setStyleSheet(
                f"""
                QPushButton {{
                    text-align:left; padding-left:16px;
                    background:{colors.BG_CARD}; color:{colors.TEXT_PRIMARY};
                    border:none; border-left:3px solid {colors.ACCENT_CYAN};
                    border-radius:0px; font-size:13px; font-weight:600;
                }}
                """
            )
        else:
            self.setStyleSheet(
                f"""
                QPushButton {{
                    text-align:left; padding-left:16px;
                    background:transparent; color:{colors.TEXT_SECONDARY};
                    border:none; border-left:3px solid transparent;
                    border-radius:0px; font-size:13px; font-weight:500;
                }}
                QPushButton:hover {{
                    background:{colors.BG_CARD}; color:{colors.TEXT_PRIMARY};
                }}
                """
            )


class Sidebar(QWidget):
    """Navigation verticale Dashboard / Applications / Station."""

    page_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedWidth(200)
        self.setStyleSheet(
            f"background:{colors.BG_HEADER}; border-right:1px solid {colors.BORDER};"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 18, 0, 0)
        layout.setSpacing(2)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._buttons: dict[str, _NavButton] = {}

        for key, label, icon_name in PAGES:
            button = _NavButton(key, label, icon_name)
            self._group.addButton(button)
            self._buttons[key] = button
            button.clicked.connect(lambda _checked, k=key: self.page_changed.emit(k))
            layout.addWidget(button)

        layout.addStretch(1)

        self._buttons[PAGES[0][0]].setChecked(True)

    def set_active(self, key: str) -> None:
        button = self._buttons.get(key)
        if button is not None:
            button.setChecked(True)
