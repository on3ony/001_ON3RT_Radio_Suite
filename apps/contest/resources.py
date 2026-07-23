"""
apps/contest/resources.py
ON3RT Radio Suite - Contest Logbook
"""

APP_NAME = "ON3RT Contest Logbook"
APP_VERSION = "V1.0"

WINDOW_TITLE = f"{APP_NAME} {APP_VERSION}"

ON3RT_DARK_THEME = """
QMainWindow {
    background-color: #101820;
    color: #ffffff;
}

QWidget {
    background-color: #101820;
    color: #ffffff;
    font-size: 11pt;
}

QLineEdit, QTableWidget {
    background-color: #18242f;
    color: #ffffff;
    border: 1px solid #00aaff;
}

QPushButton {
    background-color: #003b5c;
    color: white;
    border: 1px solid #00aaff;
    padding: 5px;
}

QPushButton:hover {
    background-color: #005f8f;
}

QHeaderView::section {
    background-color: #003b5c;
    color: white;
    padding: 4px;
}

QMenuBar {
    background-color: #101820;
    color: white;
}

QMenuBar::item:selected {
    background-color: #003b5c;
}

QStatusBar {
    background-color: #003b5c;
    color: white;
}
"""


def apply_theme(app):
    app.setStyleSheet(ON3RT_DARK_THEME)
