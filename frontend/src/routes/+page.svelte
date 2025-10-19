<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { authStore } from '$lib/stores/auth';
	import Loading from '$lib/components/Loading.svelte';

	onMount(() => {
		// Redirect based on authentication status
		const unsubscribe = authStore.subscribe(($auth) => {
			// Wait for auth to finish initializing
			if (!$auth.isLoading) {
				if ($auth.isAuthenticated) {
					goto('/priorities');
				} else {
					goto('/login');
				}
			}
		});

		// Cleanup subscription
		return unsubscribe;
	});
</script>

<Loading message="Lade..." />
