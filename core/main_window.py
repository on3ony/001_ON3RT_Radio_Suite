"""
core/main_window.py
Version V3 - ouverture du module Contest
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
        self.buttons = {}
        base = Path(__file__).resolve().parent.parent
        self.setWindowTitle(f"{application.name} V{application.version}")
        self.resize(1400,900)
        icon = base/"assets"/"logos"/"app_icon.png"
        if icon.exists():
            self.setWindowIcon(QIcon(str(icon)))
        self._create_menu()
        self._create_toolbar()
        self._create_center(base)
        self._create_statusbar()

    def _create_menu(self):
        mb=self.menuBar()
        for n in ("Fichier","Radio","Contest","Logbook","Outils","Affichage","Aide"):
            m=QMenu(n,self)
            m.addAction(QAction("À venir",self))
            mb.addMenu(m)

    def _create_toolbar(self):
        tb=QToolBar("ON3RT")
        tb.setMovable(False)
        self.addToolBar(tb)

    def _open_contest(self):
        from apps.contest.window import ContestWindow
        if not self.application.show_module("contest"):
            w=ContestWindow()
            self.application.register_module("contest", w)
            w.show()

    def _create_center(self, base):
        root=QWidget(); layout=QVBoxLayout(root)
        grid=QGridLayout()
        names=("Contest","Logbook","CAT","DX Cluster","Propagation","Scanner","WSJT-X","QRZ","Settings")
        for i,name in enumerate(names):
            b=QPushButton(name)
            b.setMinimumHeight(55)
            if name=="Contest":
                b.clicked.connect(self._open_contest)
            grid.addWidget(b,i//3,i%3)
        layout.addLayout(grid)
        self.setCentralWidget(root)
        t=QTimer(self); t.timeout.connect(self._update_clock); t.start(1000)

    def _update_clock(self): pass
    def _create_statusbar(self):
        self.setStatusBar(QStatusBar())
