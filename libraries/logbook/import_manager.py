"""
ON3RT Radio Suite
Module Logbook
Import Manager
"""

from pathlib import Path

from apps.logbook.models import QSO
from apps.logbook.repository import LogbookRepository
from libraries.logbook.adif_importer import ADIFImporter


class ImportManager:

    def __init__(self):
        self.repository = LogbookRepository()
        self.importer = ADIFImporter()

    def close(self):
        self.repository.close()

    def import_file(self, filename: str) -> dict:

        if not Path(filename).exists():
            raise FileNotFoundError(filename)

        records = self.importer.load(filename)

        imported = 0
        duplicates = 0
        errors = 0

        for record in records:

            try:

                callsign = record.get("CALL", "").strip().upper()

                qso_date = record.get("QSO_DATE", "").strip()

                time_on = record.get("TIME_ON", "").strip()

                band = record.get("BAND", "").strip()

                mode = record.get("MODE", "").strip()

                if self.repository.exists_duplicate(
                    callsign,
                    qso_date,
                    time_on,
                    band,
                    mode,
                ):
                    duplicates += 1
                    continue

                qso = QSO()

                qso.callsign = callsign
                qso.qso_date = qso_date
                qso.time_on = time_on

                qso.band = band
                qso.mode = mode

                try:
                    qso.frequency = int(record.get("FREQ", "0").replace(".", ""))
                except Exception:
                    qso.frequency = 0

                qso.rst_sent = record.get("RST_SENT", "")
                qso.rst_recv = record.get("RST_RCVD", "")

                qso.name = record.get("NAME", "")
                qso.qth = record.get("QTH", "")
                qso.locator = record.get("GRIDSQUARE", "")
                qso.country = record.get("COUNTRY", "")

                try:
                    qso.tx_power = int(float(record.get("TX_PWR", "0")))
                except Exception:
                    qso.tx_power = 0

                qso.rig = record.get("RIG", "")
                qso.antenna = record.get("ANTENNA", "")
                qso.comment = record.get("COMMENT", "")

                qso.software = record.get("PROGRAMID", "ADIF")

                qso.imported = True

                self.repository.add_imported_qso(qso)

                imported += 1

            except Exception:
                errors += 1

        return {
            "total": len(records),
            "imported": imported,
            "duplicates": duplicates,
            "errors": errors,
        }