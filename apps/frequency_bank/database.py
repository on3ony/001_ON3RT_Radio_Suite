"""
ON3RT Radio Suite
Module Banque de fréquences
Gestion de la base de données SQLite.
"""

from pathlib import Path
import sqlite3


DATABASE_NAME = "frequency_bank.db"


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
        CREATE TABLE IF NOT EXISTS frequency (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            frequency REAL NOT NULL,
            start_frequency REAL DEFAULT 0,
            end_frequency REAL DEFAULT 0,

            band TEXT,
            mode TEXT,
            category TEXT,

            step INTEGER DEFAULT 0,
            modulation TEXT,
            service TEXT,

            name TEXT,
            description TEXT,

            country TEXT,
            region TEXT,
            source TEXT,

            favorite INTEGER DEFAULT 0,
            priority INTEGER DEFAULT 0,
            active INTEGER DEFAULT 1,
            color TEXT,

            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    conn.commit()
    conn.close()
