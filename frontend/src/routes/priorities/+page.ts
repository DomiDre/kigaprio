import { browser } from '$app/environment';
import { redirect } from '@sveltejs/kit';
import type { PageLoad } from './$types';

export const load: PageLoad = async () => {
	if (browser) {
		const token = localStorage.getItem('auth_token');

		if (!token) {
			throw redirect(307, '/login');
		}
	}

	return;
};
