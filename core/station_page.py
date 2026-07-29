"""
core/station_page.py
--------------------------------------------------------------------
ON3RT Radio Suite V3 — page Station.

Regroupera à terme toute la configuration de la station (radio, CAT,
ports COM, paramètres, informations système, diagnostics). Pour
l'instant, cette page pose uniquement la navigation : chaque section
est un espace réservé honnête ("Bientôt disponible"), sans donnée
inventée, en attendant son câblage réel.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from libraries.ui import colors
from libraries.ui.components.icons import icon as make_icon

# Le 4e élément (module_key) reste None tant que la section n'a pas de
# fenêtre réelle à ouvrir : la carte affiche alors "Bientôt disponible"
# et n'est pas cliquable.
_SECTIONS = (
    ("cpu", "Radio", "Modèle, port et vitesse de communication.", None),
    ("antenna", "CAT", "État du pont CAT, réglages de polling.", "cat_server"),
    ("plug", "Ports COM", "Détection et affectation des ports série.", None),
    ("settings", "Paramètres", "Préférences générales de la suite.", None),
    ("server", "Informations système", "Version, environnement, journaux.", None),
    ("tool", "Diagnostics", "Tests de connexion et auto-diagnostic.", None),
)


class _SectionCard(QFrame):
    """Carte de section Station. Cliquable uniquement si `module_key` est fourni."""

    opened = Signal(str)

    def __init__(self, icon_name: str, title: str, description: str, module_key: str | None = None):
        super().__init__()
        self.setObjectName("StationSection")
        self._module_key = module_key

        if module_key is not None:
            self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.setStyleSheet(
            f"""
            QFrame#StationSection {{
                background:{colors.BG_CARD};
                border:1px solid {colors.BORDER};
                border-radius:14px;
            }}
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 18)
        layout.setSpacing(10)

        icon_tile = QLabel()
        icon_tile.setFixedSize(44, 44)
        icon_tile.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_tile.setPixmap(make_icon(icon_name, colors.ACCENT_CYAN, 22).pixmap(22, 22))
        icon_tile.setStyleSheet(
            f"background:{colors.BG_PANEL_2}; border:1px solid {colors.BORDER_STRONG}; border-radius:10px;"
        )

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(
            f"background:transparent; color:{colors.TEXT_PRIMARY}; font-size:15px; font-weight:600;"
        )

        desc_lbl = QLabel(description)
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet(f"background:transparent; color:{colors.TEXT_SECONDARY}; font-size:12px;")

        status_lbl = QLabel("Ouvrir" if module_key is not None else "Bientôt disponible")
        status_lbl.setStyleSheet(
            f"background:transparent; color:{colors.ACCENT_CYAN if module_key is not None else colors.TEXT_MUTED};"
            f" font-size:11px; font-style:{'normal' if module_key is not None else 'italic'};"
        )

        layout.addWidget(icon_tile)
        layout.addWidget(title_lbl)
        layout.addWidget(desc_lbl)
        layout.addStretch(1)
        layout.addWidget(status_lbl)

    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt override
        if self._module_key is not None and event.button() == Qt.MouseButton.LeftButton:
            self.opened.emit(self._module_key)
        super().mousePressEvent(event)


class StationPage(QWidget):
    """Page Station : configuration de la station (à venir)."""

    opened = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(f"QScrollArea {{ background:{colors.BG_VOID}; }}")

        content = QWidget()
        content.setStyleSheet(f"background:{colors.BG_VOID};")

        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(28, 26, 28, 30)
        content_layout.setSpacing(18)

        title = QLabel("STATION")
        title.setStyleSheet(
            f"background:transparent; color:{colors.TEXT_MUTED}; font-size:11.5px; font-weight:600; letter-spacing:2px;"
        )
        content_layout.addWidget(title)

        grid = QGridLayout()
        grid.setSpacing(16)
        for col in range(3):
            grid.setColumnStretch(col, 1)

        for index, (icon_name, section_title, description, module_key) in enumerate(_SECTIONS):
            card = _SectionCard(icon_name, section_title, description, module_key)
            card.opened.connect(self.opened.emit)
            grid.addWidget(card, index // 3, index % 3)

        content_layout.addLayout(grid)
        content_layout.addStretch(1)

        scroll.setWidget(content)
        outer.addWidget(scroll)
