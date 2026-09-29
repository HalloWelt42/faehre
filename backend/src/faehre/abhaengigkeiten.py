"""Zugriff der Routen auf die Dienste, die beim Start im App-Zustand abgelegt werden."""

from dataclasses import dataclass

from fastapi import Request

from faehre.config import Einstellungen
from faehre.dienste.auftraege import Auftragsdienst
from faehre.dienste.verteiler import Verteiler
from faehre.quellen.register import Quellenregister


@dataclass(frozen=True)
class Dienste:
    einstellungen: Einstellungen
    verteiler: Verteiler
    register: Quellenregister
    auftraege: Auftragsdienst


def dienste(request: Request) -> Dienste:
    ergebnis = request.app.state.dienste
    assert isinstance(ergebnis, Dienste)
    return ergebnis
