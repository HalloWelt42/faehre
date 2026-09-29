<script lang="ts">
  import { meldungen, type Meldungsart } from '../lib/meldungen.svelte';

  const SYMBOL: Record<Meldungsart, string> = {
    erfolg: 'fa-circle-check',
    fehler: 'fa-circle-exclamation',
    info: 'fa-circle-info',
  };
</script>

<div class="stapel" aria-live="polite">
  {#each meldungen.liste as meldung (meldung.kennung)}
    <div class="meldung {meldung.art}">
      <i class="fa-solid {SYMBOL[meldung.art]}"></i>
      <span>{meldung.text}</span>
      <button class="symbolknopf" aria-label="Schließen" onclick={() => meldungen.schliesse(meldung.kennung)}>
        <i class="fa-solid fa-xmark"></i>
      </button>
    </div>
  {/each}
</div>

<style>
  .stapel {
    position: fixed;
    right: 1rem;
    bottom: 4.5rem;
    z-index: 60;
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 0.5rem;
    pointer-events: none;
  }

  .meldung {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    max-width: min(28rem, calc(100vw - 2rem));
    padding: 0.45rem 0.4rem 0.45rem 0.9rem;
    border-radius: var(--f-radius);
    background: var(--f-flaeche-2);
    box-shadow: var(--f-schatten);
    pointer-events: auto;
  }

  .meldung span {
    flex: 1;
    overflow-wrap: anywhere;
  }

  .erfolg i:first-child {
    color: var(--f-erfolg);
  }

  .fehler i:first-child {
    color: var(--f-gefahr);
  }

  .info i:first-child {
    color: var(--f-akzent);
  }
</style>
