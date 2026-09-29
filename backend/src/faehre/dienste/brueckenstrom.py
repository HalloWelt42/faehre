"""Brücke von einem asynchronen Datenstrom (HTTP-Anfrage) zu einem synchronen Iterator.

Die Dateiquellen arbeiten synchron in einem Thread. Hochgeladene Daten kommen
asynchron aus der Anfrage. Eine begrenzte Warteschlange verbindet beide, ohne die
ganze Datei zwischenzuspeichern. Scheitert der Empfänger, endet auch das Einlesen.
"""

import asyncio
import queue
from collections.abc import AsyncIterator, Callable, Iterator
from typing import TypeVar

_ENDE = object()
_PUFFER_BLOECKE = 16
_WARTEZEIT_SEKUNDEN = 0.5

Ergebnis = TypeVar("Ergebnis")


class _Abbruch(Exception):
    pass


async def verarbeite_strom(strom: AsyncIterator[bytes], verbraucher: Callable[[Iterator[bytes]], Ergebnis]) -> Ergebnis:
    """Ruft verbraucher in einem Thread mit einem Iterator über den Strom auf."""
    warteschlange: queue.Queue[object] = queue.Queue(maxsize=_PUFFER_BLOECKE)

    def bloecke() -> Iterator[bytes]:
        while True:
            block = warteschlange.get()
            if block is _ENDE:
                return
            if isinstance(block, _Abbruch):
                raise ConnectionError("Übertragung vom Browser abgebrochen")
            assert isinstance(block, bytes)
            yield block

    arbeit = asyncio.ensure_future(asyncio.to_thread(verbraucher, bloecke()))

    async def lege_ab(eintrag: object) -> bool:
        """False, wenn der Empfänger nicht mehr liest."""
        while not arbeit.done():
            try:
                await asyncio.to_thread(warteschlange.put, eintrag, True, _WARTEZEIT_SEKUNDEN)
                return True
            except queue.Full:
                continue
        return False

    try:
        async for block in strom:
            if block and not await lege_ab(block):
                break
        else:
            await lege_ab(_ENDE)
    except BaseException:
        await lege_ab(_Abbruch())
        raise
    return await arbeit
