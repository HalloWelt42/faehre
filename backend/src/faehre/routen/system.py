"""Status und Ereignisstrom für die Oberfläche."""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends
from sse_starlette import EventSourceResponse, ServerSentEvent

from faehre.abhaengigkeiten import Dienste, dienste
from faehre.modelle import Status
from faehre.version import lies_version

router = APIRouter(prefix="/api", tags=["System"])
DiensteAbh = Annotated[Dienste, Depends(dienste)]


@router.get("/status", response_model=Status)
def status() -> Status:
    return Status(version=lies_version().voll)


@router.get("/ereignisse")
async def ereignisse(d: DiensteAbh) -> EventSourceResponse:
    """Erst der aktuelle Stand, danach jede Änderung an Geräten und Aufträgen."""

    async def strom() -> AsyncIterator[ServerSentEvent]:
        yield ServerSentEvent(event="quellen", data=d.register.stand().model_dump_json())
        for auftrag in d.auftraege.alle():
            yield ServerSentEvent(event="auftrag", data=auftrag.model_dump_json())
        async for ereignis in d.verteiler.abonniere():
            yield ServerSentEvent(event=ereignis.art, data=ereignis.daten)

    return EventSourceResponse(strom(), ping=15)
