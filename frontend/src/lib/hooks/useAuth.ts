
import { onMount } from 'svelte';
import { apiService } from '$lib/services/api';
import { authStore, isAuthenticated } from '$lib/stores/auth';
import { goto } from '$app/navigation';
import { browser } from '$app/environment';

export function useAuth(requireAuth = false) {
	let refreshInterval: NodeJS.Timeout;

	onMount(() => {
		// Check if user needs to be authenticated for this route
		if (requireAuth && !isAuthenticated) {
			goto('/login');
		}

		// Setup token refresh (every 12 hours)
		if (browser && authStore.getToken()) {
			refreshInterval = setInterval(async () => {
				try {
					await apiService.refreshToken();
				} catch (error) {
					console.error('Token refresh failed:', error);
					authStore.clearAuth();
					goto('/login');
				}
			}, 12 * 60 * 60 * 1000); // 12 hours
		}

		// Check token validity on mount
		checkTokenValidity();

		return () => {
			if (refreshInterval) {
				clearInterval(refreshInterval);
			}
		};
	});

	async function checkTokenValidity() {
		const token = authStore.getToken();
		if (token && browser) {
			try {
				// You could add an endpoint to verify token validity
				// For now, we'll just check if token exists
				// In production, decode JWT and check expiration
			} catch (error) {
				authStore.clearAuth();
				if (requireAuth) {
					goto('/login');
				}
			}
		}
	}
}

