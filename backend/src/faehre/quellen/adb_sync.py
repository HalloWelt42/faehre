"""Teile des adb-Sync-Protokolls, die adbutils nicht oder nur eingeschränkt bietet.

- LIS2/STA2: Auflisten und Abfragen mit 64-Bit-Größen. Das alte LIST/STAT liefert
  nur 32 Bit, Dateien über 4 GB hätten dort eine falsche Größe.
- SEND mit 64-KB-Blöcken und erhaltenem Änderungsdatum. adbutils sendet 4-KB-Blöcke
  und setzt immer die aktuelle Uhrzeit.

Alles läuft über eine eigene Sync-Verbindung aus AdbDevice.open_transport().
"""

import stat as dateimodus
import struct
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime

from adbutils import AdbDevice
from adbutils._adb import AdbConnection

# Nach der 4-Byte-Kennung: error, dev, ino, mode, nlink, uid, gid, size, atime, mtime, ctime
_STAT_V2 = struct.Struct("<IQQIIIIQqqq")
# Wie _STAT_V2, zusätzlich die Länge des folgenden Namens
_DENT_V2 = struct.Struct("<IQQIIIIQqqqI")
_MAX_DATENBLOCK = 64 * 1024
_FEHLERCODE_NICHT_VORHANDEN = 2


class AdbSyncFehler(Exception):
    pass


@dataclass(frozen=True)
class DateiStatus:
    name: str
    modus: int
    groesse: int
    geaendert: datetime | None

    @property
    def ist_ordner(self) -> bool:
        return dateimodus.S_ISDIR(self.modus)

    @property
    def ist_verweis(self) -> bool:
        return dateimodus.S_ISLNK(self.modus)


def _zeitpunkt(sekunden: int) -> datetime | None:
    if sekunden <= 0:
        return None
    try:
        return datetime.fromtimestamp(sekunden)
    except (OverflowError, OSError, ValueError):
        return None


@contextmanager
def _sync_verbindung(geraet: AdbDevice) -> Iterator[AdbConnection]:
    with geraet.open_transport(timeout=None) as verbindung:
        verbindung.send_command("sync:")
        verbindung.check_okay()
        yield verbindung


def _schicke(verbindung: AdbConnection, daten: bytes) -> None:
    verbindung.conn.sendall(daten)


def _lies(verbindung: AdbConnection, anzahl: int) -> bytes:
    daten = verbindung.read(anzahl)
    if len(daten) != anzahl:
        raise AdbSyncFehler("Verbindung zum Gerät unterbrochen")
    return daten


def _sende_anfrage(verbindung: AdbConnection, befehl: bytes, pfad: str) -> None:
    kodiert = pfad.encode("utf-8")
    _schicke(verbindung, befehl + struct.pack("<I", len(kodiert)) + kodiert)


def status(geraet: AdbDevice, pfad: str) -> DateiStatus | None:
    """Wie stat(2), folgt Verweisen. None, wenn der Pfad nicht existiert."""
    with _sync_verbindung(geraet) as verbindung:
        _sende_anfrage(verbindung, b"STA2", pfad)
        kennung = _lies(verbindung, 4)
        if kennung != b"STA2":
            raise AdbSyncFehler(f"Unerwartete Antwort {kennung!r} auf STA2")
        fehler, _, _, modus, _, _, _, groesse, _, geaendert, _ = _STAT_V2.unpack(_lies(verbindung, _STAT_V2.size))
    if fehler == _FEHLERCODE_NICHT_VORHANDEN:
        return None
    if fehler:
        raise AdbSyncFehler(f"Abfrage von {pfad} fehlgeschlagen (Fehlercode {fehler})")
    return DateiStatus(name=pfad.rstrip("/").rsplit("/", 1)[-1] or "/", modus=modus, groesse=groesse, geaendert=_zeitpunkt(geaendert))


def liste(geraet: AdbDevice, ordner: str) -> list[DateiStatus]:
    """Einträge eines Ordners ohne . und .., Verweise werden nicht aufgelöst."""
    ergebnis: list[DateiStatus] = []
    with _sync_verbindung(geraet) as verbindung:
        _sende_anfrage(verbindung, b"LIS2", ordner)
        while True:
            kennung = _lies(verbindung, 4)
            werte = _DENT_V2.unpack(_lies(verbindung, _DENT_V2.size))
            if kennung == b"DONE":
                break
            if kennung != b"DNT2":
                raise AdbSyncFehler(f"Unerwartete Antwort {kennung!r} auf LIS2")
            fehler, _, _, modus, _, _, _, groesse, _, geaendert, _, namenslaenge = werte
            name = _lies(verbindung, namenslaenge).decode("utf-8", errors="replace")
            if name in (".", "..") or fehler:
                continue
            ergebnis.append(DateiStatus(name=name, modus=modus, groesse=groesse, geaendert=_zeitpunkt(geaendert)))
    return ergebnis


def sende(geraet: AdbDevice, pfad: str, bloecke: Iterator[bytes], geaendert: datetime | None, modus: int = 0o644) -> int:
    """Schreibt eine Datei aufs Gerät. Fehlende Elternordner legt adbd selbst an."""
    gesendet = 0
    with _sync_verbindung(geraet) as verbindung:
        _sende_anfrage(verbindung, b"SEND", f"{pfad},{dateimodus.S_IFREG | modus}")
        for block in bloecke:
            for anfang in range(0, len(block), _MAX_DATENBLOCK):
                teil = block[anfang : anfang + _MAX_DATENBLOCK]
                _schicke(verbindung, b"DATA" + struct.pack("<I", len(teil)) + teil)
                gesendet += len(teil)
        zeitstempel = int((geaendert or datetime.now()).timestamp())
        _schicke(verbindung, b"DONE" + struct.pack("<I", zeitstempel))
        antwort = _lies(verbindung, 4)
        if antwort == b"FAIL":
            laenge = struct.unpack("<I", _lies(verbindung, 4))[0]
            meldung = _lies(verbindung, laenge).decode("utf-8", errors="replace")
            raise AdbSyncFehler(f"Schreiben von {pfad} fehlgeschlagen: {meldung}")
        if antwort != b"OKAY":
            raise AdbSyncFehler(f"Unerwartete Antwort {antwort!r} auf SEND")
    return gesendet
