<script lang="ts">
  import { anzahl, dateiSymbol, groesse, zeitpunkt } from '../lib/format';
  import type { OrdnerseitenZustand } from '../lib/ordnerseite.svelte';
  import type { Eintrag, Sortierung } from '../lib/typen';
  import { beginneZiehen, istEigenerZug, istFinderZug, willVerschieben } from '../lib/ziehen';

  interface Props {
    zustand: OrdnerseitenZustand;
    aktiv: boolean;
    onoeffne: (eintrag: Eintrag) => void;
    onablage: (ereignis: DragEvent, zielOrdner: string) => void;
    /** Rechtsklick auf einen Eintrag oder (eintrag null) auf die freie Fläche. */
    onkontext: (ereignis: MouseEvent, eintrag: Eintrag | null) => void;
  }

  let { zustand, aktiv, onoeffne, onablage, onkontext }: Props = $props();

  let rollfeld = $state<HTMLDivElement | null>(null);
  let waechter = $state<HTMLDivElement | null>(null);
  let ablageZiel = $state<string | null>(null);
  let verschieben = $state(false);

  const SPALTEN: { sortierung: Sortierung; titel: string }[] = [
    { sortierung: 'name', titel: 'Name' },
    { sortierung: 'groesse', titel: 'Größe' },
    { sortierung: 'geaendert', titel: 'Geändert' },
  ];

  // Nachladen, sobald das Ende der Liste ins Rollfeld kommt.
  $effect(() => {
    if (!rollfeld || !waechter) return;
    const beobachter = new IntersectionObserver((treffer) => {
      if (treffer.some((t) => t.isIntersecting)) void zustand.ladeWeiter();
    }, { root: rollfeld, rootMargin: '300px' });
    beobachter.observe(waechter);
    return () => beobachter.disconnect();
  });

  // Der Tastaturfokus bleibt sichtbar.
  $effect(() => {
    const index = zustand.fokus;
    if (!aktiv || !rollfeld) return;
    rollfeld.querySelector<HTMLElement>(`[data-index="${index}"]`)?.scrollIntoView({ block: 'nearest' });
  });

  function nimmtAn(e: DragEvent): boolean {
    return istEigenerZug(e) || istFinderZug(e);
  }

  function ueberZiel(e: DragEvent, ziel: string): void {
    if (!nimmtAn(e)) return;
    e.preventDefault();
    e.stopPropagation();
    verschieben = istEigenerZug(e) && willVerschieben(e);
    if (e.dataTransfer) e.dataTransfer.dropEffect = verschieben ? 'move' : 'copy';
    ablageZiel = ziel;
  }

  function verlassen(e: DragEvent): void {
    if (!rollfeld?.contains(e.relatedTarget as Node | null)) ablageZiel = null;
  }

  function ablegen(e: DragEvent, ziel: string): void {
    if (!nimmtAn(e)) return;
    e.preventDefault();
    e.stopPropagation();
    ablageZiel = null;
    onablage(e, ziel);
  }

  function zeilenklick(e: MouseEvent, index: number): void {
    zustand.klick(index, e.metaKey || e.ctrlKey, e.shiftKey);
  }

  /** Wie im Finder: gehört der Eintrag nicht zur Markierung, gilt das Menü nur für ihn. */
  function zeilenmenue(e: MouseEvent, index: number, eintrag: Eintrag): void {
    e.stopPropagation();
    if (!zustand.markiert.has(eintrag.pfad)) zustand.klick(index, false, false);
    else zustand.fokus = index;
    onkontext(e, eintrag);
  }

  function flaechenmenue(e: MouseEvent): void {
    zustand.hebeAuswahlAuf();
    onkontext(e, null);
  }

  const markierteGroesse = $derived(
    zustand.eintraege.filter((e) => zustand.markiert.has(e.pfad)).reduce((summe, e) => summe + (e.groesse ?? 0), 0),
  );
  const zielName = $derived(
    ablageZiel === zustand.pfad ? 'diesen Ordner' : `"${ablageZiel?.split('/').pop() ?? ''}"`,
  );
</script>

<svelte:window ondragend={() => (ablageZiel = null)} />

<div class="liste">
  <div class="kopf" role="row">
    {#each SPALTEN as spalte (spalte.sortierung)}
      <button class="spalte {spalte.sortierung}" onclick={() => zustand.sortiereNach(spalte.sortierung)} title="Nach {spalte.titel} sortieren, erneut klicken dreht die Reihenfolge um">
        {spalte.titel}
        {#if zustand.sortierung === spalte.sortierung}
          <i class="fa-solid {zustand.absteigend ? 'fa-arrow-down' : 'fa-arrow-up'}"></i>
        {/if}
      </button>
    {/each}
  </div>

  <div
    class="rollfeld"
    class:ablage={ablageZiel === zustand.pfad}
    bind:this={rollfeld}
    role="grid"
    tabindex="-1"
    ondragover={(e) => ueberZiel(e, zustand.pfad)}
    ondragleave={verlassen}
    ondrop={(e) => ablegen(e, zustand.pfad)}
    oncontextmenu={flaechenmenue}
  >
    {#if zustand.fehler}
      <div class="leer fehler"><i class="fa-solid fa-triangle-exclamation"></i> {zustand.fehler}</div>
    {:else if zustand.eintraege.length === 0 && !zustand.laedt}
      <div class="leer">Dieser Ordner ist leer. Dateien hierher ziehen, um sie abzulegen.</div>
    {/if}

    {#each zustand.eintraege as eintrag, index (eintrag.pfad)}
      {@const istOrdner = eintrag.art === 'ordner'}
      <!-- Tastatursteuerung läuft zentral über das Fenster (App.svelte), nicht je Zeile. -->
      <!-- svelte-ignore a11y_click_events_have_key_events -->
      <div
        class="zeile"
        class:markiert={zustand.markiert.has(eintrag.pfad)}
        class:fokus={aktiv && zustand.fokus === index}
        class:versteckt={eintrag.versteckt}
        class:ablage={istOrdner && ablageZiel === eintrag.pfad}
        data-index={index}
        role="row"
        tabindex="-1"
        aria-selected={zustand.markiert.has(eintrag.pfad)}
        draggable="true"
        onclick={(e) => zeilenklick(e, index)}
        ondblclick={() => onoeffne(eintrag)}
        oncontextmenu={(e) => zeilenmenue(e, index, eintrag)}
        ondragstart={(e) => beginneZiehen(e, zustand.quelle, zustand.waehleZumZiehen(index))}
        ondragover={istOrdner ? (e) => ueberZiel(e, eintrag.pfad) : undefined}
        ondrop={istOrdner ? (e) => ablegen(e, eintrag.pfad) : undefined}
      >
        <span class="name" title={eintrag.name}>
          {#if istOrdner}
            <i class="fa-solid fa-folder ordnersymbol"></i>
          {:else if eintrag.art === 'verweis'}
            <i class="fa-solid fa-link"></i>
          {:else}
            <i class={dateiSymbol(eintrag.name)}></i>
          {/if}
          <span class="text">{eintrag.name}</span>
        </span>
        <span class="groesse">{groesse(eintrag.groesse)}</span>
        <span class="zeit">{zeitpunkt(eintrag.geaendert)}</span>
      </div>
    {/each}
    <div class="waechter" bind:this={waechter}></div>

    {#if ablageZiel}
      <div class="ablagehinweis">
        <i class="fa-solid {verschieben ? 'fa-right-long' : 'fa-copy'}"></i>
        In {zielName} {verschieben ? 'verschieben' : 'kopieren'}
        {#if !verschieben}<span class="leise">mit ⌘ verschieben</span>{/if}
      </div>
    {/if}
  </div>

  <div class="fuss">
    <span>
      {#if zustand.vollstaendig}
        {anzahl(zustand.gesamt, 'Eintrag', 'Einträge')}
      {:else}
        {zustand.eintraege.length.toLocaleString('de-DE')} von {anzahl(zustand.gesamt, 'Eintrag', 'Einträgen')} geladen
      {/if}
    </span>
    {#if zustand.markiert.size > 0}
      <span class="auswahl">{zustand.markiert.size.toLocaleString('de-DE')} markiert{markierteGroesse > 0 ? `, ${groesse(markierteGroesse)}` : ''}</span>
    {/if}
    {#if zustand.laedt}<i class="fa-solid fa-spinner fa-spin"></i>{/if}
  </div>
</div>

<style>
  .liste {
    container-type: inline-size;
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
  }

  .kopf,
  .zeile {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 6.5rem 9.5rem;
    align-items: center;
    column-gap: 0.75rem;
  }

  .kopf {
    padding: 0 0.9rem;
    background: var(--f-flaeche-2);
  }

  .spalte {
    display: flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.45rem 0;
    border: 0;
    background: transparent;
    color: var(--f-text-leise);
    font-size: 0.85rem;
    font-weight: 600;
  }

  .spalte:hover {
    color: var(--f-text);
  }

  .spalte.groesse {
    justify-content: flex-end;
  }

  .rollfeld {
    position: relative;
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    overflow-x: clip;
    padding: 0.3rem 0.4rem;
    outline: none;
    border: 2px solid transparent;
    border-radius: var(--f-radius-klein);
  }

  .rollfeld.ablage {
    border-color: var(--f-akzent);
    background: var(--f-akzent-weich);
  }

  .zeile {
    padding: 0.28rem 0.5rem;
    border: 1px solid transparent;
    border-radius: var(--f-radius-klein);
    cursor: default;
    user-select: none;
  }

  .zeile:hover {
    background: var(--f-flaeche-2);
  }

  .zeile.markiert {
    background: var(--f-markiert);
  }

  .zeile.fokus {
    border-color: var(--f-akzent);
  }

  .zeile.ablage {
    background: var(--f-akzent);
    color: var(--f-akzent-text);
  }

  .zeile.ablage i {
    color: inherit;
  }

  .zeile.versteckt {
    opacity: 0.55;
  }

  .name {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    min-width: 0;
  }

  .name i {
    width: 1.1rem;
    text-align: center;
    color: var(--f-text-leise);
  }

  .name .ordnersymbol {
    color: var(--f-akzent);
  }

  .text {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .groesse,
  .zeit {
    color: var(--f-text-leise);
    font-size: 0.9rem;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
  }

  .groesse {
    text-align: right;
  }

  .leer {
    padding: 2.5rem 1rem;
    text-align: center;
    color: var(--f-text-leise);
  }

  .leer.fehler {
    color: var(--f-gefahr);
  }

  .waechter {
    height: 1px;
  }

  .ablagehinweis {
    position: sticky;
    bottom: 0.5rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    width: fit-content;
    max-width: 100%;
    margin: 0.5rem auto 0;
    padding: 0.4rem 0.8rem;
    border-radius: var(--f-radius);
    background: var(--f-akzent);
    color: var(--f-akzent-text);
    font-weight: 600;
    pointer-events: none;
  }

  .ablagehinweis .leise {
    font-weight: 400;
    opacity: 0.8;
  }

  .fuss {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 0.4rem 0.9rem;
    background: var(--f-flaeche-2);
    color: var(--f-text-leise);
    font-size: 0.88rem;
  }

  .auswahl {
    color: var(--f-akzent);
  }

  /* Schmale Seite: das Datum weicht, damit der Name lesbar bleibt. */
  @container (max-width: 480px) {
    .kopf,
    .zeile {
      grid-template-columns: minmax(0, 1fr) 5.5rem;
    }

    .spalte.geaendert,
    .zeit {
      display: none;
    }
  }
</style>
