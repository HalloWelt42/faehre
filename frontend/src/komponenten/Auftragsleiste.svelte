<script lang="ts">
  import { api } from '../lib/api';
  import { anzahl, groesse } from '../lib/format';
  import { hochladen } from '../lib/hochladen.svelte';
  import { meldungen } from '../lib/meldungen.svelte';
  import { ABGESCHLOSSEN, type Auftragsstatus } from '../lib/typen';
  import { verbindung } from '../lib/verbindung.svelte';

  /** Gemeinsame Sicht auf Aufträge des Dienstes und Uploads aus dem Finder. */
  interface Anzeige {
    kennung: string;
    symbol: string;
    titel: string;
    status: Auftragsstatus;
    bytesFertig: number;
    bytesGesamt: number;
    dateienFertig: number;
    dateienGesamt: number;
    aktuelleDatei: string | null;
    fehler: string | null;
    abbrechen: () => void;
  }

  const startzeiten = new Map<string, number>();

  function ortName(kennung: string, ordner: string): string {
    const name = verbindung.quelle(kennung)?.name ?? 'Gerät';
    return `${name}: ${ordner.split('/').filter(Boolean).pop() ?? '/'}`;
  }

  const anzeigen = $derived.by((): Anzeige[] => [
    ...verbindung.auftraege.map((a) => ({
      kennung: a.kennung,
      symbol: a.art === 'verschieben' ? 'fa-right-long' : 'fa-copy',
      titel: `${a.art === 'verschieben' ? 'Verschieben' : 'Kopieren'} nach ${ortName(a.ziel_quelle, a.ziel_ordner)}`,
      status: a.status,
      bytesFertig: a.bytes_fertig,
      bytesGesamt: a.bytes_gesamt,
      dateienFertig: a.dateien_fertig,
      dateienGesamt: a.dateien_gesamt,
      aktuelleDatei: a.aktuelle_datei,
      fehler: a.fehler,
      abbrechen: () => void api.abbrechen(a.kennung).catch((f) => meldungen.fehler(f)),
    })),
    ...hochladen.liste.map((p) => ({
      kennung: p.kennung,
      symbol: 'fa-arrow-up-from-bracket',
      titel: `Hochladen nach ${ortName(p.zielQuelle, p.zielOrdner)}`,
      status: p.status,
      bytesFertig: p.bytes_fertig,
      bytesGesamt: p.bytes_gesamt,
      dateienFertig: p.dateien_fertig,
      dateienGesamt: p.dateien_gesamt,
      aktuelleDatei: p.aktuelle_datei,
      fehler: p.fehler,
      abbrechen: () => hochladen.brichAb(p.kennung),
    })),
  ]);

  const hatErledigte = $derived(anzeigen.some((a) => ABGESCHLOSSEN.includes(a.status)));

  function anteil(a: Anzeige): number {
    if (a.bytesGesamt > 0) return Math.min(100, (a.bytesFertig / a.bytesGesamt) * 100);
    if (a.dateienGesamt > 0) return (a.dateienFertig / a.dateienGesamt) * 100;
    return a.status === 'fertig' ? 100 : 0;
  }

  function mengen(a: Anzeige): string {
    const dateien = `${a.dateienFertig.toLocaleString('de-DE')} von ${anzahl(a.dateienGesamt, 'Datei', 'Dateien')}`;
    return a.bytesGesamt > 0 ? `${dateien}, ${groesse(a.bytesFertig)} von ${groesse(a.bytesGesamt)}` : dateien;
  }

  function tempo(a: Anzeige): string {
    if (a.status !== 'laeuft' || a.bytesFertig === 0) return '';
    const jetzt = performance.now();
    if (!startzeiten.has(a.kennung)) startzeiten.set(a.kennung, jetzt);
    const sekunden = (jetzt - startzeiten.get(a.kennung)!) / 1000;
    if (sekunden < 1) return '';
    const proSekunde = a.bytesFertig / sekunden;
    const rest = Math.max(0, (a.bytesGesamt - a.bytesFertig) / proSekunde);
    return `${groesse(proSekunde)}/s, noch ${restzeit(rest)}`;
  }

  function restzeit(sekunden: number): string {
    if (sekunden < 60) return anzahl(Math.ceil(sekunden), 'Sekunde', 'Sekunden');
    return anzahl(Math.ceil(sekunden / 60), 'Minute', 'Minuten');
  }

  const STATUS_SYMBOL: Record<Auftragsstatus, string> = {
    wartet: 'fa-hourglass-half',
    laeuft: 'fa-spinner fa-spin',
    fertig: 'fa-circle-check',
    fehler: 'fa-circle-exclamation',
    abgebrochen: 'fa-ban',
  };

  async function raeumeAuf(): Promise<void> {
    hochladen.raeumeAuf();
    try {
      await api.aufraeumen();
    } catch (fehler) {
      meldungen.fehler(fehler);
    }
  }
</script>

{#if anzeigen.length > 0}
  <section class="leiste" aria-label="Übertragungen">
    <div class="eintraege">
      {#each anzeigen as a (a.kennung)}
        <div class="auftrag {a.status}">
          <i class="fa-solid {a.symbol} art"></i>
          <div class="mitte">
            <div class="zeile">
              <strong>{a.titel}</strong>
              <span class="zahlen">{mengen(a)}</span>
            </div>
            <div class="balken"><div style:width="{anteil(a)}%"></div></div>
            <div class="zeile leise">
              {#if a.fehler}
                <span class="fehlertext">{a.fehler}</span>
              {:else if a.aktuelleDatei}
                <span class="datei">{a.aktuelleDatei}</span>
              {:else if a.status === 'abgebrochen'}
                <span>Abgebrochen</span>
              {/if}
              <span>{tempo(a)}</span>
            </div>
          </div>
          <i class="fa-solid {STATUS_SYMBOL[a.status]} status"></i>
          {#if a.status === 'laeuft' || a.status === 'wartet'}
            <button class="symbolknopf" onclick={a.abbrechen} title="Übertragung abbrechen. Bereits übertragene Dateien bleiben erhalten.">
              <i class="fa-solid fa-xmark"></i>
            </button>
          {/if}
        </div>
      {/each}
    </div>
    {#if hatErledigte}
      <button class="knopf aufraeumen" onclick={raeumeAuf} title="Abgeschlossene Übertragungen aus der Liste entfernen">
        <i class="fa-solid fa-broom"></i> Erledigte entfernen
      </button>
    {/if}
  </section>
{/if}

<style>
  .leiste {
    display: flex;
    align-items: flex-end;
    gap: 0.6rem;
    padding: 0.5rem 0.6rem;
    border-radius: var(--f-radius);
    background: var(--f-flaeche);
  }

  .eintraege {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
    max-height: 11rem;
    overflow-y: auto;
    overflow-x: clip;
    min-width: 0;
  }

  .auftrag {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.35rem 0.5rem;
    border-radius: var(--f-radius-klein);
    background: var(--f-flaeche-2);
  }

  .art {
    color: var(--f-akzent);
    width: 1.1rem;
    text-align: center;
  }

  .mitte {
    flex: 1;
    min-width: 0;
  }

  .zeile {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    min-width: 0;
  }

  .zeile strong {
    font-weight: 600;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .zahlen,
  .leise {
    color: var(--f-text-leise);
    font-size: 0.85rem;
    white-space: nowrap;
    font-variant-numeric: tabular-nums;
  }

  .datei,
  .fehlertext {
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .fehlertext {
    color: var(--f-gefahr);
    white-space: normal;
  }

  .balken {
    height: 5px;
    margin: 0.3rem 0;
    border-radius: 5px;
    background: var(--f-flaeche-3);
    overflow: hidden;
  }

  .balken div {
    height: 100%;
    background: var(--f-akzent);
    transition: width 0.25s linear;
  }

  .fertig .balken div {
    background: var(--f-erfolg);
  }

  .fehler .balken div {
    background: var(--f-gefahr);
  }

  .status {
    color: var(--f-text-leise);
  }

  .fertig .status {
    color: var(--f-erfolg);
  }

  .fehler .status {
    color: var(--f-gefahr);
  }

  .aufraeumen {
    flex-shrink: 0;
  }
</style>
