<script lang="ts">
  import { tick } from 'svelte';
  import { dialoge } from '../lib/dialoge.svelte';

  let eingabeWert = $state('');
  let eingabefeld = $state<HTMLInputElement | null>(null);
  let hauptknopf = $state<HTMLButtonElement | null>(null);

  const dialog = $derived(dialoge.offen);
  const hauptwert = $derived(dialog?.knoepfe.at(-1)?.wert ?? null);

  $effect(() => {
    if (!dialog) return;
    eingabeWert = dialog.eingabe?.wert ?? '';
    void tick().then(() => {
      if (dialog.eingabe && eingabefeld) {
        eingabefeld.focus();
        eingabefeld.setSelectionRange(...dialog.eingabe.markierung);
      } else {
        hauptknopf?.focus();
      }
    });
  });

  function tasten(e: KeyboardEvent): void {
    if (e.key === 'Escape') {
      e.preventDefault();
      dialoge.schliesse(null);
    } else if (e.key === 'Enter' && dialog?.eingabe) {
      e.preventDefault();
      dialoge.schliesse(hauptwert, eingabeWert);
    }
  }
</script>

{#if dialog}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div class="schleier" onkeydown={tasten} onpointerdown={(e) => e.target === e.currentTarget && dialoge.schliesse(null)}>
    <div class="dialog" role="dialog" aria-modal="true" aria-labelledby="dialogtitel">
      <h2 id="dialogtitel">{dialog.titel}</h2>
      <p>{dialog.text}</p>
      {#if dialog.liste.length > 0}
        <ul class="namen">
          {#each dialog.liste as name, i (i)}
            <li>{name}</li>
          {/each}
        </ul>
      {/if}
      {#if dialog.eingabe}
        <input bind:this={eingabefeld} bind:value={eingabeWert} spellcheck="false" autocomplete="off" />
      {/if}
      <div class="knoepfe">
        {#each dialog.knoepfe as knopf, i (knopf.wert)}
          {#if i === dialog.knoepfe.length - 1}
            <button class="knopf {knopf.art}" bind:this={hauptknopf} onclick={() => dialoge.schliesse(knopf.wert, eingabeWert)}>{knopf.text}</button>
          {:else}
            <button class="knopf {knopf.art}" onclick={() => dialoge.schliesse(knopf.wert, eingabeWert)}>{knopf.text}</button>
          {/if}
        {/each}
      </div>
    </div>
  </div>
{/if}

<style>
  .schleier {
    position: fixed;
    inset: 0;
    z-index: 50;
    display: grid;
    place-items: center;
    background: rgba(5, 8, 12, 0.55);
  }

  .dialog {
    width: min(30rem, calc(100vw - 2rem));
    max-height: calc(100vh - 4rem);
    overflow-y: auto;
    overflow-x: clip;
    padding: 1.3rem 1.4rem 1.1rem;
    border-radius: var(--f-radius);
    background: var(--f-flaeche);
    box-shadow: var(--f-schatten);
  }

  h2 {
    margin: 0 0 0.5rem;
    font-size: 1.15rem;
    font-weight: 600;
  }

  p {
    margin: 0 0 0.8rem;
    color: var(--f-text-leise);
    line-height: 1.45;
  }

  .namen {
    margin: 0 0 0.9rem;
    padding: 0.5rem 0.8rem 0.5rem 1.6rem;
    border-radius: var(--f-radius-klein);
    background: var(--f-flaeche-2);
    font-size: 0.93rem;
    overflow-wrap: anywhere;
  }

  input {
    width: 100%;
    margin-bottom: 1rem;
    padding: 0.55rem 0.7rem;
    border: 1px solid var(--f-linie);
    border-radius: var(--f-radius-klein);
    background: var(--f-flaeche-2);
    color: var(--f-text);
    font: inherit;
  }

  input:focus {
    outline: none;
    border-color: var(--f-akzent);
  }

  .knoepfe {
    display: flex;
    justify-content: flex-end;
    flex-wrap: wrap;
    gap: 0.5rem;
  }
</style>
