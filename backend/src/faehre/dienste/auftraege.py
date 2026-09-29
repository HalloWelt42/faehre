"""Kopier- und Verschiebeaufträge zwischen beliebigen Dateiquellen.

Aufträge laufen nacheinander in einem Hintergrund-Thread, damit sich mehrere
Übertragungen nicht die eine USB-Verbindung teilen. Jeder Fortschritt geht als
Ereignis an die Oberfläche. Der Dienst kennt nur die Schnittstelle Dateiquelle.
"""

import logging
import threading
import time
import uuid
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime

from faehre.dienste.verteiler import Verteiler
from faehre.modelle import (
    Auftrag,
    AuftragsAnfrage,
    Auftragsart,
    Auftragsstatus,
    BeiVorhanden,
    Eintrag,
    Eintragsart,
    KonfliktPruefung,
)
from faehre.quellen.basis import Dateiquelle, NichtGefunden, QuellenFehler, dateiname, liegt_in, verbinde
from faehre.quellen.register import Quellenregister

log = logging.getLogger(__name__)
# Fortschritt höchstens so oft melden, damit die Oberfläche nicht geflutet wird.
_MELDEABSTAND_SEKUNDEN = 0.25
_ABGESCHLOSSEN = {Auftragsstatus.FERTIG, Auftragsstatus.FEHLER, Auftragsstatus.ABGEBROCHEN}


class Abgebrochen(Exception):
    pass


@dataclass(frozen=True)
class Kopierschritt:
    """Eine einzelne Datei oder ein anzulegender Ordner mit Quell- und Zielpfad."""

    eintrag: Eintrag
    ziel: str


class Auftragsdienst:
    def __init__(self, register: Quellenregister, verteiler: Verteiler) -> None:
        self._register = register
        self._verteiler = verteiler
        self._auftraege: dict[str, Auftrag] = {}
        self._abbrueche: set[str] = set()
        self._sperre = threading.Lock()
        self._ausfuehrer = ThreadPoolExecutor(max_workers=1, thread_name_prefix="auftrag")

    def alle(self) -> list[Auftrag]:
        with self._sperre:
            return sorted(self._auftraege.values(), key=lambda a: a.erstellt)

    def pruefe(self, anfrage: AuftragsAnfrage) -> KonfliktPruefung:
        ziel = self._register.hole(anfrage.ziel_quelle)
        namen = [dateiname(pfad) for pfad in anfrage.pfade]
        return KonfliktPruefung(vorhanden=ziel.vorhandene_namen(anfrage.ziel_ordner, namen))

    def lege_an(self, anfrage: AuftragsAnfrage) -> Auftrag:
        self._pruefe_ziel_nicht_in_quelle(anfrage)
        auftrag = Auftrag(
            kennung=uuid.uuid4().hex,
            art=anfrage.art,
            quelle=anfrage.quelle,
            ziel_quelle=anfrage.ziel_quelle,
            ziel_ordner=anfrage.ziel_ordner,
            pfade=anfrage.pfade,
            status=Auftragsstatus.WARTET,
            erstellt=datetime.now(),
        )
        with self._sperre:
            self._auftraege[auftrag.kennung] = auftrag
        log.info(
            "Auftrag %s: %s von %s %s nach %s:%s",
            auftrag.kennung, auftrag.art, auftrag.quelle, auftrag.pfade, auftrag.ziel_quelle, auftrag.ziel_ordner,
        )
        self._melde(auftrag)
        self._ausfuehrer.submit(self._fuehre_aus, auftrag.kennung, anfrage.bei_vorhanden)
        return auftrag

    def brich_ab(self, kennung: str) -> None:
        with self._sperre:
            if kennung not in self._auftraege:
                raise NichtGefunden("Auftrag nicht gefunden.")
            self._abbrueche.add(kennung)

    def raeume_auf(self) -> None:
        """Entfernt abgeschlossene Aufträge aus der Liste."""
        with self._sperre:
            for kennung in [k for k, a in self._auftraege.items() if a.status in _ABGESCHLOSSEN]:
                del self._auftraege[kennung]
        self._verteiler.sende("auftraege", self.alle())

    def _pruefe_ziel_nicht_in_quelle(self, anfrage: AuftragsAnfrage) -> None:
        if anfrage.quelle != anfrage.ziel_quelle:
            return
        for pfad in anfrage.pfade:
            if liegt_in(anfrage.ziel_ordner, pfad):
                raise QuellenFehler(f"{dateiname(pfad)} kann nicht in sich selbst kopiert werden.")

    # --- Ausführung im Hintergrund ------------------------------------------

    def _fuehre_aus(self, kennung: str, bei_vorhanden: BeiVorhanden) -> None:
        auftrag = self._auftraege[kennung]
        try:
            quelle = self._register.hole(auftrag.quelle)
            ziel = self._register.hole(auftrag.ziel_quelle)
            self._aendere(auftrag, status=Auftragsstatus.LAEUFT)
            if auftrag.art == Auftragsart.VERSCHIEBEN and quelle is ziel:
                self._verschiebe_intern(auftrag, quelle, bei_vorhanden)
            else:
                self._uebertrage(auftrag, quelle, ziel, bei_vorhanden)
            self._aendere(auftrag, status=Auftragsstatus.FERTIG, aktuelle_datei=None)
        except Abgebrochen:
            self._aendere(auftrag, status=Auftragsstatus.ABGEBROCHEN, aktuelle_datei=None)
        except Exception as fehler:  # noqa: BLE001 - jeder Fehler landet sichtbar im Auftrag
            log.exception("Auftrag %s fehlgeschlagen", kennung)
            self._aendere(auftrag, status=Auftragsstatus.FEHLER, fehler=str(fehler) or type(fehler).__name__)
        finally:
            with self._sperre:
                self._abbrueche.discard(kennung)

    def _zu_bearbeiten(self, auftrag: Auftrag, ziel: Dateiquelle, bei_vorhanden: BeiVorhanden) -> list[str]:
        if bei_vorhanden == BeiVorhanden.UEBERSCHREIBEN:
            return auftrag.pfade
        return [p for p in auftrag.pfade if ziel.eintrag(verbinde(auftrag.ziel_ordner, dateiname(p))) is None]

    def _verschiebe_intern(self, auftrag: Auftrag, quelle: Dateiquelle, bei_vorhanden: BeiVorhanden) -> None:
        pfade = self._zu_bearbeiten(auftrag, quelle, bei_vorhanden)
        self._aendere(auftrag, dateien_gesamt=len(pfade))
        for pfad in pfade:
            self._pruefe_abbruch(auftrag)
            neuer_pfad = verbinde(auftrag.ziel_ordner, dateiname(pfad))
            self._aendere(auftrag, aktuelle_datei=dateiname(pfad))
            if quelle.eintrag(neuer_pfad) is not None:
                log.info("Auftrag %s ersetzt %s", auftrag.kennung, neuer_pfad)
                quelle.loesche(neuer_pfad)
            quelle.benenne_um(pfad, neuer_pfad)
            self._aendere(auftrag, dateien_fertig=auftrag.dateien_fertig + 1)

    def _uebertrage(self, auftrag: Auftrag, quelle: Dateiquelle, ziel: Dateiquelle, bei_vorhanden: BeiVorhanden) -> None:
        pfade = self._zu_bearbeiten(auftrag, ziel, bei_vorhanden)
        schritte = [s for pfad in pfade for s in self._plane(quelle, pfad, verbinde(auftrag.ziel_ordner, dateiname(pfad)))]
        dateien = [s for s in schritte if s.eintrag.art != Eintragsart.ORDNER]
        self._aendere(
            auftrag,
            dateien_gesamt=len(dateien),
            bytes_gesamt=sum(s.eintrag.groesse or 0 for s in dateien),
        )
        for schritt in schritte:
            self._pruefe_abbruch(auftrag)
            if schritt.eintrag.art == Eintragsart.ORDNER:
                ziel.ordner_anlegen(schritt.ziel)
                continue
            self._aendere(auftrag, aktuelle_datei=schritt.eintrag.name)
            ziel.schreibe(schritt.ziel, self._mit_fortschritt(auftrag, quelle.lese(schritt.eintrag.pfad)), schritt.eintrag.geaendert)
            self._aendere(auftrag, dateien_fertig=auftrag.dateien_fertig + 1)
        if auftrag.art == Auftragsart.VERSCHIEBEN:
            for pfad in pfade:
                log.info("Auftrag %s entfernt verschobene Quelle %s", auftrag.kennung, pfad)
                quelle.loesche(pfad)

    def _plane(self, quelle: Dateiquelle, pfad: str, ziel: str) -> Iterator[Kopierschritt]:
        """Zerlegt einen Pfad in Ordner-Anlagen und Dateikopien, Eltern vor Kindern."""
        eintrag = quelle.eintrag(pfad)
        if eintrag is None:
            raise NichtGefunden(f"Nicht gefunden: {pfad}")
        yield Kopierschritt(eintrag=eintrag, ziel=ziel)
        if eintrag.art != Eintragsart.ORDNER:
            return
        for kind in quelle.liste(pfad):
            kind_ziel = verbinde(ziel, kind.name)
            if kind.art == Eintragsart.ORDNER:
                yield from self._plane(quelle, kind.pfad, kind_ziel)
            else:
                yield Kopierschritt(eintrag=kind, ziel=kind_ziel)

    def _mit_fortschritt(self, auftrag: Auftrag, bloecke: Iterator[bytes]) -> Iterator[bytes]:
        letzte_meldung = 0.0
        for block in bloecke:
            self._pruefe_abbruch(auftrag)
            auftrag.bytes_fertig += len(block)
            jetzt = time.monotonic()
            if jetzt - letzte_meldung >= _MELDEABSTAND_SEKUNDEN:
                letzte_meldung = jetzt
                self._melde(auftrag)
            yield block

    def _pruefe_abbruch(self, auftrag: Auftrag) -> None:
        with self._sperre:
            if auftrag.kennung in self._abbrueche:
                raise Abgebrochen()

    def _aendere(self, auftrag: Auftrag, **felder: object) -> None:
        for name, wert in felder.items():
            setattr(auftrag, name, wert)
        self._melde(auftrag)

    def _melde(self, auftrag: Auftrag) -> None:
        self._verteiler.sende("auftrag", auftrag)
