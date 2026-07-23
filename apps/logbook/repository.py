"""
ON3RT Radio Suite
Module Logbook
Accès à la base de données.
"""

from sqlite3 import Row

from apps.logbook.database import get_connection
from apps.logbook.models import QSO


class LogbookRepository:

    def __init__(self):
        self.conn = get_connection()
        self.conn.row_factory = Row

    def close(self):
        self.conn.close()

    def _row_to_qso(self, row: Row) -> QSO:
        return QSO(
            id=row["id"],
            qso_date=row["qso_date"],
            time_on=row["time_on"],
            callsign=row["callsign"],
            band=row["band"],
            frequency=row["frequency"],
            mode=row["mode"],
            rst_sent=row["rst_sent"],
            rst_recv=row["rst_recv"],
            operator=row["operator"],
            name=row["name"],
            qth=row["qth"],
            locator=row["locator"],
            country=row["country"],
            tx_power=row["tx_power"],
            rig=row["rig"],
            antenna=row["antenna"],
            comment=row["comment"],
            software=row["software"],
            imported=bool(row["imported"]),
        )

    def add_qso(self, qso: QSO) -> int:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO qso(
                qso_date,time_on,callsign,band,frequency,mode,
                rst_sent,rst_recv,operator,name,qth,locator,
                country,tx_power,rig,antenna,comment,software,imported
            )
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                qso.qso_date,
                qso.time_on,
                qso.callsign,
                qso.band,
                qso.frequency,
                qso.mode,
                qso.rst_sent,
                qso.rst_recv,
                qso.operator,
                qso.name,
                qso.qth,
                qso.locator,
                qso.country,
                qso.tx_power,
                qso.rig,
                qso.antenna,
                qso.comment,
                qso.software,
                int(qso.imported),
            ),
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_all(self) -> list[QSO]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM qso ORDER BY qso_date DESC, time_on DESC")
        return [self._row_to_qso(r) for r in cur.fetchall()]

    def get_by_id(self, qso_id: int):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM qso WHERE id=?", (qso_id,))
        row = cur.fetchone()
        return self._row_to_qso(row) if row else None

    def update_qso(self, qso: QSO):
        self.conn.execute(
            """
            UPDATE qso SET
                qso_date=?,time_on=?,callsign=?,band=?,frequency=?,mode=?,
                rst_sent=?,rst_recv=?,operator=?,name=?,qth=?,locator=?,
                country=?,tx_power=?,rig=?,antenna=?,comment=?,software=?,
                imported=?,updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (
                qso.qso_date,qso.time_on,qso.callsign,qso.band,qso.frequency,
                qso.mode,qso.rst_sent,qso.rst_recv,qso.operator,qso.name,
                qso.qth,qso.locator,qso.country,qso.tx_power,qso.rig,
                qso.antenna,qso.comment,qso.software,int(qso.imported),qso.id,
            ),
        )
        self.conn.commit()

    def delete(self, qso_id: int):
        self.conn.execute("DELETE FROM qso WHERE id=?", (qso_id,))
        self.conn.commit()

    def search(self, text: str) -> list[QSO]:
        like = f"%{text}%"
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT * FROM qso
            WHERE callsign LIKE ?
               OR name LIKE ?
               OR qth LIKE ?
               OR country LIKE ?
               OR mode LIKE ?
               OR band LIKE ?
            ORDER BY qso_date DESC,time_on DESC
            """,
            (like, like, like, like, like, like),
        )
        return [self._row_to_qso(r) for r in cur.fetchall()]

    def exists_duplicate(self, callsign: str, qso_date: str,
                         time_on: str, band: str, mode: str) -> bool:
        cur = self.conn.cursor()
        cur.execute(
            """SELECT COUNT(*) FROM qso
               WHERE callsign=? AND qso_date=? AND time_on=?
                 AND band=? AND mode=?""",
            (callsign, qso_date, time_on, band, mode),
        )
        return cur.fetchone()[0] > 0

    def add_imported_qso(self, qso: QSO):
        qso.imported = True
        return self.add_qso(qso)

    def count(self) -> int:
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM qso")
        return cur.fetchone()[0]
