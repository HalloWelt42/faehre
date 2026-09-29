import { mount } from 'svelte';
import '@fontsource/barlow/400.css';
import '@fontsource/barlow/600.css';
import '@fortawesome/fontawesome-free/css/all.min.css';
import './app.css';
import App from './App.svelte';

mount(App, { target: document.getElementById('app')! });
