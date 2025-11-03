<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { authStore } from '$lib/auth.stores';
	import Loading from '$lib/components/Loading.svelte';

	onMount(() => {
		// Redirect based on authentication status
		const unsubscribe = authStore.subscribe(($auth) => {
			if ($auth.isAuthenticated) {
				goto('/dashboard');
			} else {
				goto('/login');
			}
		});

		// Cleanup subscription
		return unsubscribe;
	});
</script>

<Loading message="Lade..." />
