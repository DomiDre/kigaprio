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
