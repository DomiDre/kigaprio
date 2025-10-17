<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { isAuthenticated } from '$lib/stores/auth';
	import Loading from './Loading.svelte';

	let { children } = $props();

	onMount(() => {
		if (!$isAuthenticated) {
			goto('/login');
		}
	});
</script>

{#if $isAuthenticated}
	{@render children?.()}
{:else}
	<Loading message="Leite zur Login-Seite um..." />
{/if}
