"""
ON3RT Radio Suite
Module Logbook
Boîte de dialogue d'ajout / modification d'un QSO.
"""

from datetime import datetime, timezone

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QPlainTextEdit,
)

from apps.logbook.models import QSO


class QSODialog(QDialog):

    def __init__(self, parent=None, qso: QSO | None = None):
        super().__init__(parent)

        self.setWindowTitle("QSO")

        self.qso = qso or QSO()

        self._build_ui()
        self._load_qso()

    def _build_ui(self):

        layout = QFormLayout(self)

        self.callsign = QLineEdit()

        self.date = QLineEdit()
        self.time = QLineEdit()

        self.band = QComboBox()
        self.band.addItems([
            "160m",
            "80m",
            "60m",
            "40m",
            "30m",
            "20m",
            "17m",
            "15m",
            "12m",
            "10m",
            "6m",
            "4m",
            "2m",
            "70cm",
            "23cm",
        ])

        self.frequency = QLineEdit()

        self.mode = QComboBox()
        self.mode.addItems([
            "SSB",
            "USB",
            "LSB",
            "CW",
            "AM",
            "FM",
            "FT8",
            "FT4",
            "RTTY",
            "PSK31",
            "JS8",
            "VARAC",
        ])

        self.rst_tx = QLineEdit()
        self.rst_rx = QLineEdit()

        self.name = QLineEdit()
        self.qth = QLineEdit()
        self.locator = QLineEdit()
        self.country = QLineEdit()

        self.power = QLineEdit()
        self.rig = QLineEdit()
        self.antenna = QLineEdit()

        self.comment = QPlainTextEdit()

        self.software = QComboBox()
        self.software.addItems([
            "Manuel",
            "WSJT-X",
            "VarAC",
            "Fldigi",
            "JTDX",
            "JS8Call",
            "N1MM",
        ])

        layout.addRow("Indicatif", self.callsign)
        layout.addRow("Date UTC", self.date)
        layout.addRow("Heure UTC", self.time)
        layout.addRow("Bande", self.band)
        layout.addRow("Fréquence", self.frequency)
        layout.addRow("Mode", self.mode)
        layout.addRow("RST TX", self.rst_tx)
        layout.addRow("RST RX", self.rst_rx)
        layout.addRow("Nom", self.name)
        layout.addRow("QTH", self.qth)
        layout.addRow("Locator", self.locator)
        layout.addRow("Pays", self.country)
        layout.addRow("Puissance", self.power)
        layout.addRow("Rig", self.rig)
        layout.addRow("Antenne", self.antenna)
        layout.addRow("Commentaire", self.comment)
        layout.addRow("Logiciel", self.software)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout.addRow(buttons)

    def _load_qso(self):

        if not self.qso.qso_date:
            now = datetime.now(timezone.utc)
            self.qso.qso_date = now.strftime("%Y-%m-%d")
            self.qso.time_on = now.strftime("%H:%M")

        self.callsign.setText(self.qso.callsign)

        self.date.setText(self.qso.qso_date)
        self.time.setText(self.qso.time_on)

        self.band.setCurrentText(self.qso.band)
        self.frequency.setText(str(self.qso.frequency))

        self.mode.setCurrentText(self.qso.mode)

        self.rst_tx.setText(self.qso.rst_sent)
        self.rst_rx.setText(self.qso.rst_recv)

        self.name.setText(self.qso.name)
        self.qth.setText(self.qso.qth)
        self.locator.setText(self.qso.locator)
        self.country.setText(self.qso.country)

        self.power.setText(str(self.qso.tx_power))
        self.rig.setText(self.qso.rig)
        self.antenna.setText(self.qso.antenna)

        self.comment.setPlainText(self.qso.comment)

        self.software.setCurrentText(self.qso.software)

    def get_qso(self) -> QSO:

        self.qso.callsign = self.callsign.text().strip().upper()

        self.qso.qso_date = self.date.text().strip()
        self.qso.time_on = self.time.text().strip()

        self.qso.band = self.band.currentText()

        try:
            self.qso.frequency = int(self.frequency.text())
        except ValueError:
            self.qso.frequency = 0

        self.qso.mode = self.mode.currentText()

        self.qso.rst_sent = self.rst_tx.text().strip()
        self.qso.rst_recv = self.rst_rx.text().strip()

        self.qso.name = self.name.text().strip()
        self.qso.qth = self.qth.text().strip()
        self.qso.locator = self.locator.text().strip()
        self.qso.country = self.country.text().strip()

        try:
            self.qso.tx_power = int(self.power.text())
        except ValueError:
            self.qso.tx_power = 0

        self.qso.rig = self.rig.text().strip()
        self.qso.antenna = self.antenna.text().strip()

        self.qso.comment = self.comment.toPlainText().strip()

        self.qso.software = self.software.currentText()

        return self.qso