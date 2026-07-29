"""
ON3RT Radio Suite
Module Banque de fréquences
Accès à la base de données.
"""

from sqlite3 import Row

from apps.frequency_bank.database import get_connection, initialize_database
from apps.frequency_bank.models import Frequency


class FrequencyRepository:

    def __init__(self):
        initialize_database()
        self.conn = get_connection()
        self.conn.row_factory = Row

    def close(self):
        self.conn.close()

    def _row_to_frequency(self, row: Row) -> Frequency:
        return Frequency(
            id=row["id"],
            frequency=row["frequency"],
            start_frequency=row["start_frequency"],
            end_frequency=row["end_frequency"],
            band=row["band"],
            mode=row["mode"],
            category=row["category"],
            step=row["step"],
            modulation=row["modulation"],
            service=row["service"],
            name=row["name"],
            description=row["description"],
            country=row["country"],
            region=row["region"],
            source=row["source"],
            favorite=bool(row["favorite"]),
            priority=row["priority"],
            active=bool(row["active"]),
            color=row["color"],
        )

    def add(self, frequency: Frequency) -> int:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO frequency(
                frequency,start_frequency,end_frequency,band,mode,category,
                step,modulation,service,name,description,
                country,region,source,favorite,priority,active,color
            )
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                frequency.frequency,
                frequency.start_frequency,
                frequency.end_frequency,
                frequency.band,
                frequency.mode,
                frequency.category,
                frequency.step,
                frequency.modulation,
                frequency.service,
                frequency.name,
                frequency.description,
                frequency.country,
                frequency.region,
                frequency.source,
                int(frequency.favorite),
                frequency.priority,
                int(frequency.active),
                frequency.color,
            ),
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_all(self) -> list[Frequency]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM frequency ORDER BY frequency")
        return [self._row_to_frequency(r) for r in cur.fetchall()]

    def get_by_id(self, frequency_id: int):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM frequency WHERE id=?", (frequency_id,))
        row = cur.fetchone()
        return self._row_to_frequency(row) if row else None

    def update(self, frequency: Frequency):
        self.conn.execute(
            """
            UPDATE frequency SET
                frequency=?,start_frequency=?,end_frequency=?,band=?,mode=?,category=?,
                step=?,modulation=?,service=?,name=?,description=?,
                country=?,region=?,source=?,favorite=?,priority=?,active=?,color=?,
                updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (
                frequency.frequency,
                frequency.start_frequency,
                frequency.end_frequency,
                frequency.band,
                frequency.mode,
                frequency.category,
                frequency.step,
                frequency.modulation,
                frequency.service,
                frequency.name,
                frequency.description,
                frequency.country,
                frequency.region,
                frequency.source,
                int(frequency.favorite),
                frequency.priority,
                int(frequency.active),
                frequency.color,
                frequency.id,
            ),
        )
        self.conn.commit()

    def delete(self, frequency_id: int):
        self.conn.execute("DELETE FROM frequency WHERE id=?", (frequency_id,))
        self.conn.commit()

    def by_band(self, band: str) -> list[Frequency]:
        cur = self.conn.cursor()
        cur.execute(
            "SELECT * FROM frequency WHERE band=? ORDER BY frequency",
            (band,),
        )
        return [self._row_to_frequency(r) for r in cur.fetchall()]

    def by_mode(self, mode: str) -> list[Frequency]:
        cur = self.conn.cursor()
        cur.execute(
            "SELECT * FROM frequency WHERE mode=? ORDER BY frequency",
            (mode,),
        )
        return [self._row_to_frequency(r) for r in cur.fetchall()]

    def by_category(self, category: str) -> list[Frequency]:
        cur = self.conn.cursor()
        cur.execute(
            "SELECT * FROM frequency WHERE category=? ORDER BY frequency",
            (category,),
        )
        return [self._row_to_frequency(r) for r in cur.fetchall()]

    def by_range(self, start: float, end: float) -> list[Frequency]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT * FROM frequency
            WHERE frequency BETWEEN ? AND ?
            ORDER BY frequency
            """,
            (start, end),
        )
        return [self._row_to_frequency(r) for r in cur.fetchall()]

    def by_nearest(self, frequency: float, tolerance: float = 0.005) -> list[Frequency]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT * FROM frequency
            WHERE frequency BETWEEN ? AND ?
            ORDER BY ABS(frequency - ?)
            """,
            (frequency - tolerance, frequency + tolerance, frequency),
        )
        return [self._row_to_frequency(r) for r in cur.fetchall()]

    def favorites(self) -> list[Frequency]:
        cur = self.conn.cursor()
        cur.execute(
            "SELECT * FROM frequency WHERE favorite=1 ORDER BY priority DESC, frequency"
        )
        return [self._row_to_frequency(r) for r in cur.fetchall()]

    def active(self) -> list[Frequency]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM frequency WHERE active=1 ORDER BY frequency")
        return [self._row_to_frequency(r) for r in cur.fetchall()]

    def search(self, text: str) -> list[Frequency]:
        like = f"%{text}%"
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT * FROM frequency
            WHERE name LIKE ?
               OR description LIKE ?
               OR band LIKE ?
               OR mode LIKE ?
               OR category LIKE ?
            ORDER BY priority DESC, frequency
            """,
            (like, like, like, like, like),
        )
        return [self._row_to_frequency(r) for r in cur.fetchall()]

    def count(self) -> int:
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM frequency")
        return cur.fetchone()[0]
