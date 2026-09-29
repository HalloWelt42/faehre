"""Datenmodelle der Schnittstelle. Einzige Stelle für alle Typen, die über die API gehen."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class Eintragsart(StrEnum):
    ORDNER = "ordner"
    DATEI = "datei"
    VERWEIS = "verweis"


class Eintrag(BaseModel):
    name: str
    pfad: str
    art: Eintragsart
    groesse: int | None = None
    geaendert: datetime | None = None
    versteckt: bool = False


class Sortierung(StrEnum):
    NAME = "name"
    GROESSE = "groesse"
    GEAENDERT = "geaendert"


class Ordnerseite(BaseModel):
    """Ein Ausschnitt eines Ordners. Der Dienst gibt die Seitengröße vor."""

    quelle: str
    pfad: str
    eltern: str | None
    eintraege: list[Eintrag]
    gesamt: int
    ab: int
    anzahl: int


class Ort(BaseModel):
    """Ein Schnellzugriff innerhalb einer Quelle, etwa Downloads oder SD-Karte."""

    name: str
    pfad: str
    symbol: str
    # Anker ersetzen in der Pfadleiste den Pfadanfang, etwa "SD-Karte" statt /storage/3039-6133.
    anker: bool = False


class Quellenart(StrEnum):
    MAC = "mac"
    ANDROID = "android"


class Quelle(BaseModel):
    kennung: str
    name: str
    art: Quellenart
    start: str
    orte: list[Ort]


class GeraeteHinweis(BaseModel):
    """Ein angeschlossenes Gerät, das noch nicht nutzbar ist."""

    seriennummer: str
    meldung: str


class Quellenstand(BaseModel):
    quellen: list[Quelle]
    hinweise: list[GeraeteHinweis]
    adb_fehler: str | None = None


class Auftragsart(StrEnum):
    KOPIEREN = "kopieren"
    VERSCHIEBEN = "verschieben"


class Auftragsstatus(StrEnum):
    WARTET = "wartet"
    LAEUFT = "laeuft"
    FERTIG = "fertig"
    FEHLER = "fehler"
    ABGEBROCHEN = "abgebrochen"


class BeiVorhanden(StrEnum):
    UEBERSCHREIBEN = "ueberschreiben"
    UEBERSPRINGEN = "ueberspringen"


class AuftragsAnfrage(BaseModel):
    art: Auftragsart
    quelle: str
    pfade: list[str] = Field(min_length=1)
    ziel_quelle: str
    ziel_ordner: str
    bei_vorhanden: BeiVorhanden = BeiVorhanden.UEBERSCHREIBEN


class NamensPruefung(BaseModel):
    """Welche dieser Namen gibt es im Ordner schon?"""

    ordner: str
    namen: list[str]


class KonfliktPruefung(BaseModel):
    """Namen, die im Zielordner bereits vorhanden sind."""

    vorhanden: list[str]


class Auftrag(BaseModel):
    kennung: str
    art: Auftragsart
    quelle: str
    ziel_quelle: str
    ziel_ordner: str
    pfade: list[str]
    status: Auftragsstatus
    bytes_gesamt: int = 0
    bytes_fertig: int = 0
    dateien_gesamt: int = 0
    dateien_fertig: int = 0
    aktuelle_datei: str | None = None
    fehler: str | None = None
    erstellt: datetime


class OrdnerAnlegen(BaseModel):
    ordner: str
    name: str = Field(min_length=1)


class Umbenennen(BaseModel):
    pfad: str
    neuer_name: str = Field(min_length=1)


class Loeschen(BaseModel):
    pfade: list[str] = Field(min_length=1)


class LoeschErgebnis(BaseModel):
    geloescht: int
    in_papierkorb: bool


class Status(BaseModel):
    version: str
