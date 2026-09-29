// Eigene Dialoge statt der Browser-Dialoge. Jeder Aufruf liefert ein Promise mit der Wahl.

export type Knopfart = 'haupt' | 'gefahr' | 'normal';

export interface Knopf<W extends string> {
  wert: W;
  text: string;
  art: Knopfart;
}

interface OffenerDialog {
  titel: string;
  text: string;
  liste: string[];
  knoepfe: Knopf<string>[];
  eingabe: { wert: string; markierung: [number, number] } | null;
  erledige: (ergebnis: { wahl: string | null; eingabe: string }) => void;
}

class Dialoge {
  /** Dialoge warten in einer Schlange: ein neuer verdrängt nie einen offenen. */
  private schlange = $state<OffenerDialog[]>([]);

  get offen(): OffenerDialog | null {
    return this.schlange[0] ?? null;
  }

  /** Frage mit mehreren Knöpfen. null bedeutet: abgebrochen (Escape). */
  frage<W extends string>(titel: string, text: string, knoepfe: Knopf<W>[], liste: string[] = []): Promise<W | null> {
    return new Promise((erfuellt) => {
      this.schlange.push({
        titel,
        text,
        liste,
        knoepfe,
        eingabe: null,
        erledige: ({ wahl }) => erfuellt(wahl as W | null),
      });
    });
  }

  /** Texteingabe, etwa für einen neuen Namen. null bedeutet: abgebrochen. */
  eingabe(titel: string, text: string, vorgabe: string, bestaetigen: string): Promise<string | null> {
    // Beim Umbenennen nur den Namen ohne Endung vorauswählen, wie im Finder.
    const punkt = vorgabe.lastIndexOf('.');
    const ende = punkt > 0 ? punkt : vorgabe.length;
    return new Promise((erfuellt) => {
      this.schlange.push({
        titel,
        text,
        liste: [],
        knoepfe: [
          { wert: 'abbrechen', text: 'Abbrechen', art: 'normal' },
          { wert: 'ok', text: bestaetigen, art: 'haupt' },
        ],
        eingabe: { wert: vorgabe, markierung: [0, ende] },
        erledige: ({ wahl, eingabe }) => {
          const name = eingabe.trim();
          erfuellt(wahl === 'ok' && name ? name : null);
        },
      });
    });
  }

  schliesse(wahl: string | null, eingabe = ''): void {
    const dialog = this.schlange.shift();
    dialog?.erledige({ wahl: wahl === 'abbrechen' ? null : wahl, eingabe });
  }
}

export const dialoge = new Dialoge();
