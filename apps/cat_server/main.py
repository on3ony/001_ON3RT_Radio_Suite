"""
ON3RT Radio Suite
apps/cat_server/main.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

# ----------------------------------------------------------------------
# Ajoute automatiquement la racine du projet au PYTHONPATH
# ----------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ----------------------------------------------------------------------

from apps.cat_server.window import CATServerWindow


def main() -> int:

    app = QApplication.instance()

    if app is None:
        app = QApplication(sys.argv)

    app.setApplicationName("ON3RT Radio Suite")
    app.setOrganizationName("ON3RT")

    theme = PROJECT_ROOT / "assets" / "themes" / "on3rt_dark.qss"

    if theme.is_file():
        try:
            app.setStyleSheet(theme.read_text(encoding="utf-8"))
        except Exception:
            pass

    window = CATServerWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())