<script lang="ts">
  import { tick } from 'svelte';
  import type { Ort } from '../lib/typen';

  interface Props {
    pfad: string;
    orte: Ort[];
    onoeffne: (pfad: string) => void;
  }

  let { pfad, orte, onoeffne }: Props = $props();

  interface Stufe {
    name: string;
    pfad: string;
    symbol: string | null;
  }

  let bearbeiten = $state(false);
  let eingabe = $state('');
  let feld = $state<HTMLInputElement | null>(null);

  function liegtIn(ziel: string, ordner: string): boolean {
    return ziel === ordner || ziel.startsWith(ordner.replace(/\/+$/, '') + '/');
  }

  /** Der längste passende Anker ersetzt den Pfadanfang, der Rest wird Stufe für Stufe klickbar. */
  const stufen = $derived.by((): Stufe[] => {
    const anker = orte
      .filter((o) => o.anker && liegtIn(pfad, o.pfad))
      .sort((a, b) => b.pfad.length - a.pfad.length)[0];
    const anfang: Stufe = anker
      ? { name: anker.name, pfad: anker.pfad, symbol: anker.symbol }
      : { name: '', pfad: '/', symbol: 'hard-drive' };
    const rest = pfad.slice(anfang.pfad.length).split('/').filter(Boolean);
    let bisher = anfang.pfad.replace(/\/+$/, '');
    return [
      anfang,
      ...rest.map((teil) => {
        bisher = `${bisher}/${teil}`;
        return { name: teil, pfad: bisher, symbol: null };
      }),
    ];
  });

  async function beginneBearbeiten(): Promise<void> {
    eingabe = pfad;
    bearbeiten = true;
    await tick();
    feld?.select();
  }

  function tasten(e: KeyboardEvent): void {
    e.stopPropagation();
    if (e.key === 'Enter') {
      bearbeiten = false;
      const ziel = eingabe.trim();
      if (ziel && ziel !== pfad) onoeffne(ziel);
    } else if (e.key === 'Escape') {
      bearbeiten = false;
    }
  }
</script>

<div class="pfadleiste">
  {#if bearbeiten}
    <input
      bind:this={feld}
      bind:value={eingabe}
      onkeydown={tasten}
      onblur={() => (bearbeiten = false)}
      spellcheck="false"
      aria-label="Pfad eingeben"
    />
  {:else}
    <nav aria-label="Pfad">
      {#each stufen as stufe, i (stufe.pfad)}
        {#if i > 0}<i class="fa-solid fa-chevron-right trenner"></i>{/if}
        <button class="stufe" class:letzte={i === stufen.length - 1} onclick={() => onoeffne(stufe.pfad)} title={stufe.pfad}>
          {#if stufe.symbol}<i class="fa-solid fa-{stufe.symbol}"></i>{/if}
          {#if stufe.name}<span>{stufe.name}</span>{/if}
        </button>
      {/each}
    </nav>
    <button class="symbolknopf" onclick={beginneBearbeiten} title="Pfad direkt eingeben und mit der Eingabetaste öffnen">
      <i class="fa-solid fa-pen"></i>
    </button>
  {/if}
</div>

<style>
  .pfadleiste {
    display: flex;
    align-items: center;
    gap: 0.25rem;
    min-height: 2.2rem;
    padding: 0.15rem 0.2rem 0.15rem 0.35rem;
    border-radius: var(--f-radius-klein);
    background: var(--f-flaeche-2);
    min-width: 0;
  }

  nav {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.1rem;
    flex: 1;
    min-width: 0;
  }

  .stufe {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    max-width: 16rem;
    padding: 0.2rem 0.45rem;
    border: 0;
    border-radius: var(--f-radius-klein);
    background: transparent;
    color: var(--f-text-leise);
  }

  .stufe span {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .stufe:hover {
    background: var(--f-flaeche-3);
    color: var(--f-text);
  }

  .stufe.letzte {
    color: var(--f-text);
    font-weight: 600;
  }

  .trenner {
    font-size: 0.6rem;
    color: var(--f-text-leise);
    opacity: 0.6;
  }

  input {
    flex: 1;
    min-width: 0;
    padding: 0.35rem 0.5rem;
    border: 1px solid var(--f-akzent);
    border-radius: var(--f-radius-klein);
    background: var(--f-flaeche);
    color: var(--f-text);
    font: inherit;
  }

  input:focus {
    outline: none;
  }
</style>
