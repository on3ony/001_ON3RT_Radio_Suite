"""
apps/contest/qso_entry.py
"""
from datetime import datetime, timezone
from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QWidget,QHBoxLayout,QLabel,QLineEdit,QPushButton

class QSOEntry(QWidget):
    qso_add_requested = Signal(dict)

    def __init__(self, radio=None, parent=None):
        super().__init__(parent)
        self.radio=radio
        self._freq=None
        self.call=QLineEdit()
        self.band=QLineEdit(); self.band.setReadOnly(True)
        self.mode=QLineEdit(); self.mode.setReadOnly(True)
        self.rst_sent=QLineEdit("59")
        self.rst_recv=QLineEdit("59")
        self.number=QLineEdit("001")
        self.exchange=QLineEdit("001")
        self.number.textChanged.connect(self.exchange.setText)
        self.exchange_recv=QLineEdit()
        self.add_button=QPushButton("Ajouter")
        self.fields=[self.call,self.rst_sent,self.rst_recv,self.number,self.exchange,self.exchange_recv]
        lay=QHBoxLayout(self)
        for n,w in [("Call",self.call),("Band",self.band),("Mode",self.mode),("RST TX",self.rst_sent),("RST RX",self.rst_recv),("N° TX",self.number),("Exchange TX",self.exchange),("Exchange RX",self.exchange_recv)]:
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

    def set_next_serial(self, serial: int):
        self.number.setText(f"{serial:03d}")

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
            "serial_sent":self.number.text(),
            "exchange_sent":self.exchange.text(),
            "exchange_recv":self.exchange_recv.text().strip(),
            "freq":self._freq,
            "qso_date":qdate,
            "time_on":qtime
        })
        self.call.clear()
        self.exchange_recv.clear()
        self.call.setFocus()
