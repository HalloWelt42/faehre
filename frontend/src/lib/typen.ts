// Spiegel der Pydantic-Modelle aus backend/src/faehre/modelle.py.

export type Eintragsart = 'ordner' | 'datei' | 'verweis';

export interface Eintrag {
  name: string;
  pfad: string;
  art: Eintragsart;
  groesse: number | null;
  geaendert: string | null;
  versteckt: boolean;
}

export type Sortierung = 'name' | 'groesse' | 'geaendert';

export interface Ordnerseite {
  quelle: string;
  pfad: string;
  eltern: string | null;
  eintraege: Eintrag[];
  gesamt: number;
  ab: number;
  anzahl: number;
}

export interface Ort {
  name: string;
  pfad: string;
  symbol: string;
  anker: boolean;
}

export type Quellenart = 'mac' | 'android';

export interface Quelle {
  kennung: string;
  name: string;
  art: Quellenart;
  start: string;
  orte: Ort[];
}

export interface GeraeteHinweis {
  seriennummer: string;
  meldung: string;
}

export interface Quellenstand {
  quellen: Quelle[];
  hinweise: GeraeteHinweis[];
  adb_fehler: string | null;
}

export type Auftragsart = 'kopieren' | 'verschieben';
export type Auftragsstatus = 'wartet' | 'laeuft' | 'fertig' | 'fehler' | 'abgebrochen';
export type BeiVorhanden = 'ueberschreiben' | 'ueberspringen';

export interface AuftragsAnfrage {
  art: Auftragsart;
  quelle: string;
  pfade: string[];
  ziel_quelle: string;
  ziel_ordner: string;
  bei_vorhanden: BeiVorhanden;
}

export interface KonfliktPruefung {
  vorhanden: string[];
}

export interface Auftrag {
  kennung: string;
  art: Auftragsart;
  quelle: string;
  ziel_quelle: string;
  ziel_ordner: string;
  pfade: string[];
  status: Auftragsstatus;
  bytes_gesamt: number;
  bytes_fertig: number;
  dateien_gesamt: number;
  dateien_fertig: number;
  aktuelle_datei: string | null;
  fehler: string | null;
  erstellt: string;
}

export interface LoeschErgebnis {
  geloescht: number;
  in_papierkorb: boolean;
}

export interface Status {
  version: string;
}

export const ABGESCHLOSSEN: readonly Auftragsstatus[] = ['fertig', 'fehler', 'abgebrochen'];
