"""Tests ohne Telefon: Mac-Quelle, Sortierung, Seiten und Aufträge Mac zu Mac.

Alle Testdateien liegen in .test-daten im Projektordner.
"""

import os
import shutil
import time
from collections.abc import Iterator
from pathlib import Path

import pytest

from faehre.config import PROJEKT_WURZEL
from faehre.dienste.auftraege import Auftragsdienst
from faehre.dienste.ordner import ordnerseite, sortiere
from faehre.dienste.verteiler import Verteiler
from faehre.modelle import AuftragsAnfrage, Auftragsart, Auftragsstatus, BeiVorhanden, Eintrag, Eintragsart, Sortierung
from faehre.quellen.basis import QuellenFehler, liegt_in
from faehre.quellen.mac import MacQuelle
from faehre.quellen.register import Quellenregister


@pytest.fixture
def testordner(request: pytest.FixtureRequest) -> Iterator[Path]:
    ordner = PROJEKT_WURZEL / ".test-daten" / "pytest" / request.node.name
    shutil.rmtree(ordner, ignore_errors=True)
    ordner.mkdir(parents=True)
    yield ordner
    shutil.rmtree(ordner, ignore_errors=True)


@pytest.fixture
def mac() -> MacQuelle:
    return MacQuelle(startordner="", blockgroesse=4)


def _eintrag(name: str, art: Eintragsart = Eintragsart.DATEI, groesse: int = 0) -> Eintrag:
    return Eintrag(name=name, pfad=f"/{name}", art=art, groesse=groesse)


def test_natuerliche_sortierung_mit_ordnern_oben() -> None:
    eintraege = [_eintrag("datei10"), _eintrag("Datei2"), _eintrag("zordner", Eintragsart.ORDNER), _eintrag("datei1")]
    namen = [e.name for e in sortiere(eintraege, Sortierung.NAME, absteigend=False)]
    assert namen == ["zordner", "datei1", "Datei2", "datei10"]


def test_sortierung_nach_groesse_absteigend() -> None:
    eintraege = [_eintrag("a", groesse=1), _eintrag("b", groesse=30), _eintrag("c", groesse=5)]
    assert [e.name for e in sortiere(eintraege, Sortierung.GROESSE, absteigend=True)] == ["b", "c", "a"]


def test_seiten_und_versteckte(testordner: Path, mac: MacQuelle) -> None:
    for nummer in range(5):
        (testordner / f"d{nummer}.txt").write_text("x")
    (testordner / ".versteckt").write_text("x")
    seite = ordnerseite(mac, str(testordner), ab=2, anzahl=2, sortierung=Sortierung.NAME, absteigend=False, versteckte=False)
    assert seite.gesamt == 5
    assert [e.name for e in seite.eintraege] == ["d2.txt", "d3.txt"]
    alle = ordnerseite(mac, str(testordner), ab=0, anzahl=50, sortierung=Sortierung.NAME, absteigend=False, versteckte=True)
    assert alle.gesamt == 6


def test_liegt_in() -> None:
    assert liegt_in("/a/b/c", "/a/b")
    assert liegt_in("/a/b", "/a/b/")
    assert not liegt_in("/a/bc", "/a/b")


def _warte(dienst: Auftragsdienst, kennung: str) -> Auftragsstatus:
    for _ in range(200):
        auftrag = next(a for a in dienst.alle() if a.kennung == kennung)
        if auftrag.status not in (Auftragsstatus.WARTET, Auftragsstatus.LAEUFT):
            return auftrag.status
        time.sleep(0.02)
    raise TimeoutError(kennung)


def _dienst(mac: MacQuelle) -> Auftragsdienst:
    verteiler = Verteiler()
    return Auftragsdienst(Quellenregister(mac, "/sdcard", verteiler), verteiler)


def test_ordner_kopieren_erhaelt_inhalt_und_datum(testordner: Path, mac: MacQuelle) -> None:
    quelle = testordner / "quelle"
    (quelle / "unter").mkdir(parents=True)
    (quelle / "unter" / "a.txt").write_text("Inhalt mit Umlauten äöü")
    ziel = testordner / "ziel"
    ziel.mkdir()
    zeit = 1_577_964_600
    (quelle / "unter" / "a.txt").touch()
    os.utime(quelle / "unter" / "a.txt", (zeit, zeit))
    dienst = _dienst(mac)
    auftrag = dienst.lege_an(
        AuftragsAnfrage(art=Auftragsart.KOPIEREN, quelle="mac", pfade=[str(quelle)], ziel_quelle="mac", ziel_ordner=str(ziel))
    )
    assert _warte(dienst, auftrag.kennung) == Auftragsstatus.FERTIG
    kopie = ziel / "quelle" / "unter" / "a.txt"
    assert kopie.read_text() == "Inhalt mit Umlauten äöü"
    assert int(kopie.stat().st_mtime) == zeit


def test_ueberspringen_laesst_vorhandenes_unberuehrt(testordner: Path, mac: MacQuelle) -> None:
    (testordner / "a.txt").write_text("neu")
    ziel = testordner / "ziel"
    ziel.mkdir()
    (ziel / "a.txt").write_text("alt")
    dienst = _dienst(mac)
    anfrage = AuftragsAnfrage(
        art=Auftragsart.KOPIEREN,
        quelle="mac",
        pfade=[str(testordner / "a.txt")],
        ziel_quelle="mac",
        ziel_ordner=str(ziel),
        bei_vorhanden=BeiVorhanden.UEBERSPRINGEN,
    )
    assert dienst.pruefe(anfrage).vorhanden == ["a.txt"]
    assert _warte(dienst, dienst.lege_an(anfrage).kennung) == Auftragsstatus.FERTIG
    assert (ziel / "a.txt").read_text() == "alt"


def test_verschieben_innerhalb_der_quelle(testordner: Path, mac: MacQuelle) -> None:
    (testordner / "a.txt").write_text("x")
    ziel = testordner / "ziel"
    ziel.mkdir()
    dienst = _dienst(mac)
    anfrage = AuftragsAnfrage(
        art=Auftragsart.VERSCHIEBEN, quelle="mac", pfade=[str(testordner / "a.txt")], ziel_quelle="mac", ziel_ordner=str(ziel)
    )
    assert _warte(dienst, dienst.lege_an(anfrage).kennung) == Auftragsstatus.FERTIG
    assert not (testordner / "a.txt").exists()
    assert (ziel / "a.txt").read_text() == "x"


def test_kopieren_in_sich_selbst_wird_abgelehnt(testordner: Path, mac: MacQuelle) -> None:
    (testordner / "unter").mkdir()
    anfrage = AuftragsAnfrage(
        art=Auftragsart.KOPIEREN, quelle="mac", pfade=[str(testordner)], ziel_quelle="mac", ziel_ordner=str(testordner / "unter")
    )
    with pytest.raises(QuellenFehler):
        _dienst(mac).lege_an(anfrage)
