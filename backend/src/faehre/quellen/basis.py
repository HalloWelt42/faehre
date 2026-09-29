"""Schnittstelle aller Dateiquellen.

Eine Dateiquelle ist ein Ort, dessen Ordner man auflisten und dessen Dateien man
blockweise lesen und schreiben kann. Mac und Telefon sind zwei Umsetzungen davon.
Übertragungen laufen ausschließlich über diese Schnittstelle, deshalb kennt der
Auftragsdienst weder Dateisystem noch adb.
"""

import posixpath
from abc import ABC, abstractmethod
from collections.abc import Iterator
from datetime import datetime

from faehre.modelle import Eintrag, Ort, Quelle, Quellenart


class QuellenFehler(Exception):
    """Fehler mit einer Meldung, die so in der Oberfläche erscheinen darf."""


class NichtGefunden(QuellenFehler):
    pass


def verbinde(ordner: str, name: str) -> str:
    return posixpath.join(ordner, name)


def elternordner(pfad: str) -> str | None:
    normal = posixpath.normpath(pfad)
    if normal == "/":
        return None
    return posixpath.dirname(normal)


def dateiname(pfad: str) -> str:
    return posixpath.basename(posixpath.normpath(pfad))


def pruefe_name(name: str) -> str:
    """Ein einzelner Datei- oder Ordnername ohne Pfadanteile."""
    bereinigt = name.strip()
    if not bereinigt or bereinigt in (".", "..") or "/" in bereinigt or "\0" in bereinigt:
        raise QuellenFehler(f"Ungültiger Name: {name!r}")
    return bereinigt


def liegt_in(pfad: str, ordner: str) -> bool:
    """True, wenn pfad gleich ordner ist oder darin liegt."""
    pfad_normal = posixpath.normpath(pfad)
    ordner_normal = posixpath.normpath(ordner)
    return pfad_normal == ordner_normal or pfad_normal.startswith(ordner_normal.rstrip("/") + "/")


class Dateiquelle(ABC):
    kennung: str
    name: str
    art: Quellenart

    @abstractmethod
    def startordner(self) -> str: ...

    @abstractmethod
    def orte(self) -> list[Ort]: ...

    @abstractmethod
    def liste(self, ordner: str) -> list[Eintrag]:
        """Alle Einträge eines Ordners, unsortiert."""

    @abstractmethod
    def eintrag(self, pfad: str) -> Eintrag | None:
        """Angaben zu einem einzelnen Pfad oder None, wenn er nicht existiert."""

    @abstractmethod
    def lese(self, pfad: str) -> Iterator[bytes]:
        """Inhalt einer Datei als Folge von Blöcken."""

    @abstractmethod
    def schreibe(self, pfad: str, bloecke: Iterator[bytes], geaendert: datetime | None) -> None:
        """Legt die Datei an oder ersetzt sie. Fehlende Elternordner entstehen dabei.

        geaendert übernimmt das Änderungsdatum der Quelldatei, sofern bekannt.
        """

    @abstractmethod
    def ordner_anlegen(self, pfad: str) -> None: ...

    @abstractmethod
    def loesche(self, pfad: str) -> None: ...

    @abstractmethod
    def benenne_um(self, pfad: str, neuer_pfad: str) -> None:
        """Umbenennen oder Verschieben innerhalb derselben Quelle."""

    @property
    @abstractmethod
    def loeschen_in_papierkorb(self) -> bool:
        """True, wenn Löschen rückgängig zu machen ist."""

    def vorhandene_namen(self, ordner: str, namen: list[str]) -> list[str]:
        return [name for name in namen if self.eintrag(verbinde(ordner, name)) is not None]

    def beschreibung(self) -> Quelle:
        return Quelle(
            kennung=self.kennung,
            name=self.name,
            art=self.art,
            start=self.startordner(),
            orte=self.orte(),
        )
