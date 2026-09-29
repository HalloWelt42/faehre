// Anzeigeformate für Größen, Zeiten und Mengen.

const EINHEITEN = ['Byte', 'KB', 'MB', 'GB', 'TB'];
const zahl = new Intl.NumberFormat('de-DE', { maximumFractionDigits: 1 });
const ganzzahl = new Intl.NumberFormat('de-DE');
const zeit = new Intl.DateTimeFormat('de-DE', { dateStyle: 'medium', timeStyle: 'short' });

export function groesse(bytes: number | null): string {
  if (bytes === null) return '';
  let wert = bytes;
  let stufe = 0;
  while (wert >= 1024 && stufe < EINHEITEN.length - 1) {
    wert /= 1024;
    stufe += 1;
  }
  return `${stufe === 0 ? ganzzahl.format(wert) : zahl.format(wert)} ${EINHEITEN[stufe]}`;
}

export function zeitpunkt(iso: string | null): string {
  return iso ? zeit.format(new Date(iso)) : '';
}

export function anzahl(n: number, einzahl: string, mehrzahl: string): string {
  return `${ganzzahl.format(n)} ${n === 1 ? einzahl : mehrzahl}`;
}

const SYMBOLE: Record<string, string> = {
  jpg: 'file-image', jpeg: 'file-image', png: 'file-image', gif: 'file-image', webp: 'file-image', heic: 'file-image', svg: 'file-image',
  mp4: 'file-video', mkv: 'file-video', mov: 'file-video', avi: 'file-video', webm: 'file-video',
  mp3: 'file-audio', m4a: 'file-audio', flac: 'file-audio', wav: 'file-audio', ogg: 'file-audio', opus: 'file-audio',
  pdf: 'file-pdf',
  zip: 'file-zipper', gz: 'file-zipper', tar: 'file-zipper', '7z': 'file-zipper', rar: 'file-zipper',
  apk: 'android',
  txt: 'file-lines', md: 'file-lines', lrc: 'file-lines', log: 'file-lines',
  doc: 'file-word', docx: 'file-word', odt: 'file-word',
  xls: 'file-excel', xlsx: 'file-excel', ods: 'file-excel', csv: 'file-csv',
  epub: 'book', mobi: 'book',
  json: 'file-code', html: 'file-code', js: 'file-code', ts: 'file-code', py: 'file-code', sh: 'file-code',
};

/** Font-Awesome-Klasse passend zur Dateiendung. */
export function dateiSymbol(name: string): string {
  const endung = name.includes('.') ? name.split('.').pop()!.toLowerCase() : '';
  const symbol = SYMBOLE[endung] ?? 'file';
  return symbol === 'android' ? 'fa-brands fa-android' : `fa-solid fa-${symbol}`;
}
