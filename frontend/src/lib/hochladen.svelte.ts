// Warteschlange für Dateien, die aus dem Finder in eine Ordnerseite gezogen wurden.
// Posten laufen nacheinander, der Fortschritt erscheint in der Auftragsleiste.
import { api, hochladen as ladeDateiHoch } from './api';
import type { FinderInhalt } from './ziehen';
import type { Auftragsstatus } from './typen';

export interface Hochladeposten {
  kennung: string;
  zielQuelle: string;
  zielOrdner: string;
  status: Auftragsstatus;
  bytes_gesamt: number;
  bytes_fertig: number;
  dateien_gesamt: number;
  dateien_fertig: number;
  aktuelle_datei: string | null;
  fehler: string | null;
}

type AbschlussBeobachter = (posten: Hochladeposten) => void;

function verbinde(ordner: string, relativ: string): string {
  return `${ordner.replace(/\/+$/, '')}/${relativ}`;
}

class Hochladen {
  liste = $state<Hochladeposten[]>([]);
  private abbrueche = new Map<string, AbortController>();
  private beobachter = new Set<AbschlussBeobachter>();
  private kette: Promise<void> = Promise.resolve();

  starte(zielQuelle: string, zielOrdner: string, inhalt: FinderInhalt): void {
    const kennung = crypto.randomUUID();
    this.liste.push({
      kennung,
      zielQuelle,
      zielOrdner,
      status: 'wartet',
      bytes_gesamt: inhalt.dateien.reduce((summe, d) => summe + d.datei.size, 0),
      bytes_fertig: 0,
      dateien_gesamt: inhalt.dateien.length,
      dateien_fertig: 0,
      aktuelle_datei: null,
      fehler: null,
    });
    const abbruch = new AbortController();
    this.abbrueche.set(kennung, abbruch);
    this.kette = this.kette.then(() => this.fuehreAus(kennung, inhalt, abbruch.signal));
  }

  brichAb(kennung: string): void {
    this.abbrueche.get(kennung)?.abort();
  }

  raeumeAuf(): void {
    this.liste = this.liste.filter((p) => p.status === 'wartet' || p.status === 'laeuft');
  }

  beiAbschluss(beobachter: AbschlussBeobachter): () => void {
    this.beobachter.add(beobachter);
    return () => this.beobachter.delete(beobachter);
  }

  private posten(kennung: string): Hochladeposten {
    return this.liste.find((p) => p.kennung === kennung)!;
  }

  private async fuehreAus(kennung: string, inhalt: FinderInhalt, signal: AbortSignal): Promise<void> {
    const posten = this.posten(kennung);
    if (signal.aborted) return this.schliesseAb(posten, 'abgebrochen');
    posten.status = 'laeuft';
    try {
      await this.legeOrdnerAn(posten, inhalt.ordner);
      for (const { datei, relativ } of inhalt.dateien) {
        posten.aktuelle_datei = datei.name;
        const bisher = posten.bytes_fertig;
        await ladeDateiHoch(posten.zielQuelle, verbinde(posten.zielOrdner, relativ), datei, (bytes) => (posten.bytes_fertig = bisher + bytes), signal);
        posten.bytes_fertig = bisher + datei.size;
        posten.dateien_fertig += 1;
      }
      this.schliesseAb(posten, 'fertig');
    } catch (fehler) {
      if (signal.aborted) this.schliesseAb(posten, 'abgebrochen');
      else this.schliesseAb(posten, 'fehler', fehler instanceof Error ? fehler.message : String(fehler));
    }
  }

  /** Leere Ordner entstehen nur so; Ordner mit Inhalt legt das Hochladen ohnehin an. */
  private async legeOrdnerAn(posten: Hochladeposten, ordner: string[]): Promise<void> {
    const vorhanden = new Set((await api.vorhanden(posten.zielQuelle, posten.zielOrdner, ordner)).vorhanden);
    for (const relativ of ordner) {
      if (vorhanden.has(relativ)) continue;
      const trenner = relativ.lastIndexOf('/');
      const eltern = trenner < 0 ? posten.zielOrdner : verbinde(posten.zielOrdner, relativ.slice(0, trenner));
      await api.ordnerAnlegen(posten.zielQuelle, eltern, relativ.slice(trenner + 1));
    }
  }

  private schliesseAb(posten: Hochladeposten, status: Auftragsstatus, fehler: string | null = null): void {
    posten.status = status;
    posten.fehler = fehler;
    posten.aktuelle_datei = null;
    this.abbrueche.delete(posten.kennung);
    this.beobachter.forEach((b) => b(posten));
  }
}

export const hochladen = new Hochladen();
