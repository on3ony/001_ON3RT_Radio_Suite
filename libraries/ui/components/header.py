"""
ON3RT Radio Suite
Bandeau superieur (SuiteHeader) — signature visuelle de la suite.

Ce widget est concu pour etre repris a l'identique par toutes les
applications de la suite (logo, plaque operateur, cluster d'etat,
horloge, fond grille + radar).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPixmap
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from libraries.ui import colors

_MONTHS_FR = [
    "janvier", "fevrier", "mars", "avril", "mai", "juin",
    "juillet", "aout", "septembre", "octobre", "novembre", "decembre",
]

# ---------------------------------------------------------------------
# Logo officiel ON3RT : conservé dans ses couleurs d'origine (le vert
# fait partie de l'identité visuelle du logo et n'est pas recoloré),
# le reste de la charte applicative reste bleu nuit / cyan.
# ---------------------------------------------------------------------

_LOGO_FILE = (
    Path(__file__).resolve().parents[3] / "assets" / "logos" / "app_icon.png"
)


class BrandMark(QLabel):
    """Logo officiel ON3RT (image réelle, non recolorée)."""

    def __init__(self, size: int = 84, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.setScaledContents(False)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if _LOGO_FILE.is_file():
            pixmap = QPixmap(str(_LOGO_FILE))
            if not pixmap.isNull():
                pixmap = pixmap.scaled(
                    size,
                    size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self.setPixmap(pixmap)


class StationPlate(QFrame):
    """Plaque d'identification operateur (indicatif / locator / ville)."""

    def __init__(self, callsign: str, locator: str, city: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("StationPlate")
        self.setStyleSheet(
            f"""
            QFrame#StationPlate {{
                background: rgba(255, 255, 255, 4);
                border: 1px solid {colors.BORDER};
                border-radius: 10px;
            }}
            QLabel {{ background: transparent; border: none; }}
            """
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 8, 20, 8)
        layout.setSpacing(14)

        call = QLabel(callsign)
        call.setStyleSheet(
            f"background:transparent; color:{colors.TEXT_PRIMARY}; font-family:'Cascadia Mono','Consolas',monospace;"
            f"font-size:19px; font-weight:600; letter-spacing:2px;"
        )

        divider = QFrame()
        divider.setFixedSize(1, 26)
        divider.setStyleSheet(f"background:{colors.BORDER_STRONG}; border:none;")

        meta = QVBoxLayout()
        meta.setSpacing(1)
        loc = QLabel(locator)
        loc.setStyleSheet(
            f"background:transparent; color:{colors.ACCENT_CYAN}; font-family:'Cascadia Mono','Consolas',monospace;"
            f"font-size:12px; letter-spacing:1px;"
        )
        town = QLabel(city)
        town.setStyleSheet(f"background:transparent; color:{colors.TEXT_MUTED}; font-size:10.5px;")
        meta.addWidget(loc)
        meta.addWidget(town)

        layout.addWidget(call)
        layout.addWidget(divider)
        layout.addLayout(meta)


class StatusPill(QFrame):
    """Pastille d'etat (point colore + libelle)."""

    def __init__(self, label: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("StatusPill")
        self._label_text = label

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(6)

        self._dot = QLabel()
        self._dot.setFixedSize(8, 8)

        self._text = QLabel(label)
        self._text.setStyleSheet(
            f"background:transparent; color:{colors.TEXT_SECONDARY}; font-size:10.5px; letter-spacing:0.5px;"
        )

        layout.addWidget(self._dot)
        layout.addWidget(self._text)

        self.set_connected(False)

    def set_connected(self, connected: bool) -> None:
        color = colors.STATE_GREEN if connected else colors.TEXT_MUTED
        self._dot.setStyleSheet(
            f"background:{color}; border-radius:4px;"
        )
        self.setStyleSheet(
            f"""
            QFrame#StatusPill {{
                background: {colors.BG_PANEL_2};
                border: 1px solid {colors.BORDER};
                border-radius: 12px;
            }}
            """
        )


class SuiteClock(QWidget):
    """Horloge UTC + date, mise a jour chaque seconde."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)
        layout.setAlignment(Qt.AlignmentFlag.AlignRight)

        self._time = QLabel()
        self._time.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._time.setStyleSheet(
            f"background:transparent; color:{colors.TEXT_PRIMARY};"
            f" font-family:'Cascadia Mono','Consolas',monospace; font-size:16px;"
        )
        self._date = QLabel()
        self._date.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._date.setStyleSheet(f"background:transparent; color:{colors.TEXT_MUTED}; font-size:10px;")

        layout.addWidget(self._time)
        layout.addWidget(self._date)

        self._refresh()
        timer = QTimer(self)
        timer.timeout.connect(self._refresh)
        timer.start(1000)

    def _refresh(self) -> None:
        now = datetime.utcnow()
        self._time.setText(now.strftime("%H:%M:%S") + " UTC")
        self._date.setText(f"{now.day} {_MONTHS_FR[now.month - 1]} {now.year}")


class SuiteHeader(QFrame):
    """Bandeau superieur complet : logo, plaque operateur, statuts, horloge."""

    def __init__(
        self,
        callsign: str = "ON3RT",
        locator: str = "JO20EU",
        city: str = "Brussels · Belgium",
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setObjectName("SuiteHeader")
        self.setFixedHeight(108)
        self.setStyleSheet("QFrame#SuiteHeader { background: transparent; }")

        self._pills: dict[str, StatusPill] = {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        row = QWidget()
        row.setStyleSheet("background: transparent;")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(28, 0, 28, 0)
        row_layout.setSpacing(20)

        # --- Bloc de marque (gauche) ---------------------------------
        brand = QWidget()
        brand.setStyleSheet("background: transparent;")
        brand_layout = QHBoxLayout(brand)
        brand_layout.setContentsMargins(0, 0, 0, 0)
        brand_layout.setSpacing(16)
        brand_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        mark = BrandMark(84)

        # Le logo officiel affiche déjà "ON3RT" ; seul le nom du
        # produit logiciel est répété ici, pour ne pas dupliquer
        # l'identité déjà portée par l'image.
        text_col = QVBoxLayout()
        text_col.setSpacing(3)
        text_col.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        line = QLabel("RADIO SUITE")
        line.setStyleSheet(
            f"color:{colors.ACCENT_CYAN}; font-size:14px; font-weight:600; letter-spacing:5px; background:transparent;"
        )
        text_col.addWidget(line)

        brand_layout.addWidget(mark, 0, Qt.AlignmentFlag.AlignVCenter)
        brand_layout.addLayout(text_col)

        # --- Bloc de statut (droite) ----------------------------------
        status = QWidget()
        status.setStyleSheet("background: transparent;")
        status_layout = QHBoxLayout(status)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(10)
        status_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        for key, label in (("cat", "CAT"), ("radio", "IC-7300"), ("internet", "Internet"), ("wsjtx", "WSJT-X")):
            pill = StatusPill(label)
            self._pills[key] = pill
            status_layout.addWidget(pill)

        clock = SuiteClock()
        status_layout.addSpacing(6)
        status_layout.addWidget(clock)

        # --- Conteneurs de largeur egale (pour un vrai centrage) ------
        left_hint = brand.sizeHint().width()
        right_hint = status.sizeHint().width()
        side_width = max(left_hint, right_hint) + 8

        left_container = QWidget()
        left_container.setFixedWidth(side_width)
        left_container.setStyleSheet("background: transparent;")
        left_inner = QHBoxLayout(left_container)
        left_inner.setContentsMargins(0, 0, 0, 0)
        left_inner.addWidget(brand)
        left_inner.addStretch(1)

        right_container = QWidget()
        right_container.setFixedWidth(side_width)
        right_container.setStyleSheet("background: transparent;")
        right_inner = QHBoxLayout(right_container)
        right_inner.setContentsMargins(0, 0, 0, 0)
        right_inner.addStretch(1)
        right_inner.addWidget(status)

        # --- Plaque operateur (centre) ----------------------------------
        plate = StationPlate(callsign, locator, city)

        row_layout.addWidget(left_container)
        row_layout.addStretch(1)
        row_layout.addWidget(plate)
        row_layout.addStretch(1)
        row_layout.addWidget(right_container)

        outer.addWidget(row, 1)

        accent = QFrame()
        accent.setFixedHeight(2)
        accent.setStyleSheet(
            f"background: qlineargradient(x1:0, y1:0, x2:1, y2:0,"
            f" stop:0 transparent, stop:0.2 {colors.ACCENT}, stop:0.5 {colors.ACCENT_CYAN},"
            f" stop:0.8 {colors.ACCENT}, stop:1 transparent); border:none;"
        )
        outer.addWidget(accent)

    def set_status(self, key: str, connected: bool) -> None:
        """Met a jour l'etat (vert=connecte / gris=deconnecte) d'une pastille."""

        pill = self._pills.get(key)
        if pill is not None:
            pill.set_connected(connected)

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        bg = QLinearGradient(0, 0, 0, rect.height())
        bg.setColorAt(0.0, QColor("#0c1830"))
        bg.setColorAt(1.0, QColor("#08101f"))
        painter.fillRect(rect, bg)

        # Grille discrete (moitie gauche uniquement)
        grid_color = QColor(colors.ACCENT)
        grid_color.setAlpha(14)
        painter.setPen(grid_color)
        step = 48
        clip_w = int(rect.width() * 0.6)
        x = 0
        while x < clip_w:
            painter.drawLine(x, 0, x, rect.height())
            x += step
        y = 0
        while y < rect.height():
            painter.drawLine(0, y, clip_w, y)
            y += step

        # Radar discret derriere le logo
        radar_color = QColor(colors.ACCENT_CYAN)
        radar_color.setAlpha(30)
        painter.setPen(radar_color)
        cx, cy = 60, rect.height() // 2
        for radius in (40, 74, 108, 142):
            painter.drawEllipse(
                QRectF(cx - radius, cy - radius, radius * 2, radius * 2)
            )
        painter.drawLine(cx, cy, cx + 100, cy - 100)
