"""
ON3RT Radio Suite
Fenêtre de base commune à toutes les applications.
"""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QLabel,
    QMainWindow,
    QVBoxLayout,
    QWidget,
    QHBoxLayout,
    QSizePolicy,
)


class BaseWindow(QMainWindow):
    """
    Fenêtre principale commune.
    """

    def __init__(self, title: str, subtitle: str = ""):
        super().__init__()

        self.setWindowTitle(f"ON3RT Radio Suite - {title}")
        self.resize(1000, 700)
        self.setMinimumSize(900, 600)

        self._build_ui(title, subtitle)

        self.statusBar().showMessage("Prêt")

    def _build_ui(self, title: str, subtitle: str):

        central = QWidget()
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(20)

        # ------------------------------------------------------------------
        # Entête
        # ------------------------------------------------------------------

        header = QHBoxLayout()

        logo = QLabel()

        logo_file = (
            Path(__file__).resolve().parents[2]
            / "assets"
            / "images"
            / "logo.png"
        )

        if logo_file.exists():
            pix = QPixmap(str(logo_file))
            logo.setPixmap(
                pix.scaled(
                    64,
                    64,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
            )

        header.addWidget(logo)

        titles = QVBoxLayout()

        lbl_title = QLabel(title.upper())
        lbl_title.setObjectName("Title")

        lbl_sub = QLabel(subtitle)
        lbl_sub.setObjectName("Subtitle")

        titles.addWidget(lbl_title)

        if subtitle:
            titles.addWidget(lbl_sub)

        header.addLayout(titles)

        header.addStretch()

        root.addLayout(header)

        # ------------------------------------------------------------------
        # Zone de travail
        # ------------------------------------------------------------------

        self.content = QWidget()

        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setSpacing(12)
        self.content_layout.setContentsMargins(0, 0, 0, 0)

        root.addWidget(self.content)

        # ------------------------------------------------------------------
        # Barre d'état
        # ------------------------------------------------------------------

        self.statusBar().showMessage("ON3RT Radio Suite")