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

		let navigatingToLogin = false;

		const handleStorageChange = (e: StorageEvent) => {
			if (e.key === 'auth_token') {
				if (!e.newValue) {
					authStore.clearAuth();
					if (!navigatingToLogin) {
						navigatingToLogin = true;
						goto('/login', { replaceState: true });
					}
				} else if (e.newValue && !authStore.getToken()) {
					setTimeout(() => {
						window.location.reload();
					}, 100);
				}
			}
		};

		const originalFetch = window.fetch;
		window.fetch = async (...args) => {
			const response = await originalFetch(...args);
			if (response.status === 401) {
				authStore.clearAuth();
				if (!navigatingToLogin) {
					navigatingToLogin = true;
					goto('/login', { replaceState: true });
				}
			}
			return response;
		};

		window.addEventListener('storage', handleStorageChange);

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
