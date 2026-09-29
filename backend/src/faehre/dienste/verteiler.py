"""Verteilt Ereignisse an alle offenen Oberflächen (Server-Sent Events).

Ereignisse entstehen auch in Hintergrund-Threads (Übertragungen, Geräteüberwachung).
Deshalb reicht der Verteiler sie threadsicher in die Ereignisschleife weiter.
"""

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass

from pydantic import BaseModel


@dataclass(frozen=True)
class Ereignis:
    art: str
    daten: str


class Verteiler:
    def __init__(self) -> None:
        self._schleife: asyncio.AbstractEventLoop | None = None
        self._abonnenten: set[asyncio.Queue[Ereignis]] = set()

    def binde_an_schleife(self, schleife: asyncio.AbstractEventLoop) -> None:
        self._schleife = schleife

    def sende(self, art: str, inhalt: BaseModel | list[BaseModel]) -> None:
        """Aus jedem Thread aufrufbar."""
        if self._schleife is None:
            return
        if isinstance(inhalt, list):
            daten = "[" + ",".join(e.model_dump_json() for e in inhalt) + "]"
        else:
            daten = inhalt.model_dump_json()
        self._schleife.call_soon_threadsafe(self._verteile, Ereignis(art=art, daten=daten))

    def _verteile(self, ereignis: Ereignis) -> None:
        for warteschlange in self._abonnenten:
            warteschlange.put_nowait(ereignis)

    async def abonniere(self) -> AsyncIterator[Ereignis]:
        warteschlange: asyncio.Queue[Ereignis] = asyncio.Queue()
        self._abonnenten.add(warteschlange)
        try:
            while True:
                yield await warteschlange.get()
        finally:
            self._abonnenten.discard(warteschlange)
