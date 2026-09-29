<script lang="ts">
  import { onMount, untrack } from 'svelte';
  import Auftragsleiste from './komponenten/Auftragsleiste.svelte';
  import Dialog from './komponenten/Dialog.svelte';
  import Funktionsleiste, { type Befehl } from './komponenten/Funktionsleiste.svelte';
  import Kontextmenue from './komponenten/Kontextmenue.svelte';
  import Meldungen from './komponenten/Meldungen.svelte';
  import Ordnerseite from './komponenten/Ordnerseite.svelte';
  import { herunterladen, loesche, neuerOrdner, pfadKopieren, uebertrage, umbenennen } from './lib/aktionen';
  import { dialoge } from './lib/dialoge.svelte';
  import { anzahl } from './lib/format';
  import { hochladen } from './lib/hochladen.svelte';
  import { kontextmenue, type Menueeintrag } from './lib/kontextmenue.svelte';
  import { meldungen } from './lib/meldungen.svelte';
  import { OrdnerseitenZustand, type Seitenname } from './lib/ordnerseite.svelte';
  import type { Auftragsart, Eintrag } from './lib/typen';
  import { verbindung } from './lib/verbindung.svelte';

  const seiten: Record<Seitenname, OrdnerseitenZustand> = {
    links: new OrdnerseitenZustand('links'),
    rechts: new OrdnerseitenZustand('rechts'),
  };
  let aktiv = $state<Seitenname>('links');
  const version = __FAEHRE_VERSION__;
  const zuletztVerfuegbar: Record<Seitenname, boolean> = { links: false, rechts: false };

  const aktive = $derived(seiten[aktiv]);
  const andere = $derived(seiten[aktiv === 'links' ? 'rechts' : 'links']);

  onMount(() => {
    verbindung.starte();
    const ohneAuftrag = verbindung.beiAbschluss((auftrag) => {
      if (auftrag.status === 'fertig') meldungen.zeige('erfolg', `${auftrag.art === 'verschieben' ? 'Verschoben' : 'Kopiert'}: ${anzahl(auftrag.dateien_fertig, 'Datei', 'Dateien')}`);
      if (auftrag.status === 'fehler') meldungen.zeige('fehler', auftrag.fehler ?? 'Übertragung fehlgeschlagen');
      ladeBeideNeu();
    });
    const ohneHochladen = hochladen.beiAbschluss((posten) => {
      if (posten.status === 'fertig') meldungen.zeige('erfolg', `Hochgeladen: ${anzahl(posten.dateien_fertig, 'Datei', 'Dateien')}`);
      if (posten.status === 'fehler') meldungen.zeige('fehler', posten.fehler ?? 'Hochladen fehlgeschlagen');
      ladeBeideNeu();
    });
    return () => {
      ohneAuftrag();
      ohneHochladen();
    };
  });

  function ladeBeideNeu(): void {
    for (const seite of Object.values(seiten)) {
      if (verbindung.quelle(seite.quelle)) void seite.lade();
    }
  }

  // Geräte kommen und gehen: Seiten laden neu, sobald ihre Quelle (wieder) da ist.
  $effect(() => {
    const quellen = verbindung.stand.quellen;
    if (quellen.length === 0) return;
    untrack(() => {
      for (const name of ['links', 'rechts'] as Seitenname[]) {
        const seite = seiten[name];
        waehleVorgabe(seite, name);
        const quelle = quellen.find((q) => q.kennung === seite.quelle);
        const verfuegbar = quelle !== undefined;
        if (quelle && !zuletztVerfuegbar[name]) void oeffneGemerkt(seite, quelle.start);
        zuletztVerfuegbar[name] = verfuegbar;
      }
    });
  });

  /** Der gemerkte Ordner kann inzwischen fehlen, dann gilt der Startordner der Quelle. */
  async function oeffneGemerkt(seite: OrdnerseitenZustand, start: string): Promise<void> {
    await seite.oeffne(seite.quelle, seite.pfad || start);
    if (seite.fehler && seite.pfad !== start) await seite.oeffne(seite.quelle, start);
  }

  /** Links startet der Mac, rechts das erste Telefon, sobald es eines gibt. */
  function waehleVorgabe(seite: OrdnerseitenZustand, name: Seitenname): void {
    const quellen = verbindung.stand.quellen;
    if (verbindung.quelle(seite.quelle)) return;
    const telefon = quellen.find((q) => q.art === 'android');
    if (name === 'links' && !seite.quelle) {
      seite.quelle = 'mac';
    } else if (name === 'rechts' && telefon && (!seite.quelle || seite.quelle.startsWith('android:'))) {
      if (seite.quelle !== telefon.kennung) seite.pfad = '';
      seite.quelle = telefon.kennung;
    }
  }

  function zuDerAnderenSeite(art: Auftragsart): void {
    if (!verbindung.quelle(andere.quelle)) {
      meldungen.zeige('info', 'Auf der anderen Seite ist kein Gerät geöffnet.');
      return;
    }
    const pfade = aktive.auswahl.map((e) => e.pfad);
    void uebertrage(art, aktive.quelle, pfade, { quelle: andere.quelle, ordner: andere.pfad });
  }

  const befehle: Befehl[] = [
    { taste: 'F2', text: 'Umbenennen', symbol: 'fa-i-cursor', erklaerung: 'Den markierten Eintrag umbenennen', ausfuehren: () => void umbenennen(aktive) },
    { taste: 'F5', text: 'Kopieren', symbol: 'fa-copy', erklaerung: 'Auswahl in den Ordner der anderen Seite kopieren', ausfuehren: () => zuDerAnderenSeite('kopieren') },
    { taste: 'F6', text: 'Verschieben', symbol: 'fa-right-long', erklaerung: 'Auswahl in den Ordner der anderen Seite verschieben', ausfuehren: () => zuDerAnderenSeite('verschieben') },
    { taste: 'F7', text: 'Neuer Ordner', symbol: 'fa-folder-plus', erklaerung: 'Im aktuellen Ordner einen Ordner anlegen', ausfuehren: () => void neuerOrdner(aktive) },
    { taste: 'F8', text: 'Löschen', symbol: 'fa-trash-can', erklaerung: 'Auswahl löschen: auf dem Mac in den Papierkorb, auf dem Telefon endgültig', ausfuehren: () => void loesche(aktive) },
  ];

  /** Rechtsklick: dieselben Befehle wie in der Leiste, passend zum angeklickten Ziel. */
  function zeigeMenue(name: Seitenname, ereignis: MouseEvent, eintrag: Eintrag | null): void {
    aktiv = name;
    const seite = seiten[name];
    const gegenueber = verbindung.quelle(seiten[name === 'links' ? 'rechts' : 'links'].quelle);
    const ziel = gegenueber?.name ?? 'die andere Seite';
    if (eintrag === null) {
      kontextmenue.zeige(ereignis, null, [
        { text: 'Neuer Ordner', symbol: 'fa-folder-plus', taste: 'F7', ausfuehren: () => void neuerOrdner(seite) },
        { text: 'Übergeordneter Ordner', symbol: 'fa-arrow-up', taste: '⌫', gesperrt: seite.eltern === null, ausfuehren: () => void seite.hoch() },
        { text: 'Neu einlesen', symbol: 'fa-rotate-right', ausfuehren: () => void seite.lade() },
        null,
        { text: 'Alle markieren', symbol: 'fa-check-double', taste: '⌘A', gesperrt: seite.eintraege.length === 0, ausfuehren: () => seite.markiereAlle() },
        { text: seite.versteckte ? 'Versteckte ausblenden' : 'Versteckte einblenden', symbol: seite.versteckte ? 'fa-eye-slash' : 'fa-eye', ausfuehren: () => void seite.schalteVersteckte() },
        null,
        { text: 'Ordnerpfad kopieren', symbol: 'fa-clipboard', ausfuehren: () => void pfadKopieren([seite.pfad]) },
      ]);
      return;
    }
    const auswahl = seite.auswahl;
    const einzeln = auswahl.length === 1;
    const papierkorb = verbindung.quelle(seite.quelle)?.art === 'mac';
    const eintraege: Menueeintrag[] = [];
    if (einzeln && eintrag.art === 'ordner') {
      eintraege.push({ text: 'Öffnen', symbol: 'fa-folder-open', taste: '↵', ausfuehren: () => void seite.oeffne(seite.quelle, eintrag.pfad) });
    } else if (einzeln) {
      eintraege.push({ text: 'Im Browser herunterladen', symbol: 'fa-download', ausfuehren: () => herunterladen(seite.quelle, eintrag) });
    }
    if (eintraege.length > 0) eintraege.push(null);
    eintraege.push(
      { text: `Nach ${ziel} kopieren`, symbol: 'fa-copy', taste: 'F5', gesperrt: !gegenueber, ausfuehren: () => zuDerAnderenSeite('kopieren') },
      { text: `Nach ${ziel} verschieben`, symbol: 'fa-right-long', taste: 'F6', gesperrt: !gegenueber, ausfuehren: () => zuDerAnderenSeite('verschieben') },
      null,
      { text: 'Umbenennen', symbol: 'fa-i-cursor', taste: 'F2', gesperrt: !einzeln, ausfuehren: () => void umbenennen(seite) },
      { text: einzeln ? 'Pfad kopieren' : 'Pfade kopieren', symbol: 'fa-clipboard', ausfuehren: () => void pfadKopieren(auswahl.map((e) => e.pfad)) },
      null,
      { text: papierkorb ? 'In den Papierkorb' : 'Endgültig löschen', symbol: 'fa-trash-can', taste: 'F8', gefahr: true, ausfuehren: () => void loesche(seite) },
    );
    kontextmenue.zeige(ereignis, einzeln ? eintrag.name : anzahl(auswahl.length, 'Eintrag', 'Einträge'), eintraege);
  }

  const SEITENSPRUNG = 15;

  function tasten(e: KeyboardEvent): void {
    if (dialoge.offen) return;
    if (e.target instanceof Element && e.target.closest('input, textarea')) return;
    const seite = aktive;
    const befehl = befehle.find((b) => b.taste === e.key);
    if (befehl) {
      e.preventDefault();
      befehl.ausfuehren();
      return;
    }
    switch (e.key) {
      case 'Tab':
        aktiv = aktiv === 'links' ? 'rechts' : 'links';
        break;
      case 'ArrowDown':
        seite.bewegeFokus(1, e.shiftKey);
        break;
      case 'ArrowUp':
        seite.bewegeFokus(-1, e.shiftKey);
        break;
      case 'PageDown':
        seite.bewegeFokus(SEITENSPRUNG, e.shiftKey);
        break;
      case 'PageUp':
        seite.bewegeFokus(-SEITENSPRUNG, e.shiftKey);
        break;
      case 'Home':
        seite.bewegeFokus(-seite.eintraege.length, e.shiftKey);
        break;
      case 'End':
        seite.bewegeFokus(seite.eintraege.length, e.shiftKey);
        break;
      case 'Enter':
        if (seite.fokussiert?.art === 'ordner') void seite.oeffne(seite.quelle, seite.fokussiert.pfad);
        break;
      case 'Backspace':
        if (e.metaKey) void loesche(seite);
        else void seite.hoch();
        break;
      case 'Delete':
        void loesche(seite);
        break;
      case ' ':
      case 'Insert':
        seite.schalteMarkierung(seite.fokus);
        seite.bewegeFokus(1, false);
        break;
      case 'Escape':
        seite.hebeAuswahlAuf();
        break;
      case 'a':
        if (!e.metaKey) return;
        seite.markiereAlle();
        break;
      default:
        return;
    }
    e.preventDefault();
  }
</script>

<svelte:window onkeydown={tasten} />

<div class="rahmen">
  {#if verbindung.veraltet}
    <div class="neue-version">
      <i class="fa-solid fa-arrows-rotate"></i>
      <span>Es läuft eine neuere Version von Fähre ({verbindung.dienstVersion}). Diese Ansicht ist noch {version}.</span>
      <button class="knopf haupt" onclick={() => location.reload()}>Jetzt neu laden</button>
    </div>
  {/if}
  <main>
    <Ordnerseite zustand={seiten.links} aktiv={aktiv === 'links'} onaktiviere={() => (aktiv = 'links')} onkontext={(e, eintrag) => zeigeMenue('links', e, eintrag)} />
    <Ordnerseite zustand={seiten.rechts} aktiv={aktiv === 'rechts'} onaktiviere={() => (aktiv = 'rechts')} onkontext={(e, eintrag) => zeigeMenue('rechts', e, eintrag)} />
  </main>
  <Auftragsleiste />
  <Funktionsleiste {befehle} {version} />
</div>

<Kontextmenue />
<Dialog />
<Meldungen />

<style>
  .rahmen {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    height: 100%;
    padding: 0.5rem;
  }

  .neue-version {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.45rem 0.6rem 0.45rem 0.9rem;
    border-radius: var(--f-radius);
    background: var(--f-akzent-weich);
  }

  .neue-version span {
    flex: 1;
  }

  .neue-version i {
    color: var(--f-akzent);
  }

  main {
    flex: 1;
    min-height: 0;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.5rem;
  }
</style>
