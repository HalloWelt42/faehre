// Helles oder dunkles Thema. Ohne gespeicherte Wahl gilt die Systemeinstellung.

export type Thema = 'hell' | 'dunkel';

const SCHLUESSEL = 'faehre.thema';

function gespeichert(): Thema | null {
  try {
    const wert = localStorage.getItem(SCHLUESSEL);
    return wert === 'hell' || wert === 'dunkel' ? wert : null;
  } catch {
    return null;
  }
}

function system(): Thema {
  return window.matchMedia('(prefers-color-scheme: light)').matches ? 'hell' : 'dunkel';
}

class Themawahl {
  aktuell = $state<Thema>(gespeichert() ?? system());

  constructor() {
    this.anwenden();
  }

  umschalten(): void {
    this.aktuell = this.aktuell === 'hell' ? 'dunkel' : 'hell';
    try {
      localStorage.setItem(SCHLUESSEL, this.aktuell);
    } catch {
      // Ohne Speicher gilt die Wahl nur bis zum Neuladen.
    }
    this.anwenden();
  }

  private anwenden(): void {
    document.documentElement.dataset.thema = this.aktuell;
  }
}

export const thema = new Themawahl();
