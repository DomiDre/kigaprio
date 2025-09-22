import tailwindcss from '@tailwindcss/vite';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';
import fs from 'fs';
import type { ServerOptions } from 'https';

const useDevHTTPS = process.env.USE_DEV_HTTPS === 'true';
let httpsConfig: ServerOptions | undefined = undefined;
if (useDevHTTPS) {
	httpsConfig = {
		key: fs.readFileSync('./local_dev.key'),
		cert: fs.readFileSync('./local_dev.cert')
	};
}

export default defineConfig({
	plugins: [tailwindcss(), sveltekit()],
	server: {
		https: httpsConfig,
		host: true
	}
});
