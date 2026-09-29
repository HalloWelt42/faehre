import { readFileSync } from 'node:fs';
import { defineConfig, loadEnv } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

// Ports kommen aus der .env im Projektwurzelverzeichnis (tools/einrichten.sh).
export default defineConfig(({ mode }) => {
  const umgebung = loadEnv(mode, '..', 'FAEHRE_');
  const backendPort = umgebung.FAEHRE_BACKEND_PORT ?? '8490';
  // Einzige Quelle der Version ist version.json; die Oberfläche bekommt sie beim Bauen eingesetzt.
  const version = (JSON.parse(readFileSync(new URL('../version.json', import.meta.url), 'utf-8')) as { voll: string }).voll;
  return {
    plugins: [svelte()],
    define: { __FAEHRE_VERSION__: JSON.stringify(version) },
    envDir: '..',
    server: {
      port: Number(umgebung.FAEHRE_FRONTEND_PORT ?? '5490'),
      proxy: {
        '/api': { target: `http://127.0.0.1:${backendPort}`, changeOrigin: false },
      },
    },
  };
});
