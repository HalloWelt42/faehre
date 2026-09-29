"""Dateiquelle für das lokale Dateisystem des Mac. Löschen verschiebt in den Papierkorb."""

import os
import shutil
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

from send2trash import send2trash

from faehre.modelle import Eintrag, Eintragsart, Ort, Quellenart
from faehre.quellen.basis import Dateiquelle, NichtGefunden, QuellenFehler, dateiname

MAC_KENNUNG = "mac"


def _eintrag_aus_status(name: str, pfad: str, status: os.stat_result, ist_verweis: bool) -> Eintrag:
    ist_ordner = os.path.isdir(pfad)
    if ist_ordner:
        art = Eintragsart.ORDNER
    elif ist_verweis:
        art = Eintragsart.VERWEIS
    else:
        art = Eintragsart.DATEI
    return Eintrag(
        name=name,
        pfad=pfad,
        art=art,
        groesse=None if ist_ordner else status.st_size,
        geaendert=datetime.fromtimestamp(status.st_mtime),
        versteckt=name.startswith("."),
    )


class MacQuelle(Dateiquelle):
    kennung = MAC_KENNUNG
    art = Quellenart.MAC

    def __init__(self, startordner: str, blockgroesse: int) -> None:
        self.name = "Mac"
        self._start = startordner or str(Path.home())
        self._blockgroesse = blockgroesse

    def startordner(self) -> str:
        return self._start

    def orte(self) -> list[Ort]:
        heim = Path.home()
        vorschlaege = [
            ("Benutzerordner", heim, "house"),
            ("Schreibtisch", heim / "Desktop", "desktop"),
            ("Downloads", heim / "Downloads", "download"),
            ("Dokumente", heim / "Documents", "file-lines"),
            ("Bilder", heim / "Pictures", "image"),
            ("Musik", heim / "Music", "music"),
            ("Filme", heim / "Movies", "film"),
        ]
        orte = [
            Ort(name=name, pfad=str(pfad), symbol=symbol, anker=pfad == heim)
            for name, pfad, symbol in vorschlaege
            if pfad.is_dir()
        ]
        orte += [
            Ort(name=laufwerk.name, pfad=str(laufwerk), symbol="hard-drive", anker=True)
            for laufwerk in sorted(Path("/Volumes").iterdir())
            if laufwerk.is_dir() and not laufwerk.is_symlink()
        ]
        return orte

    def liste(self, ordner: str) -> list[Eintrag]:
        try:
            with os.scandir(ordner) as eintraege:
                return [self._eintrag_aus_scandir(e) for e in eintraege]
        except FileNotFoundError as fehler:
            raise NichtGefunden(f"Ordner nicht gefunden: {ordner}") from fehler
        except PermissionError as fehler:
            raise QuellenFehler(f"Kein Zugriff auf {ordner}") from fehler
        except NotADirectoryError as fehler:
            raise QuellenFehler(f"Kein Ordner: {ordner}") from fehler

    def _eintrag_aus_scandir(self, e: os.DirEntry[str]) -> Eintrag:
        try:
            status = e.stat()
        except OSError:
            status = e.stat(follow_symlinks=False)
        return _eintrag_aus_status(e.name, e.path, status, e.is_symlink())

    def eintrag(self, pfad: str) -> Eintrag | None:
        try:
            status = os.stat(pfad)
        except FileNotFoundError:
            return None
        return _eintrag_aus_status(dateiname(pfad), pfad, status, os.path.islink(pfad))

    def lese(self, pfad: str) -> Iterator[bytes]:
        try:
            with open(pfad, "rb") as datei:
                while block := datei.read(self._blockgroesse):
                    yield block
        except FileNotFoundError as fehler:
            raise NichtGefunden(f"Datei nicht gefunden: {pfad}") from fehler

    def schreibe(self, pfad: str, bloecke: Iterator[bytes], geaendert: datetime | None) -> None:
        os.makedirs(os.path.dirname(pfad), exist_ok=True)
        with open(pfad, "wb") as datei:
            for block in bloecke:
                datei.write(block)
        if geaendert is not None:
            zeitstempel = geaendert.timestamp()
            os.utime(pfad, (zeitstempel, zeitstempel))

    def ordner_anlegen(self, pfad: str) -> None:
        os.makedirs(pfad, exist_ok=True)

    def loesche(self, pfad: str) -> None:
        if not os.path.lexists(pfad):
            raise NichtGefunden(f"Nicht gefunden: {pfad}")
        send2trash(pfad)

    def benenne_um(self, pfad: str, neuer_pfad: str) -> None:
        if os.path.lexists(neuer_pfad):
            raise QuellenFehler(f"Ziel existiert bereits: {dateiname(neuer_pfad)}")
        shutil.move(pfad, neuer_pfad)

    @property
    def loeschen_in_papierkorb(self) -> bool:
        return True
