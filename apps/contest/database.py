"""
apps/contest/database.py
Contest Logbook V1 - ON3RT Radio Suite
"""

from __future__ import annotations
import sqlite3
from pathlib import Path
from typing import Any

class ContestDatabase:
    def __init__(self, db_path: str | None = None):
        root = Path(__file__).resolve().parents[2]
        self.db_path = Path(db_path) if db_path else root / "data" / "contest.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_table()

    def _create_table(self):
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS qso(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            callsign TEXT NOT NULL,
            qso_date TEXT,
            time_on TEXT,
            band TEXT,
            freq REAL,
            mode TEXT,
            rst_sent TEXT,
            rst_recv TEXT,
            serial_sent INTEGER,
            serial_recv INTEGER,
            exchange_sent TEXT,
            exchange_recv TEXT,
            operator TEXT,
            locator TEXT,
            points INTEGER DEFAULT 1,
            multiplier INTEGER DEFAULT 0,
            notes TEXT
        )
        """)
        self.conn.commit()

    def add_qso(self, **fields: Any) -> int:
        cols = ",".join(fields.keys())
        vals = list(fields.values())
        marks = ",".join("?" for _ in vals)
        cur = self.conn.execute(
            f"INSERT INTO qso ({cols}) VALUES ({marks})", vals
        )
        self.conn.commit()
        return cur.lastrowid

    def update_qso(self, qso_id: int, **fields: Any):
        if not fields:
            return
        sql = ", ".join(f"{k}=?" for k in fields)
        self.conn.execute(
            f"UPDATE qso SET {sql} WHERE id=?",
            list(fields.values()) + [qso_id],
        )
        self.conn.commit()

    def delete_qso(self, qso_id: int):
        self.conn.execute("DELETE FROM qso WHERE id=?", (qso_id,))
        self.conn.commit()

    def get_qso(self, qso_id: int):
        cur = self.conn.execute("SELECT * FROM qso WHERE id=?", (qso_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def get_all_qsos(self):
        cur = self.conn.execute(
            "SELECT * FROM qso ORDER BY qso_date,time_on,id"
        )
        return [dict(r) for r in cur.fetchall()]

    def search_callsign(self, callsign: str):
        cur = self.conn.execute(
            "SELECT * FROM qso WHERE callsign LIKE ? ORDER BY id DESC",
            (f"%{callsign.upper()}%",),
        )
        return [dict(r) for r in cur.fetchall()]

    def get_next_serial(self) -> int:
        cur = self.conn.execute("SELECT MAX(serial_sent) FROM qso")
        value = cur.fetchone()[0]
        return 1 if value is None else value + 1

    def get_statistics(self):
        cur = self.conn.execute("""
            SELECT
              COUNT(*) qsos,
              COALESCE(SUM(points),0) points,
              COALESCE(SUM(multiplier),0) multipliers
            FROM qso
        """)
        r = cur.fetchone()
        return {
            "qsos": r["qsos"],
            "points": r["points"],
            "multipliers": r["multipliers"],
            "score": r["points"] * max(r["multipliers"], 1),
        }

    def close(self):
        self.conn.close()

if __name__ == "__main__":
    db = ContestDatabase()
    print("Base :", db.db_path)
    print("Prochain numéro :", db.get_next_serial())
    print("Stats :", db.get_statistics())
    db.close()
