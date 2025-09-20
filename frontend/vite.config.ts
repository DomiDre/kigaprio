import tailwindcss from '@tailwindcss/vite';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';
import fs from 'fs';

const useDevHTTPS = process.env.USE_DEV_HTTPS && process.env.USE_DEV_HTTPS === 'true';

export default defineConfig({
	plugins: [tailwindcss(), sveltekit()],
	server: {
		https: useDevHTTPS
			? {
				key: fs.readFileSync('./local_dev.key'),
				cert: fs.readFileSync('./local_dev.cert')
			}
			: false,
		host: true
	}
});
