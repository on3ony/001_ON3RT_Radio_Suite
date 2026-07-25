"""
core/main_window.py
Version de transition V3
"""

from pathlib import Path
from PySide6.QtCore import Qt, QTimer, QDateTime
from PySide6.QtGui import QAction, QIcon, QPixmap
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QLabel, QVBoxLayout,
    QToolBar, QStatusBar, QMenu, QGridLayout,
    QPushButton, QFrame
)

class MainWindow(QMainWindow):
    def __init__(self, application):
        super().__init__()
        self.application = application

        base = Path(__file__).resolve().parent.parent

        self.setWindowTitle(f"{application.name} V{application.version}")
        self.resize(1400, 900)

        icon = base / "assets" / "logos" / "app_icon.png"
        if icon.exists():
            self.setWindowIcon(QIcon(str(icon)))

        self._create_menu()
        self._create_toolbar()
        self._create_center(base)
        self._create_statusbar()

    def _create_menu(self):
        mb = self.menuBar()
        for name in ("Fichier","Radio","Contest","Logbook","Outils","Affichage","Aide"):
            menu = QMenu(name, self)
            menu.addAction(QAction("À venir", self))
            mb.addMenu(menu)

    def _create_toolbar(self):
        tb = QToolBar("ON3RT")
        tb.setMovable(False)
        self.addToolBar(tb)
        for txt in ("CAT","Contest","Logbook","Cluster","Propagation"):
            tb.addAction(txt)

    def _create_center(self, base):
        root = QWidget()
        layout = QVBoxLayout(root)

        info = QFrame()
        info.setStyleSheet("QFrame{border:1px solid #444;padding:6px;} QLabel{font-size:11pt;}")
        il = QGridLayout(info)
        self.lbl_radio = QLabel("IC-7300 : En attente")
        self.lbl_com = QLabel("COM : COM20")
        self.lbl_freq = QLabel("Fréquence : ---")
        self.lbl_mode = QLabel("Mode : ---")
        self.lbl_band = QLabel("Bande : ---")
        self.lbl_utc = QLabel()

        il.addWidget(self.lbl_radio,0,0)
        il.addWidget(self.lbl_com,0,1)
        il.addWidget(self.lbl_freq,1,0)
        il.addWidget(self.lbl_mode,1,1)
        il.addWidget(self.lbl_band,2,0)
        il.addWidget(self.lbl_utc,2,1)

        layout.addWidget(info)

        logo = base / "assets" / "logos" / "on3rt_logo.png"
        if logo.exists():
            img = QLabel(alignment=Qt.AlignCenter)
            img.setPixmap(QPixmap(str(logo)).scaledToHeight(180, Qt.SmoothTransformation))
            layout.addWidget(img)

        grid = QGridLayout()
        for i,name in enumerate(("Contest","Logbook","CAT","DX Cluster","Propagation","Scanner","WSJT-X","QRZ","Settings")):
            b = QPushButton(name)
            b.setMinimumHeight(55)
            grid.addWidget(b,i//3,i%3)
        layout.addLayout(grid)
        layout.addStretch()
        self.setCentralWidget(root)

        timer = QTimer(self)
        timer.timeout.connect(self._update_clock)
        timer.start(1000)
        self._update_clock()

    def _update_clock(self):
        self.lbl_utc.setText("UTC : " + QDateTime.currentDateTimeUtc().toString("yyyy-MM-dd HH:mm:ss"))

    def _create_statusbar(self):
        sb = QStatusBar()
        sb.showMessage("IC-7300 : Déconnecté | COM20 prêt | COM3 non utilisé")
        self.setStatusBar(sb)
