"""Hält alle verfügbaren Dateiquellen: den Mac und jedes freigegebene Android-Gerät.

Ein Hintergrund-Thread verfolgt über adb, wann Geräte kommen und gehen,
und meldet jede Änderung über den Verteiler an die Oberfläche.
"""

import logging
import threading
import time

import adbutils

from faehre.dienste.verteiler import Verteiler
from faehre.modelle import GeraeteHinweis, Quelle, Quellenstand
from faehre.quellen.android import AndroidQuelle
from faehre.quellen.basis import Dateiquelle, NichtGefunden
from faehre.quellen.mac import MacQuelle

log = logging.getLogger(__name__)
_WARTEZEIT_NACH_ADB_FEHLER = 3.0
_BEREIT = "device"
_ZUSTANDSMELDUNGEN = {
    "unauthorized": "Wartet auf Freigabe: am Telefon \"USB-Debugging zulassen\" bestätigen.",
    "offline": "Verbindung gestört: Kabel kurz abziehen und wieder einstecken.",
    "authorizing": "Freigabe wird geprüft.",
    "connecting": "Verbindung wird aufgebaut.",
}


class Quellenregister:
    def __init__(self, mac: MacQuelle, android_start: str, verteiler: Verteiler) -> None:
        self._mac = mac
        self._android_start = android_start
        self._verteiler = verteiler
        self._geraete: dict[str, AndroidQuelle] = {}
        self._beschreibungen: dict[str, Quelle] = {}
        self._hinweise: list[GeraeteHinweis] = []
        self._adb_fehler: str | None = None
        self._sperre = threading.Lock()

    def alle(self) -> list[Dateiquelle]:
        with self._sperre:
            return [self._mac, *self._geraete.values()]

    def stand(self) -> Quellenstand:
        with self._sperre:
            geraete = [self._beschreibungen[s] for s in self._geraete]
            hinweise = list(self._hinweise)
            adb_fehler = self._adb_fehler
        return Quellenstand(quellen=[self._mac.beschreibung(), *geraete], hinweise=hinweise, adb_fehler=adb_fehler)

    def hole(self, kennung: str) -> Dateiquelle:
        for quelle in self.alle():
            if quelle.kennung == kennung:
                return quelle
        raise NichtGefunden("Das Gerät ist nicht mehr verbunden.")

    def starte_ueberwachung(self) -> None:
        threading.Thread(target=self._ueberwache, name="geraeteueberwachung", daemon=True).start()

    def _ueberwache(self) -> None:
        while True:
            try:
                self._aktualisiere()
                for _ereignis in adbutils.adb.track_devices():
                    self._aktualisiere()
            except Exception as fehler:  # noqa: BLE001 - die Überwachung darf nie enden
                log.warning("Geräteüberwachung unterbrochen: %s", fehler)
                self._setze_adb_fehler("Der adb-Dienst läuft nicht. Er wird automatisch neu gestartet.")
                self._starte_adb_dienst()
                time.sleep(_WARTEZEIT_NACH_ADB_FEHLER)

    @staticmethod
    def _starte_adb_dienst() -> None:
        try:
            adbutils.adb.server_version()
        except Exception:  # noqa: BLE001 - der nächste Durchlauf versucht es erneut
            log.debug("adb-Dienst antwortet noch nicht")

    def _aktualisiere(self) -> None:
        angeschlossen = adbutils.adb.list()
        bereite = {g.serial for g in angeschlossen if g.state == _BEREIT}
        hinweise = [
            GeraeteHinweis(seriennummer=g.serial, meldung=_ZUSTANDSMELDUNGEN.get(g.state, f"Zustand: {g.state}"))
            for g in angeschlossen
            if g.state != _BEREIT
        ]
        neue = {s: self._verbinde(s) for s in bereite if s not in self._geraete}
        with self._sperre:
            for seriennummer in list(self._geraete):
                if seriennummer not in bereite:
                    del self._geraete[seriennummer]
                    del self._beschreibungen[seriennummer]
            for seriennummer, (quelle, beschreibung) in neue.items():
                self._geraete[seriennummer] = quelle
                self._beschreibungen[seriennummer] = beschreibung
            self._hinweise = hinweise
            self._adb_fehler = None
        self._verteiler.sende("quellen", self.stand())

    def _verbinde(self, seriennummer: str) -> tuple[AndroidQuelle, Quelle]:
        quelle = AndroidQuelle(adbutils.adb.device(serial=seriennummer), self._android_start)
        return quelle, quelle.beschreibung()

    def _setze_adb_fehler(self, fehler: str) -> None:
        with self._sperre:
            self._geraete.clear()
            self._beschreibungen.clear()
            self._hinweise = []
            self._adb_fehler = fehler
        self._verteiler.sende("quellen", self.stand())
