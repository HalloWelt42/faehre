// Zustand einer Ordnerseite: welche Quelle, welcher Ordner, was ist geladen und ausgewählt.
import { SvelteSet } from 'svelte/reactivity';
import { api } from './api';
import { meldungen } from './meldungen.svelte';
import type { Eintrag, Sortierung } from './typen';

export type Seitenname = 'links' | 'rechts';

interface GemerkteAnsicht {
  quelle: string;
  pfad: string;
  sortierung: Sortierung;
  absteigend: boolean;
  versteckte: boolean;
}

function lies(name: Seitenname): Partial<GemerkteAnsicht> {
  try {
    return JSON.parse(localStorage.getItem(`faehre.seite.${name}`) ?? '{}') as Partial<GemerkteAnsicht>;
  } catch {
    return {};
  }
}

export class OrdnerseitenZustand {
  readonly name: Seitenname;
  quelle = $state('');
  pfad = $state('');
  sortierung = $state<Sortierung>('name');
  absteigend = $state(false);
  versteckte = $state(false);

  eintraege = $state<Eintrag[]>([]);
  gesamt = $state(0);
  eltern = $state<string | null>(null);
  laedt = $state(false);
  fehler = $state<string | null>(null);

  markiert = new SvelteSet<string>();
  fokus = $state(0);
  private anker = 0;
  private ladelauf = 0;

  constructor(name: Seitenname) {
    this.name = name;
    const gemerkt = lies(name);
    this.quelle = gemerkt.quelle ?? '';
    this.pfad = gemerkt.pfad ?? '';
    this.sortierung = gemerkt.sortierung ?? 'name';
    this.absteigend = gemerkt.absteigend ?? false;
    this.versteckte = gemerkt.versteckte ?? false;
  }

  get fokussiert(): Eintrag | undefined {
    return this.eintraege[this.fokus];
  }

  /** Markierte Einträge, sonst der fokussierte. */
  get auswahl(): Eintrag[] {
    if (this.markiert.size > 0) return this.eintraege.filter((e) => this.markiert.has(e.pfad));
    const eintrag = this.fokussiert;
    return eintrag ? [eintrag] : [];
  }

  get vollstaendig(): boolean {
    return this.eintraege.length >= this.gesamt;
  }

  async oeffne(quelle: string, pfad: string, fokusName?: string): Promise<void> {
    this.quelle = quelle;
    this.pfad = pfad;
    this.merke();
    await this.lade(fokusName);
  }

  async hoch(): Promise<void> {
    if (this.eltern === null) return;
    const bisher = this.pfad.split('/').filter(Boolean).pop();
    await this.oeffne(this.quelle, this.eltern, bisher);
  }

  /** Lädt die erste Seite neu. Fokus bleibt nach Möglichkeit auf demselben Namen. */
  async lade(fokusName = this.fokussiert?.name): Promise<void> {
    const lauf = ++this.ladelauf;
    this.laedt = true;
    try {
      const seite = await api.ordner(this.quelle, this.pfad, 0, this.sortierung, this.absteigend, this.versteckte);
      if (lauf !== this.ladelauf) return;
      this.eintraege = seite.eintraege;
      this.gesamt = seite.gesamt;
      this.eltern = seite.eltern;
      this.fehler = null;
      this.markiert.clear();
      const index = fokusName ? this.eintraege.findIndex((e) => e.name === fokusName) : -1;
      this.fokus = Math.max(0, index);
      this.anker = this.fokus;
    } catch (fehler) {
      if (lauf !== this.ladelauf) return;
      this.eintraege = [];
      this.gesamt = 0;
      // Auch ohne Antwort soll der Weg nach oben offen bleiben.
      this.eltern = this.pfad === '/' ? null : this.pfad.replace(/\/+$/, '').replace(/\/[^/]*$/, '') || '/';
      this.fehler = fehler instanceof Error ? fehler.message : String(fehler);
    } finally {
      if (lauf === this.ladelauf) this.laedt = false;
    }
  }

  /** Nächste Seite anhängen. Der Dienst gibt die Seitengröße vor. */
  async ladeWeiter(): Promise<void> {
    if (this.laedt || this.vollstaendig) return;
    const lauf = this.ladelauf;
    this.laedt = true;
    try {
      const seite = await api.ordner(this.quelle, this.pfad, this.eintraege.length, this.sortierung, this.absteigend, this.versteckte);
      if (lauf !== this.ladelauf) return;
      this.eintraege.push(...seite.eintraege);
      this.gesamt = seite.gesamt;
    } catch (fehler) {
      meldungen.fehler(fehler);
    } finally {
      if (lauf === this.ladelauf) this.laedt = false;
    }
  }

  async sortiereNach(sortierung: Sortierung): Promise<void> {
    if (this.sortierung === sortierung) this.absteigend = !this.absteigend;
    else {
      this.sortierung = sortierung;
      this.absteigend = sortierung !== 'name';
    }
    this.merke();
    await this.lade();
  }

  async schalteVersteckte(): Promise<void> {
    this.versteckte = !this.versteckte;
    this.merke();
    await this.lade();
  }

  // --- Auswahl --------------------------------------------------------------

  klick(index: number, umschalten: boolean, bereich: boolean): void {
    if (bereich) {
      this.markiereBereich(this.anker, index);
    } else if (umschalten) {
      this.schalteMarkierung(index);
      this.anker = index;
    } else {
      this.markiert.clear();
      this.anker = index;
    }
    this.fokus = index;
  }

  /** Beim Ziehen: gehört der Eintrag nicht zur Auswahl, wird nur er gezogen. */
  waehleZumZiehen(index: number): Eintrag[] {
    const eintrag = this.eintraege[index];
    if (!eintrag) return [];
    if (!this.markiert.has(eintrag.pfad)) {
      this.markiert.clear();
      this.fokus = index;
      this.anker = index;
      return [eintrag];
    }
    return this.auswahl;
  }

  bewegeFokus(schritt: number, bereich: boolean): void {
    if (this.eintraege.length === 0) return;
    const ziel = Math.min(this.eintraege.length - 1, Math.max(0, this.fokus + schritt));
    if (bereich) this.markiereBereich(this.anker, ziel);
    else this.anker = ziel;
    this.fokus = ziel;
    if (ziel >= this.eintraege.length - 5) void this.ladeWeiter();
  }

  schalteMarkierung(index: number): void {
    const eintrag = this.eintraege[index];
    if (!eintrag) return;
    if (this.markiert.has(eintrag.pfad)) this.markiert.delete(eintrag.pfad);
    else this.markiert.add(eintrag.pfad);
  }

  markiereAlle(): void {
    this.eintraege.forEach((e) => this.markiert.add(e.pfad));
  }

  hebeAuswahlAuf(): void {
    this.markiert.clear();
  }

  private markiereBereich(von: number, bis: number): void {
    this.markiert.clear();
    const [anfang, ende] = von <= bis ? [von, bis] : [bis, von];
    for (let i = anfang; i <= ende; i++) {
      const eintrag = this.eintraege[i];
      if (eintrag) this.markiert.add(eintrag.pfad);
    }
  }

  private merke(): void {
    const ansicht: GemerkteAnsicht = {
      quelle: this.quelle,
      pfad: this.pfad,
      sortierung: this.sortierung,
      absteigend: this.absteigend,
      versteckte: this.versteckte,
    };
    try {
      localStorage.setItem(`faehre.seite.${this.name}`, JSON.stringify(ansicht));
    } catch {
      // Ohne Speicher startet die Seite beim nächsten Mal im Startordner.
    }
  }
}
