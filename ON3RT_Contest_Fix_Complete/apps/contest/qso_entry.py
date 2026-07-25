"""
apps/contest/qso_entry.py
"""
from datetime import datetime, timezone
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import QWidget,QHBoxLayout,QLabel,QLineEdit,QPushButton

class QSOEntry(QWidget):
    qso_add_requested = pyqtSignal(dict)

    def __init__(self, radio=None, parent=None):
        super().__init__(parent)
        self.radio=radio
        self.serial=1
        self._freq=None
        self.call=QLineEdit()
        self.band=QLineEdit(); self.band.setReadOnly(True)
        self.mode=QLineEdit(); self.mode.setReadOnly(True)
        self.rst_sent=QLineEdit("59")
        self.rst_recv=QLineEdit("59")
        self.number=QLineEdit(f"{self.serial:03d}")
        self.exchange=QLineEdit(f"{self.serial:03d}")
        self.number.textChanged.connect(self.exchange.setText)
        self.add_button=QPushButton("Ajouter")
        self.fields=[self.call,self.rst_sent,self.rst_recv,self.number,self.exchange]
        lay=QHBoxLayout(self)
        for n,w in [("Call",self.call),("Band",self.band),("Mode",self.mode),("RST TX",self.rst_sent),("RST RX",self.rst_recv),("N°",self.number),("Exchange",self.exchange)]:
            lay.addWidget(QLabel(n)); lay.addWidget(w)
        lay.addWidget(self.add_button)
        self.add_button.clicked.connect(self.emit_qso)
        for f in self.fields: f.installEventFilter(self)
        self.update_from_radio()

    def eventFilter(self,o,e):
        if o in self.fields and e.type()==e.Type.KeyPress and e.key() in (Qt.Key.Key_Tab,Qt.Key.Key_Return,Qt.Key.Key_Enter):
            if self.fields.index(o)==len(self.fields)-1:
                self.emit_qso(); return True
        return super().eventFilter(o,e)

    def update_from_radio(self):
        if not self.radio: return
        self.radio.info()
        self.band.setText(str(self.radio.band or ""))
        self.mode.setText(str(self.radio.mode or ""))
        self._freq=self.radio.frequency

    def emit_qso(self):
        self.update_from_radio()
        now=datetime.now(timezone.utc)
        qdate=self.radio.adif_date if self.radio else now.strftime("%Y%m%d")
        qtime=self.radio.adif_time if self.radio else now.strftime("%H%M")
        self.qso_add_requested.emit({
            "callsign":self.call.text().strip().upper(),
            "band":self.band.text().strip(),
            "mode":self.mode.text().strip().upper(),
            "rst_sent":self.rst_sent.text(),
            "rst_recv":self.rst_recv.text(),
            "serial":self.number.text(),
            "exchange":self.exchange.text(),
            "freq":self._freq,
            "qso_date":qdate,
            "time_on":qtime
        })
        self.serial+=1
        self.call.clear()
        self.number.setText(f"{self.serial:03d}")
        self.call.setFocus()
