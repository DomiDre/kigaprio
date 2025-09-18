<!-- src/routes/scanner/+page.svelte -->
<script lang="ts">
	import Scanner from '$lib/components/Scanner/Scanner.svelte';
	import { browser } from '$app/environment';
	import { checkBrowserCompatibility } from '$lib/utils/scanner.utils';

	let compatible = true;
	let issues: string[] = [];

	if (browser) {
		const compatibility = checkBrowserCompatibility();
		compatible = compatibility.compatible;
		issues = compatibility.issues;
	}
</script>

<svelte:head>
	<title>Priolisten Scanner</title>
	<meta name="description" content="Scan and extract schedule information" />
</svelte:head>

{#if compatible}
	<Scanner />
{:else}
	<div class="flex min-h-screen items-center justify-center p-4">
		<div class="text-center">
			<h1 class="mb-4 text-2xl font-bold">Browser Compatibility Issue</h1>
			<p class="mb-4">Your browser doesn't support all required features:</p>
			<ul class="list-inside list-disc">
				{#each issues as issue}
					<li>{issue}</li>
				{/each}
			</ul>
			<p class="mt-4">Please use a modern browser like Chrome, Firefox, or Safari.</p>
		</div>
	</div>
{/if}
