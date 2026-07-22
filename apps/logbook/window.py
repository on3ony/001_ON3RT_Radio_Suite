"""
ON3RT Radio Suite
Module Logbook
"""

from PySide6.QtWidgets import QMainWindow

from apps.logbook.ui import LogbookUI


class LogbookWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("ON3RT Radio Suite - Logbook")
        self.resize(1200, 750)

        self.ui = LogbookUI()
        self.setCentralWidget(self.ui)