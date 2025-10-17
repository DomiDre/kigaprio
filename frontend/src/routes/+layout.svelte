<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { authStore } from '$lib/stores/auth';
	import ReAuthModal from '$lib/components/ReAuthModal.svelte';
	import '../app.css';
	import favicon from '$lib/assets/favicon.svg';

	let { children } = $props();

	let showReAuthModal = $state(false);
	let isInitializing = $state(true);

	// Public routes that don't require authentication
	const publicRoutes = ['/login', '/register', '/', '/imprint', '/privacy'];

	onMount(async () => {
		// Verify session with server (checks httpOnly cookies)
		const isValid = await authStore.verifyAuth();

		const currentPath = window.location.pathname;
		const isPublicRoute = publicRoutes.includes(currentPath);

		if (!isValid && !isPublicRoute) {
			// Not authenticated and trying to access protected route
			goto('/login');
		} else if (isValid && currentPath === '/login') {
			// Already authenticated, redirect to app
			goto('/priorities');
		}

		isInitializing = false;
	});

	function handleReAuthSuccess() {
		showReAuthModal = false;
	}
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

{#if isInitializing}
	<div class="flex min-h-screen items-center justify-center bg-gray-50 dark:bg-gray-900">
		<div class="text-center">
			<div
				class="mb-4 inline-block h-12 w-12 animate-spin rounded-full border-b-2 border-blue-600"
			></div>
			<p class="text-gray-600 dark:text-gray-400">Lade...</p>
		</div>
	</div>
{:else}
	{@render children?.()}
{/if}

<!-- Re-Authentication Modal -->
<ReAuthModal isOpen={showReAuthModal} onClose={handleReAuthSuccess} />

