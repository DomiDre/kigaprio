import { authStore } from '$lib/stores/auth';
import { get } from 'svelte/store';
import { browser } from '$app/environment';

/**
 * Check if the current session is valid based on the security tier
 */
export function isSessionValid(): boolean {
	if (!browser) return false;

	const auth = get(authStore);

	return auth.isAuthenticated;
}

