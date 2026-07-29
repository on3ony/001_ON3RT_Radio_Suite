"""
core/main_window.py
--------------------------------------------------------------------
ON3RT Radio Suite V3 — fenetre principale

Identite graphique commune a toute la suite : bandeau signature (logo
officiel ON3RT), navigation Dashboard / Applications / Station, barre
d'etat. Cette fenetre sert de reference visuelle a toutes les autres
applications (Contest, Radio Control, Logbook, ...).
"""

from pathlib import Path

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMenuBar,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from libraries.ui import colors
from libraries.ui.components.cards import ModuleCard
from libraries.ui.components.header import SuiteHeader
from libraries.ui.components.icons import icon as make_icon
from libraries.ui.components.sidebar import Sidebar
from libraries.ui.components.statusbar import SuiteStatusBar

from apps.dashboard.dashboard_page import DashboardPage
from core.station_page import StationPage

_MENU_ENTRIES = (
    ("Fichier", "file"),
    ("Radio", "antenna"),
    ("Contest", "trophy"),
    ("Logbook", "book"),
    ("Outils", "tool"),
    ("Affichage", "layout"),
    ("Aide", "help"),
)

_MODULES = (
    ("trophy", "Contest", "Journal de concours, calcul de points, export Cabrillo.", "contest"),
    ("antenna", "Radio Control", "Pilotage CAT direct, VFO, filtres, préamplis.", "radio_control"),
    ("book", "Logbook", "Journal général des contacts et import ADIF.", "logbook"),
    ("broadcast", "DX Cluster", "Flux de spots en direct, filtres par bande et mode.", "dxcluster"),
    ("sun", "Propagation", "Indices solaires, prévisions HF en temps réel.", "propagation"),
    ("signal", "Banque de fréquences", "Fréquences de référence, plan de bandes, favoris.", "frequency_bank"),
    ("radar", "Scanner", "Balayage de fréquences et mémoires programmables.", "scanner"),
    ("wave", "WSJT-X Bridge", "Pont UDP vers WSJT-X, décodage et logging auto.", "wsjtx"),
    ("mail", "QSL Manager", "Suivi des cartes QSL, envoi et bureau QSL.", "qsl"),
    ("settings", "Settings", "Préférences radio, thème, comptes et intégrations.", "settings"),
)

# Modules disposant deja d'une fenetre reelle dans le projet.
_IMPLEMENTED = {"contest", "radio_control", "logbook", "cat_server", "frequency_bank"}


class MainWindow(QMainWindow):
    def __init__(self, application):
        super().__init__()
        self.application = application

        base = Path(__file__).resolve().parent.parent

        self.setWindowTitle(f"{application.name} V{application.version}")
        self.resize(1500, 950)
        self.setMinimumSize(1180, 760)

        icon_file = base / "assets" / "logos" / "app_icon.png"
        if icon_file.exists():
            self.setWindowIcon(QIcon(str(icon_file)))

        self._build_top()
        self._build_center()
        self._build_statusbar()

        # Le Dashboard est la seule source d'état CAT/radio réelle pour
        # l'instant : le header et la barre d'état s'y abonnent pour ne
        # jamais afficher un statut "connecté" fictif.
        self.dashboard_page.live_service.state_changed.connect(self._on_live_state)
        self._on_live_state(self.dashboard_page.live_service.state())

    # ------------------------------------------------------------------
    # Bandeau + menu
    # ------------------------------------------------------------------

    def _build_top(self) -> None:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        station = self.application.station_service
        self.header = SuiteHeader(callsign=station.callsign, locator=station.locator, city=station.qth)
        self.header.set_status("cat", False)
        self.header.set_status("radio", False)
        self.header.set_status("internet", False)
        self.header.set_status("wsjtx", False)

        layout.addWidget(self.header)
        layout.addWidget(self._build_menu())

        self.setMenuWidget(container)

    def _build_menu(self) -> QMenuBar:
        bar = QMenuBar()
        bar.setStyleSheet(
            f"""
            QMenuBar {{
                background:{colors.BG_PANEL_2};
                border-bottom:1px solid {colors.BORDER};
                padding:4px 22px;
            }}
            QMenuBar::item {{
                padding:7px 14px;
                border-radius:6px;
                color:{colors.TEXT_SECONDARY};
            }}
            QMenuBar::item:selected {{
                background:{colors.BG_CARD};
                color:{colors.TEXT_PRIMARY};
            }}
            """
        )
        for name, icon_name in _MENU_ENTRIES:
            menu = QMenu(name, bar)
            menu.addAction(QAction("À venir", self))
            action = bar.addMenu(menu)
            action.setIcon(make_icon(icon_name, colors.TEXT_SECONDARY, 16))
        return bar

    # ------------------------------------------------------------------
    # Zone centrale : navigation Dashboard / Applications / Station
    # ------------------------------------------------------------------

    def _build_center(self) -> None:
        central = QWidget()
        central.setStyleSheet(f"background:{colors.BG_VOID};")

        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.sidebar = Sidebar()
        self.sidebar.page_changed.connect(self._go_to_page)

        self.stack = QStackedWidget()

        self.dashboard_page = DashboardPage(
            dxcluster_service=self.application.dxcluster_service,
            weather_service=self.application.weather_service,
            propagation_service=self.application.propagation_service,
        )
        self.applications_page = self._build_applications_page()
        self.station_page = StationPage()
        self.station_page.opened.connect(lambda key: self._open_module(key, "CAT Server"))

        self.stack.addWidget(self.dashboard_page)
        self.stack.addWidget(self.applications_page)
        self.stack.addWidget(self.station_page)

        root.addWidget(self.sidebar)
        root.addWidget(self.stack, 1)

        self.setCentralWidget(central)

    def _go_to_page(self, key: str) -> None:
        index = {"dashboard": 0, "applications": 1, "station": 2}.get(key, 0)
        self.stack.setCurrentIndex(index)

    # ------------------------------------------------------------------
    # Page Applications — grille d'accès aux modules
    # ------------------------------------------------------------------

    def _build_applications_page(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(f"QScrollArea {{ background:{colors.BG_VOID}; }}")

        content = QWidget()
        content.setStyleSheet(f"background:{colors.BG_VOID};")

        outer = QVBoxLayout(content)
        outer.setContentsMargins(28, 26, 28, 30)
        outer.setSpacing(14)

        outer.addWidget(self._section_head("Applications", f"{len(_MODULES)} modules"))
        outer.addLayout(self._build_module_cards())
        outer.addStretch(1)

        scroll.setWidget(content)
        return scroll

    @staticmethod
    def _section_head(title: str, subtitle: str) -> QWidget:
        row = QWidget()
        row.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)

        title_lbl = QLabel(title.upper())
        title_lbl.setStyleSheet(
            f"background:transparent; color:{colors.TEXT_MUTED}; font-size:11.5px; font-weight:600; letter-spacing:2px;"
        )
        sub_lbl = QLabel(subtitle)
        sub_lbl.setStyleSheet(f"background:transparent; color:{colors.TEXT_MUTED}; font-size:11px;")

        layout.addWidget(title_lbl)
        layout.addStretch(1)
        layout.addWidget(sub_lbl)
        return row

    def _build_module_cards(self) -> QGridLayout:
        grid = QGridLayout()
        grid.setSpacing(16)
        for col in range(3):
            grid.setColumnStretch(col, 1)

        for index, (icon_name, title, desc, key) in enumerate(_MODULES):
            card = ModuleCard(icon_name, title, desc, accent=colors.ACCENT_CYAN)
            card.opened.connect(lambda k=key, t=title: self._open_module(k, t))
            grid.addWidget(card, index // 3, index % 3)
        return grid

    # ------------------------------------------------------------------
    # Barre d'etat
    # ------------------------------------------------------------------

    def _build_statusbar(self) -> None:
        self._status_bar = SuiteStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_bar.set_cat(False)
        self._status_bar.set_radio(False, "Radio")
        self._status_bar.set_internet(False)
        self._status_bar.set_wsjtx(False)

    # ------------------------------------------------------------------
    # État CAT/radio réel (Dashboard -> header + barre d'état)
    # ------------------------------------------------------------------

    def _on_live_state(self, state: dict) -> None:
        connected = bool(state.get("connected", False)) if isinstance(state, dict) else False
        model = state.get("model") if isinstance(state, dict) else None

        self.header.set_status("cat", connected)
        self.header.set_status("radio", connected)

        self._status_bar.set_cat(connected)
        self._status_bar.set_radio(connected, model if (connected and model) else "Radio")

    # ------------------------------------------------------------------
    # Ouverture des modules
    # ------------------------------------------------------------------

    def _open_module(self, key: str, title: str) -> None:
        if key not in _IMPLEMENTED:
            self.statusBar().showMessage(f"{title} — module bientôt disponible", 3000)
            return

        if self.application.show_module(key):
            return

        window = self._create_module_window(key)
        self.application.register_module(key, window)
        window.show()

    def _create_module_window(self, key: str):
        if key == "contest":
            from apps.contest.window import ContestWindow
            return ContestWindow(
                radio_service=self.application.radio_service,
                station_service=self.application.station_service,
            )
        if key == "radio_control":
            from apps.radio_control.window import RadioControlWindow
            return RadioControlWindow(radio_service=self.application.radio_service)
        if key == "logbook":
            from apps.logbook.window import LogbookWindow
            return LogbookWindow(radio_service=self.application.radio_service)
        if key == "cat_server":
            from apps.cat_server.window import CATServerWindow
            return CATServerWindow(service=self.application.radio_service)
        if key == "frequency_bank":
            from apps.frequency_bank.window import FrequencyBankWindow
            return FrequencyBankWindow(frequency_service=self.application.frequency_service)
        raise ValueError(f"Module inconnu : {key}")
