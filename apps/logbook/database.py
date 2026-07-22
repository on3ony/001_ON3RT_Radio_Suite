"""
ON3RT Radio Suite
Module Logbook
Gestion de la base de données SQLite.
"""

from pathlib import Path
import sqlite3


DATABASE_NAME = "logbook.db"


def database_path() -> Path:
    """
    Retourne le chemin de la base SQLite.
    """

    root = Path(__file__).resolve().parents[2]

    data = root / "data"
    data.mkdir(exist_ok=True)

    return data / DATABASE_NAME


def get_connection() -> sqlite3.Connection:
    """
    Ouvre une connexion SQLite.
    """

    return sqlite3.connect(database_path())


def initialize_database() -> None:
    """
    Crée la base de données si elle n'existe pas.
    """

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS qso (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            qso_date TEXT NOT NULL,
            time_on TEXT NOT NULL,

            callsign TEXT NOT NULL,

            band TEXT,
            frequency INTEGER,
            mode TEXT,

            rst_sent TEXT,
            rst_recv TEXT,

            operator TEXT,
            name TEXT,
            qth TEXT,
            locator TEXT,

            country TEXT,

            tx_power INTEGER,
            rig TEXT,
            antenna TEXT,

            comment TEXT,

            software TEXT,

            imported INTEGER DEFAULT 0,

            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    conn.commit()
    conn.close()