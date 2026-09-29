// Rechtsklick-Menü: welche Punkte, an welcher Stelle.

export interface Menuepunkt {
  text: string;
  symbol: string;
  taste?: string;
  gefahr?: boolean;
  gesperrt?: boolean;
  ausfuehren: () => void;
}

/** null steht für eine Trennlinie zwischen Gruppen. */
export type Menueeintrag = Menuepunkt | null;

interface OffenesMenue {
  x: number;
  y: number;
  titel: string | null;
  eintraege: Menueeintrag[];
}

class Kontextmenue {
  offen = $state<OffenesMenue | null>(null);

  zeige(ereignis: MouseEvent, titel: string | null, eintraege: Menueeintrag[]): void {
    ereignis.preventDefault();
    this.offen = { x: ereignis.clientX, y: ereignis.clientY, titel, eintraege };
  }

  schliesse(): void {
    this.offen = null;
  }
}

export const kontextmenue = new Kontextmenue();
