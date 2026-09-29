"""Ordner ansehen, Dateien hoch- und herunterladen, anlegen, umbenennen, löschen."""

import logging
import mimetypes
from collections.abc import Iterator
from datetime import datetime
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

from faehre.abhaengigkeiten import Dienste, dienste
from faehre.dienste.brueckenstrom import verarbeite_strom
from faehre.dienste.ordner import ordnerseite
from faehre.modelle import (
    Eintrag,
    Eintragsart,
    KonfliktPruefung,
    LoeschErgebnis,
    Loeschen,
    NamensPruefung,
    Ordnerseite,
    OrdnerAnlegen,
    Quellenstand,
    Sortierung,
    Umbenennen,
)
from faehre.quellen.basis import NichtGefunden, QuellenFehler, dateiname, elternordner, pruefe_name, verbinde

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/quellen", tags=["Quellen"])
DiensteAbh = Annotated[Dienste, Depends(dienste)]


def _eintrag_oder_fehler(eintrag: Eintrag | None, pfad: str) -> Eintrag:
    if eintrag is None:
        raise NichtGefunden(f"Nicht gefunden: {pfad}")
    return eintrag


@router.get("", response_model=Quellenstand)
def quellen(d: DiensteAbh) -> Quellenstand:
    return d.register.stand()


@router.get("/{kennung}/ordner", response_model=Ordnerseite)
def ordner(
    kennung: str,
    d: DiensteAbh,
    pfad: str,
    ab: Annotated[int, Query(ge=0)] = 0,
    sortierung: Sortierung = Sortierung.NAME,
    absteigend: bool = False,
    versteckte: bool = False,
) -> Ordnerseite:
    quelle = d.register.hole(kennung)
    return ordnerseite(quelle, pfad, ab, d.einstellungen.seitengroesse, sortierung, absteigend, versteckte)


@router.post("/{kennung}/vorhanden", response_model=KonfliktPruefung)
def vorhanden(kennung: str, anfrage: NamensPruefung, d: DiensteAbh) -> KonfliktPruefung:
    """Vor dem Hochladen: Welche Namen würden überschrieben?"""
    quelle = d.register.hole(kennung)
    return KonfliktPruefung(vorhanden=quelle.vorhandene_namen(anfrage.ordner, anfrage.namen))


@router.post("/{kennung}/ordner-anlegen", response_model=Eintrag)
def ordner_anlegen(kennung: str, anfrage: OrdnerAnlegen, d: DiensteAbh) -> Eintrag:
    quelle = d.register.hole(kennung)
    pfad = verbinde(anfrage.ordner, pruefe_name(anfrage.name))
    if quelle.eintrag(pfad) is not None:
        raise QuellenFehler(f"{dateiname(pfad)} gibt es hier schon.")
    quelle.ordner_anlegen(pfad)
    log.info("Ordner angelegt auf %s: %s", kennung, pfad)
    return _eintrag_oder_fehler(quelle.eintrag(pfad), pfad)


@router.post("/{kennung}/umbenennen", response_model=Eintrag)
def umbenennen(kennung: str, anfrage: Umbenennen, d: DiensteAbh) -> Eintrag:
    quelle = d.register.hole(kennung)
    eltern = elternordner(anfrage.pfad)
    if eltern is None:
        raise QuellenFehler("Der oberste Ordner lässt sich nicht umbenennen.")
    neuer_pfad = verbinde(eltern, pruefe_name(anfrage.neuer_name))
    quelle.benenne_um(anfrage.pfad, neuer_pfad)
    log.info("Umbenannt auf %s: %s -> %s", kennung, anfrage.pfad, neuer_pfad)
    return _eintrag_oder_fehler(quelle.eintrag(neuer_pfad), neuer_pfad)


@router.post("/{kennung}/loeschen", response_model=LoeschErgebnis)
def loeschen(kennung: str, anfrage: Loeschen, d: DiensteAbh) -> LoeschErgebnis:
    quelle = d.register.hole(kennung)
    for pfad in anfrage.pfade:
        quelle.loesche(pfad)
        log.info("Gelöscht auf %s (Papierkorb: %s): %s", kennung, quelle.loeschen_in_papierkorb, pfad)
    return LoeschErgebnis(geloescht=len(anfrage.pfade), in_papierkorb=quelle.loeschen_in_papierkorb)


@router.put("/{kennung}/datei", response_model=Eintrag)
async def hochladen(
    kennung: str,
    request: Request,
    d: DiensteAbh,
    pfad: str,
    geaendert: Annotated[int | None, Query(description="Änderungszeit in Millisekunden seit 1970")] = None,
) -> Eintrag:
    """Der Rumpf ist der rohe Dateiinhalt. Er wird ohne Zwischendatei weitergereicht."""
    quelle = d.register.hole(kennung)
    zeitpunkt = datetime.fromtimestamp(geaendert / 1000) if geaendert else None
    await verarbeite_strom(request.stream(), lambda bloecke: quelle.schreibe(pfad, bloecke, zeitpunkt))
    log.info("Hochgeladen auf %s: %s", kennung, pfad)
    return _eintrag_oder_fehler(quelle.eintrag(pfad), pfad)


@router.get("/{kennung}/datei")
def herunterladen(kennung: str, d: DiensteAbh, pfad: str) -> StreamingResponse:
    quelle = d.register.hole(kennung)
    eintrag = _eintrag_oder_fehler(quelle.eintrag(pfad), pfad)
    if eintrag.art == Eintragsart.ORDNER:
        raise QuellenFehler("Ordner lassen sich nur mit einem Auftrag übertragen.")
    medientyp = mimetypes.guess_type(eintrag.name)[0] or "application/octet-stream"
    kopf = {"Content-Disposition": f"attachment; filename*=UTF-8''{quote(eintrag.name)}"}
    if eintrag.groesse is not None:
        kopf["Content-Length"] = str(eintrag.groesse)
    inhalt: Iterator[bytes] = quelle.lese(pfad)
    return StreamingResponse(inhalt, media_type=medientyp, headers=kopf)
