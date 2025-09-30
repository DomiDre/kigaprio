import { browser } from '$app/environment';
import { redirect } from '@sveltejs/kit';
import type { PageLoad } from './$types';

export const load: PageLoad = async () => {
	if (browser) {
		throw redirect(307, '/login');
	}

	return;
};
