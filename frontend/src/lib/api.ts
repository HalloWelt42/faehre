// Einzige Stelle, die mit dem Backend spricht.
import type {
  Auftrag,
  AuftragsAnfrage,
  Eintrag,
  KonfliktPruefung,
  LoeschErgebnis,
  Ordnerseite,
  Quellenstand,
  Sortierung,
  Status,
} from './typen';

export class ApiFehler extends Error {}

async function antwort<T>(anfrage: Promise<Response>): Promise<T> {
  let ergebnis: Response;
  try {
    ergebnis = await anfrage;
  } catch {
    throw new ApiFehler('Der Fähre-Dienst ist nicht erreichbar. Läuft ./start.sh?');
  }
  if (ergebnis.status === 204) return undefined as T;
  const daten: unknown = await ergebnis.json().catch(() => null);
  if (!ergebnis.ok) {
    const meldung = (daten as { meldung?: string } | null)?.meldung;
    throw new ApiFehler(meldung ?? `Anfrage fehlgeschlagen (${ergebnis.status})`);
  }
  return daten as T;
}

function holen<T>(pfad: string): Promise<T> {
  return antwort<T>(fetch(pfad, { cache: 'no-store' }));
}

function senden<T>(pfad: string, rumpf: unknown): Promise<T> {
  return antwort<T>(
    fetch(pfad, {
      method: 'POST',
      cache: 'no-store',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(rumpf),
    }),
  );
}

const quelleUrl = (kennung: string): string => `/api/quellen/${encodeURIComponent(kennung)}`;

export function dateiUrl(kennung: string, pfad: string): string {
  return `${quelleUrl(kennung)}/datei?${new URLSearchParams({ pfad })}`;
}

export const api = {
  status: (): Promise<Status> => holen('/api/status'),
  quellen: (): Promise<Quellenstand> => holen('/api/quellen'),

  ordner: (
    kennung: string,
    pfad: string,
    ab: number,
    sortierung: Sortierung,
    absteigend: boolean,
    versteckte: boolean,
  ): Promise<Ordnerseite> => {
    const parameter = new URLSearchParams({
      pfad,
      ab: String(ab),
      sortierung,
      absteigend: String(absteigend),
      versteckte: String(versteckte),
    });
    return holen(`${quelleUrl(kennung)}/ordner?${parameter}`);
  },

  vorhanden: (kennung: string, ordner: string, namen: string[]): Promise<KonfliktPruefung> =>
    senden(`${quelleUrl(kennung)}/vorhanden`, { ordner, namen }),

  ordnerAnlegen: (kennung: string, ordner: string, name: string): Promise<Eintrag> =>
    senden(`${quelleUrl(kennung)}/ordner-anlegen`, { ordner, name }),

  umbenennen: (kennung: string, pfad: string, neuerName: string): Promise<Eintrag> =>
    senden(`${quelleUrl(kennung)}/umbenennen`, { pfad, neuer_name: neuerName }),

  loeschen: (kennung: string, pfade: string[]): Promise<LoeschErgebnis> =>
    senden(`${quelleUrl(kennung)}/loeschen`, { pfade }),

  auftraege: (): Promise<Auftrag[]> => holen('/api/auftraege'),
  pruefen: (anfrage: AuftragsAnfrage): Promise<KonfliktPruefung> => senden('/api/auftraege/pruefen', anfrage),
  auftragAnlegen: (anfrage: AuftragsAnfrage): Promise<Auftrag> => senden('/api/auftraege', anfrage),
  abbrechen: (kennung: string): Promise<void> => senden(`/api/auftraege/${kennung}/abbrechen`, {}),
  aufraeumen: (): Promise<Auftrag[]> => senden('/api/auftraege/aufraeumen', {}),
};

/** Lädt eine Datei hoch. Eigener Weg über XMLHttpRequest, weil nur dieser den Fortschritt meldet. */
export function hochladen(
  kennung: string,
  pfad: string,
  datei: File,
  fortschritt: (bytes: number) => void,
  signal: AbortSignal,
): Promise<void> {
  const parameter = new URLSearchParams({ pfad, geaendert: String(datei.lastModified) });
  return new Promise((erfuellt, abgelehnt) => {
    const anfrage = new XMLHttpRequest();
    anfrage.open('PUT', `${quelleUrl(kennung)}/datei?${parameter}`);
    anfrage.upload.onprogress = (e) => fortschritt(e.loaded);
    anfrage.onload = () => {
      if (anfrage.status < 300) return erfuellt();
      let meldung = `Hochladen fehlgeschlagen (${anfrage.status})`;
      try {
        meldung = (JSON.parse(anfrage.responseText) as { meldung?: string }).meldung ?? meldung;
      } catch {
        // Antwort war kein JSON, allgemeine Meldung bleibt
      }
      abgelehnt(new ApiFehler(meldung));
    };
    anfrage.onerror = () => abgelehnt(new ApiFehler('Verbindung zum Fähre-Dienst unterbrochen'));
    anfrage.onabort = () => abgelehnt(new DOMException('Abgebrochen', 'AbortError'));
    signal.addEventListener('abort', () => anfrage.abort(), { once: true });
    anfrage.send(datei);
  });
}
