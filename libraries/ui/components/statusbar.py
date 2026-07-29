"""
ON3RT Radio Suite
Barre d'etat commune (SuiteStatusBar).

Affiche CPU / RAM / CAT / radio connectee / Internet / WSJT-X / UTC /
heure locale. Reutilisable telle quelle par toutes les fenetres de la
suite.
"""

from __future__ import annotations

from datetime import datetime

try:
    import psutil
except ImportError:  # pragma: no cover - environnement sans psutil
    psutil = None

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QStatusBar, QWidget

from libraries.ui import colors
from libraries.ui.components.icons import icon as make_icon


def _separator() -> QFrame:
    sep = QFrame()
    sep.setFixedSize(1, 12)
    sep.setStyleSheet(f"background:{colors.BORDER};")
    return sep


class _Segment(QWidget):
    def __init__(self, icon_name: str, text: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        self._icon_name = icon_name

        self._icon_lbl = QLabel()
        self._icon_lbl.setFixedSize(13, 13)
        self._icon_lbl.setStyleSheet("background: transparent;")
        self._icon_lbl.setPixmap(make_icon(icon_name, colors.TEXT_MUTED, 13).pixmap(13, 13))

        self._text_lbl = QLabel(text)
        self._text_lbl.setStyleSheet(
            f"background:transparent; color:{colors.TEXT_SECONDARY};"
            f" font-family:'Cascadia Mono','Consolas',monospace; font-size:10.5px;"
        )

        layout.addWidget(self._icon_lbl)
        layout.addWidget(self._text_lbl)

    def set_text(self, text: str) -> None:
        self._text_lbl.setText(text)

    def set_ok(self, ok: bool) -> None:
        color = colors.STATE_GREEN if ok else colors.TEXT_MUTED
        self._icon_lbl.setPixmap(make_icon(self._icon_name, color, 13).pixmap(13, 13))
        self._text_lbl.setStyleSheet(
            f"background:transparent; color:{colors.STATE_GREEN if ok else colors.TEXT_SECONDARY};"
            f" font-family:'Cascadia Mono','Consolas',monospace; font-size:10.5px;"
        )


class SuiteStatusBar(QStatusBar):
    """Barre d'etat systeme + radio, commune a toute la suite."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setStyleSheet(
            f"""
            QStatusBar {{
                background:{colors.BG_HEADER};
                border-top:1px solid {colors.BORDER};
            }}
            QStatusBar::item {{ border: none; }}
            """
        )
        self.setSizeGripEnabled(False)

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(container)
        layout.setContentsMargins(14, 4, 14, 4)
        layout.setSpacing(14)

        self._cpu = _Segment("cpu", "CPU --%")
        self._ram = _Segment("server", "RAM -- Mo")
        self._cat = _Segment("plug", "CAT")
        self._radio = _Segment("antenna", "Radio")
        self._internet = _Segment("world", "Internet")
        self._wsjtx = _Segment("wave", "WSJT-X")

        radio_segments = (self._cat, self._radio, self._internet, self._wsjtx)
        layout.addWidget(self._cpu)
        layout.addWidget(self._ram)
        layout.addWidget(_separator())
        for i, seg in enumerate(radio_segments):
            layout.addWidget(seg)
            if i < len(radio_segments) - 1:
                layout.addWidget(_separator())

        layout.addStretch(1)

        self._utc_lbl = QLabel()
        self._local_lbl = QLabel()
        for lbl in (self._utc_lbl, self._local_lbl):
            lbl.setStyleSheet(
                f"background:transparent; color:{colors.TEXT_SECONDARY};"
                f" font-family:'Cascadia Mono','Consolas',monospace; font-size:10.5px;"
            )
        layout.addWidget(self._utc_lbl)
        layout.addWidget(_separator())
        layout.addWidget(self._local_lbl)

        self.addPermanentWidget(container, 1)

        self._refresh_clock()
        clock_timer = QTimer(self)
        clock_timer.timeout.connect(self._refresh_clock)
        clock_timer.start(1000)

        self._refresh_system()
        system_timer = QTimer(self)
        system_timer.timeout.connect(self._refresh_system)
        system_timer.start(2000)

    def _refresh_clock(self) -> None:
        now_utc = datetime.utcnow()
        now_local = datetime.now()
        self._utc_lbl.setText(f"UTC {now_utc.strftime('%H:%M:%S')}")
        self._local_lbl.setText(f"Local {now_local.strftime('%H:%M:%S')}")

    def _refresh_system(self) -> None:
        if psutil is None:
            return
        cpu = psutil.cpu_percent(interval=None)
        ram_mb = psutil.virtual_memory().used / (1024 * 1024)
        self._cpu.set_text(f"CPU {cpu:.0f}%")
        self._ram.set_text(f"RAM {ram_mb:.0f} Mo")

    def set_cat(self, ok: bool) -> None:
        self._cat.set_ok(ok)

    def set_radio(self, ok: bool, label: str = "Radio") -> None:
        self._radio.set_text(label)
        self._radio.set_ok(ok)

    def set_internet(self, ok: bool) -> None:
        self._internet.set_ok(ok)

    def set_wsjtx(self, ok: bool) -> None:
        self._wsjtx.set_ok(ok)
