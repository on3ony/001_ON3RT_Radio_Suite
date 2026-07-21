"""ON3RT Radio Suite Launcher v2"""
import sys
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon,QPixmap,QFont
from PySide6.QtWidgets import QApplication,QMainWindow,QWidget,QVBoxLayout,QGridLayout,QLabel,QPushButton,QMessageBox,QStatusBar

VERSION="2.0.0"

class Launcher(QMainWindow):
    def __init__(self):
        super().__init__()
        self.base=Path(__file__).parent
        ico=self.base/"assets/logos/app_icon.png"
        if ico.exists(): self.setWindowIcon(QIcon(str(ico)))
        qss=self.base/"assets/themes/on3rt_dark.qss"
        if qss.exists(): QApplication.instance().setStyleSheet(qss.read_text(encoding="utf-8"))
        self.setWindowTitle(f"ON3RT Radio Suite {VERSION}")
        self.resize(1000,700)
        c=QWidget(); self.setCentralWidget(c); lay=QVBoxLayout(c)
        logo=self.base/"assets/logos/on3rt_logo.png"
        if logo.exists():
            l=QLabel(); l.setAlignment(Qt.AlignCenter)
            l.setPixmap(QPixmap(str(logo)).scaledToHeight(120,Qt.SmoothTransformation)); lay.addWidget(l)
        t=QLabel("ON3RT RADIO SUITE"); t.setAlignment(Qt.AlignCenter); t.setFont(QFont("Segoe UI",24,QFont.Bold)); lay.addWidget(t)
        s=QLabel("Version "+VERSION); s.setAlignment(Qt.AlignCenter); lay.addWidget(s)
        g=QGridLayout(); mods=[("📡 CAT Server","cat_server"),("📻 Radio Control","radio_control"),("📖 Logbook","logbook"),("📊 Band Map","bandmap"),("🔍 Scanner","scanner"),("🏆 Contest","contest"),("🌍 Propagation","propagation"),("📡 DX Cluster","dxcluster"),("💻 WSJT-X Bridge","wsjtx_bridge"),("📄 QSL Manager","qsl_manager"),("⚙️ Settings","settings")]
        for i,(txt,m) in enumerate(mods):
            b=QPushButton(txt); b.setMinimumHeight(60); b.clicked.connect(lambda _,x=m:self.launch(x)); g.addWidget(b,i//2,i%2)
        lay.addLayout(g); lay.addStretch()
        st=QStatusBar(); st.showMessage("IC-7300: Déconnecté | Freq: --- | Mode: --- | PTT: OFF"); self.setStatusBar(st)
    def launch(self,m):
        p=self.base/"apps"/m
        QMessageBox.information(self,"Module",f"Ouverture de {m}" if p.exists() else f"{m} n'existe pas encore.")
def main():
    app=QApplication(sys.argv); app.setStyle("Fusion"); w=Launcher(); w.show(); sys.exit(app.exec())
if __name__=="__main__": main()
