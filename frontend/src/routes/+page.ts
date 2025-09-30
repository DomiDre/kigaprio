import { browser } from '$app/environment';
import { redirect } from '@sveltejs/kit';
import type { PageLoad } from './$types';
export const load: PageLoad = async () => {
	if (browser) {
		const token = localStorage.getItem('auth_token');
		const user = localStorage.getItem('auth_user');
		if (!token || !user) {
			throw redirect(307, '/login');
		} else {
			throw redirect(307, '/priorities');
		}
	}
	return;
};
