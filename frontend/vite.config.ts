import tailwindcss from '@tailwindcss/vite';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';
import fs from 'fs';

export default defineConfig({
	plugins: [tailwindcss(), sveltekit()],
	server: {
		https: {
			key: fs.readFileSync('./local_dev.key'),
			cert: fs.readFileSync('./local_dev.cert')
		},
		host: true
	}
});
