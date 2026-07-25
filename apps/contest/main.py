import sys
from PySide6.QtWidgets import QApplication
from apps.contest.window import ContestWindow

def main():
    app=QApplication(sys.argv)
    app.setApplicationName("ON3RT Contest")
    w=ContestWindow()
    w.show()
    sys.exit(app.exec())

if __name__=="__main__":
    main()
