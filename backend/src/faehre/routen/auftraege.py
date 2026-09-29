"""Kopier- und Verschiebeaufträge anlegen, prüfen und abbrechen."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from faehre.abhaengigkeiten import Dienste, dienste
from faehre.modelle import Auftrag, AuftragsAnfrage, KonfliktPruefung

router = APIRouter(prefix="/api/auftraege", tags=["Aufträge"])
DiensteAbh = Annotated[Dienste, Depends(dienste)]


@router.get("", response_model=list[Auftrag])
def auftraege(d: DiensteAbh) -> list[Auftrag]:
    return d.auftraege.alle()


@router.post("/pruefen", response_model=KonfliktPruefung)
def pruefen(anfrage: AuftragsAnfrage, d: DiensteAbh) -> KonfliktPruefung:
    """Welche Namen gibt es im Zielordner schon? Die Oberfläche fragt dann nach."""
    return d.auftraege.pruefe(anfrage)


@router.post("", response_model=Auftrag, status_code=status.HTTP_201_CREATED)
def anlegen(anfrage: AuftragsAnfrage, d: DiensteAbh) -> Auftrag:
    return d.auftraege.lege_an(anfrage)


@router.post("/{kennung}/abbrechen", status_code=status.HTTP_204_NO_CONTENT)
def abbrechen(kennung: str, d: DiensteAbh) -> Response:
    d.auftraege.brich_ab(kennung)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/aufraeumen", response_model=list[Auftrag])
def aufraeumen(d: DiensteAbh) -> list[Auftrag]:
    d.auftraege.raeume_auf()
    return d.auftraege.alle()
