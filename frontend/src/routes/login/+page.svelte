<script lang="ts">
	import { goto } from '$app/navigation';
	import { isAuthenticated } from '$lib/stores/auth';
	import { apiService } from '$lib/services/api';
	import { onMount } from 'svelte';
	import Loading from '$lib/components/Loading.svelte';
	import SecurityTierSelector from '$lib/components/SecurityTierSelector.svelte';
	import type { SecurityTier } from '$lib/stores/auth';

	let username = '';
	let password = '';
	let error = '';
	let selectedTier: SecurityTier = 'balanced';
	let showTierSelector = false;

	onMount(() => {
		if ($isAuthenticated) {
			goto('/priorities');
		}
	});

	async function handleLogin() {
		error = '';
		try {
			await apiService.login(username, password, selectedTier);
			goto('/priorities');
		} catch (err) {
			error = (err as Error).message;
		}
	}

	function goToRegister() {
		goto('/register');
	}

	function handleTierChange(tier: SecurityTier) {
		selectedTier = tier;
	}

	function getTierLabel(tier: SecurityTier): string {
		if (tier === 'high') return 'Hoch';
		if (tier === 'convenience') return 'Bequem';
		return 'Standard';
	}
</script>

{#if $isAuthenticated}
	<Loading message="Lade..." />
{:else}
	<div
		class="min-h-screen bg-gradient-to-br from-purple-50 to-blue-50 dark:from-gray-900 dark:to-gray-800"
	>
		<div class="container mx-auto max-w-5xl px-4 py-8">
			<!-- Header -->
			<div class="mb-8 text-center">
				<h1 class="mb-2 text-4xl font-bold text-gray-800 dark:text-white">Login Prioliste</h1>
				<p class="text-gray-600 dark:text-gray-300">Kindergarten Prioliste eingeben</p>
			</div>

			<!-- Main Card -->
			<div class="mx-auto max-w-md rounded-2xl bg-white p-6 shadow-xl dark:bg-gray-800">
				<form class="space-y-6" on:submit|preventDefault={handleLogin}>
					<!-- Username -->
					<label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
						Username
						<input
							type="text"
							bind:value={username}
							required
							class="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm
								   focus:border-blue-500 focus:ring-2 focus:ring-blue-500 focus:outline-none
								   dark:border-gray-600 dark:bg-gray-700 dark:text-white"
						/>
					</label>

					<!-- Password -->
					<label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
						Passwort
						<input
							type="password"
							bind:value={password}
							required
							class="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm
								   focus:border-blue-500 focus:ring-2 focus:ring-blue-500 focus:outline-none
								   dark:border-gray-600 dark:bg-gray-700 dark:text-white"
						/>
					</label>

					<!-- Login Button -->
					<button
						type="submit"
						class="w-full transform rounded-xl bg-gradient-to-r from-purple-600 to-blue-600 py-3 font-semibold
							   text-white shadow-lg transition hover:scale-105 disabled:cursor-not-allowed disabled:opacity-50"
					>
						Anmelden
					</button>

					<!-- Register Button -->
					<button
						type="button"
						class="w-full rounded-xl bg-gray-600 py-3 font-semibold text-white shadow-lg transition-colors hover:bg-gray-700"
						on:click={goToRegister}
					>
						Registrieren
					</button>

					<!-- Security Tier - Compact -->
					<div class="border-t border-gray-200 pt-4 dark:border-gray-700">
						<button
							type="button"
							on:click={() => (showTierSelector = !showTierSelector)}
							class="flex w-full items-center justify-between text-sm text-gray-600 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-200"
						>
							<span>Sicherheit: {getTierLabel(selectedTier)}</span>
							<span class="text-xs">{showTierSelector ? '▲' : '▼'}</span>
						</button>

						{#if showTierSelector}
							<div class="mt-3">
								<SecurityTierSelector {selectedTier} onChange={handleTierChange} />
							</div>
						{/if}
					</div>

					<!-- Error Message -->
					{#if error}
						<div
							class="mt-4 rounded-md bg-red-50 p-4 text-sm text-red-700 dark:bg-red-900/20 dark:text-red-400"
						>
							{error}
						</div>
					{/if}
				</form>
			</div>

			<!-- Footer -->
			<div class="mt-8 text-center">
				<div class="flex flex-wrap justify-center gap-4 text-sm text-gray-600 dark:text-gray-400">
					<a
						href="https://github.com/domidre/kigaprio"
						target="_blank"
						rel="noopener noreferrer"
						class="transition-colors hover:text-blue-600 dark:hover:text-blue-400"
					>
						GitHub
					</a>
					<span class="text-gray-400">•</span>
					<a href="/imprint" class="transition-colors hover:text-blue-600 dark:hover:text-blue-400">
						Impressum
					</a>
					<span class="text-gray-400">•</span>
					<a href="/privacy" class="transition-colors hover:text-blue-600 dark:hover:text-blue-400">
						Datenschutz
					</a>
				</div>
			</div>
		</div>
	</div>
{/if}
