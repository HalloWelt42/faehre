"""Sortiert Ordnerinhalte und schneidet sie in Seiten."""

from datetime import datetime

from faehre.modelle import Eintrag, Eintragsart, Ordnerseite, Sortierung
from faehre.quellen.basis import Dateiquelle, elternordner

_FRUEHESTER_ZEITPUNKT = datetime.min


def _natuerlicher_schluessel(name: str) -> list[tuple[int, int | str]]:
    """Datei2 vor Datei10: Ziffernfolgen zählen als Zahl."""
    teile: list[tuple[int, int | str]] = []
    zahl = ""
    text = ""
    for zeichen in name.casefold():
        if zeichen.isdigit():
            if text:
                teile.append((1, text))
                text = ""
            zahl += zeichen
        else:
            if zahl:
                teile.append((0, int(zahl)))
                zahl = ""
            text += zeichen
    if zahl:
        teile.append((0, int(zahl)))
    if text:
        teile.append((1, text))
    return teile


def sortiere(eintraege: list[Eintrag], sortierung: Sortierung, absteigend: bool) -> list[Eintrag]:
    """Ordner stehen immer oben, innerhalb der Gruppen gilt die gewählte Sortierung."""

    def schluessel(e: Eintrag) -> tuple[object, ...]:
        if sortierung == Sortierung.GROESSE:
            return (e.groesse or 0, _natuerlicher_schluessel(e.name))
        if sortierung == Sortierung.GEAENDERT:
            return (e.geaendert or _FRUEHESTER_ZEITPUNKT, _natuerlicher_schluessel(e.name))
        return (_natuerlicher_schluessel(e.name),)

    ordner = sorted((e for e in eintraege if e.art == Eintragsart.ORDNER), key=schluessel, reverse=absteigend)
    rest = sorted((e for e in eintraege if e.art != Eintragsart.ORDNER), key=schluessel, reverse=absteigend)
    return ordner + rest


def ordnerseite(
    quelle: Dateiquelle,
    pfad: str,
    ab: int,
    anzahl: int,
    sortierung: Sortierung,
    absteigend: bool,
    versteckte: bool,
) -> Ordnerseite:
    eintraege = quelle.liste(pfad)
    if not versteckte:
        eintraege = [e for e in eintraege if not e.versteckt]
    sortiert = sortiere(eintraege, sortierung, absteigend)
    return Ordnerseite(
        quelle=quelle.kennung,
        pfad=pfad,
        eltern=elternordner(pfad),
        eintraege=sortiert[ab : ab + anzahl],
        gesamt=len(sortiert),
        ab=ab,
        anzahl=anzahl,
    )
