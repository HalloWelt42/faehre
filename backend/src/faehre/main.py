"""Einstiegspunkt: baut die Dienste zusammen und hängt die Routen ein."""

import asyncio
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from adbutils import AdbError
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from faehre.abhaengigkeiten import Dienste
from faehre.config import einstellungen
from faehre.dienste.auftraege import Auftragsdienst
from faehre.dienste.verteiler import Verteiler
from faehre.quellen.adb_sync import AdbSyncFehler
from faehre.quellen.basis import NichtGefunden, QuellenFehler
from faehre.quellen.mac import MacQuelle
from faehre.quellen.register import Quellenregister
from faehre.routen import auftraege, quellen, system
from faehre.version import lies_version


# Änderungen an Dateien stehen mit Pfad im Protokoll (.run/backend.log), damit sie nachvollziehbar bleiben.
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lebenszyklus(app: FastAPI) -> AsyncIterator[None]:
    verteiler = Verteiler()
    verteiler.binde_an_schleife(asyncio.get_running_loop())
    mac = MacQuelle(einstellungen.mac_start, einstellungen.blockgroesse)
    register = Quellenregister(mac, einstellungen.android_start, verteiler)
    app.state.dienste = Dienste(
        einstellungen=einstellungen,
        verteiler=verteiler,
        register=register,
        auftraege=Auftragsdienst(register, verteiler),
    )
    register.starte_ueberwachung()
    yield


app = FastAPI(title="Fähre", version=lies_version().voll, lifespan=lebenszyklus)


@app.middleware("http")
async def ohne_zwischenspeicher(request: Request, weiter: Callable[[Request], Awaitable[Response]]) -> Response:
    """Ordnerinhalte ändern sich laufend: kein Browser und kein Proxy darf API-Antworten aufheben."""
    antwort = await weiter(request)
    if request.url.path.startswith("/api/"):
        antwort.headers["Cache-Control"] = "no-store"
    return antwort


app.include_router(system.router)
app.include_router(quellen.router)
app.include_router(auftraege.router)


def _fehlerantwort(status_code: int, meldung: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"meldung": meldung})


@app.exception_handler(NichtGefunden)
async def nicht_gefunden(_: Request, fehler: NichtGefunden) -> JSONResponse:
    return _fehlerantwort(404, str(fehler))


@app.exception_handler(QuellenFehler)
async def quellenfehler(_: Request, fehler: QuellenFehler) -> JSONResponse:
    return _fehlerantwort(400, str(fehler))


@app.exception_handler(AdbError)
@app.exception_handler(AdbSyncFehler)
async def geraetefehler(_: Request, fehler: Exception) -> JSONResponse:
    return _fehlerantwort(502, f"Fehler bei der Verbindung zum Telefon: {fehler}")


@app.exception_handler(PermissionError)
async def keine_berechtigung(_: Request, fehler: PermissionError) -> JSONResponse:
    return _fehlerantwort(403, f"Keine Berechtigung: {fehler.filename or fehler}")
