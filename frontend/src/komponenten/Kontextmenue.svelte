<script lang="ts">
  import { tick } from 'svelte';
  import { kontextmenue, type Menuepunkt } from '../lib/kontextmenue.svelte';

  let menue = $state<HTMLDivElement | null>(null);
  let links = $state(0);
  let oben = $state(0);
  const RAND = 8;

  // Am Bildschirmrand öffnet das Menü nach links bzw. oben, damit es nie hinausragt.
  $effect(() => {
    const offen = kontextmenue.offen;
    if (!offen) return;
    links = offen.x;
    oben = offen.y;
    void tick().then(() => {
      if (!menue) return;
      const { width, height } = menue.getBoundingClientRect();
      links = Math.max(RAND, Math.min(offen.x, window.innerWidth - width - RAND));
      oben = offen.y + height + RAND > window.innerHeight ? Math.max(RAND, offen.y - height) : offen.y;
      menue.querySelector<HTMLButtonElement>('button:not(:disabled)')?.focus();
    });
  });

  function waehle(punkt: Menuepunkt): void {
    kontextmenue.schliesse();
    punkt.ausfuehren();
  }

  function aussen(e: PointerEvent): void {
    if (menue && !menue.contains(e.target as Node)) kontextmenue.schliesse();
  }

  function tasten(e: KeyboardEvent): void {
    if (!kontextmenue.offen) return;
    const knoepfe = [...(menue?.querySelectorAll<HTMLButtonElement>('button:not(:disabled)') ?? [])];
    const index = knoepfe.indexOf(document.activeElement as HTMLButtonElement);
    if (e.key === 'Escape') kontextmenue.schliesse();
    else if (e.key === 'ArrowDown') knoepfe[(index + 1) % knoepfe.length]?.focus();
    else if (e.key === 'ArrowUp') knoepfe[(index - 1 + knoepfe.length) % knoepfe.length]?.focus();
    else if (e.key !== 'Enter') return;
    // Die Tasten gehören jetzt dem Menü, nicht der Dateiliste.
    e.stopImmediatePropagation();
    if (e.key !== 'Enter') e.preventDefault();
  }
</script>

<svelte:window onpointerdown={aussen} onkeydowncapture={tasten} onblur={() => kontextmenue.schliesse()} onresize={() => kontextmenue.schliesse()} />

{#if kontextmenue.offen}
  <div class="menue" role="menu" bind:this={menue} style:left="{links}px" style:top="{oben}px">
    {#if kontextmenue.offen.titel}
      <div class="titel">{kontextmenue.offen.titel}</div>
    {/if}
    {#each kontextmenue.offen.eintraege as eintrag, i (i)}
      {#if eintrag === null}
        <div class="trenner" role="separator"></div>
      {:else}
        <button role="menuitem" class:gefahr={eintrag.gefahr} disabled={eintrag.gesperrt} onclick={() => waehle(eintrag)}>
          <i class="fa-solid {eintrag.symbol}"></i>
          <span>{eintrag.text}</span>
          {#if eintrag.taste}<kbd>{eintrag.taste}</kbd>{/if}
        </button>
      {/if}
    {/each}
  </div>
{/if}

<style>
  .menue {
    position: fixed;
    z-index: 40;
    min-width: 15rem;
    max-width: 22rem;
    padding: 0.35rem;
    border-radius: var(--f-radius);
    background: var(--f-flaeche-2);
    box-shadow: var(--f-schatten);
  }

  .titel {
    padding: 0.3rem 0.6rem 0.4rem;
    color: var(--f-text-leise);
    font-size: 0.85rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  button {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    width: 100%;
    padding: 0.38rem 0.6rem;
    border: 0;
    border-radius: var(--f-radius-klein);
    background: transparent;
    text-align: left;
  }

  button:hover:not(:disabled),
  button:focus-visible {
    background: var(--f-flaeche-3);
    outline: none;
  }

  button:disabled {
    opacity: 0.4;
    cursor: default;
  }

  button i {
    width: 1.1rem;
    text-align: center;
    color: var(--f-akzent);
  }

  button span {
    flex: 1;
  }

  button.gefahr,
  button.gefahr i {
    color: var(--f-gefahr);
  }

  kbd {
    color: var(--f-text-leise);
    font-family: var(--f-schrift);
    font-size: 0.8rem;
  }

  .trenner {
    height: 1px;
    margin: 0.3rem 0.4rem;
    background: var(--f-linie);
  }
</style>
