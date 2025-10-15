<script lang="ts">
	import { onMount } from 'svelte';
	import { browser } from '$app/environment';
	import { authStore, isAuthenticated } from '$lib/stores/auth';
	import { goto } from '$app/navigation';
	import { isSessionValid } from '$lib/utils/sessionUtils';
	import ReAuthModal from '$lib/components/ReAuthModal.svelte';
	import '../app.css';
	import favicon from '$lib/assets/favicon.svg';

	let { children } = $props();

	let showReAuthModal = $state(false);

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

		// Session validity checker for balanced mode
		const checkSession = () => {
			if ($isAuthenticated && !isSessionValid()) {
				// Session expired, show re-auth modal
				showReAuthModal = true;
			}
		};

		// Check session every 30 seconds
		const sessionCheckInterval = setInterval(checkSession, 30000);

		window.addEventListener('storage', handleStorageChange);

		return () => {
			window.removeEventListener('storage', handleStorageChange);
			window.fetch = originalFetch;
			clearInterval(sessionCheckInterval);
		};
	});

	function handleReAuthSuccess() {
		showReAuthModal = false;
	}
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

{@render children?.()}

<!-- Re-Authentication Modal -->
<ReAuthModal isOpen={showReAuthModal} onClose={handleReAuthSuccess} />
