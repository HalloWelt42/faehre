// Dateioperationen mit allen Rückfragen. Oberfläche und Tastatur rufen nur diese Funktionen auf.
import { api, dateiUrl } from './api';
import { dialoge } from './dialoge.svelte';
import { anzahl } from './format';
import { hochladen } from './hochladen.svelte';
import { meldungen } from './meldungen.svelte';
import type { OrdnerseitenZustand } from './ordnerseite.svelte';
import type { Auftragsart, BeiVorhanden, Eintrag } from './typen';
import { verbindung } from './verbindung.svelte';
import type { FinderInhalt } from './ziehen';

export interface Ziel {
  quelle: string;
  ordner: string;
}

const MAX_NAMEN_IN_LISTE = 12;

function namenliste(namen: string[]): string[] {
  if (namen.length <= MAX_NAMEN_IN_LISTE) return namen;
  const rest = namen.length - MAX_NAMEN_IN_LISTE;
  return [...namen.slice(0, MAX_NAMEN_IN_LISTE), `und ${anzahl(rest, 'weiterer Eintrag', 'weitere Einträge')}`];
}

function zielname(ziel: Ziel): string {
  const quelle = verbindung.quelle(ziel.quelle)?.name ?? ziel.quelle;
  return `${quelle}: ${ziel.ordner}`;
}

/** Fragt bei vorhandenen Namen nach. null heißt: der Nutzer hat abgebrochen. */
async function klaereVorhandene(vorhanden: string[]): Promise<BeiVorhanden | null> {
  if (vorhanden.length === 0) return 'ueberschreiben';
  const text =
    vorhanden.length === 1
      ? 'Diesen Namen gibt es im Zielordner schon.'
      : `Diese ${anzahl(vorhanden.length, 'Namen', 'Namen')} gibt es im Zielordner schon.`;
  return dialoge.frage<BeiVorhanden>(
    'Schon vorhanden',
    `${text} Beim Überschreiben werden Dateien ersetzt und Ordner zusammengeführt.`,
    [
      { wert: 'ueberspringen', text: 'Vorhandene überspringen', art: 'normal' },
      { wert: 'ueberschreiben', text: 'Überschreiben', art: 'gefahr' },
    ],
    namenliste(vorhanden),
  );
}

export async function uebertrage(art: Auftragsart, quelle: string, pfade: string[], ziel: Ziel): Promise<void> {
  if (pfade.length === 0) return;
  const gleicherOrdner = quelle === ziel.quelle && pfade.every((p) => p.slice(0, p.lastIndexOf('/')) === ziel.ordner.replace(/\/+$/, ''));
  if (gleicherOrdner) {
    meldungen.zeige('info', 'Quelle und Ziel sind derselbe Ordner.');
    return;
  }
  try {
    const anfrage = { art, quelle, pfade, ziel_quelle: ziel.quelle, ziel_ordner: ziel.ordner, bei_vorhanden: 'ueberschreiben' as BeiVorhanden };
    const beiVorhanden = await klaereVorhandene((await api.pruefen(anfrage)).vorhanden);
    if (beiVorhanden === null) return;
    await api.auftragAnlegen({ ...anfrage, bei_vorhanden: beiVorhanden });
  } catch (fehler) {
    meldungen.fehler(fehler);
  }
}

export async function ladeHoch(ziel: Ziel, inhalt: FinderInhalt): Promise<void> {
  if (inhalt.dateien.length === 0 && inhalt.ordner.length === 0) return;
  try {
    const vorhanden = (await api.vorhanden(ziel.quelle, ziel.ordner, inhalt.obersteNamen)).vorhanden;
    const beiVorhanden = await klaereVorhandene(vorhanden);
    if (beiVorhanden === null) return;
    if (beiVorhanden === 'ueberspringen') {
      const uebersprungen = new Set(vorhanden);
      const behalten = (relativ: string): boolean => !uebersprungen.has(relativ.split('/')[0]!);
      inhalt = {
        dateien: inhalt.dateien.filter((d) => behalten(d.relativ)),
        ordner: inhalt.ordner.filter(behalten),
        obersteNamen: inhalt.obersteNamen.filter((n) => !uebersprungen.has(n)),
      };
    }
    hochladen.starte(ziel.quelle, ziel.ordner, inhalt);
  } catch (fehler) {
    meldungen.fehler(fehler);
  }
}

export async function loesche(seite: OrdnerseitenZustand): Promise<void> {
  const auswahl = seite.auswahl;
  if (auswahl.length === 0) return;
  const quelle = verbindung.quelle(seite.quelle);
  const papierkorb = quelle?.art === 'mac';
  const menge = auswahl.length === 1 ? `"${auswahl[0]!.name}"` : anzahl(auswahl.length, 'Eintrag', 'Einträge');
  const text = papierkorb
    ? `${menge} in den Papierkorb legen? Von dort lässt sich alles wiederherstellen.`
    : `${menge} auf ${quelle?.name ?? 'dem Gerät'} endgültig löschen? Auf dem Telefon gibt es keinen Papierkorb.`;
  const wahl = await dialoge.frage(
    papierkorb ? 'In den Papierkorb' : 'Endgültig löschen',
    text,
    [
      { wert: 'abbrechen', text: 'Abbrechen', art: 'normal' },
      { wert: 'loeschen', text: papierkorb ? 'In den Papierkorb' : 'Endgültig löschen', art: 'gefahr' },
    ],
    namenliste(auswahl.map((e) => e.name)),
  );
  if (wahl !== 'loeschen') return;
  try {
    await api.loeschen(seite.quelle, auswahl.map((e) => e.pfad));
    meldungen.zeige('erfolg', `${anzahl(auswahl.length, 'Eintrag', 'Einträge')} ${papierkorb ? 'im Papierkorb' : 'gelöscht'}`);
  } catch (fehler) {
    meldungen.fehler(fehler);
  }
  await seite.lade();
}

export async function neuerOrdner(seite: OrdnerseitenZustand): Promise<void> {
  const name = await dialoge.eingabe('Neuer Ordner', `In ${zielname({ quelle: seite.quelle, ordner: seite.pfad })}`, 'Neuer Ordner', 'Anlegen');
  if (name === null) return;
  try {
    await api.ordnerAnlegen(seite.quelle, seite.pfad, name);
    await seite.lade(name);
  } catch (fehler) {
    meldungen.fehler(fehler);
  }
}

export async function umbenennen(seite: OrdnerseitenZustand): Promise<void> {
  const eintrag = seite.fokussiert;
  if (!eintrag) return;
  const name = await dialoge.eingabe('Umbenennen', `Neuer Name für "${eintrag.name}"`, eintrag.name, 'Umbenennen');
  if (name === null || name === eintrag.name) return;
  try {
    await api.umbenennen(seite.quelle, eintrag.pfad, name);
    await seite.lade(name);
  } catch (fehler) {
    meldungen.fehler(fehler);
  }
}

/** Die Datei landet im Download-Ordner des Browsers. */
export function herunterladen(quelle: string, eintrag: Eintrag): void {
  const verweis = document.createElement('a');
  verweis.href = dateiUrl(quelle, eintrag.pfad);
  verweis.download = eintrag.name;
  verweis.click();
}

export async function pfadKopieren(pfade: string[]): Promise<void> {
  try {
    await navigator.clipboard.writeText(pfade.join('\n'));
    meldungen.zeige('erfolg', pfade.length === 1 ? 'Pfad kopiert' : `${anzahl(pfade.length, 'Pfad', 'Pfade')} kopiert`);
  } catch (fehler) {
    meldungen.fehler(fehler);
  }
}
