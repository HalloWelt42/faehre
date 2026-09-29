// Drag & Drop: zwischen den Ordnerseiten, aus dem Finder hinein und als Datei hinaus.
import { dateiUrl } from './api';
import { anzahl } from './format';
import type { Eintrag } from './typen';

const FAEHRE_TYP = 'application/x-faehre';

export interface GezogeneEintraege {
  quelle: string;
  pfade: string[];
}

export interface FinderDatei {
  datei: File;
  /** Pfad relativ zum Ablageort, etwa "Urlaub/Tag 1/bild.jpg". */
  relativ: string;
}

export interface FinderInhalt {
  dateien: FinderDatei[];
  /** Ordner, auch leere, relativ zum Ablageort. Eltern stehen vor Kindern. */
  ordner: string[];
  /** Namen der obersten Ebene, für die Prüfung auf vorhandene Namen. */
  obersteNamen: string[];
}

/** Beginn eines Zuges aus einer Ordnerseite. */
export function beginneZiehen(ereignis: DragEvent, quelle: string, eintraege: Eintrag[]): void {
  const daten = ereignis.dataTransfer;
  if (!daten || eintraege.length === 0) return;
  const inhalt: GezogeneEintraege = { quelle, pfade: eintraege.map((e) => e.pfad) };
  daten.effectAllowed = 'copyMove';
  daten.setData(FAEHRE_TYP, JSON.stringify(inhalt));
  daten.setData('text/plain', eintraege.map((e) => e.name).join('\n'));
  const einzelDatei = eintraege.length === 1 && eintraege[0]!.art !== 'ordner' ? eintraege[0]! : null;
  if (einzelDatei) {
    // Chromium-Format: die Datei lässt sich so direkt in den Finder ziehen.
    const adresse = new URL(dateiUrl(quelle, einzelDatei.pfad), location.origin).href;
    daten.setData('DownloadURL', `application/octet-stream:${einzelDatei.name}:${adresse}`);
  }
  setzeZugbild(daten, eintraege);
}

function setzeZugbild(daten: DataTransfer, eintraege: Eintrag[]): void {
  const bild = document.createElement('div');
  bild.className = 'zugbild';
  bild.textContent = eintraege.length === 1 ? eintraege[0]!.name : anzahl(eintraege.length, 'Eintrag', 'Einträge');
  document.body.appendChild(bild);
  daten.setDragImage(bild, 14, 14);
  requestAnimationFrame(() => bild.remove());
}

export function istEigenerZug(ereignis: DragEvent): boolean {
  return ereignis.dataTransfer?.types.includes(FAEHRE_TYP) ?? false;
}

export function istFinderZug(ereignis: DragEvent): boolean {
  const typen = ereignis.dataTransfer?.types ?? [];
  return typen.includes('Files') && !typen.includes(FAEHRE_TYP);
}

export function liesEigenenZug(ereignis: DragEvent): GezogeneEintraege | null {
  const roh = ereignis.dataTransfer?.getData(FAEHRE_TYP);
  return roh ? (JSON.parse(roh) as GezogeneEintraege) : null;
}

/** Mit gedrückter Befehlstaste wird verschoben, sonst kopiert (wie im Finder zwischen Laufwerken). */
export function willVerschieben(ereignis: DragEvent): boolean {
  return ereignis.metaKey;
}

// --- Finder ------------------------------------------------------------------

export interface FinderAblage {
  eintraege: FileSystemEntry[];
  /** Rückfall ohne Ordnerzugriff: nur die direkt gezogenen Dateien. */
  dateien: File[];
}

/** Muss noch im drop-Ereignis selbst laufen, danach gibt der Browser die Daten nicht mehr heraus. */
export function holeFinderAblage(ereignis: DragEvent): FinderAblage {
  const eintraege: FileSystemEntry[] = [];
  for (const element of Array.from(ereignis.dataTransfer?.items ?? [])) {
    const eintrag = element.kind === 'file' ? element.webkitGetAsEntry() : null;
    if (eintrag) eintraege.push(eintrag);
  }
  return { eintraege, dateien: Array.from(ereignis.dataTransfer?.files ?? []) };
}

export async function sammleFinderInhalt(ablage: FinderAblage): Promise<FinderInhalt> {
  if (ablage.eintraege.length === 0) {
    return {
      dateien: ablage.dateien.map((datei) => ({ datei, relativ: datei.name })),
      ordner: [],
      obersteNamen: ablage.dateien.map((d) => d.name),
    };
  }
  const inhalt: FinderInhalt = { dateien: [], ordner: [], obersteNamen: ablage.eintraege.map((e) => e.name) };
  for (const eintrag of ablage.eintraege) await sammle(eintrag, '', inhalt);
  return inhalt;
}

async function sammle(eintrag: FileSystemEntry, eltern: string, inhalt: FinderInhalt): Promise<void> {
  const relativ = eltern ? `${eltern}/${eintrag.name}` : eintrag.name;
  if (eintrag.isFile) {
    const datei = await new Promise<File>((erfuellt, abgelehnt) => (eintrag as FileSystemFileEntry).file(erfuellt, abgelehnt));
    inhalt.dateien.push({ datei, relativ });
    return;
  }
  if (!eintrag.isDirectory) return;
  inhalt.ordner.push(relativ);
  for (const kind of await liesOrdner(eintrag as FileSystemDirectoryEntry)) await sammle(kind, relativ, inhalt);
}

/** readEntries liefert höchstens rund 100 Einträge je Aufruf, deshalb bis zur leeren Antwort lesen. */
async function liesOrdner(ordner: FileSystemDirectoryEntry): Promise<FileSystemEntry[]> {
  const leser = ordner.createReader();
  const alle: FileSystemEntry[] = [];
  for (;;) {
    const teil = await new Promise<FileSystemEntry[]>((erfuellt, abgelehnt) => leser.readEntries(erfuellt, abgelehnt));
    if (teil.length === 0) return alle;
    alle.push(...teil);
  }
}
