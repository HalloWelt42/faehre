// Kurze Rückmeldungen am Bildschirmrand, verschwinden von selbst.

export type Meldungsart = 'erfolg' | 'fehler' | 'info';

export interface Meldung {
  kennung: string;
  art: Meldungsart;
  text: string;
}

const ANZEIGEDAUER_MS: Record<Meldungsart, number> = { erfolg: 3500, info: 4500, fehler: 9000 };

class Meldungen {
  liste = $state<Meldung[]>([]);

  zeige(art: Meldungsart, text: string): void {
    const kennung = crypto.randomUUID();
    this.liste.push({ kennung, art, text });
    setTimeout(() => this.schliesse(kennung), ANZEIGEDAUER_MS[art]);
  }

  fehler(fehler: unknown): void {
    this.zeige('fehler', fehler instanceof Error ? fehler.message : String(fehler));
  }

  schliesse(kennung: string): void {
    this.liste = this.liste.filter((m) => m.kennung !== kennung);
  }
}

export const meldungen = new Meldungen();
