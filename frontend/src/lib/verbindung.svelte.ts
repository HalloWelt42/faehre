// Hält den Ereignisstrom zum Backend offen: Geräte und Aufträge kommen hier an.
import { api } from './api';
import { ABGESCHLOSSEN, type Auftrag, type Quelle, type Quellenstand } from './typen';

type AbschlussBeobachter = (auftrag: Auftrag) => void;

class Verbindung {
  stand = $state<Quellenstand>({ quellen: [], hinweise: [], adb_fehler: null });
  auftraege = $state<Auftrag[]>([]);
  verbunden = $state(false);
  /** Version des Dienstes. Weicht sie von der dieser Oberfläche ab, bietet die App das Neuladen an. */
  dienstVersion = $state('');
  private beobachter = new Set<AbschlussBeobachter>();
  private strom: EventSource | null = null;

  starte(): void {
    this.strom?.close();
    const strom = new EventSource('/api/ereignisse');
    this.strom = strom;
    strom.onopen = () => {
      this.verbunden = true;
      this.auftraege = [];
      void this.pruefeVersion();
    };
    strom.onerror = () => (this.verbunden = false);
    strom.addEventListener('quellen', (e) => (this.stand = JSON.parse(e.data) as Quellenstand));
    strom.addEventListener('auftrag', (e) => this.uebernimm(JSON.parse(e.data) as Auftrag));
    strom.addEventListener('auftraege', (e) => (this.auftraege = JSON.parse(e.data) as Auftrag[]));
  }

  private async pruefeVersion(): Promise<void> {
    try {
      this.dienstVersion = (await api.status()).version;
    } catch {
      // Beim nächsten Verbindungsaufbau erneut
    }
  }

  get veraltet(): boolean {
    return this.dienstVersion !== '' && this.dienstVersion !== __FAEHRE_VERSION__;
  }

  quelle(kennung: string): Quelle | undefined {
    return this.stand.quellen.find((q) => q.kennung === kennung);
  }

  /** Wird aufgerufen, sobald ein Auftrag fertig, fehlgeschlagen oder abgebrochen ist. */
  beiAbschluss(beobachter: AbschlussBeobachter): () => void {
    this.beobachter.add(beobachter);
    return () => this.beobachter.delete(beobachter);
  }

  private uebernimm(auftrag: Auftrag): void {
    const index = this.auftraege.findIndex((a) => a.kennung === auftrag.kennung);
    const vorher = index >= 0 ? this.auftraege[index] : undefined;
    if (index >= 0) this.auftraege[index] = auftrag;
    else this.auftraege.push(auftrag);
    // Nur echte Übergänge melden. Beim Wiederverbinden schickt der Dienst auch längst
    // abgeschlossene Aufträge, die dürfen keine neue Erfolgsmeldung auslösen.
    const jetztFertig = ABGESCHLOSSEN.includes(auftrag.status);
    const warOffen = vorher !== undefined && !ABGESCHLOSSEN.includes(vorher.status);
    if (jetztFertig && warOffen) this.beobachter.forEach((b) => b(auftrag));
  }
}

export const verbindung = new Verbindung();
