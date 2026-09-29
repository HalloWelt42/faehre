<script lang="ts">
  import type { Ort } from '../lib/typen';

  interface Props {
    orte: Ort[];
    onwaehle: (ort: Ort) => void;
  }

  let { orte, onwaehle }: Props = $props();
  let offen = $state(false);
  let wurzel = $state<HTMLDivElement | null>(null);

  function aussenKlick(e: PointerEvent): void {
    if (wurzel && !wurzel.contains(e.target as Node)) offen = false;
  }

  function waehle(ort: Ort): void {
    offen = false;
    onwaehle(ort);
  }
</script>

<svelte:window onpointerdown={aussenKlick} />

<div class="orte" bind:this={wurzel}>
  <button class="symbolknopf" class:an={offen} onclick={() => (offen = !offen)} title="Schnellzugriff auf wichtige Ordner" aria-expanded={offen}>
    <i class="fa-solid fa-star"></i>
  </button>
  {#if offen}
    <ul class="menue">
      {#each orte as ort (ort.pfad)}
        <li>
          <button onclick={() => waehle(ort)} title={ort.pfad}>
            <i class="fa-solid fa-{ort.symbol}"></i>
            <span>{ort.name}</span>
          </button>
        </li>
      {/each}
    </ul>
  {/if}
</div>

<style>
  .orte {
    position: relative;
  }

  .menue {
    position: absolute;
    top: calc(100% + 0.3rem);
    left: 0;
    z-index: 20;
    min-width: 13rem;
    margin: 0;
    padding: 0.35rem;
    list-style: none;
    border-radius: var(--f-radius);
    background: var(--f-flaeche-2);
    box-shadow: var(--f-schatten);
  }

  .menue button {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    width: 100%;
    padding: 0.4rem 0.6rem;
    border: 0;
    border-radius: var(--f-radius-klein);
    background: transparent;
    text-align: left;
  }

  .menue button:hover {
    background: var(--f-flaeche-3);
  }

  .menue i {
    width: 1.1rem;
    text-align: center;
    color: var(--f-akzent);
  }
</style>
