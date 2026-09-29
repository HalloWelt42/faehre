"""Dateiquelle für ein Android-Gerät über adb.

Auflisten, Abfragen und Senden laufen über das Sync-Protokoll (adb_sync),
Lesen über adbutils, Ordner- und Verschiebeoperationen über die Geräte-Shell.
Nach Änderungen im gemeinsamen Speicher wird die Medienbibliothek informiert,
damit neue Bilder und Musik sofort in Galerie und Player auftauchen.
"""

import shlex
from urllib.parse import quote
from collections.abc import Iterator
from datetime import datetime

from adbutils import AdbDevice

from faehre.modelle import Eintrag, Eintragsart, Ort, Quellenart
from faehre.quellen import adb_sync
from faehre.quellen.basis import Dateiquelle, NichtGefunden, QuellenFehler, dateiname, verbinde

_GEMEINSAMER_SPEICHER = ("/sdcard", "/storage")
_ORDNER_IM_SPEICHER = [
    ("Download", "download"),
    ("DCIM", "camera"),
    ("Pictures", "image"),
    ("Music", "music"),
    ("Movies", "film"),
    ("Documents", "file-lines"),
]


def android_kennung(seriennummer: str) -> str:
    return f"android:{seriennummer}"


class AndroidQuelle(Dateiquelle):
    art = Quellenart.ANDROID

    def __init__(self, geraet: AdbDevice, startordner: str) -> None:
        self._geraet = geraet
        self._start = startordner
        self.kennung = android_kennung(geraet.serial)
        modell = geraet.prop.model or geraet.serial
        self.name = modell.replace("_", " ")

    def startordner(self) -> str:
        return self._start

    def orte(self) -> list[Ort]:
        orte = [Ort(name="Interner Speicher", pfad="/sdcard", symbol="mobile-screen", anker=True)]
        vorhandene = {e.name for e in self._liste_roh("/sdcard") if e.ist_ordner}
        orte += [
            Ort(name=name, pfad=verbinde("/sdcard", name), symbol=symbol)
            for name, symbol in _ORDNER_IM_SPEICHER
            if name in vorhandene
        ]
        orte += [
            Ort(name="SD-Karte", pfad=verbinde("/storage", e.name), symbol="sd-card", anker=True)
            for e in self._liste_roh("/storage")
            if e.name not in ("emulated", "self") and e.ist_ordner
        ]
        return orte

    def _liste_roh(self, ordner: str) -> list[adb_sync.DateiStatus]:
        try:
            return adb_sync.liste(self._geraet, ordner)
        except adb_sync.AdbSyncFehler:
            return []

    def liste(self, ordner: str) -> list[Eintrag]:
        status = adb_sync.status(self._geraet, ordner)
        if status is None:
            raise NichtGefunden(f"Ordner nicht gefunden: {ordner}")
        if not status.ist_ordner:
            raise QuellenFehler(f"Kein Ordner: {ordner}")
        return [self._eintrag(ordner, e) for e in adb_sync.liste(self._geraet, ordner)]

    def _eintrag(self, ordner: str, status: adb_sync.DateiStatus) -> Eintrag:
        pfad = verbinde(ordner, status.name)
        art = Eintragsart.DATEI
        if status.ist_ordner:
            art = Eintragsart.ORDNER
        elif status.ist_verweis:
            ziel = adb_sync.status(self._geraet, pfad)
            art = Eintragsart.ORDNER if ziel is not None and ziel.ist_ordner else Eintragsart.VERWEIS
        return Eintrag(
            name=status.name,
            pfad=pfad,
            art=art,
            groesse=None if art == Eintragsart.ORDNER else status.groesse,
            geaendert=status.geaendert,
            versteckt=status.name.startswith("."),
        )

    def eintrag(self, pfad: str) -> Eintrag | None:
        status = adb_sync.status(self._geraet, pfad)
        if status is None:
            return None
        art = Eintragsart.ORDNER if status.ist_ordner else Eintragsart.DATEI
        return Eintrag(
            name=dateiname(pfad),
            pfad=pfad,
            art=art,
            groesse=None if status.ist_ordner else status.groesse,
            geaendert=status.geaendert,
            versteckt=dateiname(pfad).startswith("."),
        )

    def lese(self, pfad: str) -> Iterator[bytes]:
        return self._geraet.sync.iter_content(pfad)

    def schreibe(self, pfad: str, bloecke: Iterator[bytes], geaendert: datetime | None) -> None:
        adb_sync.sende(self._geraet, pfad, bloecke, geaendert)
        self._medienbibliothek_informieren(pfad)

    def ordner_anlegen(self, pfad: str) -> None:
        self._shell("mkdir", "-p", "--", pfad)

    def loesche(self, pfad: str) -> None:
        if adb_sync.status(self._geraet, pfad) is None:
            raise NichtGefunden(f"Nicht gefunden: {pfad}")
        self._shell("rm", "-rf", "--", pfad)
        self._medienbibliothek_informieren(pfad)

    def benenne_um(self, pfad: str, neuer_pfad: str) -> None:
        if adb_sync.status(self._geraet, neuer_pfad) is not None:
            raise QuellenFehler(f"Ziel existiert bereits: {dateiname(neuer_pfad)}")
        self._shell("mv", "--", pfad, neuer_pfad)
        self._medienbibliothek_informieren(pfad)
        self._medienbibliothek_informieren(neuer_pfad)

    @property
    def loeschen_in_papierkorb(self) -> bool:
        return False

    def _shell(self, *argumente: str) -> str:
        befehl = " ".join(shlex.quote(a) for a in argumente)
        antwort = self._geraet.shell2(befehl)
        if antwort.returncode != 0:
            raise QuellenFehler(antwort.output.strip() or f"Befehl fehlgeschlagen: {argumente[0]}")
        return antwort.output

    def _medienbibliothek_informieren(self, pfad: str) -> None:
        """Bittet den Medienscanner, den Pfad neu einzulesen. Fehler sind hier unkritisch."""
        if not pfad.startswith(_GEMEINSAMER_SPEICHER):
            return
        befehl = " ".join(
            shlex.quote(a)
            for a in ("am", "broadcast", "-a", "android.intent.action.MEDIA_SCANNER_SCAN_FILE", "-d", f"file://{quote(pfad)}")
        )
        try:
            self._geraet.shell(befehl, timeout=10)
        except Exception:  # noqa: BLE001 - der Scan ist nur eine Gefälligkeit
            pass
