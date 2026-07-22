"""
ON3RT Radio Suite
Module Logbook
"""

import sys

from PySide6.QtWidgets import QApplication

from apps.logbook.window import LogbookWindow


def main():
    app = QApplication(sys.argv)

    window = LogbookWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()