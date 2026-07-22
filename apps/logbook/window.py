"""
ON3RT Radio Suite
Module Logbook
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QMainWindow, QVBoxLayout, QWidget


class LogbookWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("ON3RT Radio Suite - Logbook")
        self.resize(1000, 700)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)

        title = QLabel("ON3RT Radio Suite")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("Module Logbook")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addStretch()
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addStretch()