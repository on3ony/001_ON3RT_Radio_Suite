"""
apps/contest/main.py
ON3RT Radio Suite - Contest Logbook
"""

import sys

from PyQt6.QtWidgets import QApplication

from apps.contest.window import ContestWindow
from apps.contest.resources import apply_theme


def main():

    app = QApplication(sys.argv)

    app.setApplicationName(
        "ON3RT Contest Logbook"
    )

    apply_theme(app)

    window = ContestWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
