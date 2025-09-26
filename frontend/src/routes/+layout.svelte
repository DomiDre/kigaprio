<script lang="ts">
	import { onMount } from 'svelte';
	import { browser } from '$app/environment';
	import { authStore } from '$lib/stores/auth';
	import { goto } from '$app/navigation';
	import '../app.css';
	import favicon from '$lib/assets/favicon.svg';

	let { children } = $props();

	// Global session observer
	onMount(() => {
		if (!browser) return;

		// Listen for storage events (logout from another tab)
		const handleStorageChange = (e: StorageEvent) => {
			if (e.key === 'auth_token' && !e.newValue) {
				// Token was removed - user logged out in another tab
				authStore.clearAuth();
				goto('/login');
			} else if (e.key === 'auth_token' && e.newValue && !authStore.getToken()) {
				// Token was added - user logged in another tab
				window.location.reload();
			}
		};

		window.addEventListener('storage', handleStorageChange);

		// Listen for network errors / 401s globally
		const originalFetch = window.fetch;
		window.fetch = async (...args) => {
			const response = await originalFetch(...args);
			if (response.status === 401) {
				authStore.clearAuth();
				goto('/login');
			}
			return response;
		};

		return () => {
			window.removeEventListener('storage', handleStorageChange);
			window.fetch = originalFetch;
		};
	});
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

{@render children?.()}
