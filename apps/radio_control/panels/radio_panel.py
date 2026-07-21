"""
ON3RT Radio Suite
Radio Control - Radio Panel
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QGroupBox,
    QLabel,
)


class RadioPanel(QGroupBox):
    """
    Panneau principal d'informations radio.
    """

    def __init__(self):
        super().__init__("Radio")

        self._build_ui()

    def _build_ui(self):

        layout = QGridLayout(self)
        layout.setHorizontalSpacing(20)
        layout.setVerticalSpacing(10)

        # ---------------------------------------------------------
        # Etat
        # ---------------------------------------------------------

        layout.addWidget(QLabel("État"), 0, 0)

        self.lbl_state = QLabel("● Déconnecté")
        self.lbl_state.setObjectName("StatusDisconnected")

        layout.addWidget(self.lbl_state, 0, 1)

        # ---------------------------------------------------------
        # Fréquence
        # ---------------------------------------------------------

        layout.addWidget(QLabel("Fréquence"), 1, 0)

        self.lbl_frequency = QLabel("-----.---.--- Hz")
        self.lbl_frequency.setAlignment(Qt.AlignCenter)
        self.lbl_frequency.setObjectName("FrequencyDisplay")
        self.lbl_frequency.setFrameShape(QFrame.Box)

        layout.addWidget(self.lbl_frequency, 1, 1, 1, 3)

        # ---------------------------------------------------------
        # Mode
        # ---------------------------------------------------------

        layout.addWidget(QLabel("Mode"), 2, 0)

        self.lbl_mode = QLabel("---")

        layout.addWidget(self.lbl_mode, 2, 1)

        # ---------------------------------------------------------
        # VFO
        # ---------------------------------------------------------

        layout.addWidget(QLabel("VFO"), 2, 2)

        self.lbl_vfo = QLabel("A")

        layout.addWidget(self.lbl_vfo, 2, 3)

        # ---------------------------------------------------------
        # PTT
        # ---------------------------------------------------------

        layout.addWidget(QLabel("PTT"), 3, 0)

        self.lbl_ptt = QLabel("OFF")

        layout.addWidget(self.lbl_ptt, 3, 1)

        # ---------------------------------------------------------
        # Préampli
        # ---------------------------------------------------------

        layout.addWidget(QLabel("Préampli"), 3, 2)

        self.lbl_preamp = QLabel("OFF")

        layout.addWidget(self.lbl_preamp, 3, 3)

        # ---------------------------------------------------------
        # Atténuateur
        # ---------------------------------------------------------

        layout.addWidget(QLabel("ATT"), 4, 0)

        self.lbl_att = QLabel("OFF")

        layout.addWidget(self.lbl_att, 4, 1)

    # =============================================================
    # Fonctions de mise à jour
    # =============================================================

    def set_connected(self, connected: bool):

        if connected:
            self.lbl_state.setText("● Connecté")
        else:
            self.lbl_state.setText("● Déconnecté")

    def set_frequency(self, frequency: str):
        self.lbl_frequency.setText(frequency)

    def set_mode(self, mode: str):
        self.lbl_mode.setText(mode)

    def set_vfo(self, vfo: str):
        self.lbl_vfo.setText(vfo)

    def set_ptt(self, state: bool):
        self.lbl_ptt.setText("ON" if state else "OFF")

    def set_preamp(self, value: str):
        self.lbl_preamp.setText(value)

    def set_att(self, value: str):
        self.lbl_att.setText(value)