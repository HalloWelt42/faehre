<script lang="ts">
  import { herunterladen, ladeHoch, uebertrage } from '../lib/aktionen';
  import type { OrdnerseitenZustand } from '../lib/ordnerseite.svelte';
  import type { Eintrag } from '../lib/typen';
  import { verbindung } from '../lib/verbindung.svelte';
  import { holeFinderAblage, istEigenerZug, liesEigenenZug, sammleFinderInhalt, willVerschieben } from '../lib/ziehen';
  import Dateiliste from './Dateiliste.svelte';
  import OrteMenue from './OrteMenue.svelte';
  import Pfadleiste from './Pfadleiste.svelte';

  interface Props {
    zustand: OrdnerseitenZustand;
    aktiv: boolean;
    onaktiviere: () => void;
    onkontext: (ereignis: MouseEvent, eintrag: Eintrag | null) => void;
  }

  let { zustand, aktiv, onaktiviere, onkontext }: Props = $props();

  const quelle = $derived(verbindung.quelle(zustand.quelle));
  const telefone = $derived(verbindung.stand.quellen.filter((q) => q.art === 'android'));

  function oeffne(eintrag: Eintrag): void {
    if (eintrag.art === 'ordner') {
      void zustand.oeffne(zustand.quelle, eintrag.pfad);
    } else {
      herunterladen(zustand.quelle, eintrag);
    }
  }

  async function ablage(ereignis: DragEvent, zielOrdner: string): Promise<void> {
    const ziel = { quelle: zustand.quelle, ordner: zielOrdner };
    if (istEigenerZug(ereignis)) {
      const gezogen = liesEigenenZug(ereignis);
      if (gezogen) await uebertrage(willVerschieben(ereignis) ? 'verschieben' : 'kopieren', gezogen.quelle, gezogen.pfade, ziel);
      return;
    }
    const finder = holeFinderAblage(ereignis);
    await ladeHoch(ziel, await sammleFinderInhalt(finder));
  }
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<section class="seite" class:aktiv onpointerdown={onaktiviere} ondragenter={onaktiviere}>
  <header>
    <div class="quellen" role="tablist" aria-label="Gerät wählen">
      {#each verbindung.stand.quellen as q (q.kennung)}
        <button
          role="tab"
          aria-selected={q.kennung === zustand.quelle}
          class:gewaehlt={q.kennung === zustand.quelle}
          onclick={() => zustand.oeffne(q.kennung, q.start)}
        >
          <i class="fa-solid {q.art === 'mac' ? 'fa-laptop' : 'fa-mobile-screen-button'}"></i>
          {q.name}
        </button>
      {/each}
      {#if telefone.length === 0}
        <span class="kein-telefon" title="Telefon per Kabel anschließen und USB-Debugging erlauben">
          <i class="fa-solid fa-mobile-screen-button"></i> kein Telefon
        </span>
      {/if}
    </div>
    {#if quelle}
      <div class="werkzeuge">
        <OrteMenue orte={quelle.orte} onwaehle={(ort) => zustand.oeffne(zustand.quelle, ort.pfad)} />
        <button class="symbolknopf" onclick={() => zustand.hoch()} disabled={zustand.eltern === null} title="Übergeordneter Ordner (Rücktaste)">
          <i class="fa-solid fa-arrow-up"></i>
        </button>
        <div class="pfad">
          <Pfadleiste pfad={zustand.pfad} orte={quelle.orte} onoeffne={(pfad) => zustand.oeffne(zustand.quelle, pfad)} />
        </div>
        <button class="symbolknopf" class:an={zustand.versteckte} onclick={() => zustand.schalteVersteckte()} title="Versteckte Dateien (Name beginnt mit Punkt) ein- oder ausblenden">
          <i class="fa-solid fa-eye{zustand.versteckte ? '' : '-slash'}"></i>
        </button>
        <button class="symbolknopf" onclick={() => zustand.lade()} title="Ordner neu einlesen">
          <i class="fa-solid fa-rotate-right"></i>
        </button>
      </div>
    {/if}
  </header>

  {#if quelle}
    <Dateiliste {zustand} {aktiv} onoeffne={oeffne} onablage={ablage} {onkontext} />
  {:else}
    <div class="getrennt">
      <i class="fa-solid fa-mobile-screen-button gross"></i>
      <h3>Kein Telefon verbunden</h3>
      {#if verbindung.stand.adb_fehler}
        <p class="hinweis">{verbindung.stand.adb_fehler}</p>
      {/if}
      {#each verbindung.stand.hinweise as hinweis (hinweis.seriennummer)}
        <p class="hinweis"><i class="fa-solid fa-circle-exclamation"></i> {hinweis.meldung}</p>
      {/each}
      {#if verbindung.stand.hinweise.length === 0}
        <ol>
          <li>Telefon per Kabel direkt am Mac anschließen.</li>
          <li>Am Telefon: Einstellungen, Über das Telefon, 7-mal auf "Build-Nummer" tippen.</li>
          <li>Einstellungen, System, Entwickleroptionen, "USB-Debugging" einschalten.</li>
          <li>Die Abfrage "USB-Debugging zulassen?" am Telefon bestätigen.</li>
        </ol>
        <p class="leise">Sobald das Telefon bereit ist, erscheint es hier von selbst.</p>
      {/if}
    </div>
  {/if}
</section>

<style>
  .seite {
    display: flex;
    flex-direction: column;
    min-width: 0;
    min-height: 0;
    border: 1px solid transparent;
    border-radius: var(--f-radius);
    background: var(--f-flaeche);
    overflow: hidden;
  }

  .seite.aktiv {
    border-color: var(--f-akzent-weich);
    box-shadow: 0 0 0 1px var(--f-akzent-weich);
  }

  header {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    padding: 0.6rem 0.6rem 0.5rem;
  }

  .quellen {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.35rem;
  }

  .quellen button {
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    padding: 0.3rem 0.75rem;
    border: 0;
    border-radius: 999px;
    background: var(--f-flaeche-2);
    color: var(--f-text-leise);
    font-weight: 600;
  }

  .quellen button:hover {
    color: var(--f-text);
  }

  .quellen button.gewaehlt {
    background: var(--f-akzent);
    color: var(--f-akzent-text);
  }

  .kein-telefon {
    padding: 0.3rem 0.6rem;
    color: var(--f-text-leise);
    font-size: 0.9rem;
    opacity: 0.7;
  }

  .werkzeuge {
    display: flex;
    align-items: center;
    gap: 0.2rem;
  }

  .pfad {
    flex: 1;
    min-width: 0;
  }

  .symbolknopf:disabled {
    opacity: 0.35;
    cursor: default;
  }

  .getrennt {
    flex: 1;
    overflow-y: auto;
    overflow-x: clip;
    padding: 2rem 2rem 1rem;
    color: var(--f-text-leise);
    line-height: 1.5;
  }

  .getrennt .gross {
    font-size: 2.2rem;
    color: var(--f-akzent);
  }

  h3 {
    margin: 0.8rem 0 0.6rem;
    color: var(--f-text);
    font-weight: 600;
  }

  ol {
    padding-left: 1.2rem;
  }

  .hinweis {
    padding: 0.6rem 0.8rem;
    border-radius: var(--f-radius-klein);
    background: var(--f-flaeche-2);
    color: var(--f-warnung);
  }

  .leise {
    font-size: 0.9rem;
  }
</style>
