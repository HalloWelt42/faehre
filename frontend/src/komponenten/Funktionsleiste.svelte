<script lang="ts" module>
  export interface Befehl {
    taste: string;
    text: string;
    symbol: string;
    erklaerung: string;
    ausfuehren: () => void;
  }
</script>

<script lang="ts">
  import { verbindung } from '../lib/verbindung.svelte';

  interface Props {
    befehle: Befehl[];
    version: string;
  }

  let { befehle, version }: Props = $props();
</script>

<footer>
  <div class="befehle">
    {#each befehle as befehl (befehl.taste)}
      <button class="befehl" onclick={befehl.ausfuehren} title={befehl.erklaerung}>
        <kbd>{befehl.taste}</kbd>
        <i class="fa-solid {befehl.symbol}"></i>
        <span>{befehl.text}</span>
      </button>
    {/each}
  </div>
  <div class="stand">
    <span class="dienst" class:getrennt={!verbindung.verbunden} title={verbindung.verbunden ? 'Verbindung zum Fähre-Dienst steht' : 'Fähre-Dienst nicht erreichbar, neuer Versuch läuft'}>
      <i class="fa-solid fa-circle"></i>
      {verbindung.verbunden ? 'verbunden' : 'getrennt'}
    </span>
    <span class="marke"><i class="fa-solid fa-ferry"></i> Fähre {version}</span>
  </div>
</footer>

<style>
  footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    padding: 0.4rem 0.5rem;
    border-radius: var(--f-radius);
    background: var(--f-flaeche);
  }

  .befehle {
    display: flex;
    flex-wrap: wrap;
    gap: 0.3rem;
  }

  .befehl {
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    padding: 0.3rem 0.65rem 0.3rem 0.35rem;
    border: 0;
    border-radius: var(--f-radius-klein);
    background: var(--f-flaeche-2);
  }

  .befehl:hover {
    background: var(--f-flaeche-3);
  }

  .befehl i {
    color: var(--f-akzent);
  }

  kbd {
    min-width: 1.8rem;
    padding: 0.05rem 0.35rem;
    border-radius: 4px;
    background: var(--f-flaeche-3);
    color: var(--f-text-leise);
    font-family: var(--f-schrift);
    font-size: 0.78rem;
    font-weight: 600;
    text-align: center;
  }

  .stand {
    display: flex;
    align-items: center;
    gap: 1rem;
    color: var(--f-text-leise);
    font-size: 0.88rem;
    white-space: nowrap;
  }

  .dienst i {
    font-size: 0.55rem;
    vertical-align: middle;
    color: var(--f-erfolg);
  }

  .dienst.getrennt i {
    color: var(--f-gefahr);
  }

  .marke i {
    color: var(--f-akzent);
  }
</style>
